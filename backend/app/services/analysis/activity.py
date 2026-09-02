from datetime import datetime, timezone, timedelta
from collections import Counter


def analyze_activity(messages: list[dict]) -> dict:
    if not messages:
        return {
            "messages_per_day": 0,
            "unique_posters": 0,
            "freshness": "unknown",
            "activity_trend": "unknown",
            "last_message_age_days": None,
        }

    dates = []
    unique_posters = set()

    for msg in messages:
        date_str = msg.get("date")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                dates.append(dt)
            except Exception:
                pass

        poster = msg.get("from_user") or msg.get("sender_id")
        if poster:
            unique_posters.add(str(poster))

    if not dates:
        return {
            "messages_per_day": 0,
            "unique_posters": len(unique_posters),
            "freshness": "unknown",
            "activity_trend": "unknown",
            "last_message_age_days": None,
        }

    now = datetime.now(timezone.utc)
    dates.sort(reverse=True)

    last_msg_age = (now - dates[0]).days if dates else None

    if last_msg_age is not None:
        if last_msg_age <= 1:
            freshness = "very_fresh"
        elif last_msg_age <= 3:
            freshness = "fresh"
        elif last_msg_age <= 7:
            freshness = "recent"
        elif last_msg_age <= 30:
            freshness = "active"
        elif last_msg_age <= 90:
            freshness = "moderate"
        else:
            freshness = "stale"
    else:
        freshness = "unknown"

    if len(dates) >= 2:
        date_range = (dates[0] - dates[-1]).days + 1
        messages_per_day = len(dates) / max(date_range, 1)
    else:
        messages_per_day = 0

    trend = "stable"
    if len(dates) >= 6:
        midpoint = len(dates) // 2
        first_half = dates[:midpoint]
        second_half = dates[midpoint:]

        if first_half and second_half:
            first_range = (first_half[0] - first_half[-1]).days + 1
            second_range = (second_half[0] - second_half[-1]).days + 1

            first_rate = len(first_half) / max(first_range, 1)
            second_rate = len(second_half) / max(second_range, 1)

            if first_rate > second_rate * 1.3:
                trend = "growing"
            elif second_rate > first_rate * 1.3:
                trend = "declining"
            else:
                trend = "stable"

    return {
        "messages_per_day": round(messages_per_day, 1),
        "unique_posters": len(unique_posters),
        "freshness": freshness,
        "activity_trend": trend,
        "last_message_age_days": last_msg_age,
        "message_count": len(messages),
        "date_range_days": (dates[0] - dates[-1]).days + 1 if len(dates) >= 2 else 0,
    }
