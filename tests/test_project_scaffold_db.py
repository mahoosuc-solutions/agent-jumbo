import os

from instruments.custom.project_scaffold.scaffold_db import ScaffoldDatabase


def test_scaffold_db_roundtrip(tmp_path):
    db_path = os.path.join(tmp_path, "scaffold.db")
    db = ScaffoldDatabase(db_path)

    # Built-in templates are seeded on init
    builtins = db.list_templates(builtin_only=True)
    assert len(builtins) >= 6

    # Add a custom template
    tid = db.add_template(
        name="custom/flask",
        template_type="api",
        language="python",
        framework="flask",
        description="Flask API template",
        tags=["backend", "flask"],
        variables={"project_name": {"type": "string", "required": True}},
        structure={"src": ["app.py", "config.py"]},
        source_path="/templates/flask",
    )
    assert tid

    # Retrieve by name
    tmpl = db.get_template(name="custom/flask")
    assert tmpl is not None
    assert tmpl["language"] == "python"
    assert tmpl["framework"] == "flask"
    assert tmpl["tags"] == ["backend", "flask"]

    # Retrieve by id
    tmpl2 = db.get_template(template_id=tid)
    assert tmpl2["name"] == "custom/flask"

    # Filter templates
    python_templates = db.list_templates(language="python")
    assert any(t["name"] == "custom/flask" for t in python_templates)

    api_templates = db.list_templates(template_type="api")
    assert any(t["name"] == "custom/flask" for t in api_templates)

    # Add a project using the template
    pid = db.add_project(
        template_id=tid,
        name="my-flask-app",
        output_path="/projects/my-flask-app",
        variables_used={"project_name": "my-flask-app"},
        customer_id=42,
    )
    assert pid

    project = db.get_project(pid)
    assert project["name"] == "my-flask-app"
    assert project["template_id"] == tid
    assert project["variables_used"] == {"project_name": "my-flask-app"}

    # Update project status
    assert db.update_project_status(pid, "completed") is True
    updated = db.get_project(pid)
    assert updated["status"] == "completed"

    # List projects
    projects = db.list_projects(customer_id=42)
    assert len(projects) == 1

    # Add project file
    fid = db.add_project_file(pid, "src/app.py", file_type="python", template_source="app.py.j2")
    assert fid
    files = db.get_project_files(pid)
    assert len(files) == 1
    assert files[0]["file_path"] == "src/app.py"

    # Add component
    cid = db.add_component("auth_middleware", "middleware", "# auth code", variables={"secret_key": {"type": "string"}})
    assert cid
    comp = db.get_component("auth_middleware")
    assert comp["component_type"] == "middleware"
    components = db.list_components(component_type="middleware")
    assert len(components) == 1

    # Delete custom template (should succeed)
    assert db.delete_template(tid) is True

    # Delete built-in template (should fail)
    builtin_id = builtins[0]["template_id"]
    assert db.delete_template(builtin_id) is False
