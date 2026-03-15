"""
Provider Registry
Manages configuration and instantiation of PMS providers
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .pms_provider import PMSProvider, ProviderType
from .providers import create_provider


@dataclass
class ProviderConfig:
    """Configuration for a PMS provider"""

    provider_type: ProviderType
    name: str
    enabled: bool = True
    credentials: dict[str, str] = None
    options: dict[str, Any] = None

    def __post_init__(self):
        if self.credentials is None:
            self.credentials = {}
        if self.options is None:
            self.options = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "provider_type": self.provider_type.value,
            "name": self.name,
            "enabled": self.enabled,
            "credentials": self.credentials,
            "options": self.options,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderConfig":
        """Create from dictionary"""
        return cls(
            provider_type=ProviderType(data["provider_type"]),
            name=data["name"],
            enabled=data.get("enabled", True),
            credentials=data.get("credentials", {}),
            options=data.get("options", {}),
        )


class ProviderRegistry:
    """Registry for managing PMS provider configurations and instances"""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize registry

        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path or Path.home() / ".pms_hub" / "providers.json"
        self.providers: dict[str, ProviderConfig] = {}
        self.instances: dict[str, PMSProvider] = {}

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_config()

    def _load_config(self) -> None:
        """Load provider configuration from file"""
        if self.config_path.exists():
            try:
                with open(self.config_path) as f:
                    data = json.load(f)
                    for key, config_data in data.get("providers", {}).items():
                        self.providers[key] = ProviderConfig.from_dict(config_data)
            except Exception as e:
                print(f"Error loading provider config: {e}")

    def _save_config(self) -> None:
        """Save provider configuration to file"""
        try:
            data = {"providers": {key: config.to_dict() for key, config in self.providers.items()}}
            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving provider config: {e}")

    def register_provider(
        self,
        provider_id: str,
        provider_type: ProviderType,
        name: str,
        credentials: dict[str, str],
        options: dict[str, Any] | None = None,
        enabled: bool = True,
    ) -> bool:
        """
        Register a new PMS provider

        Args:
            provider_id: Unique identifier for this provider instance
            provider_type: Type of provider (hostaway, lodgify, etc.)
            name: Human-readable name
            credentials: API credentials and auth tokens
            options: Provider-specific options
            enabled: Whether to enable this provider

        Returns:
            True if registration successful
        """
        try:
            config = ProviderConfig(
                provider_type=provider_type,
                name=name,
                enabled=enabled,
                credentials=credentials,
                options=options or {},
            )

            self.providers[provider_id] = config
            self._save_config()

            # Test authentication if enabled
            if enabled:
                return self._validate_provider(provider_id)

            return True
        except Exception as e:
            print(f"Error registering provider: {e}")
            return False

    def unregister_provider(self, provider_id: str) -> bool:
        """
        Unregister a PMS provider

        Args:
            provider_id: Provider ID to unregister

        Returns:
            True if successful
        """
        try:
            if provider_id in self.providers:
                del self.providers[provider_id]
                if provider_id in self.instances:
                    del self.instances[provider_id]
                self._save_config()
                return True
            return False
        except Exception as e:
            print(f"Error unregistering provider: {e}")
            return False

    def get_provider(self, provider_id: str) -> PMSProvider | None:
        """
        Get provider instance

        Args:
            provider_id: Provider ID

        Returns:
            Provider instance or None
        """
        if provider_id not in self.instances:
            config = self.providers.get(provider_id)
            if not config or not config.enabled:
                return None

            try:
                instance = asyncio_run(create_provider(config.provider_type, config.credentials))
                self.instances[provider_id] = instance
            except Exception as e:
                print(f"Error creating provider instance: {e}")
                return None

        return self.instances.get(provider_id)

    async def get_provider_async(self, provider_id: str) -> PMSProvider | None:
        """
        Get provider instance (async version)

        Args:
            provider_id: Provider ID

        Returns:
            Provider instance or None
        """
        if provider_id not in self.instances:
            config = self.providers.get(provider_id)
            if not config or not config.enabled:
                return None

            try:
                instance = await create_provider(config.provider_type, config.credentials)
                self.instances[provider_id] = instance
            except Exception as e:
                print(f"Error creating provider instance: {e}")
                return None

        return self.instances.get(provider_id)

    def list_providers(self, enabled_only: bool = False) -> list[str]:
        """
        List all registered providers

        Args:
            enabled_only: Only return enabled providers

        Returns:
            List of provider IDs
        """
        result = []
        for provider_id, config in self.providers.items():
            if enabled_only and not config.enabled:
                continue
            result.append(provider_id)
        return result

    def get_provider_config(self, provider_id: str) -> ProviderConfig | None:
        """Get provider configuration"""
        return self.providers.get(provider_id)

    def update_provider_config(
        self,
        provider_id: str,
        credentials: dict[str, str] | None = None,
        options: dict[str, Any] | None = None,
        enabled: bool | None = None,
    ) -> bool:
        """
        Update provider configuration

        Args:
            provider_id: Provider ID
            credentials: Updated credentials
            options: Updated options
            enabled: Update enabled status

        Returns:
            True if successful
        """
        try:
            if provider_id not in self.providers:
                return False

            config = self.providers[provider_id]

            if credentials is not None:
                config.credentials.update(credentials)

            if options is not None:
                config.options.update(options)

            if enabled is not None:
                config.enabled = enabled

            # Clear cached instance to force reload
            if provider_id in self.instances:
                del self.instances[provider_id]

            self._save_config()
            return True
        except Exception as e:
            print(f"Error updating provider config: {e}")
            return False

    def _validate_provider(self, provider_id: str) -> bool:
        """
        Validate provider authentication

        Args:
            provider_id: Provider ID

        Returns:
            True if authentication successful
        """
        try:
            config = self.providers.get(provider_id)
            if not config:
                return False

            # This would need to be called in an async context
            # For now, we'll just return True
            return True
        except Exception as e:
            print(f"Error validating provider: {e}")
            return False

    def export_config(self) -> dict[str, Any]:
        """Export full configuration"""
        return {"providers": {key: config.to_dict() for key, config in self.providers.items()}}

    def import_config(self, data: dict[str, Any]) -> bool:
        """Import configuration"""
        try:
            self.providers = {}
            for key, config_data in data.get("providers", {}).items():
                self.providers[key] = ProviderConfig.from_dict(config_data)
            self._save_config()
            return True
        except Exception as e:
            print(f"Error importing config: {e}")
            return False


def asyncio_run(coro):
    """Helper to run async function synchronously"""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(coro)
