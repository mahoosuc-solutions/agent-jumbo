"""
Claude SDK Manager - Wrapper for Claude Agent SDK operations
Manages SDK sessions, tool bridging, and MCP server integration
"""

import asyncio
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any


class ClaudeSDKManager:
    """
    Manager for Claude Agent SDK operations.

    The SDK provides two main interfaces:
    1. query() - Stateless one-off requests
    2. ClaudeSDKClient - Stateful interactive sessions with custom tools

    This manager wraps both and adds Agent Zero-specific functionality.
    """

    def __init__(self):
        self.sdk_available = False
        self.client = None
        self.options = None
        self._check_sdk_availability()

    def _check_sdk_availability(self):
        """Check if Claude Code SDK is installed"""
        try:
            import claude_code_sdk  # noqa: F401

            self.sdk_available = True
        except ImportError:
            self.sdk_available = False

    def get_status(self) -> dict:
        """Get SDK availability and session status"""
        status = {
            "sdk_available": self.sdk_available,
            "session_active": self.client is not None,
            "cli_available": self._check_cli_available(),
        }

        if self.sdk_available:
            try:
                import claude_code_sdk

                status["sdk_version"] = getattr(claude_code_sdk, "__version__", "unknown")
            except Exception:
                pass

        return status

    def _check_cli_available(self) -> bool:
        """Check if Claude Code CLI is available"""
        try:
            result = subprocess.run(["claude", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except Exception:
            return False

    # ========== SDK Session Management ==========

    async def initialize_session(
        self,
        system_prompt: str | None = None,
        allowed_tools: list | None = None,
        permission_mode: str = "acceptEdits",
        max_turns: int = 10,
        mcp_servers: dict | None = None,
        cwd: str | None = None,
    ) -> dict:
        """Initialize a new SDK session with options"""
        if not self.sdk_available:
            return {"error": "Claude Code SDK not installed. Run: pip install claude-code-sdk"}

        try:
            from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient

            self.options = ClaudeCodeOptions(
                system_prompt=system_prompt,
                allowed_tools=allowed_tools or ["Read", "Write", "Bash", "Grep", "Glob"],
                permission_mode=permission_mode,
                max_turns=max_turns,
                mcp_servers=mcp_servers or {},
                cwd=Path(cwd) if cwd else None,
            )

            self.client = ClaudeSDKClient(options=self.options)

            return {
                "status": "initialized",
                "allowed_tools": allowed_tools or ["Read", "Write", "Bash", "Grep", "Glob"],
                "max_turns": max_turns,
                "permission_mode": permission_mode,
            }

        except Exception as e:
            return {"error": str(e)}

    async def close_session(self) -> dict:
        """Close the active SDK session"""
        if self.client:
            try:
                # ClaudeSDKClient should be used as context manager,
                # but we'll track state manually for the tool interface
                self.client = None
                self.options = None
                return {"status": "closed"}
            except Exception as e:
                return {"error": str(e)}
        return {"status": "no_active_session"}

    # ========== Query Operations ==========

    async def simple_query(self, prompt: str, options: dict | None = None) -> dict:
        """Send a simple stateless query"""
        if not self.sdk_available:
            return {"error": "Claude Code SDK not installed"}

        try:
            from claude_code_sdk import ClaudeCodeOptions, query

            query_options = None
            if options:
                query_options = ClaudeCodeOptions(**options)

            responses = []
            async for message in query(prompt=prompt, options=query_options):
                responses.append(self._format_message(message))

            return {"status": "completed", "responses": responses}

        except Exception as e:
            return {"error": str(e)}

    async def session_query(self, prompt: str) -> dict:
        """Send a query through the active session"""
        if not self.client:
            return {"error": "No active session. Call init_sdk first."}

        try:
            await self.client.query(prompt)

            responses = []
            async for message in self.client.receive_response():
                responses.append(self._format_message(message))

            return {"status": "completed", "responses": responses}

        except Exception as e:
            return {"error": str(e)}

    def _format_message(self, message) -> dict:
        """Format SDK message for display"""
        try:
            # Handle different message types
            msg_type = type(message).__name__

            if hasattr(message, "content"):
                content = message.content
                if isinstance(content, list):
                    # Extract text from content blocks
                    text_parts = []
                    for block in content:
                        if hasattr(block, "text"):
                            text_parts.append(block.text)
                        elif hasattr(block, "type") and block.type == "text":
                            text_parts.append(getattr(block, "text", str(block)))
                    content = "\n".join(text_parts)
                return {"type": msg_type, "content": content}

            return {"type": msg_type, "content": str(message)}

        except Exception as e:
            return {"type": "error", "content": str(e)}

    # ========== Tool Bridging ==========

    def create_sdk_tool(self, name: str, description: str, input_schema: dict, handler: Callable) -> Any:
        """
        Create an SDK tool from a handler function.

        This allows Agent Zero tools to be exposed to Claude Code via SDK.

        Example:
            def my_handler(args):
                return {"result": args["input"] * 2}

            tool = manager.create_sdk_tool(
                name="double",
                description="Double a number",
                input_schema={"input": int},
                handler=my_handler
            )
        """
        if not self.sdk_available:
            raise RuntimeError("Claude Code SDK not installed")

        from claude_code_sdk import tool

        @tool(name, description, input_schema)
        async def wrapped_handler(args):
            try:
                result = await handler(args) if asyncio.iscoroutinefunction(handler) else handler(args)
                return {
                    "content": [
                        {"type": "text", "text": json.dumps(result) if isinstance(result, dict) else str(result)}
                    ]
                }
            except Exception as e:
                return {"content": [{"type": "text", "text": f"Error: {e!s}"}], "isError": True}

        return wrapped_handler

    def create_mcp_server(self, name: str, version: str, tools: list) -> Any:
        """
        Create an in-process MCP server from a list of SDK tools.

        This is useful for exposing Agent Zero tools to Claude Code
        without running a separate server process.
        """
        if not self.sdk_available:
            raise RuntimeError("Claude Code SDK not installed")

        from claude_code_sdk import create_sdk_mcp_server

        return create_sdk_mcp_server(name=name, version=version, tools=tools)

    def export_agent_zero_tool(self, tool_name: str, tool_class) -> dict:
        """
        Export an Agent Zero tool as an SDK tool.

        This creates a wrapper that can be used with ClaudeSDKClient.
        """
        if not self.sdk_available:
            return {"error": "Claude Code SDK not installed"}

        try:
            # Create a handler that invokes the Agent Zero tool
            async def tool_handler(args):
                # This would need access to an agent instance
                # For now, return the schema info
                return {"tool_name": tool_name, "args_received": args, "note": "Tool execution requires agent context"}

            # Get tool info from class if available
            description = (
                getattr(tool_class, "__doc__", f"Agent Zero tool: {tool_name}") or f"Agent Zero tool: {tool_name}"
            )

            self.create_sdk_tool(
                name=f"az_{tool_name}",
                description=description[:200],
                input_schema={"action": str, "args": dict},
                handler=tool_handler,
            )

            return {"status": "exported", "sdk_name": f"az_{tool_name}", "original_name": tool_name}

        except Exception as e:
            return {"error": str(e)}

    # ========== CLI Operations ==========

    def run_cli_command(self, prompt: str, working_dir: str | None = None, timeout: int = 300) -> dict:
        """
        Run a command through Claude Code CLI directly.

        This bypasses the SDK and uses the CLI for simpler operations.
        """
        if not self._check_cli_available():
            return {"error": "Claude Code CLI not available"}

        try:
            cmd = ["claude", "-p", prompt]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=working_dir, timeout=timeout)

            return {
                "status": "completed" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr if result.returncode != 0 else None,
                "exit_code": result.returncode,
            }

        except subprocess.TimeoutExpired:
            return {"error": "Command timed out"}
        except Exception as e:
            return {"error": str(e)}

    # ========== MCP Bridge Operations ==========

    def get_mcp_server_config(
        self, server_name: str, command: str, args: list | None = None, env: dict | None = None
    ) -> dict:
        """
        Generate MCP server configuration for SDK.

        This creates a config dict that can be passed to ClaudeAgentOptions.mcp_servers
        """
        return {server_name: {"command": command, "args": args or [], "env": env or {}}}

    def bridge_external_mcp(self, server_name: str, server_type: str, config: dict) -> dict:
        """
        Set up an external MCP server to be used with SDK sessions.

        server_type can be: stdio, sse, http
        """
        if server_type == "stdio":
            return self.get_mcp_server_config(
                server_name=server_name,
                command=config.get("command"),
                args=config.get("args", []),
                env=config.get("env", {}),
            )
        elif server_type in ["sse", "http"]:
            return {server_name: {"url": config.get("url"), "headers": config.get("headers", {})}}
        else:
            return {"error": f"Unknown server type: {server_type}"}

    # ========== Utility Methods ==========

    def get_available_tools(self) -> list:
        """Get list of available SDK tools"""
        return ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "LS", "WebFetch", "WebSearch", "Task", "TodoWrite"]

    def install_sdk(self) -> dict:
        """Attempt to install Claude Agent SDK"""
        try:
            result = subprocess.run(["pip", "install", "claude-code-sdk"], capture_output=True, text=True, timeout=120)

            if result.returncode == 0:
                self._check_sdk_availability()
                return {"status": "installed", "output": result.stdout}
            else:
                return {"error": result.stderr}

        except Exception as e:
            return {"error": str(e)}
