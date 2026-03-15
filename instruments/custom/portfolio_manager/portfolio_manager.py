"""
Portfolio Manager - Project Scanner and Analyzer
Scans folders to detect code projects, analyze quality, and generate sale-readiness scores
"""

import json
from pathlib import Path
from typing import Any

from python.helpers.datetime_utils import isoformat_z, utc_now

from .portfolio_db import PortfolioDatabase as PortfolioDB


class ProjectScanner:
    """Scans and analyzes code projects"""

    # File patterns for language/framework detection
    LANGUAGE_MARKERS = {
        "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile", "*.py"],
        "javascript": ["package.json", "*.js", "*.mjs"],
        "typescript": ["tsconfig.json", "*.ts", "*.tsx"],
        "java": ["pom.xml", "build.gradle", "*.java"],
        "go": ["go.mod", "go.sum", "*.go"],
        "rust": ["Cargo.toml", "*.rs"],
        "ruby": ["Gemfile", "*.rb"],
        "php": ["composer.json", "*.php"],
        "csharp": ["*.csproj", "*.sln", "*.cs"],
        "swift": ["Package.swift", "*.swift"],
    }

    FRAMEWORK_MARKERS = {
        # Python
        "django": ["manage.py", "django"],
        "flask": ["flask"],
        "fastapi": ["fastapi"],
        "streamlit": ["streamlit"],
        # JavaScript/TypeScript
        "react": ["react", "react-dom"],
        "vue": ["vue"],
        "angular": ["@angular/core"],
        "next": ["next"],
        "express": ["express"],
        "nestjs": ["@nestjs/core"],
        # Other
        "spring": ["spring-boot"],
        "rails": ["rails"],
        "laravel": ["laravel/framework"],
    }

    DOC_TYPES = ["readme", "api", "tutorial", "changelog", "contributing"]

    def __init__(self, db: PortfolioDB | None = None):
        self.db = db or PortfolioDB()

    def scan_folder(self, folder_path: str, recursive: bool = False) -> list[dict]:
        """
        Scan a folder for code projects

        Args:
            folder_path: Path to scan
            recursive: If True, scan subdirectories for separate projects

        Returns:
            List of detected projects with metadata
        """
        folder = Path(folder_path).resolve()
        if not folder.exists():
            raise ValueError(f"Folder does not exist: {folder_path}")

        projects = []

        if recursive:
            # Each subdirectory might be a project
            for subdir in folder.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("."):
                    if self._is_project(subdir):
                        projects.append(self._analyze_project(subdir))
        else:
            # Treat the folder itself as a project
            if self._is_project(folder):
                projects.append(self._analyze_project(folder))

        return projects

    def _is_project(self, path: Path) -> bool:
        """Check if a directory is a code project"""
        # Check for common project indicators
        indicators = [
            "package.json",
            "requirements.txt",
            "setup.py",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "Gemfile",
            "composer.json",
            ".git",
            "README.md",
            "README",
            "readme.md",
        ]
        return any((path / indicator).exists() for indicator in indicators)

    def _analyze_project(self, path: Path) -> dict[str, Any]:
        """Analyze a project directory"""
        analysis = {
            "path": str(path),
            "name": path.name,
            "language": None,
            "framework": None,
            "version": None,
            "license": None,
            "description": None,
            "has_tests": False,
            "has_ci": False,
            "doc_status": {},
            "dependencies": [],
            "file_count": 0,
            "line_count": 0,
            "readme_quality": 0,
            "sale_readiness_score": 0,
        }

        # Detect language
        analysis["language"] = self._detect_language(path)

        # Detect framework and version info
        pkg_info = self._parse_package_info(path, analysis["language"])
        analysis.update(pkg_info)

        # Check documentation
        analysis["doc_status"] = self._check_documentation(path)
        analysis["readme_quality"] = self._score_readme(path)

        # Check for tests and CI
        analysis["has_tests"] = self._has_tests(path)
        analysis["has_ci"] = self._has_ci(path)

        # Count files and lines
        analysis["file_count"], analysis["line_count"] = self._count_code(path, analysis["language"])

        # Calculate sale readiness
        analysis["sale_readiness_score"] = self._calculate_readiness(analysis)

        return analysis

    def _detect_language(self, path: Path) -> str | None:
        """Detect primary programming language"""
        for lang, markers in self.LANGUAGE_MARKERS.items():
            for marker in markers:
                if marker.startswith("*"):
                    # Glob pattern
                    if list(path.glob(marker)):
                        return lang
                else:
                    if (path / marker).exists():
                        return lang
        return None

    def _parse_package_info(self, path: Path, language: str | None) -> dict[str, Any]:
        """Parse package/project metadata files"""
        info = {"framework": None, "version": None, "license": None, "description": None, "dependencies": []}

        # Python - pyproject.toml, setup.py, requirements.txt
        if language == "python":
            pyproject = path / "pyproject.toml"
            if pyproject.exists():
                try:
                    import tomllib

                    with open(pyproject, "rb") as f:
                        data = tomllib.load(f)
                    project = data.get("project", {})
                    info["version"] = project.get("version")
                    info["description"] = project.get("description")
                    info["license"] = (
                        project.get("license", {}).get("text")
                        if isinstance(project.get("license"), dict)
                        else project.get("license")
                    )
                    info["dependencies"] = project.get("dependencies", [])
                except:
                    pass

            requirements = path / "requirements.txt"
            if requirements.exists():
                try:
                    with open(requirements) as f:
                        info["dependencies"] = [line.strip() for line in f if line.strip() and not line.startswith("#")]
                except:
                    pass

        # JavaScript/TypeScript - package.json
        elif language in ("javascript", "typescript"):
            pkg_json = path / "package.json"
            if pkg_json.exists():
                try:
                    with open(pkg_json) as f:
                        data = json.load(f)
                    info["version"] = data.get("version")
                    info["description"] = data.get("description")
                    info["license"] = data.get("license")
                    deps = data.get("dependencies", {})
                    info["dependencies"] = list(deps.keys())

                    # Detect framework
                    for framework, markers in self.FRAMEWORK_MARKERS.items():
                        for marker in markers:
                            if marker in deps:
                                info["framework"] = framework
                                break
                except:
                    pass

        # Check for LICENSE file
        if not info["license"]:
            for license_file in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]:
                if (path / license_file).exists():
                    info["license"] = "See LICENSE file"
                    break

        return info

    def _check_documentation(self, path: Path) -> dict[str, bool]:
        """Check for various documentation files"""
        doc_status = {}

        doc_patterns = {
            "readme": ["README.md", "README", "README.rst", "README.txt"],
            "api": ["API.md", "docs/api", "api.md"],
            "tutorial": ["TUTORIAL.md", "docs/tutorial", "docs/getting-started"],
            "changelog": ["CHANGELOG.md", "CHANGELOG", "HISTORY.md", "CHANGES.md"],
            "contributing": ["CONTRIBUTING.md", "CONTRIBUTING", ".github/CONTRIBUTING.md"],
        }

        for doc_type, patterns in doc_patterns.items():
            doc_status[doc_type] = any((path / p).exists() for p in patterns)

        return doc_status

    def _score_readme(self, path: Path) -> int:
        """Score README quality (0-100)"""
        readme_files = ["README.md", "README", "README.rst"]
        readme_path = None

        for rf in readme_files:
            if (path / rf).exists():
                readme_path = path / rf
                break

        if not readme_path:
            return 0

        try:
            with open(readme_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except:
            return 0

        score = 0

        # Length scoring (up to 30 points)
        word_count = len(content.split())
        if word_count > 500:
            score += 30
        elif word_count > 200:
            score += 20
        elif word_count > 50:
            score += 10

        # Section headers (up to 25 points)
        headers = content.count("#")
        score += min(headers * 3, 25)

        # Code blocks (up to 20 points)
        code_blocks = content.count("```")
        score += min(code_blocks * 4, 20)

        # Key sections (up to 25 points)
        key_sections = ["install", "usage", "example", "getting started", "feature", "api", "license"]
        for section in key_sections:
            if section.lower() in content.lower():
                score += 3
        score = min(score, 100)

        return score

    def _has_tests(self, path: Path) -> bool:
        """Check if project has tests"""
        test_indicators = [
            "tests",
            "test",
            "spec",
            "__tests__",
            "pytest.ini",
            "jest.config.js",
            "karma.conf.js",
            ".pytest_cache",
            "test_*.py",
            "*_test.py",
            "*.test.js",
            "*.spec.js",
        ]
        for indicator in test_indicators:
            if indicator.startswith("*"):
                if list(path.rglob(indicator)):
                    return True
            elif (path / indicator).exists():
                return True
        return False

    def _has_ci(self, path: Path) -> bool:
        """Check if project has CI configuration"""
        ci_indicators = [
            ".github/workflows",
            ".gitlab-ci.yml",
            ".travis.yml",
            "Jenkinsfile",
            ".circleci",
            "azure-pipelines.yml",
        ]
        return any((path / ci).exists() for ci in ci_indicators)

    def _count_code(self, path: Path, language: str | None) -> tuple[int, int]:
        """Count code files and lines"""
        extensions = {
            "python": [".py"],
            "javascript": [".js", ".mjs", ".jsx"],
            "typescript": [".ts", ".tsx"],
            "java": [".java"],
            "go": [".go"],
            "rust": [".rs"],
            "ruby": [".rb"],
            "php": [".php"],
            "csharp": [".cs"],
            "swift": [".swift"],
        }

        exts = extensions.get(language, [".py", ".js", ".ts", ".java", ".go"])

        file_count = 0
        line_count = 0

        for ext in exts:
            for file in path.rglob(f"*{ext}"):
                # Skip node_modules, venv, etc.
                if any(skip in str(file) for skip in ["node_modules", "venv", ".venv", "__pycache__", "dist", "build"]):
                    continue
                file_count += 1
                try:
                    with open(file, encoding="utf-8", errors="ignore") as f:
                        line_count += sum(1 for _ in f)
                except:
                    pass

        return file_count, line_count

    def _calculate_readiness(self, analysis: dict) -> int:
        """Calculate sale readiness score (0-100)"""
        score = 0

        # Has good README (up to 25 points)
        score += int(analysis["readme_quality"] * 0.25)

        # Has documentation (up to 20 points)
        doc_count = sum(1 for v in analysis["doc_status"].values() if v)
        score += doc_count * 4

        # Has tests (15 points)
        if analysis["has_tests"]:
            score += 15

        # Has CI/CD (10 points)
        if analysis["has_ci"]:
            score += 10

        # Has license (10 points)
        if analysis["license"]:
            score += 10

        # Has version (5 points)
        if analysis["version"]:
            score += 5

        # Has description (5 points)
        if analysis["description"]:
            score += 5

        # Code size bonus (up to 10 points)
        if analysis["line_count"] > 5000:
            score += 10
        elif analysis["line_count"] > 1000:
            score += 5

        return min(score, 100)

    def import_project(self, folder_path: str) -> int:
        """Scan and import a project into the database"""
        analysis = self._analyze_project(Path(folder_path))

        # Check if already exists
        existing = self.db.get_project_by_path(analysis["path"])
        if existing:
            # Update existing
            self.db.update_project(
                existing["id"],
                language=analysis["language"],
                framework=analysis["framework"],
                version=analysis["version"],
                license=analysis["license"],
                description=analysis["description"],
                last_scanned_at=isoformat_z(utc_now()),
            )
            project_id = existing["id"]
        else:
            # Create new
            project_id = self.db.add_project(
                name=analysis["name"],
                path=analysis["path"],
                language=analysis["language"],
                framework=analysis["framework"],
                version=analysis["version"],
                license=analysis["license"],
                description=analysis["description"],
            )

        # Store metadata
        metadata_keys = [
            "has_tests",
            "has_ci",
            "file_count",
            "line_count",
            "readme_quality",
            "sale_readiness_score",
            "dependencies",
        ]
        for key in metadata_keys:
            if key in analysis:
                self.db.set_metadata(project_id, key, analysis[key])

        # Update documentation status
        for doc_type, exists in analysis["doc_status"].items():
            quality = analysis["readme_quality"] if doc_type == "readme" else 0
            self.db.update_documentation(project_id, doc_type, exists, quality)

        return project_id

    def scan_and_import_folder(self, folder_path: str, recursive: bool = True) -> list[int]:
        """Scan folder and import all projects"""
        folder = Path(folder_path).resolve()
        project_ids = []

        if recursive:
            for subdir in folder.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("."):
                    if self._is_project(subdir):
                        try:
                            project_id = self.import_project(str(subdir))
                            project_ids.append(project_id)
                        except Exception as e:
                            print(f"Error importing {subdir}: {e}")
        else:
            if self._is_project(folder):
                project_id = self.import_project(str(folder))
                project_ids.append(project_id)

        return project_ids


class PortfolioManager:
    """Main interface for portfolio management"""

    def __init__(self, data_dir: str | None = None):
        self.db = PortfolioDB(data_dir)
        self.scanner = ProjectScanner(self.db)

    def scan_folder(self, folder_path: str, recursive: bool = True) -> dict[str, Any]:
        """Scan a folder and import projects"""
        project_ids = self.scanner.scan_and_import_folder(folder_path, recursive)

        projects = []
        for pid in project_ids:
            project = self.db.get_project(pid)
            metadata = self.db.get_metadata(pid)
            if project:
                project["metadata"] = metadata
                projects.append(project)

        return {"imported_count": len(project_ids), "projects": projects}

    def list_projects(self, status: str | None = None) -> list[dict]:
        """List all projects with their metadata"""
        projects = self.db.list_projects(status)
        for project in projects:
            project["metadata"] = self.db.get_metadata(project["id"])
            project["tags"] = self.db.get_tags(project["id"])
        return projects

    def get_project_details(self, project_id: int) -> dict | None:
        """Get full project details"""
        project = self.db.get_project(project_id)
        if not project:
            return None

        project["metadata"] = self.db.get_metadata(project_id)
        project["tags"] = self.db.get_tags(project_id)
        project["documentation"] = self.db.get_documentation_status(project_id)

        # Get associated products
        products = self.db.fetch_all("SELECT * FROM products WHERE project_id = ?", (project_id,))
        project["products"] = products

        return project

    def create_product(self, project_id: int, **kwargs) -> int:
        """Create a product from a project"""
        project = self.db.get_project(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")

        metadata = self.db.get_metadata(project_id)

        # Set defaults from project
        name = kwargs.get("name", project["name"])
        description = kwargs.get("description", project["description"])
        readiness = metadata.get("sale_readiness_score", 0)

        return self.db.create_product(
            project_id=project_id,
            name=name,
            tagline=kwargs.get("tagline"),
            description=description,
            category=kwargs.get("category"),
            price=kwargs.get("price", 0),
            price_model=kwargs.get("price_model", "one-time"),
            demo_url=kwargs.get("demo_url"),
            docs_url=kwargs.get("docs_url"),
            sale_readiness_score=readiness,
        )

    def get_portfolio_summary(self) -> dict[str, Any]:
        """Get portfolio summary with stats"""
        stats = self.db.get_portfolio_stats()
        pipeline = self.db.get_pipeline_summary()

        # Get recent projects
        recent = self.db.fetch_all("SELECT * FROM projects ORDER BY updated_at DESC LIMIT 5")

        # Get top products by readiness
        top_products = self.db.fetch_all("SELECT * FROM products ORDER BY sale_readiness_score DESC LIMIT 5")

        return {"stats": stats, "pipeline": pipeline, "recent_projects": recent, "top_products": top_products}

    def close(self):
        """Close database connection"""
        self.db.close()
