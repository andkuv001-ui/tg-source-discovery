import json
import re
from app.llm.client import chat_completion
from app.llm.prompts import AUDIENCE_ANALYSIS_SYSTEM

AUDIENCE_INDICATORS = {
    "professional": [
        r"специалист", r"профессионал", r"эксперт", r"инженер", r"девелопер",
        r"developer", r"engineer", r"specialist", r"professional", r"expert",
        r"consultant", r"консультант",
    ],
    "consumer": [
        r"ищу подрядчика", r"нужен мастер", r"где купить", r"посоветуйте",
        r"looking for contractor", r"need a plumber", r"where to buy",
        r"рекомендуйте",
    ],
    "business": [
        r"b2b", r"партнёрство", r"сотрудничество", r"дистрибьютор",
        r"partnership", r"distributor", r"wholesale", r"оптовик",
    ],
}


def analyze_audience_regex(messages: list[dict]) -> dict:
    audience_counts = {"professional": 0, "consumer": 0, "business": 0, "other": 0}

    for msg in messages[:50]:
        text = msg.get("text", "").lower()
        if not text:
            continue

        matched = False
        for atype, patterns in AUDIENCE_INDICATORS.items():
            for pattern in patterns:
                if re.search(pattern, text):
                    audience_counts[atype] += 1
                    matched = True
                    break
            if matched:
                break
        if not matched:
            audience_counts["other"] += 1

    total = sum(audience_counts.values())
    if total == 0:
        return {"audience_type": "mixed", "confidence": 0.0}

    dominant = max(audience_counts, key=audience_counts.get)
    confidence = audience_counts[dominant] / total

    return {
        "audience_type": dominant,
        "distribution": {k: round(v / total, 2) for k, v in audience_counts.items()},
        "confidence": round(confidence, 2),
    }


async def analyze_audience(title: str, description: str, messages: list[dict]) -> dict:
    regex_result = analyze_audience_regex(messages)

    sample_texts = [m.get("text", "")[:500] for m in messages[:10] if m.get("text")]
    message_sample = "\n".join(sample_texts[:5])

    user_prompt = f"""Source title: {title}
Source description: {description[:500]}
Detected audience type: {regex_result['audience_type']}
Recent messages sample:
{message_sample}"""

    try:
        raw = await chat_completion(
            [
                {"role": "system", "content": AUDIENCE_ANALYSIS_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        llm_result = json.loads(raw)

        return {
            "audience_type": llm_result.get("audience_type", regex_result["audience_type"]),
            "expertise_level": llm_result.get("expertise_level", "mixed"),
            "engagement_level": llm_result.get("engagement_level", "medium"),
            "professions": llm_result.get("professions", []),
            "demographics": llm_result.get("demographics", {}),
            "confidence": max(regex_result["confidence"], 0.5),
        }
    except Exception:
        return {
            "audience_type": regex_result["audience_type"],
            "confidence": regex_result["confidence"],
        }
