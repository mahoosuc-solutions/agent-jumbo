"""
Skill Importer Manager
Business logic for importing Claude Code plugin skills into Agent Zero
"""

import json
import re
from pathlib import Path

import yaml

from .skill_db import SkillDatabase


class SkillImporterManager:
    """Manages importing and converting Claude Code skills to Agent Zero tools"""

    def __init__(self, db_path: str):
        self.db = SkillDatabase(db_path)

    def import_skill(self, source_path: str, category: str | None = None) -> dict:
        """
        Import a Claude Code skill from a markdown file

        Args:
            source_path: Path to skill markdown file
            category: Optional category for organization

        Returns:
            dict with skill_id, name, and import status
        """
        path = Path(source_path)
        if not path.exists():
            return {"error": f"File not found: {source_path}"}

        content = path.read_text(encoding="utf-8")

        # Parse frontmatter and content
        frontmatter, body = self._parse_frontmatter(content)

        if not frontmatter:
            # Try to infer from filename and content
            frontmatter = self._infer_frontmatter(path.name, body)

        # Extract skill metadata
        name = frontmatter.get("name") or path.stem
        description = frontmatter.get("description", "")
        arguments = self._extract_arguments(frontmatter, body)
        tool_requirements = frontmatter.get("tools", [])

        # Determine plugin name from path
        plugin_name = self._extract_plugin_name(source_path)

        # Save to database
        skill_id = self.db.add_skill(
            name=name,
            source_path=str(path.absolute()),
            description=description,
            arguments=arguments,
            tool_requirements=tool_requirements,
            content=body,
            frontmatter=frontmatter,
            plugin_name=plugin_name,
            category=category,
        )

        return {
            "skill_id": skill_id,
            "name": name,
            "description": description,
            "arguments": arguments,
            "tool_requirements": tool_requirements,
            "plugin_name": plugin_name,
            "status": "imported",
        }

    def sync_plugins_directory(self, plugins_dir: str, recursive: bool = True) -> dict:
        """
        Bulk import skills from a Claude Code plugins directory

        Args:
            plugins_dir: Path to plugins directory
            recursive: Whether to search subdirectories

        Returns:
            dict with import results
        """
        path = Path(plugins_dir)
        if not path.exists():
            return {"error": f"Directory not found: {plugins_dir}"}

        # Find all skill files
        pattern = "**/*.md" if recursive else "*.md"
        skill_files = list(path.glob(pattern))

        # Filter to likely skill files (in skills/ directories or with skill-like names)
        skill_files = [f for f in skill_files if self._is_skill_file(f)]

        results = {"imported": [], "failed": [], "skipped": []}

        for skill_file in skill_files:
            try:
                # Determine category from directory structure
                category = self._get_category_from_path(skill_file, path)

                result = self.import_skill(str(skill_file), category=category)

                if "error" in result:
                    results["failed"].append({"file": str(skill_file), "error": result["error"]})
                else:
                    results["imported"].append(result)

            except Exception as e:
                results["failed"].append({"file": str(skill_file), "error": str(e)})

        results["summary"] = {
            "total_found": len(skill_files),
            "imported": len(results["imported"]),
            "failed": len(results["failed"]),
        }

        return results

    def list_skills(
        self, enabled_only: bool = True, category: str | None = None, plugin_name: str | None = None
    ) -> list:
        """List all imported skills"""
        return self.db.list_skills(enabled_only=enabled_only, category=category, plugin_name=plugin_name)

    def get_skill(self, name: str | None = None, skill_id: int | None = None) -> dict:
        """Get a specific skill"""
        return self.db.get_skill(name=name, skill_id=skill_id)

    def remove_skill(self, skill_id: int) -> dict:
        """Remove an imported skill"""
        skill = self.db.get_skill(skill_id=skill_id)
        if not skill:
            return {"error": f"Skill not found: {skill_id}"}

        success = self.db.delete_skill(skill_id)
        return {
            "success": success,
            "skill_name": skill.get("name"),
            "message": "Skill removed" if success else "Failed to remove skill",
        }

    def toggle_skill(self, skill_id: int, enabled: bool) -> dict:
        """Enable or disable a skill"""
        success = self.db.update_skill(skill_id, enabled=1 if enabled else 0)
        return {"success": success, "enabled": enabled}

    def generate_tool_prompt(self, skill_id: int) -> str:
        """
        Generate an Agent Zero tool prompt from an imported skill

        Args:
            skill_id: ID of the imported skill

        Returns:
            Markdown content for prompts/agent.system.tool.{name}.md
        """
        skill = self.db.get_skill(skill_id=skill_id)
        if not skill:
            return None

        name = skill["name"]
        description = skill.get("description", "Imported skill")
        arguments = skill.get("arguments", {})
        content = skill.get("content", "")

        # Build prompt markdown
        prompt = f"""# {name}

{description}

## Usage

```
{{{{{name}(
"""

        # Add argument examples
        for arg_name, arg_info in arguments.items():
            default = arg_info.get("default", '""')
            prompt += f"  {arg_name}={default},\n"

        prompt = prompt.rstrip(",\n") + "\n"
        prompt += """)}}}
```

## Parameters

"""

        # Document parameters
        for arg_name, arg_info in arguments.items():
            required = "(required)" if arg_info.get("required") else "(optional)"
            desc = arg_info.get("description", "No description")
            prompt += f"- `{arg_name}` {required}: {desc}\n"

        prompt += f"""
## Details

{content}

---
*Imported from Claude Code plugin*
"""

        return prompt

    def get_execution_context(self, skill_id: int) -> dict:
        """
        Get the execution context for a skill (what it needs to run)

        Args:
            skill_id: ID of the skill

        Returns:
            dict with tool requirements, arguments, and execution hints
        """
        skill = self.db.get_skill(skill_id=skill_id)
        if not skill:
            return {"error": "Skill not found"}

        return {
            "name": skill["name"],
            "arguments": skill.get("arguments", {}),
            "tool_requirements": skill.get("tool_requirements", []),
            "content": skill.get("content", ""),
            "can_execute": self._can_execute_skill(skill),
        }

    def get_stats(self, skill_id: int | None = None) -> dict:
        """Get execution statistics"""
        return self.db.get_execution_stats(skill_id)

    def record_execution(self, skill_id: int, input_args: dict, output: str, status: str, duration_ms: float) -> int:
        """Record a skill execution"""
        return self.db.record_execution(skill_id, input_args, output, status, duration_ms)

    # ========== Private helper methods ==========

    def _parse_frontmatter(self, content: str) -> tuple:
        """Parse YAML frontmatter from markdown content"""
        frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(frontmatter_pattern, content, re.DOTALL)

        if match:
            try:
                frontmatter = yaml.safe_load(match.group(1))
                body = content[match.end() :]
                return frontmatter or {}, body
            except yaml.YAMLError:
                pass

        return {}, content

    def _infer_frontmatter(self, filename: str, content: str) -> dict:
        """Infer frontmatter from filename and content"""
        name = Path(filename).stem.replace("-", "_").replace(" ", "_")

        # Try to extract description from first paragraph
        lines = content.strip().split("\n")
        description = ""
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#"):
                description = line[:200]
                break

        return {"name": name, "description": description}

    def _extract_arguments(self, frontmatter: dict, content: str) -> dict:
        """Extract argument definitions from frontmatter and content"""
        arguments = {}

        # Check frontmatter for explicit arguments
        if "arguments" in frontmatter:
            for arg in frontmatter["arguments"]:
                if isinstance(arg, dict):
                    name = arg.get("name", "")
                    arguments[name] = {
                        "description": arg.get("description", ""),
                        "required": arg.get("required", False),
                        "default": arg.get("default", ""),
                        "type": arg.get("type", "string"),
                    }
                elif isinstance(arg, str):
                    arguments[arg] = {"description": "", "required": False, "type": "string"}

        # Also check for 'args' shorthand
        if "args" in frontmatter:
            for arg_name in frontmatter["args"]:
                if arg_name not in arguments:
                    arguments[arg_name] = {"description": "", "required": False, "type": "string"}

        # Try to extract from content patterns like {{$ARG_NAME}}
        arg_pattern = r"\{\{\s*\$(\w+)\s*\}\}"
        found_args = re.findall(arg_pattern, content)
        for arg_name in found_args:
            if arg_name.lower() not in arguments:
                arguments[arg_name.lower()] = {
                    "description": f"Argument: {arg_name}",
                    "required": False,
                    "type": "string",
                }

        return arguments

    def _extract_plugin_name(self, source_path: str) -> str | None:
        """Extract plugin name from file path"""
        path = Path(source_path)
        parts = path.parts

        # Look for patterns like .claude/plugins/{plugin_name}/
        for i, part in enumerate(parts):
            if part in ["plugins", ".claude"] and i + 1 < len(parts):
                next_part = parts[i + 1]
                if next_part not in ["skills", "commands", "hooks"]:
                    return next_part

        return None

    def _is_skill_file(self, file_path: Path) -> bool:
        """Determine if a file is likely a skill definition"""
        # Check if in a skills/ directory
        if "skills" in file_path.parts:
            return True

        # Check if in a commands/ directory
        if "commands" in file_path.parts:
            return True

        # Check filename patterns
        name = file_path.stem.lower()
        if name.startswith("skill-") or name.endswith("-skill"):
            return True

        # Skip obvious non-skill files
        skip_patterns = ["readme", "changelog", "license", "contributing"]
        if any(pattern in name for pattern in skip_patterns):
            return False

        return True

    def _get_category_from_path(self, file_path: Path, base_path: Path) -> str | None:
        """Determine category from directory structure"""
        relative = file_path.relative_to(base_path)
        parts = relative.parts

        # Use parent directory as category if meaningful
        if len(parts) > 1:
            parent = parts[-2]
            if parent not in ["skills", "commands", "."]:
                return parent

        return None

    def _can_execute_skill(self, skill: dict) -> dict:
        """Check if a skill can be executed"""
        requirements = skill.get("tool_requirements", [])

        # Map Claude Code tools to Agent Zero equivalents
        tool_mapping = {
            "Bash": "code_execution_tool",
            "Read": "code_execution_tool",
            "Write": "code_execution_tool",
            "Edit": "code_execution_tool",
            "Glob": "code_execution_tool",
            "Grep": "code_execution_tool",
            "WebFetch": "browser_agent",
            "WebSearch": "search_engine",
            "Task": "call_subordinate",
        }

        mapped_requirements = []
        for req in requirements:
            mapped = tool_mapping.get(req, req)
            if mapped not in mapped_requirements:
                mapped_requirements.append(mapped)

        return {
            "can_execute": True,  # Agent Zero can execute most things
            "required_tools": mapped_requirements,
            "original_requirements": requirements,
        }

    # ========== Plugin Import Methods ==========

    def import_plugin(self, plugin_path: str) -> dict:
        """
        Import a complete Claude Code plugin

        Args:
            plugin_path: Path to plugin directory (containing plugin.json or .claude/ structure)

        Returns:
            dict with import results for all components
        """
        path = Path(plugin_path)
        if not path.exists():
            return {"error": f"Plugin path not found: {plugin_path}"}

        # Find plugin manifest
        manifest_path = path / "plugin.json"
        if not manifest_path.exists():
            # Check for .claude structure
            manifest_path = path / ".claude" / "plugin.json"

        manifest = {}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        # Extract plugin metadata
        plugin_name = manifest.get("name") or path.name
        description = manifest.get("description", "")
        version = manifest.get("version", "1.0.0")

        # Create plugin record
        plugin_id = self.db.add_plugin(
            name=plugin_name,
            source_path=str(path.absolute()),
            description=description,
            version=version,
            manifest=manifest,
        )

        results = {
            "plugin_id": plugin_id,
            "plugin_name": plugin_name,
            "skills": [],
            "hooks": [],
            "agents": [],
            "mcp_servers": [],
        }

        # Import skills
        skills_result = self._import_plugin_skills(path, plugin_id, plugin_name)
        results["skills"] = skills_result

        # Import hooks
        hooks_result = self._import_plugin_hooks(path, plugin_id)
        results["hooks"] = hooks_result

        # Import agents
        agents_result = self._import_plugin_agents(path, plugin_id)
        results["agents"] = agents_result

        # Import MCP servers
        mcp_result = self._import_plugin_mcp(path, plugin_id, manifest)
        results["mcp_servers"] = mcp_result

        # Update counts
        self.db.update_plugin_counts(
            plugin_id,
            skills=len(results["skills"]),
            hooks=len(results["hooks"]),
            agents=len(results["agents"]),
            mcp_servers=len(results["mcp_servers"]),
        )

        results["summary"] = {
            "total_components": (
                len(results["skills"]) + len(results["hooks"]) + len(results["agents"]) + len(results["mcp_servers"])
            ),
            "status": "imported",
        }

        return results

    def _import_plugin_skills(self, plugin_path: Path, plugin_id: int, plugin_name: str) -> list:
        """Import skills from a plugin"""
        imported = []

        # Check multiple possible skill locations
        skill_dirs = [
            plugin_path / "skills",
            plugin_path / "commands",
            plugin_path / ".claude" / "skills",
            plugin_path / ".claude" / "commands",
        ]

        for skill_dir in skill_dirs:
            if skill_dir.exists():
                for skill_file in skill_dir.glob("**/*.md"):
                    try:
                        result = self.import_skill(str(skill_file), category=plugin_name)
                        if "error" not in result:
                            imported.append(result)
                    except Exception as e:
                        imported.append({"file": str(skill_file), "error": str(e)})

        return imported

    def _import_plugin_hooks(self, plugin_path: Path, plugin_id: int) -> list:
        """Import hooks from a plugin"""
        imported = []

        hook_dirs = [plugin_path / "hooks", plugin_path / ".claude" / "hooks"]

        for hook_dir in hook_dirs:
            if hook_dir.exists():
                for hook_file in hook_dir.glob("**/*.md"):
                    try:
                        content = hook_file.read_text(encoding="utf-8")
                        frontmatter, _body = self._parse_frontmatter(content)

                        hook_name = frontmatter.get("name") or hook_file.stem
                        event = frontmatter.get("event", "PreToolUse")
                        hook_type = frontmatter.get("type", "prompt")

                        hook_id = self.db.add_hook(
                            plugin_id=plugin_id, name=hook_name, event=event, hook_type=hook_type, content=content
                        )

                        imported.append({"hook_id": hook_id, "name": hook_name, "event": event})
                    except Exception as e:
                        imported.append({"file": str(hook_file), "error": str(e)})

        return imported

    def _import_plugin_agents(self, plugin_path: Path, plugin_id: int) -> list:
        """Import agent definitions from a plugin"""
        imported = []

        agent_dirs = [plugin_path / "agents", plugin_path / ".claude" / "agents"]

        for agent_dir in agent_dirs:
            if agent_dir.exists():
                for agent_file in agent_dir.glob("**/*.md"):
                    try:
                        content = agent_file.read_text(encoding="utf-8")
                        frontmatter, body = self._parse_frontmatter(content)

                        agent_name = frontmatter.get("name") or agent_file.stem
                        description = frontmatter.get("description", "")
                        tools = frontmatter.get("tools", [])
                        model = frontmatter.get("model")

                        agent_id = self.db.add_agent(
                            plugin_id=plugin_id,
                            name=agent_name,
                            description=description,
                            system_prompt=body,
                            tools=tools,
                            model=model,
                        )

                        imported.append({"agent_id": agent_id, "name": agent_name, "description": description})
                    except Exception as e:
                        imported.append({"file": str(agent_file), "error": str(e)})

        return imported

    def _import_plugin_mcp(self, plugin_path: Path, plugin_id: int, manifest: dict) -> list:
        """Import MCP server configurations from a plugin"""
        imported = []

        # Check manifest for MCP servers
        mcp_servers = manifest.get("mcpServers", {})
        for server_name, config in mcp_servers.items():
            try:
                server_type = config.get("type", "stdio")
                server_id = self.db.add_mcp_server(
                    plugin_id=plugin_id, name=server_name, server_type=server_type, config=config
                )
                imported.append({"server_id": server_id, "name": server_name, "type": server_type})
            except Exception as e:
                imported.append({"name": server_name, "error": str(e)})

        # Also check for .mcp.json files
        mcp_files = list(plugin_path.glob("**/.mcp.json"))
        mcp_files.extend(plugin_path.glob("**/mcp.json"))

        for mcp_file in mcp_files:
            try:
                mcp_config = json.loads(mcp_file.read_text(encoding="utf-8"))
                servers = mcp_config.get("mcpServers", mcp_config)

                for server_name, config in servers.items():
                    if any(s.get("name") == server_name for s in imported):
                        continue  # Skip duplicates

                    server_type = config.get("type", "stdio")
                    server_id = self.db.add_mcp_server(
                        plugin_id=plugin_id, name=server_name, server_type=server_type, config=config
                    )
                    imported.append(
                        {"server_id": server_id, "name": server_name, "type": server_type, "source": str(mcp_file)}
                    )
            except Exception as e:
                imported.append({"file": str(mcp_file), "error": str(e)})

        return imported

    def list_plugins(self, enabled_only: bool = True) -> list:
        """List all imported plugins"""
        return self.db.list_plugins(enabled_only=enabled_only)

    def get_plugin(self, name: str | None = None, plugin_id: int | None = None) -> dict:
        """Get a specific plugin with all its components"""
        plugin = self.db.get_plugin(name=name, plugin_id=plugin_id)
        if not plugin:
            return None

        # Get all components
        plugin["skills"] = self.db.list_skills(plugin_name=plugin["name"])
        plugin["hooks"] = self.db.list_hooks(plugin_id=plugin["plugin_id"])
        plugin["agents"] = self.db.list_agents(plugin_id=plugin["plugin_id"])
        plugin["mcp_servers"] = self.db.list_mcp_servers(plugin_id=plugin["plugin_id"])

        return plugin

    def remove_plugin(self, plugin_id: int) -> dict:
        """Remove a plugin and all its components"""
        plugin = self.db.get_plugin(plugin_id=plugin_id)
        if not plugin:
            return {"error": f"Plugin not found: {plugin_id}"}

        success = self.db.delete_plugin(plugin_id)
        return {
            "success": success,
            "plugin_name": plugin.get("name"),
            "message": "Plugin and all components removed" if success else "Failed to remove plugin",
        }

    def get_plugin_mcp_config(self, plugin_id: int) -> dict:
        """
        Get MCP configuration for Agent Zero integration

        Returns config that can be added to Agent Zero's MCP settings
        """
        servers = self.db.list_mcp_servers(plugin_id=plugin_id)

        mcp_config = {"mcpServers": {}}
        for server in servers:
            config = server.get("config", {})
            mcp_config["mcpServers"][server["name"]] = config

        return mcp_config
