import json
import re
from collections import Counter

from app.llm.client import chat_completion
from app.llm.prompts import TOPIC_ANALYSIS_SYSTEM

STOP_WORDS_EN = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "shall", "should", "may", "might", "must", "can", "could", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them", "my", "your", "his", "its", "our", "their", "this", "that", "these", "those", "and", "but", "or", "nor", "not", "no", "so", "if", "then", "than", "too", "very", "just", "about", "above", "after", "again", "all", "also", "am", "an", "any", "at", "because", "before", "between", "both", "by", "each", "few", "more", "most", "other", "some", "such", "into", "only", "own", "same", "through", "to", "from", "in", "on", "of", "for", "with", "as", "at"}
STOP_WORDS_RU = {"и", "в", "во", "не", "что", "он", "на", "я", "с", "со", "как", "а", "то", "все", "она", "так", "его", "но", "да", "ты", "к", "у", "же", "вы", "за", "бы", "по", "только", "ее", "мне", "было", "вот", "от", "меня", "еще", "нет", "о", "из", "ему", "теперь", "когда", "даже", "ну", "ли", "если", "или", "ни", "быть", "был", "него", "до", "вас", "нибудь", "опять", "уж", "вам", "ведь", "там", "потом", "себя", "ничего", "ей", "может", "они", "тут", "где", "есть", "надо", "ней", "для", "мы", "тебя", "их", "чем", "была", "сам", "чтоб", "без", "будто", "чего", "раз", "тоже", "себе", "под", "будет", "ж", "тогда", "кто", "этот", "того", "потому", "этого", "какой", "совсем", "ним", "здесь", "этом", "один", "почти", "мой", "тем", "чтобы", "нее", "сейчас", "были", "куда", "зачем", "всех", "никогда", "можно", "при", "наконец", "два", "об", "другой", "хоть", "после", "над", "больше", "тот", "через", "эти", "нас", "про", "всего", "них", "какая", "много", "разве", "три", "эту", "моя", "впрочем", "хорошо", "свою", "этой", "перед", "иногда", "лучше", "чуть", "том", "нельзя", "такой", "им", "более", "всегда", "уже", "конечно", "всю", "между"}


def extract_keywords(texts: list[str], top_n: int = 15) -> list[str]:
    all_words = []
    for text in texts:
        words = re.findall(r'\b[a-zA-Zа-яА-ЯёЁ]{3,}\b', text.lower())
        all_words.extend(w for w in words if w not in STOP_WORDS_EN and w not in STOP_WORDS_RU)

    counter = Counter(all_words)
    return [word for word, _ in counter.most_common(top_n)]


async def analyze_topic(title: str, description: str, messages: list[dict], query_topics: list[str] = None) -> dict:
    sample_texts = [m.get("text", "")[:500] for m in messages[:15] if m.get("text")]
    message_sample = "\n".join(sample_texts[:8])
    all_text = f"{title} {description} {message_sample}"

    keywords = extract_keywords(sample_texts + [title, description])

    topics_detected = []
    if query_topics:
        all_text_lower = all_text.lower()
        for topic in query_topics:
            if topic.lower() in all_text_lower:
                topics_detected.append(topic)

    user_prompt = f"""Source title: {title}
Source description: {description[:500]}
Keywords: {', '.join(keywords)}
Detected query topics: {', '.join(topics_detected)}
Recent messages sample:
{message_sample}"""

    try:
        raw = await chat_completion(
            [
                {"role": "system", "content": TOPIC_ANALYSIS_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        llm_result = json.loads(raw)

        return {
            "primary_topic": llm_result.get("primary_topic", keywords[0] if keywords else ""),
            "subtopics": llm_result.get("subtopics", [])[:5],
            "relevance_to_query": llm_result.get("relevance_to_query", 0.5),
            "topic_consistency": llm_result.get("topic_consistency", 0.5),
            "keywords": keywords[:10],
            "categories": llm_result.get("categories", []),
        }
    except Exception:
        return {
            "primary_topic": keywords[0] if keywords else "",
            "subtopics": [],
            "relevance_to_query": 0.3,
            "topic_consistency": 0.3,
            "keywords": keywords[:10],
            "categories": [],
        }
