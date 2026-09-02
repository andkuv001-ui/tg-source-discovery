from app.services.analysis import analyze_source
from app.services.scoring import calculate_total_score, PRESET_WEIGHTS


async def full_source_analysis(
    title: str,
    description: str,
    messages: list[dict],
    query_topics: list[str] = None,
    query_context: str = "",
    scoring_profile: str = "lead_generation",
    target_countries: list[str] = None,
    target_cities: list[str] = None,
    target_languages: list[str] = None,
    target_audience: list[str] = None,
    target_intent: list[str] = None,
    commercial_target: bool = False,
) -> dict:
    analyses = await analyze_source(
        title=title,
        description=description,
        messages=messages,
        query_topics=query_topics,
        query_context=query_context,
    )

    weights = PRESET_WEIGHTS.get(scoring_profile, PRESET_WEIGHTS["lead_generation"])

    source_data = {
        "title": title,
        "description": description,
        "member_count": None,
        "topic_analysis": analyses["topic_analysis"],
        "language_analysis": analyses["language_analysis"],
        "geography_analysis": analyses["geography_analysis"],
        "intent_analysis": analyses["intent_analysis"],
        "audience_analysis": analyses["audience_analysis"],
        "activity_analysis": analyses["activity_analysis"],
    }

    total_score, breakdown = calculate_total_score(
        source_data=source_data,
        query_topics=query_topics,
        target_countries=target_countries,
        target_cities=target_cities,
        target_languages=target_languages,
        target_audience=target_audience,
        target_intent=target_intent,
        commercial_target=commercial_target,
        weights=weights,
    )

    return {
        **analyses,
        "total_score": total_score,
        "score_breakdown": breakdown,
        "scoring_profile": scoring_profile,
    }
