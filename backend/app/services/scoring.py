from dataclasses import dataclass


@dataclass
class ScoringWeights:
    topic: float = 0.30
    geography: float = 0.15
    language: float = 0.10
    audience: float = 0.15
    intent: float = 0.10
    activity: float = 0.10
    freshness: float = 0.05
    commercial: float = 0.07
    quality: float = 0.03


DEFAULT_WEIGHTS = ScoringWeights()

PRESET_WEIGHTS = {
    "lead_generation": ScoringWeights(topic=0.30, geography=0.15, language=0.10, audience=0.15, intent=0.10, activity=0.10, freshness=0.05, commercial=0.07, quality=0.03),
    "market_research": ScoringWeights(topic=0.35, geography=0.15, language=0.10, audience=0.10, intent=0.05, activity=0.10, freshness=0.05, commercial=0.03, quality=0.07),
    "news_monitoring": ScoringWeights(topic=0.25, geography=0.20, language=0.15, audience=0.05, intent=0.05, activity=0.15, freshness=0.10, commercial=0.00, quality=0.05),
}


def score_topic(analysis: dict, query_topics: list[str]) -> float:
    if not analysis:
        return 0.0
    relevance = analysis.get("relevance_to_query", 0.0)
    consistency = analysis.get("topic_consistency", 0.0)
    return min(relevance * 70 + consistency * 30, 100)


def score_geography(analysis: dict, target_countries: list[str], target_cities: list[str]) -> float:
    if not analysis:
        return 0.0
    countries = [c.lower() for c in analysis.get("countries", [])]
    cities = [c.lower() for c in analysis.get("cities", [])]
    specificity = analysis.get("specificity", "global")

    country_overlap = len(set(countries) & set(c.lower() for c in target_countries))
    city_overlap = len(set(cities) & set(c.lower() for c in target_cities))

    if not target_countries and not target_cities:
        return 70.0

    score = 0.0
    if target_countries:
        if country_overlap > 0:
            score += (country_overlap / len(target_countries)) * 80
        elif countries:
            score += 30.0
    if target_cities:
        if city_overlap > 0:
            score += (city_overlap / len(target_cities)) * 20
        elif cities:
            score += 5.0

    specificity_bonus = {"city": 10, "regional": 5, "country": 8, "global": 0}
    score += specificity_bonus.get(specificity, 0)
    return min(score, 100)


def score_language(analysis: dict, target_languages: list[str]) -> float:
    if not analysis:
        return 0.0
    primary = analysis.get("primary_language")
    supported = analysis.get("supported", False)
    distribution = analysis.get("distribution", {})

    if not target_languages:
        return 80.0 if supported else 30.0
    if primary and primary.lower() in [l.lower() for l in target_languages]:
        lang_match = distribution.get(primary, 0)
        return min(60 + lang_match * 40, 100)
    for lang, ratio in distribution.items():
        if lang.lower() in [l.lower() for l in target_languages]:
            return min(40 + ratio * 40, 80)
    return 10.0 if not supported else 30.0


def score_audience(analysis: dict, target_audience: list[str]) -> float:
    if not analysis:
        return 50.0
    audience_type = analysis.get("audience_type", "mixed")
    confidence = analysis.get("confidence", 0.0)
    if not target_audience:
        return 60.0
    if audience_type.lower() in [a.lower() for a in target_audience]:
        return min(70 + confidence * 30, 100)
    return max(30, 60 - confidence * 30)


def score_intent(analysis: dict, target_intent: list[str], commercial_target: bool = False) -> float:
    if not analysis:
        return 50.0
    commercial_score = analysis.get("commercial_intent_score", 0)
    lead_potential = analysis.get("lead_potential", 0)
    if commercial_target:
        return min(commercial_score * 60 + lead_potential * 40, 100)
    return min(50 + commercial_score * 30, 90)


def score_activity(analysis: dict) -> float:
    if not analysis:
        return 30.0
    messages_per_day = analysis.get("messages_per_day", 0)
    freshness = analysis.get("freshness", "unknown")
    trend = analysis.get("activity_trend", "unknown")

    score = 0.0
    if messages_per_day >= 50:
        score += 40
    elif messages_per_day >= 20:
        score += 35
    elif messages_per_day >= 5:
        score += 25
    elif messages_per_day >= 1:
        score += 15
    else:
        score += 5

    freshness_scores = {
        "very_fresh": 30, "fresh": 28, "recent": 25,
        "active": 20, "moderate": 15, "stale": 5, "unknown": 10,
    }
    score += freshness_scores.get(freshness, 10)
    trend_scores = {"growing": 20, "stable": 15, "declining": 5, "unknown": 10}
    score += trend_scores.get(trend, 10)
    return min(score, 100)


def score_freshness(analysis: dict) -> float:
    if not analysis:
        return 30.0
    last_age = analysis.get("last_message_age_days")
    if last_age is None:
        return 20.0
    if last_age <= 1:
        return 100.0
    elif last_age <= 3:
        return 85.0
    elif last_age <= 7:
        return 70.0
    elif last_age <= 14:
        return 55.0
    elif last_age <= 30:
        return 40.0
    elif last_age <= 90:
        return 25.0
    else:
        return 10.0


def score_commercial(analysis: dict) -> float:
    if not analysis:
        return 20.0
    commercial = analysis.get("commercial_intent_score", 0)
    lead = analysis.get("lead_potential", 0)
    return min(commercial * 60 + lead * 40, 100)


def score_quality(source_data: dict) -> float:
    score = 50.0
    member_count = source_data.get("member_count", 0)
    if member_count and member_count > 10000:
        score += 15
    elif member_count and member_count > 1000:
        score += 10
    elif member_count and member_count > 100:
        score += 5
    title = source_data.get("title", "")
    description = source_data.get("description", "")
    if title and len(title) > 5:
        score += 10
    if description and len(description) > 20:
        score += 10
    return min(score, 100)


def calculate_total_score(
    source_data: dict,
    query_topics: list[str] = None,
    target_countries: list[str] = None,
    target_cities: list[str] = None,
    target_languages: list[str] = None,
    target_audience: list[str] = None,
    target_intent: list[str] = None,
    commercial_target: bool = False,
    weights: ScoringWeights = None,
) -> tuple[float, dict]:
    if weights is None:
        weights = DEFAULT_WEIGHTS

    breakdown = {
        "topic": score_topic(source_data.get("topic_analysis", {}), query_topics or []),
        "geography": score_geography(source_data.get("geography_analysis", {}), target_countries or [], target_cities or []),
        "language": score_language(source_data.get("language_analysis", {}), target_languages or []),
        "audience": score_audience(source_data.get("audience_analysis", {}), target_audience or []),
        "intent": score_intent(source_data.get("intent_analysis", {}), target_intent or [], commercial_target),
        "activity": score_activity(source_data.get("activity_analysis", {})),
        "freshness": score_freshness(source_data.get("activity_analysis", {})),
        "commercial": score_commercial(source_data.get("intent_analysis", {})),
        "quality": score_quality(source_data),
    }

    total = sum(
        breakdown[factor] * getattr(weights, factor, 0)
        for factor in breakdown
    )

    return round(total, 2), breakdown


def get_score_label(score: float) -> str:
    if score >= 80:
        return "highly_relevant"
    elif score >= 60:
        return "relevant"
    elif score >= 40:
        return "potentially_relevant"
    else:
        return "irrelevant"
