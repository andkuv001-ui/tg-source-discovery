from app.services.discovery.base import DiscoveryProvider
from app.services.discovery.search_engine import SearchEngineProvider
from app.services.discovery.directory import DirectoryProvider
from app.services.discovery.link import LinkProvider

PROVIDERS: dict[str, type[DiscoveryProvider]] = {
    "search_engine": SearchEngineProvider,
    "directory": DirectoryProvider,
    "link_extraction": LinkProvider,
}


def get_provider(name: str) -> DiscoveryProvider:
    cls = PROVIDERS.get(name)
    if not cls:
        raise ValueError(f"Unknown provider: {name}")
    return cls()


def get_all_providers() -> list[DiscoveryProvider]:
    return sorted(
        [cls() for cls in PROVIDERS.values()],
        key=lambda p: -p.priority,
    )
