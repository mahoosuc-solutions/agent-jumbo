"""
PMS Provider Adapters
Each adapter implements the PMSProvider interface for a specific PMS platform
"""

from typing import Any

from ..pms_provider import PMSProvider, ProviderType


async def create_provider(
    provider_type: ProviderType,
    config: dict[str, Any],
) -> PMSProvider:
    """
    Factory function to create provider instances

    Args:
        provider_type: Type of provider to create
        config: Provider configuration

    Returns:
        Initialized provider instance
    """
    if provider_type == ProviderType.HOSTAWAY:
        from .hostaway import HostawayProvider

        provider = HostawayProvider(config)
    elif provider_type == ProviderType.LODGIFY:
        from .lodgify import LodgifyProvider

        provider = LodgifyProvider(config)
    elif provider_type == ProviderType.HOSTIFY:
        from .hostify import HostifyProvider

        provider = HostifyProvider(config)
    elif provider_type == ProviderType.ICAL:
        from .ical import ICalProvider

        provider = ICalProvider(config)
    else:
        raise ValueError(f"Unsupported provider type: {provider_type}")

    # Authenticate provider
    if not await provider.authenticate():
        raise Exception(f"Failed to authenticate with {provider_type}")

    return provider
