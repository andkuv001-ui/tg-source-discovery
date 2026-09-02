import json
import re
from dataclasses import dataclass, field

from app.llm.client import chat_completion
from app.llm.prompts import (
    QUERY_UNDERSTANDING_SYSTEM,
    QUERY_UNDERSTANDING_USER,
)


COUNTRIES = {
    "germany": ["germany", "deutschland", "german", "de", "немец", "германия"],
    "russia": ["russia", "russian", "ru", "россия", "русский"],
    "usa": ["usa", "united states", "american", "us", "сша", "америка"],
    "uk": ["uk", "united kingdom", "british", "england", "великобритания"],
    "uae": ["uae", "united arab emirates", "dubai", "абу", "оаэ"],
    "france": ["france", "french", "fr", "франция"],
    "ukraine": ["ukraine", "ukrainian", "ua", "украина"],
    "kazakhstan": ["kazakhstan", "kz", "казахстан"],
    "israel": ["israel", "il", "израиль"],
    "canada": ["canada", "ca", "канада"],
}

CITIES = {
    "berlin": "germany", "munich": "germany", "hamburg": "germany",
    "moscow": "russia", "spb": "russia", "saint petersburg": "russia",
    "new york": "usa", "san francisco": "usa", "los angeles": "usa",
    "london": "uk", "manchester": "uk",
    "dubai": "uae", "abu dhabi": "uae",
    "paris": "france", "lyon": "france",
    "kyiv": "ukraine", "kiev": "ukraine",
    "almaty": "kazakhstan", "astana": "kazakhstan",
    "tel aviv": "israel", "jerusalem": "israel",
    "toronto": "canada", "vancouver": "canada",
}

LANGUAGES = {
    "ru": ["russian", "русский", "по-русски"],
    "en": ["english", "английский", "по-английски"],
    "de": ["german", "немецкий", "по-немецки"],
    "uk": ["ukrainian", "украинский"],
    "fr": ["french", "французский"],
    "he": ["hebrew", "иврит"],
    "ar": ["arabic", "арабский"],
    "tr": ["turkish", "турецкий"],
    "zh": ["chinese", "китайский"],
}

SOURCE_TYPES = {
    "channel": ["channel", "канал"],
    "group": ["group", "группа", "чат"],
    "supergroup": ["supergroup", "супергруппа"],
}


@dataclass
class QueryModel:
    topics: list[str] = field(default_factory=list)
    subtopics: list[str] = field(default_factory=list)
    related_topics: list[str] = field(default_factory=list)
    audience: list[str] = field(default_factory=list)
    intent: list[str] = field(default_factory=list)
    commercial_intent: bool = False
    countries: list[str] = field(default_factory=list)
    cities: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    source_types: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "topics": self.topics,
            "subtopics": self.subtopics,
            "related_topics": self.related_topics,
            "audience": self.audience,
            "intent": self.intent,
            "commercial_intent": self.commercial_intent,
            "countries": self.countries,
            "cities": self.cities,
            "languages": self.languages,
            "source_types": self.source_types,
        }


def extract_deterministic(query: str) -> QueryModel:
    model = QueryModel()
    query_lower = query.lower()

    for country, keywords in COUNTRIES.items():
        for kw in keywords:
            if kw in query_lower:
                if country not in model.countries:
                    model.countries.append(country)

    for city, country in CITIES.items():
        if city in query_lower:
            if city not in model.cities:
                model.cities.append(city)
            if country not in model.countries:
                model.countries.append(country)

    for lang, keywords in LANGUAGES.items():
        for kw in keywords:
            if kw in query_lower:
                if lang not in model.languages:
                    model.languages.append(lang)

    for stype, keywords in SOURCE_TYPES.items():
        for kw in keywords:
            if kw in query_lower:
                if stype not in model.source_types:
                    model.source_types.append(stype)

    if any(w in query_lower for w in ["купить", "продать", "услуги", "заказать", "hire", "buy", "sell", "service", "price", "цена", "lead", "b2b"]):
        model.commercial_intent = True

    words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]{3,}\b', query)
    model.topics = list(set(w.lower() for w in words if len(w) > 3))[:5]

    return model


async def understand_query(query: str) -> QueryModel:
    deterministic = extract_deterministic(query)

    messages = [
        {"role": "system", "content": QUERY_UNDERSTANDING_SYSTEM},
        {"role": "user", "content": QUERY_UNDERSTANDING_USER.format(query=query)},
    ]

    try:
        raw = await chat_completion(messages, response_format={"type": "json_object"}, temperature=0.2)
        llm_data = json.loads(raw)

        for t in llm_data.get("topics", []):
            if t not in deterministic.topics:
                deterministic.topics.append(t)

        for t in llm_data.get("subtopics", []):
            if t not in deterministic.subtopics:
                deterministic.subtopics.append(t)

        for t in llm_data.get("related_topics", []):
            if t not in deterministic.related_topics:
                deterministic.related_topics.append(t)

        for a in llm_data.get("audience", []) if isinstance(llm_data.get("audience"), list) else [llm_data.get("audience", "")]:
            if a and a not in deterministic.audience:
                deterministic.audience.append(a)

        for i in llm_data.get("intent", []) if isinstance(llm_data.get("intent"), list) else [llm_data.get("intent", "")]:
            if i and i not in deterministic.intent:
                deterministic.intent.append(i)

        if "commercial_intent" in llm_data:
            deterministic.commercial_intent = llm_data["commercial_intent"]

        for c in llm_data.get("countries", []) if isinstance(llm_data.get("countries"), list) else []:
            if c and c not in deterministic.countries:
                deterministic.countries.append(c.lower())

        for c in llm_data.get("cities", []) if isinstance(llm_data.get("cities"), list) else []:
            if c and c not in deterministic.cities:
                deterministic.cities.append(c.lower())

        for l in llm_data.get("languages", []) if isinstance(llm_data.get("languages"), list) else []:
            if l and l not in deterministic.languages:
                deterministic.languages.append(l.lower())

    except Exception:
        pass

    return deterministic
