import re
from app.services.discovery.base import DiscoveryProvider, DiscoveryCandidate


TME_LINK_PATTERN = re.compile(r'(?:https?://)?t\.me/(?:s/)?([a-zA-Z0-9_]{4,})')
INVITE_LINK_PATTERN = re.compile(r'(?:https?://)?t\.me/joinchat/([a-zA-Z0-9_-]+)')

SKIP_USERNAMES = {
    "s", "joinchat", "addstickers", "setlanguage", "proxy", "socks",
    "boost", "faq", "privacy", "terms", "cdn", "telegram", "addlist",
    "msg", "passport", "vlive", "blog", "corporate", "press",
}


def extract_links_from_text(text: str, source_title: str = "") -> list[DiscoveryCandidate]:
    candidates = []
    seen = set()

    for match in TME_LINK_PATTERN.finditer(text):
        username = match.group(1)
        if username.lower() in SKIP_USERNAMES or len(username) < 4:
            continue
        if username in seen:
            continue
        seen.add(username)
        candidates.append(DiscoveryCandidate(
            username=username,
            url=f"https://t.me/{username}",
            discovered_via="link_extraction",
            confidence=0.5,
            raw_data={"source_title": source_title},
        ))

    for match in INVITE_LINK_PATTERN.finditer(text):
        invite = f"https://t.me/joinchat/{match.group(1)}"
        if invite in seen:
            continue
        seen.add(invite)
        candidates.append(DiscoveryCandidate(
            invite_link=invite,
            discovered_via="link_extraction",
            confidence=0.4,
        ))

    return candidates


class LinkProvider(DiscoveryProvider):
    def __init__(self):
        self._link_cache: dict[int, list[str]] = {}

    @property
    def provider_name(self) -> str:
        return "link_extraction"

    @property
    def priority(self) -> int:
        return 6

    async def discover(self, query: str, limit: int = 20) -> list[DiscoveryCandidate]:
        return []

    def extract_from_messages(self, messages: list[dict], source_title: str = "") -> list[DiscoveryCandidate]:
        all_candidates = []
        for msg in messages:
            text = msg.get("text", "")
            candidates = extract_links_from_text(text, source_title)
            all_candidates.extend(candidates)
        return all_candidates[:limit] if limit else all_candidates

    def extract_from_description(self, description: str, source_title: str = "") -> list[DiscoveryCandidate]:
        return extract_links_from_text(description, source_title)
