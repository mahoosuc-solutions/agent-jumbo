"""
Project Scaffold Manager
Business logic for generating project structures from templates
"""

import json
import re
from pathlib import Path
from typing import Any

from python.helpers.datetime_utils import isoformat_z, utc_now

from .scaffold_db import ScaffoldDatabase


class ScaffoldManager:
    """Manages project scaffolding from templates"""

    def __init__(self, db_path: str, templates_dir: str | None = None):
        self.db = ScaffoldDatabase(db_path)
        self.templates_dir = templates_dir or str(Path(__file__).parent / "templates")

    # ========== Project Scaffolding ==========

    def scaffold_project(
        self,
        template_name: str,
        project_name: str,
        output_path: str,
        variables: dict[str, Any] | None = None,
        customer_id: int | None = None,
        generate_app_spec: bool = True,
    ) -> dict:
        """
        Generate a new project from a template

        Args:
            template_name: Name of template (e.g., 'web_app/react')
            project_name: Name for the new project
            output_path: Where to create the project
            variables: Template variables to apply
            customer_id: Optional customer ID for tracking
            generate_app_spec: Whether to generate app_spec.json

        Returns:
            dict with project_id, files created, and status
        """
        # Get template
        template = self.db.get_template(name=template_name)
        if not template:
            return {"error": f"Template not found: {template_name}"}

        # Merge variables with defaults
        merged_vars = self._merge_variables(template.get("variables", {}), variables or {})
        merged_vars["project_name"] = project_name
        merged_vars["project_name_slug"] = self._slugify(project_name)
        merged_vars["created_date"] = isoformat_z(utc_now())

        # Create output directory
        output = Path(output_path)
        output.mkdir(parents=True, exist_ok=True)

        # Generate project structure
        generated_files = []
        template_type = template["type"]
        framework = template.get("framework", "")

        # Generate files based on template type
        file_generators = {
            "web_app": self._generate_web_app,
            "api": self._generate_api,
            "cli": self._generate_cli,
            "microservice": self._generate_microservice,
        }

        generator = file_generators.get(template_type)
        if generator:
            files = generator(output, framework, merged_vars)
            generated_files.extend(files)

        # Generate common files
        common_files = self._generate_common_files(output, merged_vars, template)
        generated_files.extend(common_files)

        # Generate app_spec.json if requested
        app_spec_path = None
        if generate_app_spec:
            app_spec_path = self._generate_app_spec(output, template, merged_vars)
            if app_spec_path:
                generated_files.append(app_spec_path)

        # Record in database
        project_id = self.db.add_project(
            template_id=template["template_id"],
            name=project_name,
            output_path=str(output),
            variables_used=merged_vars,
            customer_id=customer_id,
            app_spec_path=app_spec_path,
        )

        # Record generated files
        for file_path in generated_files:
            self.db.add_project_file(project_id, file_path)

        return {
            "project_id": project_id,
            "project_name": project_name,
            "output_path": str(output),
            "template": template_name,
            "files_created": len(generated_files),
            "files": generated_files[:20],  # First 20 files
            "app_spec_path": app_spec_path,
            "status": "created",
        }

    def preview_scaffold(self, template_name: str, variables: dict[str, Any] | None = None) -> dict:
        """
        Preview what files would be generated

        Args:
            template_name: Name of template
            variables: Template variables

        Returns:
            dict with file structure preview
        """
        template = self.db.get_template(name=template_name)
        if not template:
            return {"error": f"Template not found: {template_name}"}

        merged_vars = self._merge_variables(template.get("variables", {}), variables or {})

        # Get file list based on template type
        template_type = template["type"]
        framework = template.get("framework", "")

        files = self._get_template_file_list(template_type, framework, merged_vars)

        return {
            "template": template_name,
            "type": template_type,
            "framework": framework,
            "variables": merged_vars,
            "files": files,
        }

    # ========== Template Management ==========

    def list_templates(
        self, template_type: str | None = None, language: str | None = None, framework: str | None = None
    ) -> list[dict]:
        """List available templates"""
        return self.db.list_templates(template_type=template_type, language=language, framework=framework)

    def get_template(self, name: str) -> dict:
        """Get template details"""
        return self.db.get_template(name=name)

    def create_template_from_project(self, project_path: str, template_name: str, description: str = "") -> dict:
        """
        Create a new template from an existing project

        Args:
            project_path: Path to existing project
            template_name: Name for new template
            description: Template description

        Returns:
            dict with template_id and status
        """
        path = Path(project_path)
        if not path.exists():
            return {"error": f"Project path not found: {project_path}"}

        # Analyze project structure
        analysis = self._analyze_project(path)

        # Create template
        template_id = self.db.add_template(
            name=template_name,
            template_type=analysis["type"],
            language=analysis["language"],
            framework=analysis.get("framework"),
            description=description,
            tags=analysis.get("tags", []),
            variables=analysis.get("variables", {}),
            structure=analysis.get("structure", {}),
            source_path=str(path),
        )

        return {
            "template_id": template_id,
            "name": template_name,
            "type": analysis["type"],
            "language": analysis["language"],
            "framework": analysis.get("framework"),
            "status": "created",
        }

    # ========== App Spec Generation ==========

    def generate_app_spec(self, project_path: str, analyze_code: bool = True) -> dict:
        """
        Generate app_spec.json for an existing project

        Args:
            project_path: Path to project
            analyze_code: Whether to analyze code for components

        Returns:
            dict with app_spec content
        """
        path = Path(project_path)
        if not path.exists():
            return {"error": f"Project path not found: {project_path}"}

        # Analyze project
        analysis = self._analyze_project(path)

        # Build app_spec
        app_spec = {
            "$schema": "app_spec/app_spec.schema.json",
            "name": path.name,
            "version": "0.0.1",
            "purpose": analysis.get("description", "Generated project"),
            "entrypoints": analysis.get("entrypoints", {}),
            "spec_files": {},
            "schemas": {},
        }

        # Save app_spec.json
        spec_path = path / "app_spec.json"
        spec_path.write_text(json.dumps(app_spec, indent=2))

        return {"app_spec_path": str(spec_path), "content": app_spec}

    # ========== Component Management ==========

    def add_component(self, project_path: str, component_type: str, name: str, **kwargs) -> dict:
        """
        Add a component to an existing project

        Args:
            project_path: Path to project
            component_type: Type of component (e.g., 'page', 'api_endpoint', 'model')
            name: Component name
            **kwargs: Additional component options

        Returns:
            dict with created files
        """
        path = Path(project_path)
        if not path.exists():
            return {"error": f"Project path not found: {project_path}"}

        # Detect project type
        analysis = self._analyze_project(path)
        analysis["type"]
        framework = analysis.get("framework")

        # Generate component based on type
        component_generators = {
            "page": self._add_page_component,
            "api_endpoint": self._add_api_endpoint,
            "model": self._add_model_component,
            "service": self._add_service_component,
            "test": self._add_test_component,
        }

        generator = component_generators.get(component_type)
        if not generator:
            return {"error": f"Unknown component type: {component_type}"}

        files = generator(path, name, framework, **kwargs)

        return {"component_type": component_type, "name": name, "files_created": files}

    # ========== Private Generator Methods ==========

    def _generate_web_app(self, output: Path, framework: str, vars: dict) -> list[str]:
        """Generate web application files"""
        files = []

        if framework == "react":
            files.extend(self._generate_react_app(output, vars))
        elif framework == "nextjs":
            files.extend(self._generate_nextjs_app(output, vars))
        elif framework == "vue":
            files.extend(self._generate_vue_app(output, vars))

        return files

    def _generate_react_app(self, output: Path, vars: dict) -> list[str]:
        """Generate React application structure"""
        files = []
        use_ts = vars.get("use_typescript", True)
        ext = "tsx" if use_ts else "jsx"

        # package.json
        package_json = {
            "name": vars["project_name_slug"],
            "private": True,
            "version": "0.0.0",
            "type": "module",
            "scripts": {"dev": "vite", "build": "vite build", "lint": "eslint .", "preview": "vite preview"},
            "dependencies": {"react": "^18.2.0", "react-dom": "^18.2.0", "react-router-dom": "^6.22.0"},
            "devDependencies": {"@vitejs/plugin-react": "^4.2.0", "vite": "^5.0.0"},
        }

        if use_ts:
            package_json["devDependencies"]["typescript"] = "^5.3.0"
            package_json["devDependencies"]["@types/react"] = "^18.2.0"
            package_json["devDependencies"]["@types/react-dom"] = "^18.2.0"

        if vars.get("use_tailwind", True):
            package_json["devDependencies"]["tailwindcss"] = "^3.4.0"
            package_json["devDependencies"]["postcss"] = "^8.4.0"
            package_json["devDependencies"]["autoprefixer"] = "^10.4.0"

        self._write_file(output / "package.json", json.dumps(package_json, indent=2))
        files.append("package.json")

        # index.html
        index_html = f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{vars["project_name"]}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.{ext}"></script>
  </body>
