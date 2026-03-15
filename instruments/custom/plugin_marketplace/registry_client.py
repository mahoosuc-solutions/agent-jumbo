"""
Registry Client - HTTP client for marketplace APIs
Abstracts different marketplace API formats behind a common interface
"""

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

# Use aiohttp if available, fall back to requests
try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    import requests


class BaseRegistryClient(ABC):
    """Base class for marketplace registry clients"""

    @abstractmethod
    async def fetch_plugins(self, limit: int = 100) -> list:
        """Fetch plugin listings from marketplace"""
        pass

    @abstractmethod
    async def get_plugin_details(self, identifier: str) -> dict:
        """Get detailed info for a specific plugin"""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 50) -> list:
        """Search plugins"""
        pass


class ClaudePluginsDevClient(BaseRegistryClient):
    """Client for claude-plugins.dev community registry"""

    BASE_URL = "https://claude-plugins.dev"
    API_URL = "https://claude-plugins.dev/api"

    def __init__(self):
        self.session = None

    async def _get_session(self):
        if HAS_AIOHTTP and self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _fetch(self, url: str) -> dict:
        """Fetch JSON from URL"""
        if HAS_AIOHTTP:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": f"HTTP {resp.status}"}
        else:
            # Synchronous fallback
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}"}

    async def fetch_plugins(self, limit: int = 100) -> list:
        """Fetch plugin listings"""
        try:
            # Try API endpoint first
            data = await self._fetch(f"{self.API_URL}/registry")

            if "error" not in data and isinstance(data, list):
                return self._normalize_plugins(data[:limit])

            # Fallback: parse HTML or use cached data
            return []

        except Exception as e:
            return [{"error": str(e)}]

    async def get_plugin_details(self, identifier: str) -> dict:
        """Get plugin details by identifier"""
        try:
            data = await self._fetch(f"{self.API_URL}/plugins/{identifier}")
            if "error" not in data:
                return self._normalize_plugin(data)
            return data
        except Exception as e:
            return {"error": str(e)}

    async def search(self, query: str, limit: int = 50) -> list:
        """Search plugins"""
        try:
            data = await self._fetch(f"{self.API_URL}/search?q={query}&limit={limit}")
            if "error" not in data and isinstance(data, list):
                return self._normalize_plugins(data)
            return []
        except Exception as e:
            return [{"error": str(e)}]

    def _normalize_plugins(self, plugins: list) -> list:
        """Normalize plugin list to standard format"""
        return [self._normalize_plugin(p) for p in plugins if p]

    def _normalize_plugin(self, plugin: dict) -> dict:
        """Normalize single plugin to standard format"""
        return {
            "identifier": plugin.get("identifier") or plugin.get("name", ""),
            "name": plugin.get("name", plugin.get("identifier", "")),
            "description": plugin.get("description", ""),
            "version": plugin.get("version", "1.0.0"),
            "downloads": plugin.get("downloads", 0),
            "stars": plugin.get("stars", 0),
            "tags": plugin.get("tags", []),
            "author": plugin.get("author") or plugin.get("publisher", ""),
            "repository": plugin.get("repository") or plugin.get("repo", ""),
            "homepage": plugin.get("homepage", ""),
            "license": plugin.get("license", ""),
            "last_updated": plugin.get("last_updated") or plugin.get("updated", ""),
            "metadata": {
                "install_command": plugin.get("install_command"),
                "skills": plugin.get("skills", []),
                "hooks": plugin.get("hooks", []),
            },
        }

    async def close(self):
        """Close session"""
        if HAS_AIOHTTP and self.session:
            await self.session.close()
            self.session = None


