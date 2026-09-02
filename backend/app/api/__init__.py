from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, DiscoveryRun, Source, SourceScore, SourceReview, ScoringProfile, DiscoveryEvent
from app.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    DiscoveryRunResponse, SourceResponse, SourceScoreResponse,
    SourceReviewCreate, SourceReviewResponse,
    ScoringProfileResponse, ScoringProfileCreate,
    DiscoveryEventResponse, GraphData, GraphNode, GraphEdge,
    ExportFormat, StatsResponse,
)
from app.tasks.discovery_tasks import run_discovery_pipeline

router = APIRouter(prefix="/api")


@router.post("/projects", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, db: AsyncSession = Depends(get_db)):
    project = Project(**data.model_dump())
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    status: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    query = query.order_by(desc(Project.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: UUID, data: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/projects/{project_id}")
async def delete_project(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
    return {"ok": True}


@router.post("/projects/{project_id}/discover", response_model=DiscoveryRunResponse)
async def start_discovery(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    run = DiscoveryRun(project_id=project_id, status="pending")
    db.add(run)
    await db.commit()
    await db.refresh(run)

    run_discovery_pipeline.delay(str(run.id))
    return run


@router.get("/projects/{project_id}/runs", response_model=list[DiscoveryRunResponse])
async def list_runs(project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DiscoveryRun)
        .where(DiscoveryRun.project_id == project_id)
        .order_by(desc(DiscoveryRun.created_at))
    )
    return result.scalars().all()


@router.get("/runs/{run_id}", response_model=DiscoveryRunResponse)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DiscoveryRun).where(DiscoveryRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DiscoveryRun).where(DiscoveryRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status not in ("pending", "running"):
        raise HTTPException(status_code=400, detail="Run is not cancellable")
    run.status = "cancelled"
    await db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/sources")
async def list_project_sources(
    project_id: UUID,
    min_score: float = Query(0, ge=0, le=100),
    max_score: float = Query(100, ge=0, le=100),
    source_type: str = Query(None),
    status: str = Query(None),
    language: str = Query(None),
    sort_by: str = Query("total_score", pattern="^(total_score|member_count|freshness|discovered_at)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Source, SourceScore)
        .join(SourceScore, Source.id == SourceScore.source_id)
        .where(SourceScore.project_id == project_id)
        .where(SourceScore.total_score >= min_score)
        .where(SourceScore.total_score <= max_score)
    )

    if source_type:
        query = query.where(Source.source_type == source_type)
    if status:
        query = query.where(Source.status == status)

    sort_column = getattr(SourceScore, sort_by, SourceScore.total_score)
    query = query.order_by(desc(sort_column)).offset(offset).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "source": {
                "id": str(source.id),
                "telegram_id": source.telegram_id,
                "username": source.username,
                "title": source.title,
                "source_type": source.source_type,
                "member_count": source.member_count,
                "status": source.status,
            },
            "score": {
                "total": score.total_score,
                "breakdown": score.breakdown,
                "profile": score.scoring_profile,
            },
        }
        for source, score in rows
    ]


@router.get("/sources/{source_id}", response_model=SourceResponse)
async def get_source(source_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.get("/sources/{source_id}/score")
async def get_source_score(source_id: UUID, project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SourceScore)
        .where(SourceScore.source_id == source_id)
        .where(SourceScore.project_id == project_id)
        .order_by(desc(SourceScore.scored_at))
        .limit(1)
    )
    score = result.scalar_one_or_none()
    if not score:
        raise HTTPException(status_code=404, detail="Score not found")
    return {"total": score.total_score, "breakdown": score.breakdown, "profile": score.scoring_profile}


@router.get("/sources/{source_id}/related")
async def get_related_sources(source_id: UUID, db: AsyncSession = Depends(get_db)):
    from app.models import SourceLink
    result = await db.execute(
        select(SourceLink)
        .where((SourceLink.source_id == source_id) | (SourceLink.target_source_id == source_id))
    )
    links = result.scalars().all()

    related_ids = set()
    for link in links:
        if str(link.source_id) == str(source_id):
            related_ids.add(link.target_source_id)
        else:
            related_ids.add(link.source_id)

    if not related_ids:
        return []

    related_result = await db.execute(select(Source).where(Source.id.in_(related_ids)))
    return related_result.scalars().all()


@router.post("/sources/{source_id}/review", response_model=SourceReviewResponse)
async def review_source(source_id: UUID, data: SourceReviewCreate, project_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Source).where(Source.id == source_id))
    source = result.scalar_one_or_none()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    review = SourceReview(source_id=source_id, project_id=project_id, action=data.action, reason=data.reason)
    db.add(review)

    if data.action == "approve":
        source.status = "approved"
    elif data.action == "reject":
        source.status = "rejected"

    await db.commit()
    await db.refresh(review)
    return review


@router.post("/projects/{project_id}/sources/manual")
async def add_manual_source(project_id: UUID, username: str, db: AsyncSession = Depends(get_db)):
    from app.services.telegram_collector import collect_source_data

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    source_data = await collect_source_data(username)
    if not source_data or source_data.get("status") == "dead":
        raise HTTPException(status_code=400, detail="Could not fetch source data")

    existing = await db.execute(select(Source).where(Source.telegram_id == source_data.get("telegram_id")))
    existing_source = existing.scalar_one_or_none()

    if existing_source:
        return {"id": str(existing_source.id), "status": "exists"}

    source = Source(
        telegram_id=source_data.get("telegram_id"),
        username=source_data.get("username"),
        title=source_data.get("title"),
        description=source_data.get("description"),
        source_type=source_data.get("source_type"),
        member_count=source_data.get("member_count"),
        recent_messages=source_data.get("recent_messages", []),
        pinned_messages=source_data.get("pinned_messages", []),
        status="discovered",
    )
    db.add(source)
    await db.commit()
    await db.refresh(source)
    return {"id": str(source.id), "status": "created"}


@router.get("/projects/{project_id}/graph", response_model=GraphData)
async def get_project_graph(project_id: UUID, db: AsyncSession = Depends(get_db)):
    from app.models import SourceLink

    result = await db.execute(
        select(Source, SourceScore)
        .join(SourceScore, Source.id == SourceScore.source_id)
        .where(SourceScore.project_id == project_id)
        .where(SourceScore.total_score >= 40)
        .order_by(desc(SourceScore.total_score))
        .limit(100)
    )
    scored_sources = result.all()

    source_ids = {source.id for source, _ in scored_sources}

    links_result = await db.execute(
        select(SourceLink)
        .where(SourceLink.source_id.in_(source_ids))
        .where(SourceLink.target_source_id.in_(source_ids))
    )
    links = links_result.scalars().all()

    score_map = {source.id: score.total_score for source, score in scored_sources}

    nodes = [
        GraphNode(
            id=str(source.id),
            label=source.title or source.username or str(source.telegram_id),
            size=source.member_count or 100,
            color=_score_color(score_map.get(source.id, 0)),
            score=score_map.get(source.id),
        )
        for source, _ in scored_sources
    ]

    edges = [
        GraphEdge(
            source=str(link.source_id),
            target=str(link.target_source_id),
            edge_type=link.edge_type,
            confidence=link.confidence,
        )
        for link in links
    ]

    return GraphData(nodes=nodes, edges=edges)


def _score_color(score: float) -> str:
    if score >= 80:
        return "#22c55e"
    elif score >= 60:
        return "#eab308"
    elif score >= 40:
        return "#f97316"
    else:
        return "#ef4444"


@router.get("/projects/{project_id}/export")
async def export_sources(
    project_id: UUID,
    format: str = Query("json", pattern="^(csv|json)$"),
    min_score: float = Query(0, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Source, SourceScore)
        .join(SourceScore, Source.id == SourceScore.source_id)
        .where(SourceScore.project_id == project_id)
        .where(SourceScore.total_score >= min_score)
        .order_by(desc(SourceScore.total_score))
    )
    rows = result.all()

    if format == "json":
        return [
            {
                "chat_username": source.username,
                "chat_title": source.title,
                "chat_type": source.source_type,
                "telegram_id": source.telegram_id,
                "member_count": source.member_count,
                "score": score.total_score,
                "breakdown": score.breakdown,
            }
            for source, score in rows
        ]
    else:
        import csv
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "chat_username", "chat_title", "chat_type", "telegram_id", "member_count", "score"
        ])
        writer.writeheader()
        for source, score in rows:
            writer.writerow({
                "chat_username": source.username,
                "chat_title": source.title,
                "chat_type": source.source_type,
                "telegram_id": source.telegram_id,
                "member_count": source.member_count,
                "score": score.total_score,
            })
        return {"csv": output.getvalue()}


