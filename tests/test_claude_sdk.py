from instruments.custom.claude_sdk.sdk_manager import ClaudeSDKManager


def test_claude_sdk_manager_roundtrip():
    manager = ClaudeSDKManager()

    # Status check (SDK likely not installed in test env)
    status = manager.get_status()
    assert "sdk_available" in status
    assert "session_active" in status
    assert "cli_available" in status
    assert status["session_active"] is False

    # Available tools list
    tools = manager.get_available_tools()
    assert isinstance(tools, list)
    assert "Read" in tools
    assert "Bash" in tools

    # MCP server config generation (pure logic, no SDK required)
    config = manager.get_mcp_server_config(
        server_name="test-server",
        command="node",
        args=["server.js"],
        env={"PORT": "3000"},
    )
    assert "test-server" in config
    assert config["test-server"]["command"] == "node"
    assert config["test-server"]["args"] == ["server.js"]
    assert config["test-server"]["env"] == {"PORT": "3000"}

    # Bridge external MCP - stdio
    stdio_config = manager.bridge_external_mcp(
        server_name="stdio-server",
        server_type="stdio",
        config={"command": "python", "args": ["-m", "server"], "env": {}},
    )
    assert "stdio-server" in stdio_config
    assert stdio_config["stdio-server"]["command"] == "python"

    # Bridge external MCP - sse
    sse_config = manager.bridge_external_mcp(
        server_name="sse-server",
        server_type="sse",
        config={"url": "http://localhost:8080/sse"},
    )
    assert "sse-server" in sse_config
    assert sse_config["sse-server"]["url"] == "http://localhost:8080/sse"

    # Unknown server type
    err_config = manager.bridge_external_mcp(
        server_name="bad",
        server_type="unknown",
        config={},
    )
    assert "error" in err_config
