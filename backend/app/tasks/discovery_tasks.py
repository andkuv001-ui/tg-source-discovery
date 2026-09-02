import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks import celery_app
from app.database import async_session_factory
from app.models import DiscoveryRun, DiscoveryEvent, QueryVariant, DiscoveryCandidate, Source, Project
from app.services.query_understanding import understand_query
from app.services.query_expansion import expand_query
from app.services.discovery import get_all_providers
from app.services.telegram_collector import collect_source_data, batch_collect
from app.services.analysis import analyze_source
from app.services.scoring import calculate_total_score, PRESET_WEIGHTS


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _log_event(session: AsyncSession, run_id, event_type: str, payload: dict = None):
    event = DiscoveryEvent(
        discovery_run_id=run_id,
        event_type=event_type,
        payload=payload or {},
    )
    session.add(event)
    await session.commit()


async def _update_run(session: AsyncSession, run_id, **kwargs):
    await session.execute(
        update(DiscoveryRun).where(DiscoveryRun.id == run_id).values(**kwargs)
    )
    await session.commit()


@celery_app.task(name="discovery.run_pipeline", bind=True)
def run_discovery_pipeline(self, run_id: str):
    _run_async(_run_pipeline_impl(self, run_id))


async def _run_pipeline_impl(task, run_id: str):
    async with async_session_factory() as session:
        result = await session.execute(
            select(DiscoveryRun).where(DiscoveryRun.id == run_id)
        )
        run = result.scalar_one_or_none()
        if not run:
            return

        project_result = await session.execute(
            select(Project).where(Project.id == run.project_id)
        )
        project = project_result.scalar_one_or_none()
        if not project:
            return

        try:
            await _update_run(session, run_id, status="running", current_stage="understanding", started_at=datetime.now(timezone.utc))
            await _log_event(session, run_id, "run_started")

            query_model = await understand_query(project.query)
            project.query_model = query_model.to_dict()
            await session.commit()

            await _update_run(session, run_id, current_stage="expanding", progress=0.1)
            await _log_event(session, run_id, "query_expanded", {"topics": query_model.topics})

            variants = await expand_query(query_model)
            for v in variants:
                qv = QueryVariant(
                    discovery_run_id=run_id,
                    variant_text=v.text,
                    variant_type=v.variant_type,
                    priority=v.priority,
                )
                session.add(qv)
            await session.commit()

            await _update_run(session, run_id, current_stage="discovering", progress=0.2)
            providers = get_all_providers()
            all_candidates = []

            for provider in providers:
                for variant in variants:
                    try:
                        candidates = await provider.discover(variant.text, limit=10)
                        for c in candidates:
                            dc = DiscoveryCandidate(
                                discovery_run_id=run_id,
                                username=c.username,
                                telegram_id=c.telegram_id,
                                invite_link=c.invite_link,
                                url=c.url,
                                title=c.title,
                                source_type=c.source_type,
                                discovered_via=c.discovered_via,
                                discovery_query=variant.text,
                                confidence=c.confidence,
                                raw_data=c.raw_data,
                            )
                            session.add(dc)
                            all_candidates.append(c)
                        await _log_event(session, run_id, "provider_completed", {
                            "provider": provider.provider_name,
                            "query": variant.text,
                            "results": len(candidates),
                        })
                    except Exception as e:
                        await _log_event(session, run_id, "error", {
                            "provider": provider.provider_name,
                            "error": str(e),
                        })

            await session.commit()

            await _update_run(session, run_id, current_stage="fetching", progress=0.4)
            unique_usernames = list(set(c.username for c in all_candidates if c.username))[:100]
            source_data_list = await batch_collect(unique_usernames, batch_size=10, delay=3.0)

            await _update_run(session, run_id, current_stage="analyzing", progress=0.6)

            target_countries = query_model.countries
            target_cities = query_model.cities
            target_languages = query_model.languages
            target_audience = query_model.audience
            target_intent = query_model.intent

            for source_data in source_data_list:
                if not source_data or source_data.get("status") in ("dead", "private"):
                    continue

                existing = await session.execute(
                    select(Source).where(Source.telegram_id == source_data.get("telegram_id"))
                )
                existing_source = existing.scalar_one_or_none()

                if existing_source:
                    source_obj = existing_source
                else:
                    source_obj = Source(
                        telegram_id=source_data.get("telegram_id"),
                        username=source_data.get("username"),
                        title=source_data.get("title"),
                        description=source_data.get("description"),
                        source_type=source_data.get("source_type"),
                        member_count=source_data.get("member_count"),
                        linked_chat_id=source_data.get("linked_chat_id"),
                        has_pinned_messages=source_data.get("has_pinned_messages", False),
                        pinned_messages=source_data.get("pinned_messages", []),
                        recent_messages=source_data.get("recent_messages", []),
                        recent_messages_fetched_at=datetime.now(timezone.utc),
                        status="discovered",
                    )
                    session.add(source_obj)

                try:
                    analysis_result = await analyze_source(
                        title=source_data.get("title", ""),
                        description=source_data.get("description", ""),
                        messages=source_data.get("recent_messages", []),
                        query_topics=query_model.topics,
                        query_context=project.query,
                    )

                    source_obj.topic_analysis = analysis_result["topic_analysis"]
                    source_obj.language_analysis = analysis_result["language_analysis"]
                    source_obj.geography_analysis = analysis_result["geography_analysis"]
                    source_obj.intent_analysis = analysis_result["intent_analysis"]
                    source_obj.audience_analysis = analysis_result["audience_analysis"]
                    source_obj.activity_analysis = analysis_result["activity_analysis"]
                    source_obj.last_analyzed_at = datetime.now(timezone.utc)

                    total_score, breakdown = calculate_total_score(
                        source_data={**source_data, **analysis_result},
                        query_topics=query_model.topics,
                        target_countries=target_countries,
                        target_cities=target_cities,
                        target_languages=target_languages,
                        target_audience=target_audience,
                        target_intent=target_intent,
                        commercial_target=query_model.commercial_intent,
                        weights=PRESET_WEIGHTS.get(project.scoring_profile, PRESET_WEIGHTS["lead_generation"]),
                    )

                    await session.commit()

                    from app.models import SourceScore
                    score_obj = SourceScore(
                        source_id=source_obj.id,
                        project_id=project.id,
                        discovery_run_id=run_id,
                        total_score=total_score,
                        breakdown=breakdown,
                        scoring_profile=project.scoring_profile,
                    )
                    session.add(score_obj)
                    await session.commit()

                    await _log_event(session, run_id, "source_scored", {
                        "source_id": str(source_obj.id),
                        "score": total_score,
                    })

                except Exception as e:
                    await _log_event(session, run_id, "error", {
                        "source": source_data.get("username"),
                        "error": str(e),
                    })

            await _update_run(session, run_id, current_stage="completed", progress=1.0, status="completed", completed_at=datetime.now(timezone.utc))
            await _log_event(session, run_id, "run_completed", {"sources_found": len(source_data_list)})

        except Exception as e:
            await _update_run(session, run_id, status="failed", error=str(e))
            await _log_event(session, run_id, "error", {"error": str(e)})
