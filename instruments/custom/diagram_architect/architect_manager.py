"""
Diagram Architect Manager - Business logic for architecture analysis and diagram generation
Analyzes codebases to detect components, relationships, and generates architecture diagrams
"""

import json
import os
import re
from pathlib import Path

from .architect_db import DiagramArchitectDatabase


class DiagramArchitectManager:
    """Manager for architecture analysis and diagram generation"""

    # File patterns for component detection
    COMPONENT_PATTERNS = {
        "service": [
            r"class\s+(\w+)Service",
            r"(\w+)Service\s*=",
            r"def\s+(\w+)_service",
        ],
        "controller": [
            r"class\s+(\w+)Controller",
            r'@Controller\s*\(\s*[\'"]([^\'"]+)',
            r"router\s*=\s*APIRouter",
        ],
        "model": [
            r"class\s+(\w+)\(.*Model\)",
            r"class\s+(\w+)\(.*Base\)",
            r"@Entity",
            r"class\s+(\w+)Schema",
        ],
        "repository": [
            r"class\s+(\w+)Repository",
            r"class\s+(\w+)DAO",
        ],
        "middleware": [
            r"class\s+(\w+)Middleware",
            r"@middleware",
        ],
        "api_endpoint": [
            r'@app\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)',
            r'@router\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)',
            r'app\.(get|post|put|delete|patch)\s*\(\s*[\'"]([^\'"]+)',
        ],
        "database": [
            r"create_engine\s*\(",
            r"sqlite3\.connect",
            r"MongoClient\s*\(",
            r"redis\.Redis",
            r"psycopg2\.connect",
        ],
        "queue": [
            r"pika\..*Connection",
            r"kafka\..*Producer",
            r"celery\.Celery",
        ],
        "cache": [
            r"redis\.Redis",
            r"memcache",
            r"@cache",
        ],
    }

    # External integration patterns
    INTEGRATION_PATTERNS = {
        "http_api": [
            (r'requests\.(get|post|put|delete)\s*\(\s*[\'"]([^\'"]+)', "requests"),
            (r'httpx\.(get|post|put|delete)\s*\(\s*[\'"]([^\'"]+)', "httpx"),
            (r'fetch\s*\(\s*[\'"]([^\'"]+)', "fetch"),
            (r'axios\.(get|post|put|delete)\s*\(\s*[\'"]([^\'"]+)', "axios"),
        ],
        "websocket": [
            (r"websocket\.WebSocket", "websocket"),
            (r"socketio", "socketio"),
        ],
        "grpc": [
            (r"grpc\.", "grpc"),
        ],
        "smtp": [
            (r"smtplib\.SMTP", "smtp"),
            (r"sendgrid", "sendgrid"),
        ],
        "cloud_storage": [
            (r'boto3\.client\s*\(\s*[\'"]s3', "aws_s3"),
            (r"storage\.Client", "gcs"),
            (r"BlobServiceClient", "azure_blob"),
        ],
        "authentication": [
            (r"OAuth", "oauth"),
            (r"jwt\.", "jwt"),
            (r"firebase", "firebase"),
        ],
    }

    # File type patterns
    FILE_PATTERNS = {
        "python": ["*.py"],
        "javascript": ["*.js", "*.jsx", "*.ts", "*.tsx"],
        "go": ["*.go"],
        "java": ["*.java"],
        "config": ["*.yaml", "*.yml", "*.json", "*.toml", "*.env*"],
        "docker": ["Dockerfile*", "docker-compose*"],
    }

    def __init__(self, db_path: str):
        self.db = DiagramArchitectDatabase(db_path)

    # ========== Analysis Operations ==========

    def analyze_architecture(self, project_path: str, analysis_type: str = "full") -> dict:
        """Perform full architecture analysis of a project"""
        if not os.path.isdir(project_path):
            return {"error": f"Project path does not exist: {project_path}"}

        project_name = Path(project_path).name

        # Create analysis record
        analysis_id = self.db.create_analysis(
            project_path=project_path, project_name=project_name, analysis_type=analysis_type
        )

        try:
            self.db.update_analysis_status(analysis_id, "analyzing")

            # Detect components
            components = self._detect_components(project_path, analysis_id)

            # Detect relationships between components
            relationships = self._detect_relationships(analysis_id)

            # Detect external integrations
            integrations = self._detect_integrations(project_path, analysis_id)

            # Detect data flows
            data_flows = self._detect_data_flows(project_path, analysis_id)

            self.db.update_analysis_status(analysis_id, "completed")

            return {
                "analysis_id": analysis_id,
                "project_name": project_name,
                "project_path": project_path,
                "components": len(components),
                "relationships": len(relationships),
                "integrations": len(integrations),
                "data_flows": len(data_flows),
                "status": "completed",
            }

        except Exception as e:
            self.db.update_analysis_status(analysis_id, "failed")
            return {"error": str(e), "analysis_id": analysis_id}

    def get_analysis(self, analysis_id: int) -> dict:
        """Get analysis details"""
        return self.db.get_analysis(analysis_id)

    def list_analyses(self, project_path: str | None = None) -> list:
        """List all analyses"""
        return self.db.list_analyses(project_path)

    # ========== Component Detection ==========

    def _detect_components(self, project_path: str, analysis_id: int) -> list:
        """Detect software components in the project"""
        components = []

        # Scan Python files
        for py_file in Path(project_path).rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                content = py_file.read_text(errors="ignore")
                file_components = self._extract_components_from_content(content, str(py_file), analysis_id)
                components.extend(file_components)
            except Exception:
                continue

        # Scan JavaScript/TypeScript files
        for pattern in ["*.js", "*.ts", "*.jsx", "*.tsx"]:
            for js_file in Path(project_path).rglob(pattern):
                if self._should_skip_file(js_file):
                    continue

                try:
                    content = js_file.read_text(errors="ignore")
                    file_components = self._extract_components_from_content(content, str(js_file), analysis_id)
                    components.extend(file_components)
                except Exception:
                    continue

        # Detect infrastructure components
        infra_components = self._detect_infrastructure(project_path, analysis_id)
        components.extend(infra_components)

        return components

    def _extract_components_from_content(self, content: str, file_path: str, analysis_id: int) -> list:
        """Extract components from file content"""
        components = []

        for comp_type, patterns in self.COMPONENT_PATTERNS.items():
            for pattern in patterns:
                matches = re.findall(pattern, content, re.MULTILINE)
                for match in matches:
                    # Handle tuple matches from grouped patterns
                    name = match[1] if isinstance(match, tuple) else match
                    if name and len(name) > 1:
                        comp_id = self.db.add_component(
                            analysis_id=analysis_id,
                            name=name,
                            component_type=comp_type,
                            file_path=file_path,
                            properties={"pattern": pattern},
                        )
                        components.append({"component_id": comp_id, "name": name, "type": comp_type, "file": file_path})

        return components

    def _detect_infrastructure(self, project_path: str, analysis_id: int) -> list:
        """Detect infrastructure components from config files"""
        components = []

        # Check for Docker
        docker_files = list(Path(project_path).glob("**/Dockerfile*"))
        docker_compose = list(Path(project_path).glob("**/docker-compose*"))

        if docker_files or docker_compose:
            comp_id = self.db.add_component(
                analysis_id=analysis_id,
                name="Docker",
                component_type="container",
                description="Containerization",
                properties={"dockerfile_count": len(docker_files), "compose_count": len(docker_compose)},
            )
            components.append({"component_id": comp_id, "name": "Docker", "type": "container"})

        # Check for Kubernetes
        k8s_files = list(Path(project_path).glob("**/k8s/**/*.yaml"))
        k8s_files.extend(Path(project_path).glob("**/kubernetes/**/*.yaml"))

        if k8s_files:
            comp_id = self.db.add_component(
                analysis_id=analysis_id,
                name="Kubernetes",
                component_type="orchestration",
                description="Container orchestration",
                properties={"manifest_count": len(k8s_files)},
            )
            components.append({"component_id": comp_id, "name": "Kubernetes", "type": "orchestration"})

        # Check for CI/CD
        ci_files = []
        ci_files.extend(Path(project_path).glob("**/.github/workflows/*.yml"))
        ci_files.extend(Path(project_path).glob("**/.gitlab-ci.yml"))
        ci_files.extend(Path(project_path).glob("**/azure-pipelines.yml"))

        if ci_files:
            comp_id = self.db.add_component(
                analysis_id=analysis_id,
                name="CI/CD Pipeline",
                component_type="cicd",
                description="Continuous Integration/Deployment",
                properties={"pipeline_files": len(ci_files)},
            )
            components.append({"component_id": comp_id, "name": "CI/CD", "type": "cicd"})

        return components

    def _should_skip_file(self, file_path: Path) -> bool:
        """Check if file should be skipped"""
        skip_dirs = ["node_modules", "venv", ".venv", "__pycache__", ".git", "dist", "build", ".next", "coverage"]
        return any(skip in str(file_path) for skip in skip_dirs)

    # ========== Relationship Detection ==========

    def _detect_relationships(self, analysis_id: int) -> list:
        """Detect relationships between components"""
        relationships = []
        components = self.db.get_components(analysis_id)

        # Build component index
        comp_by_name = {c["name"].lower(): c for c in components}
        comp_by_file = {}
        for c in components:
            if c.get("file_path"):
                comp_by_file.setdefault(c["file_path"], []).append(c)

        # Infer relationships from naming conventions
        for comp in components:
            comp_name = comp["name"].lower()

            # Service -> Repository pattern
            if comp["component_type"] == "service":
                repo_name = comp_name.replace("service", "repository")
                if repo_name in comp_by_name:
                    rel_id = self.db.add_relationship(
                        analysis_id=analysis_id,
                        source_id=comp["component_id"],
                        target_id=comp_by_name[repo_name]["component_id"],
                        relationship_type="uses",
                        label="data access",
                    )
                    relationships.append({"relationship_id": rel_id})

            # Controller -> Service pattern
            if comp["component_type"] == "controller":
                svc_name = comp_name.replace("controller", "service")
                if svc_name in comp_by_name:
                    rel_id = self.db.add_relationship(
                        analysis_id=analysis_id,
                        source_id=comp["component_id"],
                        target_id=comp_by_name[svc_name]["component_id"],
                        relationship_type="calls",
                        label="business logic",
                    )
                    relationships.append({"relationship_id": rel_id})

        return relationships

    # ========== Integration Detection ==========

    def _detect_integrations(self, project_path: str, analysis_id: int) -> list:
        """Detect external service integrations"""
        integrations = []
        seen = set()

        for py_file in Path(project_path).rglob("*.py"):
            if self._should_skip_file(py_file):
                continue

            try:
                content = py_file.read_text(errors="ignore")

                for int_type, patterns in self.INTEGRATION_PATTERNS.items():
                    for pattern, name in patterns:
                        matches = re.findall(pattern, content)
                        for match in matches:
                            endpoint = match[1] if isinstance(match, tuple) and len(match) > 1 else None
                            key = (name, int_type, endpoint)
                            if key not in seen:
                                seen.add(key)
                                int_id = self.db.add_integration(
                                    analysis_id=analysis_id,
                                    name=name,
                                    integration_type=int_type,
                                    endpoint=endpoint,
                                    detected_in=str(py_file),
                                )
                                integrations.append({"integration_id": int_id, "name": name, "type": int_type})
            except Exception:
                continue

        return integrations

    # ========== Data Flow Detection ==========

    def _detect_data_flows(self, project_path: str, analysis_id: int) -> list:
        """Detect data flows in the project"""
        data_flows = []

        # Detect API endpoint flows
        components = self.db.get_components(analysis_id, component_type="api_endpoint")
        for comp in components:
            flow_id = self.db.add_data_flow(
                analysis_id=analysis_id,
                name=f"API: {comp['name']}",
                source="Client",
                destination=comp["name"],
                data_type="HTTP",
                flow_type="request",
            )
            data_flows.append({"flow_id": flow_id, "name": comp["name"]})

        # Detect database flows
        db_components = self.db.get_components(analysis_id, component_type="database")
        services = self.db.get_components(analysis_id, component_type="service")

        for svc in services:
            for db in db_components:
                flow_id = self.db.add_data_flow(
                    analysis_id=analysis_id,
                    name=f"{svc['name']} -> {db['name']}",
                    source=svc["name"],
                    destination=db["name"],
                    data_type="query",
                    flow_type="database",
                )
                data_flows.append({"flow_id": flow_id})

        return data_flows

    # ========== Diagram Generation ==========

    def generate_system_diagram(self, analysis_id: int, title: str | None = None) -> dict:
        """Generate system/component architecture diagram"""
        analysis = self.db.get_analysis(analysis_id)
        if not analysis:
            return {"error": "Analysis not found"}

        components = self.db.get_components(analysis_id)
        relationships = self.db.get_relationships(analysis_id)

        title = title or f"System Architecture: {analysis['project_name']}"

        # Build Mermaid flowchart
        lines = ["flowchart TB"]
        lines.append(f"    title[{title}]")
        lines.append("")

        # Group components by type
        comp_by_type = {}
        for c in components:
            comp_by_type.setdefault(c["component_type"], []).append(c)

        # Add subgraphs for each type
        type_labels = {
            "controller": "Controllers",
            "service": "Services",
            "repository": "Repositories",
            "model": "Models",
            "database": "Data Stores",
            "api_endpoint": "API Endpoints",
            "middleware": "Middleware",
            "container": "Infrastructure",
            "queue": "Message Queues",
            "cache": "Caching",
        }

        for comp_type, comps in comp_by_type.items():
            if comps:
                label = type_labels.get(comp_type, comp_type.title())
                lines.append(f"    subgraph {comp_type}[{label}]")
                for c in comps:
                    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", c["name"])
                    lines.append(f'        {safe_name}["{c["name"]}"]')
                lines.append("    end")
                lines.append("")

        # Add relationships
        for rel in relationships:
            source = re.sub(r"[^a-zA-Z0-9_]", "_", rel["source_name"])
            target = re.sub(r"[^a-zA-Z0-9_]", "_", rel["target_name"])
            label = rel.get("label", rel["relationship_type"])
            lines.append(f"    {source} -->|{label}| {target}")

        mermaid_code = "\n".join(lines)

        # Save diagram
        diagram_id = self.db.save_diagram(
            diagram_type="system", title=title, mermaid_code=mermaid_code, analysis_id=analysis_id
        )

        return {
            "diagram_id": diagram_id,
            "title": title,
            "type": "system",
            "mermaid_code": mermaid_code,
            "components_shown": len(components),
            "relationships_shown": len(relationships),
        }

    def generate_data_flow_diagram(self, analysis_id: int, title: str | None = None) -> dict:
        """Generate data flow diagram"""
        analysis = self.db.get_analysis(analysis_id)
        if not analysis:
            return {"error": "Analysis not found"}

        data_flows = self.db.get_data_flows(analysis_id)
        title = title or f"Data Flow: {analysis['project_name']}"

        # Build Mermaid flowchart
        lines = ["flowchart LR"]
        lines.append(f"    title[{title}]")
        lines.append("")

        # Track unique nodes
        nodes = set()

        for flow in data_flows:
            source = re.sub(r"[^a-zA-Z0-9_]", "_", flow["source"])
            dest = re.sub(r"[^a-zA-Z0-9_]", "_", flow["destination"])

            if source not in nodes:
                nodes.add(source)
                lines.append(f"    {source}[{flow['source']}]")
            if dest not in nodes:
                nodes.add(dest)
                lines.append(f"    {dest}[{flow['destination']}]")

            label = flow.get("data_type", "")
            if label:
                lines.append(f"    {source} -->|{label}| {dest}")
            else:
                lines.append(f"    {source} --> {dest}")

        mermaid_code = "\n".join(lines)

        diagram_id = self.db.save_diagram(
            diagram_type="data_flow", title=title, mermaid_code=mermaid_code, analysis_id=analysis_id
        )

        return {
            "diagram_id": diagram_id,
            "title": title,
            "type": "data_flow",
            "mermaid_code": mermaid_code,
            "flows_shown": len(data_flows),
        }

    def generate_integration_diagram(self, analysis_id: int, title: str | None = None) -> dict:
        """Generate external integrations diagram"""
        analysis = self.db.get_analysis(analysis_id)
        if not analysis:
            return {"error": "Analysis not found"}

        integrations = self.db.get_integrations(analysis_id)
        title = title or f"External Integrations: {analysis['project_name']}"

        # Build Mermaid flowchart
        lines = ["flowchart TB"]
        lines.append(f"    title[{title}]")
        lines.append("")

        # Central application node
        lines.append(f'    APP[["{analysis["project_name"]}"]]')
        lines.append("")

        # Group integrations by type
        int_by_type = {}
        for i in integrations:
            int_by_type.setdefault(i["integration_type"], []).append(i)

        type_shapes = {
            "http_api": ("(", ")"),
            "database": ("[(", ")]"),
            "queue": ("{{", "}}"),
            "cache": ("([", "])"),
            "smtp": (">", "]"),
            "cloud_storage": ("[(", ")]"),
            "authentication": ("((", "))"),
        }

        for int_type, ints in int_by_type.items():
            shapes = type_shapes.get(int_type, ("[", "]"))
            lines.append(f"    subgraph {int_type}[{int_type.replace('_', ' ').title()}]")
            for idx, i in enumerate(ints):
                safe_name = f"{int_type}_{idx}"
                lines.append(f"        {safe_name}{shapes[0]}{i['name']}{shapes[1]}")
            lines.append("    end")
            lines.append(f"    APP <--> {int_type}")
            lines.append("")

        mermaid_code = "\n".join(lines)

        diagram_id = self.db.save_diagram(
            diagram_type="integration", title=title, mermaid_code=mermaid_code, analysis_id=analysis_id
        )

        return {
            "diagram_id": diagram_id,
            "title": title,
            "type": "integration",
            "mermaid_code": mermaid_code,
            "integrations_shown": len(integrations),
        }

    def generate_deployment_diagram(self, analysis_id: int, title: str | None = None) -> dict:
        """Generate deployment/infrastructure diagram"""
        analysis = self.db.get_analysis(analysis_id)
        if not analysis:
            return {"error": "Analysis not found"}

        components = self.db.get_components(analysis_id)
        title = title or f"Deployment: {analysis['project_name']}"

        # Build Mermaid flowchart
        lines = ["flowchart TB"]
        lines.append(f"    title[{title}]")
        lines.append("")

        # Infrastructure components
        infra_types = ["container", "orchestration", "cicd", "database", "cache", "queue"]
        infra_comps = [c for c in components if c["component_type"] in infra_types]

        if not infra_comps:
            # Generate basic deployment structure
            lines.append("    subgraph Cloud[Cloud Environment]")
            lines.append("        subgraph App[Application]")
            lines.append(f'            API["{analysis["project_name"]}"]')
            lines.append("        end")
            lines.append("    end")
            lines.append("    Client[Client] --> Cloud")
        else:
            lines.append("    subgraph Infrastructure")
            for c in infra_comps:
                safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", c["name"])
                if c["component_type"] == "container":
                    lines.append(f'        {safe_name}[["{c["name"]}"]]')
                elif c["component_type"] == "database":
                    lines.append(f'        {safe_name}[("{c["name"]}")]')
                else:
                    lines.append(f'        {safe_name}["{c["name"]}"]')
            lines.append("    end")

        mermaid_code = "\n".join(lines)

        diagram_id = self.db.save_diagram(
            diagram_type="deployment", title=title, mermaid_code=mermaid_code, analysis_id=analysis_id
        )

        return {"diagram_id": diagram_id, "title": title, "type": "deployment", "mermaid_code": mermaid_code}

    def generate_from_app_spec(self, app_spec_path: str, diagram_type: str = "system") -> dict:
        """Generate diagram from app_spec.json"""
        try:
            with open(app_spec_path) as f:
                app_spec = json.load(f)
        except Exception as e:
            return {"error": f"Failed to read app_spec: {e}"}

        project_name = app_spec.get("name", "Unknown Project")

        # Build diagram based on app_spec structure
        lines = ["flowchart TB"]
        lines.append(f'    title["{project_name} Architecture"]')
        lines.append("")

        # Components from app_spec
        if "components" in app_spec:
            lines.append("    subgraph Components")
            for comp in app_spec["components"]:
                name = comp.get("name", "Unknown")
                safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
                lines.append(f'        {safe_name}["{name}"]')
            lines.append("    end")

        # Tech stack
        if "tech_stack" in app_spec:
            lines.append("    subgraph TechStack[Tech Stack]")
            for tech in app_spec["tech_stack"]:
                safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", tech)
                lines.append(f'        {safe_name}["{tech}"]')
            lines.append("    end")

        mermaid_code = "\n".join(lines)

        diagram_id = self.db.save_diagram(
            diagram_type=diagram_type,
            title=f"{project_name} Architecture",
            mermaid_code=mermaid_code,
            metadata={"source": "app_spec", "path": app_spec_path},
        )

        return {
            "diagram_id": diagram_id,
            "title": f"{project_name} Architecture",
            "type": diagram_type,
            "mermaid_code": mermaid_code,
        }

    def export_all_diagrams(self, analysis_id: int, output_dir: str | None = None) -> dict:
        """Generate and export all diagram types for an analysis"""
        analysis = self.db.get_analysis(analysis_id)
        if not analysis:
            return {"error": "Analysis not found"}

        output_dir = output_dir or f"./diagrams/{analysis['project_name']}"
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        results = {"analysis_id": analysis_id, "output_dir": output_dir, "diagrams": []}

        # Generate all diagram types
        diagram_generators = [
            ("system", self.generate_system_diagram),
            ("data_flow", self.generate_data_flow_diagram),
            ("integration", self.generate_integration_diagram),
            ("deployment", self.generate_deployment_diagram),
        ]

        for diagram_type, generator in diagram_generators:
            diagram = generator(analysis_id)
            if "error" not in diagram:
                # Save mermaid file
                mermaid_path = Path(output_dir) / f"{diagram_type}.mmd"
                mermaid_path.write_text(diagram["mermaid_code"])

                results["diagrams"].append(
                    {"type": diagram_type, "diagram_id": diagram["diagram_id"], "mermaid_file": str(mermaid_path)}
                )

        return results

    # ========== Diagram Retrieval ==========

    def get_diagram(self, diagram_id: int) -> dict:
        """Get diagram by ID"""
        return self.db.get_diagram(diagram_id)

    def list_diagrams(self, analysis_id: int | None = None, diagram_type: str | None = None) -> list:
        """List diagrams with optional filters"""
        return self.db.get_diagrams(analysis_id, diagram_type)

    # ========== Statistics ==========

    def get_analysis_summary(self, analysis_id: int) -> dict:
        """Get comprehensive analysis summary"""
        analysis = self.db.get_analysis(analysis_id)
        if not analysis:
            return {"error": "Analysis not found"}

        components = self.db.get_components(analysis_id)
        relationships = self.db.get_relationships(analysis_id)
        integrations = self.db.get_integrations(analysis_id)
        data_flows = self.db.get_data_flows(analysis_id)
        diagrams = self.db.get_diagrams(analysis_id)

        # Component breakdown
        comp_breakdown = {}
        for c in components:
            comp_type = c["component_type"]
            comp_breakdown[comp_type] = comp_breakdown.get(comp_type, 0) + 1

        # Integration breakdown
        int_breakdown = {}
        for i in integrations:
            int_type = i["integration_type"]
            int_breakdown[int_type] = int_breakdown.get(int_type, 0) + 1

        return {
            "analysis_id": analysis_id,
            "project_name": analysis["project_name"],
            "status": analysis["status"],
            "summary": {
                "total_components": len(components),
                "total_relationships": len(relationships),
                "total_integrations": len(integrations),
                "total_data_flows": len(data_flows),
                "diagrams_generated": len(diagrams),
            },
            "component_breakdown": comp_breakdown,
            "integration_breakdown": int_breakdown,
            "diagram_types": [d["diagram_type"] for d in diagrams],
        }
