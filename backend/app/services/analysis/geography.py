import re
from app.llm.client import chat_completion
from app.llm.prompts import GEOGRAPHY_ANALYSIS_SYSTEM

COUNTRY_KEYWORDS = {
    "germany": ["germany", "german", "deutschland", "de", "berlin", "munich", "hamburg", "german", "deutschen"],
    "russia": ["russia", "russian", "ru", "moscow", "saint petersburg", "россия", "россий", "москв"],
    "usa": ["usa", "united states", "american", "new york", "california", "texas"],
    "uk": ["uk", "united kingdom", "british", "london", "england", "manchester"],
    "uae": ["uae", "dubai", "abu dhabi", "dubai", "оаэ", "дубай"],
    "france": ["france", "french", "paris", "lyon", "франц"],
    "ukraine": ["ukkraine", "ukrainian", "kyiv", "kiev", "одесса", "украин"],
    "kazakhstan": ["kazakhstan", "almaty", "astana", "казахстан"],
    "israel": ["israel", "israeli", "tel aviv", "jerusalem", "израил"],
    "canada": ["canada", "canadian", "toronto", "vancouver"],
}

PHONE_CODES = {
    "+49": "germany", "+7": "russia", "+1": "usa", "+44": "uk",
    "+971": "uae", "+33": "france", "+380": "ukkraine", "+7": "kazakhstan",
    "+972": "israel", "+1": "canada",
}

CURRENCY_SYMBOLS = {
    "€": "europe", "$": "usa", "₽": "russia", "£": "uk",
    "AED": "uae", "₸": "kazakhstan",
}


def analyze_geography_regex(title: str, description: str, messages: list[dict]) -> dict:
    combined = f"{title} {description} ".join(m.get("text", "") for m in messages[:20])
    combined_lower = combined.lower()

    countries = []
    for country, keywords in COUNTRY_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in combined_lower:
                if country not in countries:
                    countries.append(country)
                break

    for code, country in PHONE_CODES.items():
        if code in combined:
            if country not in countries:
                countries.append(country)

    for symbol, region in CURRENCY_SYMBOLS.items():
        if symbol in combined:
            if region == "europe" and "europe" not in countries:
                countries.append("europe")

    specificity = "global"
    if len(countries) == 1:
        specificity = "country"
    elif len(countries) > 1:
        specificity = "regional"

    return {
        "countries": countries[:5],
        "regions": [],
        "cities": [],
        "specificity": specificity,
        "confidence": min(0.3 + len(countries) * 0.15, 0.9),
    }


async def analyze_geography(title: str, description: str, messages: list[dict], query_context: str = "") -> dict:
    regex_result = analyze_geography_regex(title, description, messages)

    if regex_result["confidence"] >= 0.7:
        return regex_result

    sample_texts = [m.get("text", "")[:500] for m in messages[:10] if m.get("text")]
    message_sample = "\n".join(sample_texts[:5])

    user_prompt = f"""Source title: {title}
Source description: {description[:500]}
Recent messages sample:
{message_sample}

Query context: {query_context}"""

    try:
        raw = await chat_completion(
            [
                {"role": "system", "content": GEOGRAPHY_ANALYSIS_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        import json
        llm_result = json.loads(raw)

        countries = llm_result.get("countries", [])
        for c in countries:
            c_lower = c.lower()
            for country_name in COUNTRY_KEYWORDS:
                if country_name in c_lower or c_lower in country_name:
                    if country_name not in regex_result["countries"]:
                        regex_result["countries"].append(country_name)

        if llm_result.get("cities"):
            regex_result["cities"] = llm_result["cities"][:5]
        if llm_result.get("regions"):
            regex_result["regions"] = llm_result["regions"][:5]
        if llm_result.get("specificity"):
            regex_result["specificity"] = llm_result["specificity"]
        regex_result["confidence"] = max(regex_result["confidence"], llm_result.get("confidence", 0.5))

    except Exception:
        pass

    return regex_result
