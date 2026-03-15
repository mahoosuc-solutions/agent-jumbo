import os

from instruments.custom.deployment_orchestrator.deployment_db import DeploymentOrchestratorDatabase


def test_deployment_orchestrator_db_roundtrip(tmp_path):
    db_path = os.path.join(tmp_path, "deployment.db")
    db = DeploymentOrchestratorDatabase(db_path)

    # Register project
    project_id = db.register_project(
        name="my-api",
        project_path="/projects/my-api",
        project_type="web",
        language="python",
        framework="flask",
        metadata={"repo": "github.com/test/my-api"},
    )
    assert project_id

    project = db.get_project(project_id)
    assert project["name"] == "my-api"
    assert project["language"] == "python"
    assert project["metadata"] == {"repo": "github.com/test/my-api"}

    # List projects
    projects = db.list_projects()
    assert len(projects) == 1

    # Save pipeline
    pipeline_id = db.save_pipeline(
        project_id=project_id,
        platform="github-actions",
        name="CI Pipeline",
        config_path=".github/workflows/ci.yml",
        config_content="name: CI\non: push",
    )
    assert pipeline_id

    pipeline = db.get_pipeline(pipeline_id)
    assert pipeline["platform"] == "github-actions"
    assert pipeline["name"] == "CI Pipeline"

    pipelines = db.get_pipelines(project_id)
    assert len(pipelines) == 1

    # Save Docker config
    docker_id = db.save_docker_config(
        project_id=project_id,
        dockerfile_content="FROM python:3.11\nCOPY . /app",
        compose_content="version: '3'\nservices:\n  app:\n    build: .",
    )
    assert docker_id

    docker = db.get_docker_config(project_id)
    assert "FROM python:3.11" in docker["dockerfile_content"]
    assert docker["compose_content"] is not None

    # Save K8s manifest
    manifest_id = db.save_k8s_manifest(
        project_id=project_id,
        manifest_type="deployment",
        name="my-api-deployment",
        content="apiVersion: apps/v1\nkind: Deployment",
    )
    assert manifest_id

    manifests = db.get_k8s_manifests(project_id)
    assert len(manifests) == 1
    assert manifests[0]["manifest_type"] == "deployment"

    # Filtered by type
    deploy_manifests = db.get_k8s_manifests(project_id, manifest_type="deployment")
    assert len(deploy_manifests) == 1
    svc_manifests = db.get_k8s_manifests(project_id, manifest_type="service")
    assert len(svc_manifests) == 0

    # Create environment
    env_id = db.create_environment(
        project_id=project_id,
        name="staging",
        env_type="staging",
        config={"replicas": 2},
        secrets={"DB_PASSWORD": "***"},
    )
    assert env_id

    env = db.get_environment(env_id)
    assert env["name"] == "staging"
    assert env["config"] == {"replicas": 2}

    envs = db.get_environments(project_id)
    assert len(envs) == 1

    # Create deployment
    deploy_id = db.create_deployment(
        project_id=project_id,
        environment_id=env_id,
        version="1.0.0",
    )
    assert deploy_id

    deployment = db.get_deployment(deploy_id)
    assert deployment["status"] == "pending"
    assert deployment["version"] == "1.0.0"

    # Update deployment status
    db.update_deployment_status(deploy_id, "completed", logs="All checks passed")
    updated = db.get_deployment(deploy_id)
    assert updated["status"] == "completed"
    assert updated["logs"] == "All checks passed"
    assert updated["completed_at"] is not None

    # List deployments
    deployments = db.get_deployments(project_id)
    assert len(deployments) == 1

    # Latest deployment
    latest = db.get_latest_deployment(project_id)
    assert latest["deployment_id"] == deploy_id
