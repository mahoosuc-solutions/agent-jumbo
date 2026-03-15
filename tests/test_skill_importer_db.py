import os

from instruments.custom.skill_importer.skill_db import SkillDatabase


def test_skill_importer_db_roundtrip(tmp_path):
    db_path = os.path.join(tmp_path, "skills.db")
    db = SkillDatabase(db_path)

    # Add a skill
    skill_id = db.add_skill(
        name="code_review",
        source_path="/skills/code_review.md",
        description="Automated code review skill",
        arguments={"files": {"type": "list"}},
        tool_requirements=["Read", "Grep"],
        content="Review code for quality",
        frontmatter={"version": "1.0"},
        category="development",
    )
    assert skill_id

    # Get skill by name
    skill = db.get_skill(name="code_review")
    assert skill is not None
    assert skill["description"] == "Automated code review skill"
    assert skill["arguments"] == {"files": {"type": "list"}}
    assert skill["tool_requirements"] == ["Read", "Grep"]
    assert skill["category"] == "development"

    # Get skill by id
    skill2 = db.get_skill(skill_id=skill_id)
    assert skill2["name"] == "code_review"

    # Update skill
    assert db.update_skill(skill_id, description="Updated description", enabled=0) is True
    updated = db.get_skill(skill_id=skill_id)
    assert updated["description"] == "Updated description"
    assert updated["enabled"] == 0

    # List skills (enabled_only=True should exclude disabled)
    skills = db.list_skills(enabled_only=True)
    assert len(skills) == 0

    # Re-enable and list
    db.update_skill(skill_id, enabled=1)
    skills = db.list_skills(enabled_only=True, category="development")
    assert len(skills) == 1

    # Record execution
    exec_id = db.record_execution(
        skill_id=skill_id,
        input_args={"files": ["main.py"]},
        output="LGTM",
        status="success",
        duration_ms=1234.5,
    )
    assert exec_id

    # Get execution stats
    stats = db.get_execution_stats(skill_id=skill_id)
    assert stats["total_executions"] == 1
    assert stats["successful"] == 1
    assert stats["avg_duration_ms"] == 1234.5

    # Register generated tool
    tool_id = db.register_generated_tool(skill_id, "/tools/code_review.py", "/prompts/code_review.md")
    assert tool_id

    # Add plugin
    plugin_id = db.add_plugin(
        name="test-plugin",
        source_path="/plugins/test",
        description="Test plugin",
        version="1.0.0",
        manifest={"skills": ["code_review"]},
    )
    assert plugin_id

    plugin = db.get_plugin(name="test-plugin")
    assert plugin["version"] == "1.0.0"
    assert plugin["manifest"] == {"skills": ["code_review"]}

    # Update plugin counts
    assert db.update_plugin_counts(plugin_id, skills=1, hooks=2) is True

    plugins = db.list_plugins()
    assert len(plugins) == 1
    assert plugins[0]["skills_count"] == 1

    # Add hook
    hook_id = db.add_hook(plugin_id, "pre-commit", "PreCommit", "validation", "check lint")
    assert hook_id
    hooks = db.list_hooks(plugin_id=plugin_id)
    assert len(hooks) == 1

    # Add agent
    agent_id = db.add_agent(plugin_id, "reviewer", "Code reviewer", "You review code", ["Read", "Grep"], "gpt-4")
    assert agent_id
    agents = db.list_agents(plugin_id=plugin_id)
    assert len(agents) == 1

    # Add MCP server
    server_id = db.add_mcp_server(plugin_id, "local-mcp", "stdio", {"command": "node", "args": ["server.js"]})
    assert server_id
    servers = db.list_mcp_servers(plugin_id=plugin_id)
    assert len(servers) == 1

    # Delete skill
    assert db.delete_skill(skill_id) is True
    assert db.get_skill(skill_id=skill_id) is None

    # Delete plugin (cascades)
    assert db.delete_plugin(plugin_id) is True
    assert db.get_plugin(plugin_id=plugin_id) is None
