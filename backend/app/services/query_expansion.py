import json
import re
from dataclasses import dataclass, field
from typing import Any

from app.llm.client import chat_completion
from app.llm.prompts import QUERY_EXPANSION_SYSTEM, QUERY_EXPANSION_USER
from app.services.query_understanding import QueryModel

MAX_VARIANTS_PER_TYPE = 10
MAX_TOTAL_VARIANTS = 50


@dataclass
class QueryVariant:
    text: str
    variant_type: str
    priority: int = 5


def _normalize(text: str) -> str:
    return re.sub(r'\s+', ' ', text.lower().strip())


def _deduplicate(variants: list[QueryVariant]) -> list[QueryVariant]:
    seen = set()
    result = []
    for v in variants:
        norm = _normalize(v.text)
        if norm not in seen:
            seen.add(norm)
            result.append(v)
    return result


def _transliterate_cyrillic_to_latin(text: str) -> str:
    mapping = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    }
    result = []
    for ch in text.lower():
        result.append(mapping.get(ch, ch))
    return ''.join(result)


def _transliterate_latin_to_cyrillic(text: str) -> str:
    mapping = {
        'ya': 'я', 'yu': 'ю', 'yo': 'ё', 'zh': 'ж', 'kh': 'х',
        'ts': 'ц', 'ch': 'ч', 'sh': 'ш', 'shch': 'щ',
    }
    result = text.lower()
    for lat, cyr in sorted(mapping.items(), key=lambda x: -len(x[0])):
        result = result.replace(lat, cyr)
    return result


def deterministic_expand(query_model: QueryModel) -> list[QueryVariant]:
    variants = []
    topics = query_model.topics + query_model.subtopics

    for topic in topics[:3]:
        variants.append(QueryVariant(f'site:t.me "{topic}"', "platform", 8))
        variants.append(QueryVariant(f'"t.me/" {topic}', "platform", 7))
        variants.append(QueryVariant(f'@{topic.replace(" ", "_")}', "platform", 6))

    for topic in topics[:3]:
        latin = _transliterate_cyrillic_to_latin(topic)
        if latin != topic.lower():
            variants.append(QueryVariant(f'telegram {latin}', "transliteration", 6))
            variants.append(QueryVariant(f't.me {latin}', "transliteration", 7))

    for country in query_model.countries[:2]:
        for topic in topics[:2]:
            variants.append(QueryVariant(f'{topic} telegram {country}', "geo", 8))
            variants.append(QueryVariant(f'{topic} t.me {country}', "geo", 7))

    for city in query_model.cities[:2]:
        for topic in topics[:2]:
            variants.append(QueryVariant(f'{topic} telegram {city}', "geo", 7))

    variants.append(QueryVariant(f'telegram group {" ".join(topics[:2])}', "professional", 6))
    variants.append(QueryVariant(f'telegram channel {" ".join(topics[:2])}', "professional", 6))

    return variants[:MAX_TOTAL_VARIANTS]


async def llm_expand(query_model: QueryModel) -> list[QueryVariant]:
    messages = [
        {"role": "system", "content": QUERY_EXPANSION_SYSTEM},
        {"role": "user", "content": QUERY_EXPANSION_USER.format(query_model=json.dumps(query_model.to_dict()))},
    ]

    try:
        raw = await chat_completion(messages, response_format={"type": "json_object"}, temperature=0.5)
        data = json.loads(raw)
        llm_variants = data.get("variants", [])

        return [
            QueryVariant(text=v, variant_type="llm_generated", priority=5)
            for v in llm_variants[:15]
        ]
    except Exception:
        return []


async def expand_query(query_model: QueryModel) -> list[QueryVariant]:
    deterministic = deterministic_expand(query_model)
    llm_variants = await llm_expand(query_model)

    all_variants = deterministic + llm_variants
    deduped = _deduplicate(all_variants)

    by_type: dict[str, list[QueryVariant]] = {}
    for v in deduped:
        by_type.setdefault(v.variant_type, []).append(v)

    result = []
    for vtype, variants in by_type.items():
        sorted_v = sorted(variants, key=lambda x: -x.priority)
        result.extend(sorted_v[:MAX_VARIANTS_PER_TYPE])

    result = sorted(result, key=lambda x: -x.priority)[:MAX_TOTAL_VARIANTS]
    return result
