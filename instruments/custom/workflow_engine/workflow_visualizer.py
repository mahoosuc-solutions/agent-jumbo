"""
Workflow Visualizer - Generate visual representations of workflows and progress
Creates Mermaid diagrams, ASCII art, and progress visualizations
"""

from datetime import datetime


class WorkflowVisualizer:
    """Generate visual representations of workflows and progress"""

    def __init__(self):
        pass

    # ========== Workflow Diagrams ==========

    def generate_workflow_diagram(self, workflow: dict, execution_status: dict | None = None) -> str:
        """Generate Mermaid flowchart for a workflow"""
        definition = workflow.get("definition", workflow)
        stages = definition.get("stages", [])
        transitions = definition.get("transitions", [])

        lines = ["```mermaid", "flowchart TD"]

        # Define stage nodes
        for stage in stages:
            stage_id = stage["id"]
            stage_name = stage["name"]
            stage_type = stage.get("type", "custom")

            # Style based on status
            status = self._get_stage_status(stage_id, execution_status)
            style = self._get_node_style(status, stage_type)

            lines.append(f"    {stage_id}[{stage_name}]{style}")

        lines.append("")

        # Define transitions
        if transitions:
            for trans in transitions:
                from_stage = trans["from"]
                to_stage = trans["to"]
                condition = trans.get("condition", "")
                label = f"|{condition}|" if condition else ""
                lines.append(f"    {from_stage} -->{label} {to_stage}")
        else:
            # Auto-generate sequential transitions
            for i in range(len(stages) - 1):
                lines.append(f"    {stages[i]['id']} --> {stages[i + 1]['id']}")

        # Add styling
        lines.append("")
        lines.append("    classDef completed fill:#4CAF50,stroke:#2E7D32,color:#fff")
        lines.append("    classDef inProgress fill:#2196F3,stroke:#1565C0,color:#fff")
        lines.append("    classDef pending fill:#9E9E9E,stroke:#616161,color:#fff")
        lines.append("    classDef blocked fill:#F44336,stroke:#C62828,color:#fff")

        # Apply classes based on status
        if execution_status:
            for stage in stages:
                stage_id = stage["id"]
                status = self._get_stage_status(stage_id, execution_status)
                if status:
                    lines.append(f"    class {stage_id} {status}")

        lines.append("```")
        return "\n".join(lines)

    def _get_stage_status(self, stage_id: str, execution_status: dict) -> str | None:
        """Get status for a stage from execution status"""
        if not execution_status:
            return None

        stage_details = execution_status.get("stage_details", [])
        for stage in stage_details:
            if stage.get("stage_id") == stage_id:
                status = stage.get("status", "pending")
                if status == "completed":
                    return "completed"
                elif status == "in_progress":
                    return "inProgress"
                elif status == "blocked":
                    return "blocked"
        return "pending"

    def _get_node_style(self, status: str, stage_type: str) -> str:
        """Get node shape based on stage type"""
        return ""  # Mermaid shapes are defined in the node itself

    # ========== Task Diagrams ==========

    def generate_task_diagram(self, stage: dict, task_status: list | None = None) -> str:
        """Generate Mermaid diagram for tasks within a stage"""
        tasks = stage.get("tasks", [])

        lines = ["```mermaid", "flowchart LR"]

        # Start node
        lines.append("    start((Start))")
        lines.append("")

        # Define tasks
        for task in tasks:
            task_id = task["id"]
            task_name = task["name"]
            role = task.get("role", "")

            status = self._get_task_status(task_id, task_status)
            style_class = status or "pending"

            role_label = f"<br><small>({role})</small>" if role else ""
            lines.append(f'    {task_id}["{task_name}{role_label}"]:::{style_class}')

        # End node
        lines.append("    finish((End))")
        lines.append("")

        # Build dependency graph
        no_deps = []
        has_deps = {}

        for task in tasks:
            task_id = task["id"]
            deps = task.get("dependencies", [])
            if not deps:
                no_deps.append(task_id)
            else:
                has_deps[task_id] = deps

        # Connect start to tasks with no dependencies
        for task_id in no_deps:
            lines.append(f"    start --> {task_id}")

        # Connect dependencies
        for task_id, deps in has_deps.items():
            for dep in deps:
                lines.append(f"    {dep} --> {task_id}")

        # Find terminal tasks (not a dependency of any other)
        all_deps = set()
        for deps in has_deps.values():
            all_deps.update(deps)

        terminals = [t["id"] for t in tasks if t["id"] not in all_deps]
        for task_id in terminals:
            lines.append(f"    {task_id} --> finish")

        # Styling
        lines.append("")
        lines.append("    classDef completed fill:#4CAF50,stroke:#2E7D32,color:#fff")
        lines.append("    classDef running fill:#2196F3,stroke:#1565C0,color:#fff")
        lines.append("    classDef pending fill:#E0E0E0,stroke:#9E9E9E")
        lines.append("    classDef failed fill:#F44336,stroke:#C62828,color:#fff")

        lines.append("```")
        return "\n".join(lines)

    def _get_task_status(self, task_id: str, task_status: list) -> str | None:
        """Get status for a task"""
        if not task_status:
            return None

        for task in task_status:
            if task.get("task_id") == task_id:
                status = task.get("status", "pending")
                return status
        return "pending"

    # ========== Progress Visualization ==========

    def generate_progress_bar(self, completed: int, total: int, width: int = 20) -> str:
        """Generate ASCII progress bar"""
        if total == 0:
            return f"[{'░' * width}] 0%"

        pct = completed / total
        filled = int(pct * width)
        empty = width - filled

        bar = "█" * filled + "░" * empty
        return f"[{bar}] {pct * 100:.0f}%"

    def generate_stage_progress(self, stages: list, execution_status: dict) -> str:
        """Generate visual stage progress"""
        stage_details = execution_status.get("stage_details", [])
        status_map = {s["stage_id"]: s["status"] for s in stage_details}

        lines = []

        for i, stage in enumerate(stages):
            stage_id = stage["id"]
            stage_name = stage["name"]
            status = status_map.get(stage_id, "pending")

            if status == "completed":
                icon = "✓"
            elif status == "in_progress":
                icon = "▶"
            else:
                icon = "○"

            if i == 0:
                lines.append(f"  {icon} {stage_name}")
            else:
                lines.append("  │")
                lines.append(f"  {icon} {stage_name}")

        return "\n".join(lines)

    def generate_timeline(self, execution: dict, events: list) -> str:
        """Generate execution timeline visualization"""
        lines = ["```", "Timeline"]
        lines.append("─" * 50)

        for event in events:
            ts = event.get("timestamp", "")[:19]
            event_type = event.get("event_type", "unknown")
            stage = event.get("stage_id", "")
            task = event.get("task_id", "")

            icon = {
                "execution_started": "🚀",
                "stage_updated": "📍",
                "task_updated": "✏️",
                "execution_completed": "🏁",
            }.get(event_type, "•")

            location = stage
            if task:
                location = f"{stage}/{task}"

            lines.append(f"  {ts}  {icon}  {event_type}")
            if location:
                lines.append(f"                  └─ {location}")

        lines.append("```")
        return "\n".join(lines)

    # ========== Skill Visualization ==========

    def generate_skill_chart(self, skills: list) -> str:
        """Generate skill proficiency chart"""
        lines = ["```", "Skill Proficiency"]
        lines.append("═" * 50)

        # Group by category
        categories = {}
        for skill in skills:
            cat = skill.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(skill)

        for category, cat_skills in sorted(categories.items()):
            lines.append(f"\n┌─ {category.upper()} ─┐")

            for skill in sorted(cat_skills, key=lambda x: -x.get("current_level", 0)):
                name = skill.get("name", skill.get("skill_id", "Unknown"))
                level = skill.get("current_level", 1)
                completions = skill.get("completions", 0)

                bar = "★" * level + "☆" * (5 - level)
                lines.append(f"  {name[:20]:<20} {bar} ({completions})")

        lines.append("```")
        return "\n".join(lines)

    def generate_learning_path_map(self, path: dict, progress: dict | None = None) -> str:
        """Generate learning path visualization"""
        modules = path.get("modules", [])
        completed = progress.get("modules_completed", []) if progress else []

        lines = ["```mermaid", "flowchart TD"]

        # Define module nodes
        for mod in modules:
            mod_id = mod.get("module_id", mod.get("id"))
            required = "🔒" if mod.get("required", True) else "📖"
            status = "✓" if mod_id in completed else ""

            style = "completed" if mod_id in completed else "pending"
            lines.append(f"    {mod_id}[{required} {mod_id} {status}]:::{style}")

        lines.append("")

        # Build prerequisite graph
        start_modules = []
        for mod in modules:
            mod_id = mod.get("module_id", mod.get("id"))
            prereqs = mod.get("prerequisites", [])

            if not prereqs:
                start_modules.append(mod_id)
            else:
                for prereq in prereqs:
                    lines.append(f"    {prereq} --> {mod_id}")

        # Certification node
        if path.get("certification"):
            cert_name = path["certification"].get("name", "Certification")
            lines.append(f"    cert{{🏆 {cert_name}}}")
            for mod in modules:
                if mod.get("required", True):
                    lines.append(f"    {mod.get('module_id', mod.get('id'))} -.-> cert")

        # Styling
        lines.append("")
        lines.append("    classDef completed fill:#4CAF50,stroke:#2E7D32,color:#fff")
        lines.append("    classDef pending fill:#E0E0E0,stroke:#9E9E9E")

        lines.append("```")
        return "\n".join(lines)

    # ========== Dashboard Visualization ==========

    def generate_dashboard(self, stats: dict, recent_executions: list | None = None, skills: list | None = None) -> str:
        """Generate comprehensive dashboard visualization"""
        lines = ["```"]
        lines.append("╔══════════════════════════════════════════════════════════════╗")
        lines.append("║            WORKFLOW ENGINE DASHBOARD                         ║")
        lines.append("╠══════════════════════════════════════════════════════════════╣")

        # Stats section
        workflows = stats.get("total_workflows", 0)
        templates = stats.get("workflow_templates", 0)
        executions = stats.get("total_executions", 0)
        skills_count = stats.get("total_skills", 0)
        paths = stats.get("total_learning_paths", 0)

        lines.append(f"║  Workflows: {workflows:<8}  Templates: {templates:<8}  Executions: {executions:<8}  ║")
        lines.append(f"║  Skills: {skills_count:<10}  Learning Paths: {paths:<22}     ║")

        # Execution status breakdown
        by_status = stats.get("executions_by_status", {})
        if by_status:
            lines.append("╠══════════════════════════════════════════════════════════════╣")
            lines.append("║  Execution Status                                            ║")
            status_str = "  ".join([f"{s}: {c}" for s, c in by_status.items()])
            lines.append(f"║  {status_str:<60} ║")

        # Recent executions
        if recent_executions:
            lines.append("╠══════════════════════════════════════════════════════════════╣")
            lines.append("║  Recent Executions                                           ║")
            for exec in recent_executions[:3]:
                name = exec.get("name", exec.get("workflow_name", "Unknown"))[:30]
                status = exec.get("status", "unknown")
                icon = {"completed": "✓", "running": "▶", "failed": "✗"}.get(status, "○")
                lines.append(f"║  {icon} {name:<56} ║")

        # Top skills
        if skills:
            lines.append("╠══════════════════════════════════════════════════════════════╣")
            lines.append("║  Top Skills                                                  ║")
            for skill in sorted(skills, key=lambda x: -(x.get("current_level") or 0))[:3]:
                name = skill.get("name", skill.get("skill_id", "Unknown"))[:25]
                level = skill.get("current_level") or 1
                bar = "★" * level + "☆" * (5 - level)
                lines.append(f"║  {name:<25} {bar}                          ║")

        lines.append("╚══════════════════════════════════════════════════════════════╝")
        lines.append("```")
        return "\n".join(lines)

    # ========== Gantt Chart ==========

    def generate_gantt(self, workflow: dict, start_date: str | None = None) -> str:
        """Generate Mermaid Gantt chart for workflow"""
        definition = workflow.get("definition", workflow)
        stages = definition.get("stages", [])

        if not start_date:
            start_date = datetime.now().strftime("%Y-%m-%d")

        lines = ["```mermaid", "gantt"]
        lines.append(f"    title {definition.get('name', 'Workflow')} Timeline")
        lines.append("    dateFormat YYYY-MM-DD")
        lines.append("")

        for stage in stages:
            stage_name = stage["name"]
            stage.get("type", "custom")
            duration = stage.get("duration_days", 7)

            lines.append(f"    section {stage_name}")

            tasks = stage.get("tasks", [])
            if tasks:
                for task in tasks:
                    task_name = task["name"]
                    lines.append(f"    {task_name} :a{task['id']}, {duration}d")
            else:
                lines.append(f"    {stage_name} work :s{stage['id']}, {duration}d")

        lines.append("```")
        return "\n".join(lines)
