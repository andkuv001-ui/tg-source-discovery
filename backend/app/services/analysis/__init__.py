from app.services.analysis.topic import analyze_topic
from app.services.analysis.language import analyze_language
from app.services.analysis.geography import analyze_geography
from app.services.analysis.intent import analyze_intent
from app.services.analysis.audience import analyze_audience
from app.services.analysis.activity import analyze_activity


async def analyze_source(
    title: str,
    description: str,
    messages: list[dict],
    query_topics: list[str] = None,
    query_context: str = "",
) -> dict:
    language = analyze_language(messages)
    geography = await analyze_geography(title, description, messages, query_context)
    topic = await analyze_topic(title, description, messages, query_topics or [])
    intent = await analyze_intent(title, description, messages)
    audience = await analyze_audience(title, description, messages)
    activity = analyze_activity(messages)

    return {
        "topic_analysis": topic,
        "language_analysis": language,
        "geography_analysis": geography,
        "intent_analysis": intent,
        "audience_analysis": audience,
        "activity_analysis": activity,
    }
