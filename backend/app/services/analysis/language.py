from langdetect import detect, DetectorFactory
from collections import Counter

DetectorFactory.seed = 0

SUPPORTED_LANGUAGES = {"ru", "en", "de", "uk", "fr", "he", "ar", "tr", "zh"}


def analyze_language(messages: list[dict]) -> dict:
    if not messages:
        return {
            "primary_language": None,
            "distribution": {},
            "supported": False,
            "message_count": 0,
        }

    lang_counts = Counter()
    total = 0

    for msg in messages:
        text = msg.get("text", "").strip()
        if not text or len(text) < 10:
            continue
        try:
            lang = detect(text)
            lang_counts[lang] += 1
            total += 1
        except Exception:
            continue

    if total == 0:
        return {
            "primary_language": None,
            "distribution": {},
            "supported": False,
            "message_count": 0,
        }

    distribution = {lang: round(count / total, 2) for lang, count in lang_counts.most_common()}
    primary = lang_counts.most_common(1)[0][0]

    return {
        "primary_language": primary,
        "secondary_languages": [lang for lang, _ in lang_counts.most_common(3) if lang != primary],
        "distribution": distribution,
        "supported": primary in SUPPORTED_LANGUAGES,
        "message_count": total,
    }