class GitHubRegistryClient(BaseRegistryClient):
    """Client for GitHub-based plugin discovery"""

    API_URL = "https://api.github.com"

    def __init__(self, org: str = "anthropics"):
        self.org = org
        self.token = os.environ.get("GITHUB_TOKEN")
        self.session = None

    async def _get_session(self):
        if HAS_AIOHTTP and self.session is None:
            headers = {"Accept": "application/vnd.github.v3+json"}
            if self.token:
                headers["Authorization"] = f"token {self.token}"
            self.session = aiohttp.ClientSession(headers=headers)
        return self.session

    async def _fetch(self, url: str) -> dict:
        """Fetch JSON from GitHub API"""
        headers = {"Accept": "application/vnd.github.v3+json"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        if HAS_AIOHTTP:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    return await resp.json()
                return {"error": f"HTTP {resp.status}"}
        else:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}"}

    async def fetch_plugins(self, limit: int = 100) -> list:
        """Fetch repos that look like Claude Code plugins"""
        try:
            # Search for repos with claude-code or plugin in name/topic
            data = await self._fetch(
                f"{self.API_URL}/search/repositories?q=org:{self.org}+topic:claude-code-plugin&per_page={limit}"
            )

            if "error" in data:
                # Fallback: list org repos
                data = await self._fetch(f"{self.API_URL}/orgs/{self.org}/repos?per_page={limit}")

            if isinstance(data, dict) and "items" in data:
                repos = data["items"]
            elif isinstance(data, list):
                repos = data
            else:
                return []

            return self._normalize_repos(repos)

        except Exception as e:
            return [{"error": str(e)}]

    async def get_plugin_details(self, identifier: str) -> dict:
        """Get repo details"""
        try:
            # identifier format: owner/repo or just repo (assume org)
            if "/" not in identifier:
                identifier = f"{self.org}/{identifier}"

            data = await self._fetch(f"{self.API_URL}/repos/{identifier}")
            if "error" not in data:
                return self._normalize_repo(data)
            return data
        except Exception as e:
            return {"error": str(e)}

    async def search(self, query: str, limit: int = 50) -> list:
        """Search GitHub repos"""
        try:
            data = await self._fetch(f"{self.API_URL}/search/repositories?q={query}+topic:claude-code&per_page={limit}")
            if isinstance(data, dict) and "items" in data:
                return self._normalize_repos(data["items"])
            return []
        except Exception as e:
            return [{"error": str(e)}]

    def _normalize_repos(self, repos: list) -> list:
        """Normalize repo list"""
        return [self._normalize_repo(r) for r in repos if r]

    def _normalize_repo(self, repo: dict) -> dict:
        """Normalize GitHub repo to standard plugin format"""
        return {
            "identifier": repo.get("full_name", ""),
            "name": repo.get("name", ""),
            "description": repo.get("description", ""),
            "version": "latest",
            "downloads": 0,
            "stars": repo.get("stargazers_count", 0),
            "tags": repo.get("topics", []),
            "author": repo.get("owner", {}).get("login", ""),
            "repository": repo.get("html_url", ""),
            "homepage": repo.get("homepage", ""),
            "license": repo.get("license", {}).get("spdx_id", "") if repo.get("license") else "",
            "last_updated": repo.get("updated_at", ""),
            "metadata": {
                "forks": repo.get("forks_count", 0),
                "open_issues": repo.get("open_issues_count", 0),
                "language": repo.get("language"),
            },
        }

    async def close(self):
        """Close session"""
        if HAS_AIOHTTP and self.session:
            await self.session.close()
            self.session = None


class LocalFilesystemClient(BaseRegistryClient):
    """Client for discovering locally installed plugins"""

    def __init__(self, base_path: str | None = None):
        self.base_path = Path(base_path or os.path.expanduser("~/.claude/plugins"))

    async def fetch_plugins(self, limit: int = 100) -> list:
        """Scan local directory for plugins"""
        plugins = []

        if not self.base_path.exists():
            return plugins

        for path in self.base_path.iterdir():
            if path.is_dir():
                plugin = await self._scan_plugin_dir(path)
                if plugin:
                    plugins.append(plugin)
                    if len(plugins) >= limit:
                        break

        return plugins

    async def get_plugin_details(self, identifier: str) -> dict:
        """Get local plugin details"""
        plugin_path = self.base_path / identifier
        if plugin_path.exists():
            return await self._scan_plugin_dir(plugin_path)
        return {"error": f"Plugin not found: {identifier}"}

    async def search(self, query: str, limit: int = 50) -> list:
        """Search local plugins by name"""
        all_plugins = await self.fetch_plugins(1000)
        query_lower = query.lower()

        matches = [
            p
            for p in all_plugins
            if query_lower in p.get("name", "").lower() or query_lower in p.get("description", "").lower()
        ]

        return matches[:limit]

    async def _scan_plugin_dir(self, path: Path) -> dict:
        """Scan a directory to extract plugin info"""
        plugin = None

        # Check for plugin.json at root
        manifest_paths = [path / "plugin.json", path / ".claude" / "plugin.json"]

        for manifest_path in manifest_paths:
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        manifest = json.load(f)

                    plugin = {
                        "identifier": path.name,
                        "name": manifest.get("name", path.name),
                        "description": manifest.get("description", ""),
                        "version": manifest.get("version", "1.0.0"),
                        "downloads": 0,
                        "stars": 0,
                        "tags": ["local"],
                        "author": manifest.get("author", "local"),
                        "repository": "",
                        "homepage": "",
                        "license": manifest.get("license", ""),
                        "last_updated": "",
                        "metadata": {"local_path": str(path), "manifest": manifest},
                    }
                    break
                except Exception:
                    pass

        # Fallback: infer from directory structure
        if not plugin and path.is_dir():
            # Check for skills/ or commands/ subdirectory
            has_skills = (path / "skills").exists() or (path / ".claude" / "skills").exists()
            has_commands = (path / "commands").exists() or (path / ".claude" / "commands").exists()

            if has_skills or has_commands:
                plugin = {
                    "identifier": path.name,
                    "name": path.name,
                    "description": f"Local plugin: {path.name}",
                    "version": "1.0.0",
                    "downloads": 0,
                    "stars": 0,
                    "tags": ["local"],
                    "author": "local",
                    "repository": "",
                    "homepage": "",
                    "license": "",
                    "last_updated": "",
                    "metadata": {"local_path": str(path)},
                }

        return plugin


class RegistryClientFactory:
    """Factory for creating registry clients"""

    @staticmethod
    def create(marketplace_type: str, **kwargs) -> BaseRegistryClient:
        """Create a registry client based on marketplace type"""
        if marketplace_type == "community":
            return ClaudePluginsDevClient()
        elif marketplace_type == "official":
            org = kwargs.get("org", "anthropics")
            return GitHubRegistryClient(org=org)
        elif marketplace_type == "local":
            base_path = kwargs.get("base_path")
            return LocalFilesystemClient(base_path=base_path)
        else:
            raise ValueError(f"Unknown marketplace type: {marketplace_type}")
