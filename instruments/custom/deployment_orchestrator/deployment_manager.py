"""
Deployment Orchestrator Manager - Business logic for CI/CD and deployment automation
Generates pipelines, Docker configs, Kubernetes manifests, and manages deployments
"""

import json
from pathlib import Path

from .deployment_db import DeploymentOrchestratorDatabase


class DeploymentOrchestratorManager:
    """Manager for deployment orchestration"""

    # Supported CI/CD platforms
    CICD_PLATFORMS = ["github_actions", "gitlab_ci", "azure_pipelines"]

    # Language-specific configurations
    LANGUAGE_CONFIGS = {
        "python": {
            "base_image": "python:3.11-slim",
            "install_cmd": "pip install -r requirements.txt",
            "test_cmd": "pytest",
            "lint_cmd": "ruff check .",
        },
        "javascript": {
            "base_image": "node:20-alpine",
            "install_cmd": "npm ci",
            "test_cmd": "npm test",
            "lint_cmd": "npm run lint",
        },
        "typescript": {
            "base_image": "node:20-alpine",
            "install_cmd": "npm ci",
            "test_cmd": "npm test",
            "lint_cmd": "npm run lint",
            "build_cmd": "npm run build",
        },
        "go": {
            "base_image": "golang:1.21-alpine",
            "install_cmd": "go mod download",
            "test_cmd": "go test ./...",
            "lint_cmd": "golangci-lint run",
            "build_cmd": "go build -o app .",
        },
    }

    def __init__(self, db_path: str):
        self.db = DeploymentOrchestratorDatabase(db_path)

    # ========== Project Operations ==========

    def register_project(
        self,
        name: str,
        project_path: str,
        project_type: str | None = None,
        language: str | None = None,
        framework: str | None = None,
    ) -> dict:
        """Register a project for deployment management"""
        # Auto-detect language if not provided
        if not language:
            language = self._detect_language(project_path)

        project_id = self.db.register_project(
            name=name, project_path=project_path, project_type=project_type, language=language, framework=framework
        )

        return {
            "project_id": project_id,
            "name": name,
            "project_path": project_path,
            "language": language,
            "framework": framework,
        }

    def _detect_language(self, project_path: str) -> str:
        """Auto-detect project language"""
        path = Path(project_path)

        if (path / "requirements.txt").exists() or (path / "setup.py").exists():
            return "python"
        elif (path / "package.json").exists():
            pkg_json = path / "package.json"
            try:
                with open(pkg_json) as f:
                    pkg = json.load(f)
                    if "typescript" in str(pkg.get("devDependencies", {})):
                        return "typescript"
            except Exception:
                pass
            return "javascript"
        elif (path / "go.mod").exists():
            return "go"
        elif (path / "Cargo.toml").exists():
            return "rust"

        return "unknown"

    def get_project(self, project_id: int) -> dict:
        """Get project details"""
        return self.db.get_project(project_id)

    def list_projects(self) -> list:
        """List all registered projects"""
        return self.db.list_projects()

    # ========== CI/CD Pipeline Generation ==========

    def generate_cicd(
        self,
        project_id: int,
        platform: str = "github_actions",
        include_tests: bool = True,
        include_lint: bool = True,
        include_build: bool = True,
        deploy_env: str | None = None,
    ) -> dict:
        """Generate CI/CD pipeline configuration"""
        project = self.db.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        if platform not in self.CICD_PLATFORMS:
            return {"error": f"Unsupported platform: {platform}. Supported: {', '.join(self.CICD_PLATFORMS)}"}

        language = project.get("language", "python")
        lang_config = self.LANGUAGE_CONFIGS.get(language, self.LANGUAGE_CONFIGS["python"])

        if platform == "github_actions":
            config = self._generate_github_actions(
                project, lang_config, include_tests, include_lint, include_build, deploy_env
            )
            config_path = ".github/workflows/ci.yml"
        elif platform == "gitlab_ci":
            config = self._generate_gitlab_ci(
                project, lang_config, include_tests, include_lint, include_build, deploy_env
            )
            config_path = ".gitlab-ci.yml"
        elif platform == "azure_pipelines":
            config = self._generate_azure_pipelines(
                project, lang_config, include_tests, include_lint, include_build, deploy_env
            )
            config_path = "azure-pipelines.yml"

        # Save to database
        pipeline_id = self.db.save_pipeline(
            project_id=project_id,
            platform=platform,
            name=f"{project['name']} CI/CD",
            config_path=config_path,
            config_content=config,
        )

        return {"pipeline_id": pipeline_id, "platform": platform, "config_path": config_path, "config_content": config}

    def _generate_github_actions(
        self,
        project: dict,
        lang_config: dict,
        include_tests: bool,
        include_lint: bool,
        include_build: bool,
        deploy_env: str,
    ) -> str:
        """Generate GitHub Actions workflow"""
        language = project.get("language", "python")

        lines = [
            f"name: CI/CD for {project['name']}",
            "",
            "on:",
            "  push:",
            "    branches: [main, develop]",
            "  pull_request:",
            "    branches: [main]",
            "",
            "jobs:",
        ]

        # Test job
        if include_tests or include_lint:
            lines.extend(
                [
                    "  test:",
                    "    runs-on: ubuntu-latest",
                    "    steps:",
                    "      - uses: actions/checkout@v4",
                    "",
                ]
            )

            if language == "python":
                lines.extend(
                    [
                        "      - name: Set up Python",
                        "        uses: actions/setup-python@v5",
                        "        with:",
                        "          python-version: '3.11'",
                        "",
                        "      - name: Install dependencies",
                        f"        run: {lang_config['install_cmd']}",
                        "",
                    ]
                )
            elif language in ["javascript", "typescript"]:
                lines.extend(
                    [
                        "      - name: Set up Node.js",
                        "        uses: actions/setup-node@v4",
                        "        with:",
                        "          node-version: '20'",
                        "          cache: 'npm'",
                        "",
                        "      - name: Install dependencies",
                        f"        run: {lang_config['install_cmd']}",
                        "",
                    ]
                )
            elif language == "go":
                lines.extend(
                    [
                        "      - name: Set up Go",
                        "        uses: actions/setup-go@v5",
                        "        with:",
                        "          go-version: '1.21'",
                        "",
                    ]
                )

            if include_lint and lang_config.get("lint_cmd"):
                lines.extend(
                    [
                        "      - name: Lint",
                        f"        run: {lang_config['lint_cmd']}",
                        "",
                    ]
                )

            if include_tests:
                lines.extend(
                    [
                        "      - name: Run tests",
                        f"        run: {lang_config['test_cmd']}",
                        "",
                    ]
                )

        # Build job
        if include_build and lang_config.get("build_cmd"):
            lines.extend(
                [
                    "  build:",
                    "    runs-on: ubuntu-latest",
                    "    needs: test" if (include_tests or include_lint) else "    runs-on: ubuntu-latest",
                    "    steps:",
                    "      - uses: actions/checkout@v4",
                    "",
                    "      - name: Build",
                    f"        run: {lang_config['build_cmd']}",
                    "",
                ]
            )

        # Deploy job
        if deploy_env:
            lines.extend(
                [
                    f"  deploy-{deploy_env}:",
                    "    runs-on: ubuntu-latest",
                    "    needs: [test, build]" if include_build else "    needs: test",
                    "    if: github.ref == 'refs/heads/main'",
                    f"    environment: {deploy_env}",
                    "    steps:",
                    "      - uses: actions/checkout@v4",
                    "",
                    "      - name: Deploy",
                    "        run: |",
                    f"          echo 'Deploying to {deploy_env}'",
                    "          # Add deployment commands here",
                    "",
                ]
            )

        return "\n".join(lines)

    def _generate_gitlab_ci(
        self,
        project: dict,
        lang_config: dict,
        include_tests: bool,
        include_lint: bool,
        include_build: bool,
        deploy_env: str,
    ) -> str:
        """Generate GitLab CI configuration"""
        project.get("language", "python")

        lines = [
            "stages:",
            "  - test",
            "  - build",
            "  - deploy",
            "",
            "variables:",
            f"  PROJECT_NAME: {project['name']}",
            "",
        ]

        # Test stage
        if include_tests or include_lint:
            lines.extend(
                [
                    "test:",
                    "  stage: test",
                    f"  image: {lang_config['base_image']}",
                    "  script:",
                    f"    - {lang_config['install_cmd']}",
                ]
            )

            if include_lint and lang_config.get("lint_cmd"):
                lines.append(f"    - {lang_config['lint_cmd']}")

            if include_tests:
                lines.append(f"    - {lang_config['test_cmd']}")

            lines.append("")

        # Build stage
        if include_build and lang_config.get("build_cmd"):
            lines.extend(
                [
                    "build:",
                    "  stage: build",
                    f"  image: {lang_config['base_image']}",
                    "  script:",
                    f"    - {lang_config['install_cmd']}",
                    f"    - {lang_config['build_cmd']}",
                    "  artifacts:",
                    "    paths:",
                    "      - dist/",
                    "",
                ]
            )

        # Deploy stage
        if deploy_env:
            lines.extend(
                [
                    f"deploy-{deploy_env}:",
                    "  stage: deploy",
                    f"  environment: {deploy_env}",
                    "  script:",
                    f"    - echo 'Deploying to {deploy_env}'",
                    "  only:",
                    "    - main",
                    "",
                ]
            )

        return "\n".join(lines)

    def _generate_azure_pipelines(
        self,
        project: dict,
        lang_config: dict,
        include_tests: bool,
        include_lint: bool,
        include_build: bool,
        deploy_env: str,
    ) -> str:
        """Generate Azure Pipelines configuration"""
        language = project.get("language", "python")

        lines = [
            "trigger:",
            "  - main",
            "  - develop",
            "",
            "pool:",
            "  vmImage: 'ubuntu-latest'",
            "",
            "stages:",
        ]

        # Test stage
        if include_tests or include_lint:
            lines.extend(
                [
                    "  - stage: Test",
                    "    jobs:",
                    "      - job: Test",
                    "        steps:",
                ]
            )

            if language == "python":
                lines.extend(
                    [
                        "          - task: UsePythonVersion@0",
                        "            inputs:",
                        "              versionSpec: '3.11'",
                        "",
                        "          - script: |",
                        f"              {lang_config['install_cmd']}",
                        "            displayName: 'Install dependencies'",
                    ]
                )
            elif language in ["javascript", "typescript"]:
                lines.extend(
                    [
                        "          - task: NodeTool@0",
                        "            inputs:",
                        "              versionSpec: '20.x'",
                        "",
                        "          - script: |",
                        f"              {lang_config['install_cmd']}",
                        "            displayName: 'Install dependencies'",
                    ]
                )

            if include_lint and lang_config.get("lint_cmd"):
                lines.extend(
                    [
                        "",
                        "          - script: |",
                        f"              {lang_config['lint_cmd']}",
                        "            displayName: 'Lint'",
                    ]
                )

            if include_tests:
                lines.extend(
                    [
                        "",
                        "          - script: |",
                        f"              {lang_config['test_cmd']}",
                        "            displayName: 'Run tests'",
                    ]
                )

            lines.append("")

        # Build stage
        if include_build and lang_config.get("build_cmd"):
            lines.extend(
                [
                    "  - stage: Build",
                    "    dependsOn: Test",
                    "    jobs:",
                    "      - job: Build",
                    "        steps:",
                    "          - script: |",
                    f"              {lang_config['build_cmd']}",
                    "            displayName: 'Build'",
                    "",
                ]
            )

        return "\n".join(lines)

    def get_pipeline(self, pipeline_id: int) -> dict:
        """Get pipeline details"""
        return self.db.get_pipeline(pipeline_id)

    def list_pipelines(self, project_id: int) -> list:
        """List pipelines for a project"""
        return self.db.get_pipelines(project_id)

    # ========== Docker Generation ==========

    def generate_docker(
        self, project_id: int, port: int = 8000, include_compose: bool = True, multi_stage: bool = True
    ) -> dict:
        """Generate Docker configuration"""
        project = self.db.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        language = project.get("language", "python")
        lang_config = self.LANGUAGE_CONFIGS.get(language, self.LANGUAGE_CONFIGS["python"])

        # Generate Dockerfile
        if multi_stage:
            dockerfile = self._generate_multistage_dockerfile(project, lang_config, port)
        else:
            dockerfile = self._generate_simple_dockerfile(project, lang_config, port)

        # Generate docker-compose
        compose = None
        if include_compose:
            compose = self._generate_docker_compose(project, port)

        # Generate .dockerignore
        dockerignore = self._generate_dockerignore(language)

        # Save to database
        config_id = self.db.save_docker_config(
            project_id=project_id,
            dockerfile_content=dockerfile,
            compose_content=compose,
            dockerignore_content=dockerignore,
        )

        return {
            "config_id": config_id,
            "dockerfile": dockerfile,
            "docker_compose": compose,
            "dockerignore": dockerignore,
        }

    def _generate_simple_dockerfile(self, project: dict, lang_config: dict, port: int) -> str:
        """Generate a simple Dockerfile"""
        language = project.get("language", "python")

        if language == "python":
            return f"""FROM {lang_config["base_image"]}

WORKDIR /app

COPY requirements.txt .
RUN {lang_config["install_cmd"]}

COPY . .

EXPOSE {port}

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
"""
        elif language in ["javascript", "typescript"]:
            return f"""FROM {lang_config["base_image"]}

WORKDIR /app

COPY package*.json ./
RUN {lang_config["install_cmd"]}

COPY . .
{"RUN npm run build" if language == "typescript" else ""}

EXPOSE {port}

CMD ["node", "dist/index.js"]
"""
        elif language == "go":
            return f"""FROM {lang_config["base_image"]}

WORKDIR /app

COPY go.mod go.sum ./
RUN {lang_config["install_cmd"]}

COPY . .
RUN {lang_config["build_cmd"]}

EXPOSE {port}

CMD ["./app"]
"""

        return f"""FROM ubuntu:22.04

WORKDIR /app
COPY . .
EXPOSE {port}
CMD ["./start.sh"]
"""

    def _generate_multistage_dockerfile(self, project: dict, lang_config: dict, port: int) -> str:
        """Generate a multi-stage Dockerfile"""
        language = project.get("language", "python")

        if language == "python":
            return f"""# Build stage
FROM {lang_config["base_image"]} AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --user -r requirements.txt

COPY . .

# Production stage
FROM {lang_config["base_image"]}

WORKDIR /app

COPY --from=builder /root/.local /root/.local
COPY --from=builder /app .

ENV PATH=/root/.local/bin:$PATH

EXPOSE {port}

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
"""
        elif language in ["javascript", "typescript"]:
            return f"""# Build stage
FROM {lang_config["base_image"]} AS builder

WORKDIR /app

COPY package*.json ./
RUN {lang_config["install_cmd"]}

COPY . .
RUN npm run build

# Production stage
FROM {lang_config["base_image"]}

WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package*.json ./

EXPOSE {port}

CMD ["node", "dist/index.js"]
"""
        elif language == "go":
            return f"""# Build stage
FROM {lang_config["base_image"]} AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN {lang_config["install_cmd"]}

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o app .

# Production stage
FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/app .

EXPOSE {port}

CMD ["./app"]
"""

        return self._generate_simple_dockerfile(project, lang_config, port)

    def _generate_docker_compose(self, project: dict, port: int) -> str:
        """Generate docker-compose.yml"""
        name = project["name"].lower().replace(" ", "-")

        return f"""version: '3.8'

services:
  {name}:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - NODE_ENV=production
    volumes:
      - .:/app
      - /app/node_modules
    restart: unless-stopped

  # Optional: Add database service
  # db:
  #   image: postgres:15
  #   environment:
  #     POSTGRES_DB: {name}
  #     POSTGRES_USER: user
  #     POSTGRES_PASSWORD: password
  #   volumes:
  #     - postgres_data:/var/lib/postgresql/data

# volumes:
#   postgres_data:
"""

    def _generate_dockerignore(self, language: str) -> str:
        """Generate .dockerignore"""
        common = [
            ".git",
            ".gitignore",
            "README.md",
            "*.md",
            ".env*",
            "*.log",
            ".DS_Store",
        ]

        if language == "python":
            common.extend(
                [
                    "__pycache__",
                    "*.pyc",
                    ".pytest_cache",
                    ".venv",
                    "venv",
                    "*.egg-info",
                    ".ruff_cache",
                ]
            )
        elif language in ["javascript", "typescript"]:
            common.extend(
                [
                    "node_modules",
                    ".next",
                    "dist",
                    "coverage",
                    ".turbo",
                ]
            )
        elif language == "go":
            common.extend(
                [
                    "*.test",
                    "vendor",
                ]
            )

        return "\n".join(common)

    def get_docker_config(self, project_id: int) -> dict:
        """Get Docker configuration"""
        return self.db.get_docker_config(project_id)

    # ========== Kubernetes Generation ==========

    def generate_k8s(
        self,
        project_id: int,
        replicas: int = 2,
        port: int = 8000,
        namespace: str = "default",
        include_service: bool = True,
        include_ingress: bool = False,
    ) -> dict:
        """Generate Kubernetes manifests"""
        project = self.db.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        name = project["name"].lower().replace(" ", "-")
        manifests = []

        # Deployment
        deployment = self._generate_k8s_deployment(name, replicas, port, namespace)
        manifest_id = self.db.save_k8s_manifest(
            project_id=project_id, manifest_type="deployment", name=f"{name}-deployment", content=deployment
        )
        manifests.append({"type": "deployment", "manifest_id": manifest_id, "content": deployment})

        # Service
        if include_service:
            service = self._generate_k8s_service(name, port, namespace)
            manifest_id = self.db.save_k8s_manifest(
                project_id=project_id, manifest_type="service", name=f"{name}-service", content=service
            )
            manifests.append({"type": "service", "manifest_id": manifest_id, "content": service})

        # Ingress
        if include_ingress:
            ingress = self._generate_k8s_ingress(name, namespace)
            manifest_id = self.db.save_k8s_manifest(
                project_id=project_id, manifest_type="ingress", name=f"{name}-ingress", content=ingress
            )
            manifests.append({"type": "ingress", "manifest_id": manifest_id, "content": ingress})

        return {"project_id": project_id, "namespace": namespace, "manifests": manifests}

    def _generate_k8s_deployment(self, name: str, replicas: int, port: int, namespace: str) -> str:
        """Generate Kubernetes Deployment"""
        return f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {name}
  namespace: {namespace}
  labels:
    app: {name}
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {name}
  template:
    metadata:
      labels:
        app: {name}
    spec:
      containers:
        - name: {name}
          image: {name}:latest
          ports:
            - containerPort: {port}
          resources:
            requests:
              memory: "128Mi"
              cpu: "100m"
            limits:
              memory: "256Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: {port}
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: {port}
            initialDelaySeconds: 5
            periodSeconds: 5