</html>"""
        self._write_file(output / "index.html", index_html)
        files.append("index.html")

        # vite.config
        vite_config = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})"""
        config_ext = "ts" if use_ts else "js"
        self._write_file(output / f"vite.config.{config_ext}", vite_config)
        files.append(f"vite.config.{config_ext}")

        # src directory
        src = output / "src"
        src.mkdir(exist_ok=True)

        # main entry
        main_content = f"""import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root'){"!" if use_ts else ""}).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""
        self._write_file(src / f"main.{ext}", main_content)
        files.append(f"src/main.{ext}")

        # App component
        app_content = f"""import {{ useState }} from "react"

function App() {{
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          {vars["project_name"]}
        </h1>
        <p className="text-gray-600 mb-8">{vars.get("description", "Welcome to your new React app")}</p>
        <button
          onClick={{() => setCount((count) => count + 1)}}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Count is {{count}}
        </button>
      </div>
    </div>
  )
}}

export default App"""
        self._write_file(src / f"App.{ext}", app_content)
        files.append(f"src/App.{ext}")

        # CSS
        css_content = """@tailwind base;
@tailwind components;
@tailwind utilities;"""
        self._write_file(src / "index.css", css_content)
        files.append("src/index.css")

        # tailwind.config.js
        if vars.get("use_tailwind", True):
            tailwind_config = """/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}"""
            self._write_file(output / "tailwind.config.js", tailwind_config)
            files.append("tailwind.config.js")

            postcss_config = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}"""
            self._write_file(output / "postcss.config.js", postcss_config)
            files.append("postcss.config.js")

        # TypeScript config
        if use_ts:
            tsconfig = {
                "compilerOptions": {
                    "target": "ES2020",
                    "useDefineForClassFields": True,
                    "lib": ["ES2020", "DOM", "DOM.Iterable"],
                    "module": "ESNext",
                    "skipLibCheck": True,
                    "moduleResolution": "bundler",
                    "allowImportingTsExtensions": True,
                    "resolveJsonModule": True,
                    "isolatedModules": True,
                    "noEmit": True,
                    "jsx": "react-jsx",
                    "strict": True,
                    "noUnusedLocals": True,
                    "noUnusedParameters": True,
                    "noFallthroughCasesInSwitch": True,
                },
                "include": ["src"],
                "references": [{"path": "./tsconfig.node.json"}],
            }
            self._write_file(output / "tsconfig.json", json.dumps(tsconfig, indent=2))
            files.append("tsconfig.json")

        return files

    def _generate_nextjs_app(self, output: Path, vars: dict) -> list[str]:
        """Generate Next.js application structure"""
        files = []
        use_src = vars.get("use_src_dir", True)
        base = output / "src" if use_src else output

        # package.json
        package_json = {
            "name": vars["project_name_slug"],
            "version": "0.1.0",
            "private": True,
            "scripts": {"dev": "next dev", "build": "next build", "start": "next start", "lint": "next lint"},
            "dependencies": {"next": "14.1.0", "react": "^18", "react-dom": "^18"},
            "devDependencies": {
                "typescript": "^5",
                "@types/node": "^20",
                "@types/react": "^18",
                "@types/react-dom": "^18",
                "tailwindcss": "^3.4.0",
                "postcss": "^8",
                "autoprefixer": "^10.0.1",
            },
        }
        self._write_file(output / "package.json", json.dumps(package_json, indent=2))
        files.append("package.json")

        # next.config.js
        next_config = """/** @type {import('next').NextConfig} */
const nextConfig = {}

module.exports = nextConfig"""
        self._write_file(output / "next.config.js", next_config)
        files.append("next.config.js")

        # App directory
        app_dir = base / "app"
        app_dir.mkdir(parents=True, exist_ok=True)

        # layout.tsx
        layout = f"""import type {{ Metadata }} from 'next'
import './globals.css'

export const metadata: Metadata = {{
  title: '{vars["project_name"]}',
  description: '{vars.get("description", "Generated with Agent Zero")}',
}}

export default function RootLayout({{
  children,
}}: {{
  children: React.ReactNode
}}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  )
}}"""
        rel_path = "src/app/layout.tsx" if use_src else "app/layout.tsx"
        self._write_file(app_dir / "layout.tsx", layout)
        files.append(rel_path)

        # page.tsx
        page = f"""export default function Home() {{
  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          {vars["project_name"]}
        </h1>
        <p className="text-gray-600">
          {vars.get("description", "Welcome to your Next.js application")}
        </p>
      </div>
    </main>
  )
}}"""
        rel_path = "src/app/page.tsx" if use_src else "app/page.tsx"
        self._write_file(app_dir / "page.tsx", page)
        files.append(rel_path)

        # globals.css
        globals_css = """@tailwind base;
@tailwind components;
@tailwind utilities;"""
        rel_path = "src/app/globals.css" if use_src else "app/globals.css"
        self._write_file(app_dir / "globals.css", globals_css)
        files.append(rel_path)

        # tailwind.config
        tailwind_config = """import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
export default config"""
        self._write_file(output / "tailwind.config.ts", tailwind_config)
        files.append("tailwind.config.ts")

        # tsconfig.json
        tsconfig = {
            "compilerOptions": {
                "lib": ["dom", "dom.iterable", "esnext"],
                "allowJs": True,
                "skipLibCheck": True,
                "strict": True,
                "noEmit": True,
                "esModuleInterop": True,
                "module": "esnext",
                "moduleResolution": "bundler",
                "resolveJsonModule": True,
                "isolatedModules": True,
                "jsx": "preserve",
                "incremental": True,
                "plugins": [{"name": "next"}],
                "paths": {"@/*": ["./src/*"] if use_src else ["./*"]},
            },
            "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
            "exclude": ["node_modules"],
        }
        self._write_file(output / "tsconfig.json", json.dumps(tsconfig, indent=2))
        files.append("tsconfig.json")

        return files

    def _generate_vue_app(self, output: Path, vars: dict) -> list[str]:
        """Generate Vue.js application structure"""
        # Simplified Vue structure
        files = []
        # Implementation similar to React...
        return files

    def _generate_api(self, output: Path, framework: str, vars: dict) -> list[str]:
        """Generate API files"""
        files = []

        if framework == "fastapi":
            files.extend(self._generate_fastapi(output, vars))
        elif framework == "express":
            files.extend(self._generate_express(output, vars))

        return files

    def _generate_fastapi(self, output: Path, vars: dict) -> list[str]:
        """Generate FastAPI application structure"""
        files = []

        # requirements.txt
        requirements = """fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
python-dotenv>=1.0.0"""

        if vars.get("use_sqlalchemy", True):
            requirements += """
sqlalchemy>=2.0.0
alembic>=1.13.0"""

        self._write_file(output / "requirements.txt", requirements)
        files.append("requirements.txt")

        # main.py
        main_py = f'''"""
{vars["project_name"]} API
{vars.get("description", "Generated with Agent Zero")}
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="{vars["project_name"]}",
    description="{vars.get("description", "")}",
    version="0.1.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {{"message": "Welcome to {vars["project_name"]}"}}

@app.get("/health")
async def health_check():
    return {{"status": "healthy"}}
'''
        self._write_file(output / "main.py", main_py)
        files.append("main.py")

        # Create app directory structure
        app_dir = output / "app"
        app_dir.mkdir(exist_ok=True)

        # __init__.py
        self._write_file(app_dir / "__init__.py", "")
        files.append("app/__init__.py")

        # models directory
        models_dir = app_dir / "models"
        models_dir.mkdir(exist_ok=True)
        self._write_file(models_dir / "__init__.py", "")
        files.append("app/models/__init__.py")

        # routes directory
        routes_dir = app_dir / "routes"
        routes_dir.mkdir(exist_ok=True)
        self._write_file(routes_dir / "__init__.py", "")
        files.append("app/routes/__init__.py")

        # Dockerfile
        dockerfile = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        self._write_file(output / "Dockerfile", dockerfile)
        files.append("Dockerfile")

        return files

    def _generate_express(self, output: Path, vars: dict) -> list[str]:
        """Generate Express.js application structure"""
        files = []
        use_ts = vars.get("use_typescript", True)

        # package.json
        package_json = {
            "name": vars["project_name_slug"],
            "version": "1.0.0",
            "description": vars.get("description", ""),
            "main": "dist/index.js" if use_ts else "src/index.js",
            "scripts": {
                "start": "node dist/index.js" if use_ts else "node src/index.js",
                "dev": "ts-node-dev src/index.ts" if use_ts else "nodemon src/index.js",
                "build": "tsc" if use_ts else "echo 'No build step'",
            },
            "dependencies": {"express": "^4.18.0", "cors": "^2.8.5", "helmet": "^7.1.0", "dotenv": "^16.4.0"},
            "devDependencies": {},
        }

        if use_ts:
            package_json["devDependencies"] = {
                "typescript": "^5.3.0",
                "@types/node": "^20.0.0",
                "@types/express": "^4.17.0",
                "@types/cors": "^2.8.0",
                "ts-node-dev": "^2.0.0",
            }

        self._write_file(output / "package.json", json.dumps(package_json, indent=2))
        files.append("package.json")

        # src directory
        src = output / "src"
        src.mkdir(exist_ok=True)

        # index file
        ext = "ts" if use_ts else "js"
        index_content = f"""import express from 'express';
import cors from 'cors';
import helmet from 'helmet';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {{
  res.json({{ message: 'Welcome to {vars["project_name"]}' }});
}});

app.get('/health', (req, res) => {{
  res.json({{ status: 'healthy' }});
}});

app.listen(PORT, () => {{
  console.log(`Server running on port ${{PORT}}`);
}});
"""
        self._write_file(src / f"index.{ext}", index_content)
        files.append(f"src/index.{ext}")

        if use_ts:
            tsconfig = {
                "compilerOptions": {
                    "target": "ES2020",
                    "module": "commonjs",
                    "lib": ["ES2020"],
                    "outDir": "./dist",
                    "rootDir": "./src",
                    "strict": True,
                    "esModuleInterop": True,
                    "skipLibCheck": True,
                    "forceConsistentCasingInFileNames": True,
                },
                "include": ["src/**/*"],
                "exclude": ["node_modules"],
            }
            self._write_file(output / "tsconfig.json", json.dumps(tsconfig, indent=2))
            files.append("tsconfig.json")

        return files

    def _generate_cli(self, output: Path, framework: str, vars: dict) -> list[str]:
        """Generate CLI application files"""
        files = []

        # Python CLI with Click
        if framework == "click":
            # requirements.txt
            requirements = """click>=8.1.0
rich>=13.7.0"""
            self._write_file(output / "requirements.txt", requirements)
            files.append("requirements.txt")

            # main CLI file
            cli_content = f'''#!/usr/bin/env python3
"""
{vars["project_name"]}
{vars.get("description", "A CLI application")}
"""

import click
from rich.console import Console

console = Console()

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """{vars["project_name"]} - {vars.get("description", "CLI application")}"""
    pass

@cli.command()
@click.argument('name', default='World')
def hello(name: str):
    """Say hello"""
    console.print(f"[bold green]Hello, {{name}}![/bold green]")

@cli.command()
def info():
    """Show application info"""
    console.print("[bold]{vars["project_name"]}[/bold]")
    console.print("Version: 0.1.0")

if __name__ == '__main__':
    cli()
'''
            self._write_file(output / f"{vars['project_name_slug']}.py", cli_content)
            files.append(f"{vars['project_name_slug']}.py")

            # setup.py
            setup_py = f'''from setuptools import setup, find_packages

setup(
    name="{vars["project_name_slug"]}",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.0",
        "rich>=13.7.0",
    ],
    entry_points={{
        "console_scripts": [
            "{vars["project_name_slug"]}={vars["project_name_slug"]}:cli",
        ],
    }},
)
'''
            self._write_file(output / "setup.py", setup_py)
            files.append("setup.py")

        return files

    def _generate_microservice(self, output: Path, framework: str, vars: dict) -> list[str]:
        """Generate microservice files"""
        files = []

        # Start with API generation
        if framework == "fastapi":
            files.extend(self._generate_fastapi(output, vars))

        # Add docker-compose
        port = vars.get("port", 8000)
        docker_compose = f"""version: '3.8'

services:
  {vars["project_name_slug"]}:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - PORT={port}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
"""
        self._write_file(output / "docker-compose.yml", docker_compose)
        files.append("docker-compose.yml")

        return files

    def _generate_common_files(self, output: Path, vars: dict, template: dict) -> list[str]:
        """Generate common files for all project types"""
        files = []

        # README.md
        readme = f"""# {vars["project_name"]}

{vars.get("description", "Generated with Agent Zero")}

## Getting Started

This project was scaffolded with Agent Zero using the `{template["name"]}` template.

## Development

```bash
# Install dependencies
npm install  # or pip install -r requirements.txt

# Start development server
npm run dev  # or uvicorn main:app --reload
```

## Project Structure

Generated on {vars["created_date"]}

---
*Generated with Agent Zero Project Scaffold*
"""
        self._write_file(output / "README.md", readme)
        files.append("README.md")

        # .gitignore
        gitignore = """# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/
venv/

# Build
dist/
build/
*.egg-info/

# IDE
.idea/
.vscode/
*.swp

# Environment
.env
.env.local

# Logs
*.log
npm-debug.log*

# OS
.DS_Store
Thumbs.db
"""
        self._write_file(output / ".gitignore", gitignore)
        files.append(".gitignore")

        # .env.example
        env_example = """# Environment Variables
NODE_ENV=development
PORT=3000
"""
        self._write_file(output / ".env.example", env_example)
        files.append(".env.example")

        return files

    def _generate_app_spec(self, output: Path, template: dict, vars: dict) -> str | None:
        """Generate app_spec.json for the project"""
        app_spec = {
            "$schema": "app_spec/app_spec.schema.json",
            "name": vars["project_name_slug"],
            "version": "0.0.1",
            "purpose": vars.get("description", "Generated project"),
            "entrypoints": self._detect_entrypoints(template),
            "spec_files": {},
            "schemas": {},
        }

        spec_path = output / "app_spec.json"
        self._write_file(spec_path, json.dumps(app_spec, indent=2))
        return "app_spec.json"

    # ========== Helper Methods ==========

    def _write_file(self, path: Path, content: str):
        """Write content to file, creating directories as needed"""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _slugify(self, text: str) -> str:
        """Convert text to slug format"""
        text = text.lower()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[-\s]+", "-", text)
        return text.strip("-")

    def _merge_variables(self, template_vars: dict, user_vars: dict) -> dict:
        """Merge user variables with template defaults"""
        result = {}

        for key, config in template_vars.items():
            if isinstance(config, dict):
                if key in user_vars:
                    result[key] = user_vars[key]
                elif "default" in config:
                    result[key] = config["default"]
            else:
                result[key] = user_vars.get(key, config)

        # Add any extra user vars
        for key, value in user_vars.items():
            if key not in result:
                result[key] = value

        return result

    def _get_template_file_list(self, template_type: str, framework: str, vars: dict) -> list[str]:
        """Get list of files that would be generated"""
        # Return standard file lists based on template type
        files = ["README.md", ".gitignore", ".env.example"]

        if template_type == "web_app":
            files.extend(["package.json", "index.html", "src/main.tsx", "src/App.tsx"])
        elif template_type == "api":
            if framework == "fastapi":
                files.extend(["requirements.txt", "main.py", "Dockerfile"])
            elif framework == "express":
                files.extend(["package.json", "src/index.ts", "tsconfig.json"])
        elif template_type == "cli":
            files.extend(["requirements.txt", "setup.py", f"{vars.get('project_name_slug', 'cli')}.py"])
        elif template_type == "microservice":
            files.extend(["requirements.txt", "main.py", "Dockerfile", "docker-compose.yml"])

        return files

    def _analyze_project(self, path: Path) -> dict:
        """Analyze an existing project to determine its type and structure"""
        analysis = {"type": "unknown", "language": "unknown", "entrypoints": {}}

        # Check for common files
        if (path / "package.json").exists():
            analysis["language"] = "javascript"
            pkg = json.loads((path / "package.json").read_text())

            if "next" in pkg.get("dependencies", {}):
                analysis["type"] = "web_app"
                analysis["framework"] = "nextjs"
            elif "react" in pkg.get("dependencies", {}):
                analysis["type"] = "web_app"
                analysis["framework"] = "react"
            elif "express" in pkg.get("dependencies", {}):
                analysis["type"] = "api"
                analysis["framework"] = "express"

        elif (path / "requirements.txt").exists():
            analysis["language"] = "python"
            reqs = (path / "requirements.txt").read_text()

            if "fastapi" in reqs:
                analysis["type"] = "api"
                analysis["framework"] = "fastapi"
            elif "click" in reqs:
                analysis["type"] = "cli"
                analysis["framework"] = "click"
            elif "flask" in reqs:
                analysis["type"] = "api"
                analysis["framework"] = "flask"

        return analysis

    def _detect_entrypoints(self, template: dict) -> dict:
        """Detect entrypoints based on template type"""
        template_type = template.get("type", "")
        framework = template.get("framework", "")

        entrypoints = {}

        if template_type == "web_app":
            entrypoints["web"] = "src/main.tsx"
        elif template_type == "api":
            if framework == "fastapi":
                entrypoints["api"] = "main.py"
            elif framework == "express":
                entrypoints["api"] = "src/index.ts"
        elif template_type == "cli":
            entrypoints["cli"] = "cli.py"

        return entrypoints

    # ========== Component Addition Methods ==========

    def _add_page_component(self, path: Path, name: str, framework: str, **kwargs) -> list[str]:
        """Add a page component to a web app"""
        files = []
        # Implementation for adding pages
        return files

    def _add_api_endpoint(self, path: Path, name: str, framework: str, **kwargs) -> list[str]:
        """Add an API endpoint"""
        files = []
        # Implementation for adding API endpoints
        return files

    def _add_model_component(self, path: Path, name: str, framework: str, **kwargs) -> list[str]:
        """Add a data model"""
        files = []
        # Implementation for adding models
        return files

    def _add_service_component(self, path: Path, name: str, framework: str, **kwargs) -> list[str]:
        """Add a service/business logic component"""
        files = []
        # Implementation for adding services
        return files

    def _add_test_component(self, path: Path, name: str, framework: str, **kwargs) -> list[str]:
        """Add test files"""
        files = []
        # Implementation for adding tests
        return files
