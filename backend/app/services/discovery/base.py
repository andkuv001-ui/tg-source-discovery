from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscoveryCandidate:
    username: str | None = None
    telegram_id: int | None = None
    invite_link: str | None = None
    url: str | None = None
    title: str | None = None
    source_type: str | None = None
    discovered_via: str = ""
    discovery_query: str = ""
    confidence: float = 0.5
    raw_data: dict = field(default_factory=dict)


class DiscoveryProvider(ABC):
    @abstractmethod
    async def discover(self, query: str, limit: int = 20) -> list[DiscoveryCandidate]:
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def priority(self) -> int:
        ...
