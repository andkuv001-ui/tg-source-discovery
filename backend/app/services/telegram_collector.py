import asyncio
import json
from datetime import datetime, timezone

from telethon import TelegramClient
from telethon.errors import (
    FloodWaitError,
    UsernameInvalidError,
    UsernameNotOccupiedError,
    ChannelPrivateError,
    ChatAdminRequiredError,
)

from app.config import get_settings

settings = get_settings()

_client: TelegramClient | None = None


async def get_client() -> TelegramClient:
    global _client
    if _client is None:
        _client = TelegramClient(
            "tg_source_radar_session",
            settings.telethon_api_id,
            settings.telethon_api_hash,
        )
        if settings.telethon_session_string:
            await _client.start()
        else:
            await _client.start()
    return _client


async def fetch_source_metadata(username: str) -> dict | None:
    client = await get_client()
    try:
        entity = await client.get_entity(username)
        info = {
            "telegram_id": entity.id,
            "username": getattr(entity, "username", None),
            "title": getattr(entity, "title", None),
            "description": getattr(entity, "about", None),
            "source_type": _get_source_type(entity),
            "member_count": getattr(entity, "participants_count", None),
            "linked_chat_id": getattr(entity, "linked_chat_id", None) if hasattr(entity, "linked_chat_id") else None,
        }
        return info
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 5)
        return await fetch_source_metadata(username)
    except (UsernameInvalidError, UsernameNotOccupiedError):
        return {"username": username, "status": "dead"}
    except ChannelPrivateError:
        return {"username": username, "status": "private"}
    except Exception:
        return None


async def fetch_recent_messages(username: str, limit: int = 100) -> list[dict]:
    client = await get_client()
    try:
        entity = await client.get_entity(username)
        messages = []
        async for message in client.iter_messages(entity, limit=limit):
            msg_data = {
                "id": message.id,
                "date": message.date.isoformat(),
                "text": message.text or "",
                "views": message.views,
                "forwards": message.forwards,
            }
            if message.forward:
                fwd = message.forward
                if hasattr(fwd, "channel") and fwd.channel:
                    msg_data["forward_from"] = getattr(fwd.channel, "username", None)
                elif hasattr(fwd, "sender") and fwd.sender:
                    msg_data["forward_from"] = getattr(fwd.sender, "username", None)
            messages.append(msg_data)
        return messages
    except FloodWaitError as e:
        await asyncio.sleep(e.seconds + 5)
        return await fetch_recent_messages(username, limit)
    except Exception:
        return []


async def fetch_pinned_messages(username: str) -> list[dict]:
    client = await get_client()
    try:
        entity = await client.get_entity(username)
        messages = []
        async for message in client.iter_messages(entity, limit=10):
            if message.pinned:
                messages.append({
                    "id": message.id,
                    "date": message.date.isoformat(),
                    "text": message.text or "",
                })
        return messages
    except Exception:
        return []


async def fetch_channel_recommendations(username: str) -> list[dict]:
    client = await get_client()
    try:
        entity = await client.get_entity(username)
        recommendations = await client.get_entity_recommendations(entity.id)
        results = []
        for rec in recommendations:
            results.append({
                "username": getattr(rec, "username", None),
                "title": getattr(rec, "title", None),
                "telegram_id": rec.id,
            })
        return results
    except Exception:
        return []


async def collect_source_data(username: str, fetch_messages: bool = True) -> dict:
    metadata = await fetch_source_metadata(username)
    if not metadata or metadata.get("status") in ("dead", "private"):
        return metadata or {"username": username, "status": "dead"}

    metadata["recent_messages"] = []
    metadata["pinned_messages"] = []

    if fetch_messages:
        metadata["recent_messages"] = await fetch_recent_messages(username, limit=50)
        await asyncio.sleep(1)
        metadata["pinned_messages"] = await fetch_pinned_messages(username)
        metadata["has_pinned_messages"] = bool(metadata["pinned_messages"])

    metadata["recent_messages_fetched_at"] = datetime.now(timezone.utc).isoformat()
    return metadata


async def batch_collect(usernames: list[str], batch_size: int = 10, delay: float = 3.0) -> list[dict]:
    results = []
    for i in range(0, len(usernames), batch_size):
        batch = usernames[i:i + batch_size]
        tasks = [collect_source_data(u) for u in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in batch_results:
            if isinstance(result, dict):
                results.append(result)
        if i + batch_size < len(usernames):
            await asyncio.sleep(delay)
    return results


def _get_source_type(entity) -> str:
    if hasattr(entity, "megagroup") and entity.megagroup:
        return "supergroup"
    if hasattr(entity, "broadcast") and entity.broadcast:
        return "channel"
    return "group"
