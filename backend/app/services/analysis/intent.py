import json
import re
from app.llm.client import chat_completion
from app.llm.prompts import INTENT_ANALYSIS_SYSTEM

SEARCH_PATTERNS_RU = [
    r"ищу", r"нужен", r"нужна", r"нужно", r"поиск", r"подскажите", r"посоветуйте",
    r"где найти", r"как найти", r"рекомендуйте",
]
SEARCH_PATTERNS_EN = [
    r"looking for", r"need", r"find", r"recommend", r"search", r"anyone know",
    r"where can", r"how to find",
]
OFFER_PATTERNS_RU = [
    r"услуги", r"предлагаю", r"продажа", r"купить", r"цена", r"стоимость",
    r"заказать", r"выполню", r"сделаю", r"профессионал",
]
OFFER_PATTERNS_EN = [
    r"services", r"offering", r"for sale", r"buy", r"price", r"cost",
    r"order", r"professional", r"expert",
]
QUESTION_PATTERNS = [r"\?", r"?", r"как\s+вас", r"что\s+думаете", r"what\s+do\s+you\s+think"]


def analyze_intent_regex(messages: list[dict]) -> dict:
    search_count = 0
    offer_count = 0
    question_count = 0
    total = 0

    for msg in messages[:50]:
        text = msg.get("text", "").lower()
        if not text:
            continue
        total += 1

        for pattern in SEARCH_PATTERNS_RU + SEARCH_PATTERNS_EN:
            if re.search(pattern, text):
                search_count += 1
                break

        for pattern in OFFER_PATTERNS_RU + OFFER_PATTERNS_EN:
            if re.search(pattern, text):
                offer_count += 1
                break

        for pattern in QUESTION_PATTERNS:
            if re.search(pattern, text):
                question_count += 1
                break

    if total == 0:
        return {
            "primary_intent": "information",
            "commercial_intent_score": 0.0,
            "lead_potential": 0.0,
            "search_ratio": 0.0,
            "offer_ratio": 0.0,
            "question_ratio": 0.0,
        }

    search_ratio = search_count / total
    offer_ratio = offer_count / total
    question_ratio = question_count / total

    if search_ratio > 0.3:
        primary = "discussion"
        commercial = min(search_ratio * 1.5, 1.0)
    elif offer_ratio > 0.3:
        primary = "marketplace"
        commercial = min(offer_ratio * 2, 1.0)
    elif question_ratio > 0.3:
        primary = "support"
        commercial = 0.2
    else:
        primary = "information"
        commercial = 0.1

    return {
        "primary_intent": primary,
        "commercial_intent_score": round(commercial, 2),
        "lead_potential": round(commercial * 0.8, 2),
        "search_ratio": round(search_ratio, 2),
        "offer_ratio": round(offer_ratio, 2),
        "question_ratio": round(question_ratio, 2),
    }


async def analyze_intent(title: str, description: str, messages: list[dict]) -> dict:
    regex_result = analyze_intent_regex(messages)

    sample_texts = [m.get("text", "")[:500] for m in messages[:10] if m.get("text")]
    message_sample = "\n".join(sample_texts[:5])

    user_prompt = f"""Source title: {title}
Source description: {description[:500]}
Search/offer/question ratios: search={regex_result['search_ratio']}, offer={regex_result['offer_ratio']}, question={regex_result['question_ratio']}
Recent messages sample:
{message_sample}"""

    try:
        raw = await chat_completion(
            [
                {"role": "system", "content": INTENT_ANALYSIS_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        llm_result = json.loads(raw)

        return {
            "primary_intent": llm_result.get("primary_intent", regex_result["primary_intent"]),
            "commercial_intent_score": llm_result.get("commercial_intent_score", regex_result["commercial_intent_score"]),
            "lead_potential": llm_result.get("lead_potential", regex_result["lead_potential"]),
            "buyer_signals": llm_result.get("buyer_signals", []),
            "seller_signals": llm_result.get("seller_signals", []),
            "engagement_type": llm_result.get("engagement_type", "passive"),
            "search_ratio": regex_result["search_ratio"],
            "offer_ratio": regex_result["offer_ratio"],
            "question_ratio": regex_result["question_ratio"],
        }
    except Exception:
        return regex_result