"""

    def _generate_k8s_service(self, name: str, port: int, namespace: str) -> str:
        """Generate Kubernetes Service"""
        return f"""apiVersion: v1
kind: Service
metadata:
  name: {name}
  namespace: {namespace}
spec:
  selector:
    app: {name}
  ports:
    - protocol: TCP
      port: 80
      targetPort: {port}
  type: ClusterIP
"""

    def _generate_k8s_ingress(self, name: str, namespace: str) -> str:
        """Generate Kubernetes Ingress"""
        return f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {name}
  namespace: {namespace}
  annotations:
    kubernetes.io/ingress.class: nginx
spec:
  rules:
    - host: {name}.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {name}
                port:
                  number: 80
"""

    def get_k8s_manifests(self, project_id: int, manifest_type: str | None = None) -> list:
        """Get Kubernetes manifests"""
        return self.db.get_k8s_manifests(project_id, manifest_type)

    # ========== Environment Operations ==========

    def setup_environment(
        self, project_id: int, name: str, env_type: str = "staging", config: dict | None = None
    ) -> dict:
        """Set up a deployment environment"""
        env_id = self.db.create_environment(project_id=project_id, name=name, env_type=env_type, config=config)

        return {"environment_id": env_id, "name": name, "env_type": env_type, "config": config}

    def get_environment(self, environment_id: int) -> dict:
        """Get environment details"""
        return self.db.get_environment(environment_id)

    def list_environments(self, project_id: int) -> list:
        """List environments for a project"""
        return self.db.get_environments(project_id)

    # ========== Deployment Operations ==========

    def get_deployment_dashboard(self, project_id: int) -> dict:
        """Get deployment dashboard for a project"""
        project = self.db.get_project(project_id)
        if not project:
            return {"error": "Project not found"}

        environments = self.db.get_environments(project_id)
        pipelines = self.db.get_pipelines(project_id)
        deployments = self.db.get_deployments(project_id, limit=10)

        # Get latest deployment per environment
        env_status = []
        for env in environments:
            latest = self.db.get_latest_deployment(project_id, env["environment_id"])
            env_status.append(
                {
                    "environment": env["name"],
                    "env_type": env["env_type"],
                    "latest_version": latest.get("version") if latest else None,
                    "status": latest.get("status") if latest else "never_deployed",
                    "last_deployed": latest.get("completed_at") if latest else None,
                }
            )

        return {
            "project_id": project_id,
            "project_name": project["name"],
            "language": project.get("language"),
            "environments": env_status,
            "pipelines": len(pipelines),
            "recent_deployments": deployments,
        }

    def health_check(self, project_id: int, environment_id: int | None = None) -> dict:
        """Check health status of deployments"""
        latest = self.db.get_latest_deployment(project_id, environment_id)

        if not latest:
            return {"status": "no_deployments", "message": "No deployments found"}

        return {
            "deployment_id": latest["deployment_id"],
            "version": latest.get("version"),
            "status": latest["status"],
            "started_at": latest["started_at"],
            "completed_at": latest.get("completed_at"),
            "healthy": latest["status"] == "completed",
        }

    def list_deployments(self, project_id: int, limit: int = 10) -> list:
        """List recent deployments"""
        return self.db.get_deployments(project_id, limit)
