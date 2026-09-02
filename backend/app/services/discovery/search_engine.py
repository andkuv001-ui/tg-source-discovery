import re
import asyncio
from urllib.parse import urlparse

from duckduckgo_search import DDGS

from app.services.discovery.base import DiscoveryProvider, DiscoveryCandidate

TME_PATTERN = re.compile(r'(?:https?://)?t\.me/(?:s/)?([a-zA-Z0-9_]+)')
INVITE_PATTERN = re.compile(r'(?:https?://)?t\.me/joinchat/([a-zA-Z0-9_-]+)')


def _extract_username_from_url(url: str) -> str | None:
    match = TME_PATTERN.search(url)
    if match:
        username = match.group(1)
        if username not in ("s", "joinchat", "addstickers", "setlanguage", "proxy", "socks", "boost", "faq", "privacy", "terms", "cdn", "telegram"):
            return username
    return None


def _extract_invite_link(text: str) -> str | None:
    match = INVITE_PATTERN.search(text)
    if match:
        return f"https://t.me/joinchat/{match.group(1)}"
    return None


class SearchEngineProvider(DiscoveryProvider):
    def __init__(self):
        self._delay = 2.0

    @property
    def provider_name(self) -> str:
        return "search_engine"

    @property
    def priority(self) -> int:
        return 10

    async def discover(self, query: str, limit: int = 20) -> list[DiscoveryCandidate]:
        candidates = []
        search_patterns = [
            f'site:t.me "{query}"',
            f'"t.me/" {query}',
            f'"t.me/joinchat" {query}',
            f'telegram {query} group',
            f'telegram {query} channel',
        ]

        with DDGS() as ddgs:
            for pattern in search_patterns:
                try:
                    results = list(ddgs.text(pattern, max_results=min(limit, 10)))
                    for result in results:
                        body = result.get("body", "")
                        title = result.get("title", "")
                        href = result.get("href", "")

                        combined_text = f"{title} {body} {href}"

                        for match in TME_PATTERN.finditer(combined_text):
                            username = match.group(1)
                            if username in ("s", "joinchat", "addstickers", "setlanguage", "proxy"):
                                continue
                            candidates.append(DiscoveryCandidate(
                                username=username,
                                url=f"https://t.me/{username}",
                                title=title[:200],
                                discovered_via="search_engine",
                                discovery_query=pattern,
                                confidence=0.4,
                                raw_data={"body": body[:500], "href": href},
                            ))

                        invite = _extract_invite_link(combined_text)
                        if invite:
                            candidates.append(DiscoveryCandidate(
                                invite_link=invite,
                                discovered_via="search_engine",
                                discovery_query=pattern,
                                confidence=0.3,
                                raw_data={"body": body[:500]},
                            ))

                    await asyncio.sleep(self._delay)
                except Exception:
                    await asyncio.sleep(self._delay * 2)
                    continue

        return candidates[:limit]
