import asyncio
import re

import httpx
from bs4 import BeautifulSoup

from app.services.discovery.base import DiscoveryProvider, DiscoveryCandidate

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


class DirectoryProvider(DiscoveryProvider):
    def __init__(self):
        self._delay = 3.0

    @property
    def provider_name(self) -> str:
        return "directory"

    @property
    def priority(self) -> int:
        return 8

    async def discover(self, query: str, limit: int = 20) -> list[DiscoveryCandidate]:
        candidates = []
        candidates.extend(await self._scrape_tgstat(query, limit // 2))
        await asyncio.sleep(self._delay)
        candidates.extend(await self._scrape_telemetr(query, limit // 2))
        return candidates[:limit]

    async def _scrape_tgstat(self, query: str, limit: int) -> list[DiscoveryCandidate]:
        candidates = []
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                headers = {"User-Agent": USER_AGENTS[0]}
                resp = await client.get(
                    "https://tgstat.com/search",
                    params={"q": query, "lang": "en"},
                    headers=headers,
                )
                if resp.status_code != 200:
                    return candidates

                soup = BeautifulSoup(resp.text, "lxml")
                for item in soup.select(".channel-card, .group-card, [data-entity]")[:limit]:
                    link = item.select_one("a[href*='t.me']")
                    if not link:
                        continue

                    href = link.get("href", "")
                    username_match = re.search(r't\.me/([a-zA-Z0-9_]+)', href)
                    if not username_match:
                        continue

                    username = username_match.group(1)
                    title_el = item.select_one(".channel-name, .title, h4, h5")
                    title = title_el.get_text(strip=True) if title_el else username

                    members_el = item.select_one(".members, .subscribers")
                    members_text = members_el.get_text(strip=True) if members_el else "0"
                    members = int(re.sub(r'[^\d]', '', members_text) or 0)

                    candidates.append(DiscoveryCandidate(
                        username=username,
                        url=f"https://t.me/{username}",
                        title=title[:200],
                        source_type="channel",
                        discovered_via="directory",
                        discovery_query=query,
                        confidence=0.6,
                        raw_data={"member_count": members, "source": "tgstat"},
                    ))
        except Exception:
            pass
        return candidates

    async def _scrape_telemetr(self, query: str, limit: int) -> list[DiscoveryCandidate]:
        candidates = []
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                headers = {"User-Agent": USER_AGENTS[1]}
                resp = await client.get(
                    "https://telemetr.me/en/channels",
                    params={"q": query},
                    headers=headers,
                )
                if resp.status_code != 200:
                    return candidates

                soup = BeautifulSoup(resp.text, "lxml")
                for item in soup.select(".channel-item, .channel-card, tr[data-id]")[:limit]:
                    link = item.select_one("a[href*='t.me']")
                    if not link:
                        continue

                    href = link.get("href", "")
                    username_match = re.search(r't\.me/([a-zA-Z0-9_]+)', href)
                    if not username_match:
                        continue

                    username = username_match.group(1)
                    title = link.get_text(strip=True) or username

                    candidates.append(DiscoveryCandidate(
                        username=username,
                        url=f"https://t.me/{username}",
                        title=title[:200],
                        source_type="channel",
                        discovered_via="directory",
                        discovery_query=query,
                        confidence=0.5,
                        raw_data={"source": "telemetr"},
                    ))
        except Exception:
            pass
        return candidates