@router.get("/scoring-profiles", response_model=list[ScoringProfileResponse])
async def list_scoring_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScoringProfile))
    return result.scalars().all()


@router.post("/scoring-profiles", response_model=ScoringProfileResponse)
async def create_scoring_profile(data: ScoringProfileCreate, db: AsyncSession = Depends(get_db)):
    profile = ScoringProfile(**data.model_dump())
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/runs/{run_id}/events", response_model=list[DiscoveryEventResponse])
async def get_run_events(run_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(DiscoveryEvent)
        .where(DiscoveryEvent.discovery_run_id == run_id)
        .order_by(DiscoveryEvent.created_at)
    )
    return result.scalars().all()


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    sources_count = await db.execute(select(func.count(Source.id)))
    projects_count = await db.execute(select(func.count(Project.id)))
    runs_count = await db.execute(select(func.count(DiscoveryRun.id)))

    status_counts = await db.execute(
        select(Source.status, func.count(Source.id)).group_by(Source.status)
    )
    sources_by_status = {row[0]: row[1] for row in status_counts.all()}

    avg_result = await db.execute(select(func.avg(SourceScore.total_score)))
    avg_score = avg_result.scalar()

    return StatsResponse(
        total_sources=sources_count.scalar() or 0,
        total_projects=projects_count.scalar() or 0,
        total_runs=runs_count.scalar() or 0,
        sources_by_status=sources_by_status,
        avg_score=round(avg_score, 2) if avg_score else None,
    )
