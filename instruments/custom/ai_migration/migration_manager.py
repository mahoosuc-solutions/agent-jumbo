"""
AI Migration Manager
Business logic for analyzing processes and designing human-AI workflows
"""

from datetime import datetime

from .migration_db import MigrationDatabase


class MigrationManager:
    """Manages AI migration analysis and workflow design"""

    # Task types that indicate high automation potential
    AUTOMATION_INDICATORS = {
        "high": [
            "data_entry",
            "data_validation",
            "calculation",
            "report_generation",
            "scheduling",
            "notification",
            "file_processing",
            "format_conversion",
            "data_extraction",
            "form_filling",
            "invoice_processing",
            "document_classification",
            "email_routing",
            "status_updates",
        ],
        "medium": [
            "pattern_recognition",
            "categorization",
            "summarization",
            "translation",
            "content_generation",
            "research",
            "data_analysis",
            "recommendation",
            "anomaly_detection",
            "sentiment_analysis",
            "quality_check",
            "customer_inquiry_response",
        ],
        "low": [
            "strategic_decision",
            "negotiation",
            "creative_design",
            "relationship_building",
            "complex_judgment",
            "crisis_management",
            "physical_task",
            "emotional_support",
            "innovation",
            "stakeholder_management",
            "conflict_resolution",
        ],
    }

    # AI tools for different task types
    AI_TOOL_SUGGESTIONS = {
        "data_entry": ["OCR/Document AI", "RPA (UiPath/Power Automate)", "Form Recognition"],
        "data_validation": ["Rule Engine", "ML Validation Model", "Data Quality Tools"],
        "calculation": ["Spreadsheet Automation", "Custom Calculation API"],
        "report_generation": ["Business Intelligence (Tableau/PowerBI)", "Auto-Report Generator"],
        "scheduling": ["AI Scheduling Assistant", "Calendar Automation"],
        "notification": ["Workflow Automation", "Alert Management System"],
        "email_routing": ["Email AI Classifier", "Intent Recognition"],
        "document_classification": ["Document AI", "NLP Classifier"],
        "summarization": ["LLM Summarizer (GPT/Claude)", "Text Analytics"],
        "translation": ["Neural Machine Translation", "DeepL/Google Translate API"],
        "content_generation": ["LLM Content Generator", "Template Engine"],
        "data_analysis": ["AutoML", "Statistical Analysis Tools", "BI Dashboards"],
        "recommendation": ["Recommendation Engine", "Collaborative Filtering"],
        "customer_inquiry_response": ["AI Chatbot", "Knowledge Base + LLM"],
        "quality_check": ["Computer Vision", "ML Quality Model", "Rules Engine"],
    }

    def __init__(self, db_path: str):
        self.db = MigrationDatabase(db_path)

    # ========== Assessment Methods ==========

    def start_assessment(
        self, business_name: str, customer_id: int | None = None, industry: str | None = None, **kwargs
    ) -> dict:
        """
        Start a new business migration assessment

        Args:
            business_name: Name of the business
            customer_id: Optional link to customer_lifecycle
            industry: Industry sector
            **kwargs: Additional fields (company_size, pain_points, goals, etc.)

        Returns:
            dict with project_id and next steps
        """
        project_id = self.db.create_project(
            business_name=business_name, customer_id=customer_id, industry=industry, **kwargs
        )

        return {
            "project_id": project_id,
            "business_name": business_name,
            "status": "assessment",
            "next_steps": [
                "Add business processes with add_process",
                "Document tasks within each process",
                "Run analyze_process to get automation scores",
                "Design optimized workflows with design_workflow",
                "Generate migration roadmap with generate_roadmap",
            ],
        }

    def get_assessment_summary(self, project_id: int) -> dict:
        """Get comprehensive assessment summary"""
        project = self.db.get_project(project_id)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        processes = self.db.list_processes(project_id)
        workflows = self.db.list_workflows(project_id=project_id)
        roadmaps = self.db.list_roadmaps(project_id)
        quick_wins = self.db.list_quick_wins(project_id)
        roi_projections = self.db.list_roi_projections(project_id)

        # Calculate summary metrics
        total_current_hours = sum(p.get("current_time_hours", 0) or 0 for p in processes)
        total_current_cost = sum(p.get("current_cost", 0) or 0 for p in processes)
        avg_automation_score = 0
        if processes:
            scores = [p.get("automation_score", 0) or 0 for p in processes]
            avg_automation_score = sum(scores) / len(scores) if scores else 0

        # Get all tasks for detailed analysis
        all_tasks = []
        for process in processes:
            tasks = self.db.list_tasks(process["process_id"])
            all_tasks.extend(tasks)

        # Categorize tasks
        fully_automatable = [t for t in all_tasks if t.get("automation_category") == "fully_automatable"]
        ai_assisted = [t for t in all_tasks if t.get("automation_category") == "ai_assisted"]
        human_required = [t for t in all_tasks if t.get("automation_category") == "human_required"]

        return {
            "project_id": project_id,
            "business_name": project["business_name"],
            "industry": project.get("industry"),
            "status": project.get("status"),
            "assessment_score": project.get("assessment_score"),
            "summary": {
                "total_processes": len(processes),
                "total_tasks": len(all_tasks),
                "total_current_hours_monthly": total_current_hours,
                "total_current_cost_monthly": total_current_cost,
                "average_automation_score": round(avg_automation_score, 1),
            },
            "task_breakdown": {
                "fully_automatable": len(fully_automatable),
                "ai_assisted": len(ai_assisted),
                "human_required": len(human_required),
                "unanalyzed": len(all_tasks) - len(fully_automatable) - len(ai_assisted) - len(human_required),
            },
            "workflows_designed": len(workflows),
            "roadmaps_created": len(roadmaps),
            "quick_wins_identified": len(quick_wins),
            "roi_scenarios": len(roi_projections),
            "processes": [
                {
                    "name": p["name"],
                    "department": p.get("department"),
                    "automation_score": p.get("automation_score"),
                    "current_time_hours": p.get("current_time_hours"),
                    "status": p.get("status"),
                }
                for p in processes
            ],
        }

    # ========== Process Methods ==========

    def add_process(self, project_id: int, name: str, **kwargs) -> dict:
        """Add a business process to analyze"""
        process_id = self.db.add_process(project_id, name, **kwargs)

        return {
            "process_id": process_id,
            "name": name,
            "status": "documented",
            "next_steps": ["Add tasks with add_task", "Analyze automation potential with analyze_process"],
        }

    def add_task(self, process_id: int, name: str, **kwargs) -> dict:
        """Add a task to a process"""
        task_id = self.db.add_task(process_id, name, **kwargs)

        return {"task_id": task_id, "name": name, "process_id": process_id, "status": "documented"}

    def analyze_process(self, process_id: int) -> dict:
        """
        Analyze a process for automation potential

        Calculates automation scores for each task and overall process,
        suggests AI tools, and identifies optimization opportunities.
        """
        process = self.db.get_process(process_id)
        if not process:
            return {"error": f"Process not found: {process_id}"}

        tasks = self.db.list_tasks(process_id)
        if not tasks:
            return {"error": "No tasks found for this process. Add tasks first."}

        analyzed_tasks = []
        total_time = 0
        total_savings = 0

        for task in tasks:
            analysis = self._analyze_task(task)
            analyzed_tasks.append(analysis)

            # Update task in database
            self.db.update_task(
                task["task_id"],
                automation_score=analysis["automation_score"],
                automation_category=analysis["category"],
                proposed_owner=analysis["proposed_owner"],
                ai_tools_suggested=analysis["ai_tools"],
                estimated_savings_minutes=analysis["estimated_savings_minutes"],
                implementation_effort=analysis["implementation_effort"],
            )

            total_time += task.get("time_minutes", 0) or 0
            total_savings += analysis["estimated_savings_minutes"]

        # Calculate process-level score
        process_score = self._calculate_process_score(analyzed_tasks)
        automation_percentage = (total_savings / total_time * 100) if total_time > 0 else 0

        # Update process
        self.db.update_process(process_id, automation_score=process_score, status="analyzed")

        return {
            "process_id": process_id,
            "process_name": process["name"],
            "automation_score": process_score,
            "automation_percentage": round(automation_percentage, 1),
            "total_time_minutes": total_time,
            "potential_savings_minutes": round(total_savings, 1),
            "tasks_analyzed": len(analyzed_tasks),
            "task_breakdown": {
                "fully_automatable": sum(1 for t in analyzed_tasks if t["category"] == "fully_automatable"),
                "ai_assisted": sum(1 for t in analyzed_tasks if t["category"] == "ai_assisted"),
                "human_required": sum(1 for t in analyzed_tasks if t["category"] == "human_required"),
            },
            "tasks": analyzed_tasks,
            "recommendations": self._generate_process_recommendations(analyzed_tasks, process),
        }

    def _analyze_task(self, task: dict) -> dict:
        """Analyze a single task for automation potential"""
        task_type = (task.get("task_type") or "").lower().replace(" ", "_")
        complexity = task.get("complexity", "medium")
        time_minutes = task.get("time_minutes", 0) or 0
        error_rate = task.get("error_rate", 0) or 0
        decision_points = task.get("decision_points", [])

        # Calculate base automation score
        score = 50  # Start neutral

        # Adjust based on task type
        if task_type in self.AUTOMATION_INDICATORS["high"]:
            score += 35
        elif task_type in self.AUTOMATION_INDICATORS["medium"]:
            score += 15
        elif task_type in self.AUTOMATION_INDICATORS["low"]:
            score -= 25

        # Adjust for complexity
        complexity_adjustments = {"low": 10, "medium": 0, "high": -15}
        score += complexity_adjustments.get(complexity, 0)

        # High error rate = good candidate for automation
        if error_rate > 0.1:
            score += 10
        elif error_rate > 0.05:
            score += 5

        # Many decision points = harder to automate
        if len(decision_points) > 3:
            score -= 15
        elif len(decision_points) > 1:
            score -= 5

        # Clamp score
        score = max(0, min(100, score))

        # Determine category
        if score >= 70:
            category = "fully_automatable"
            proposed_owner = "ai"
            savings_pct = 0.85
        elif score >= 40:
            category = "ai_assisted"
            proposed_owner = "hybrid"
            savings_pct = 0.50
        else:
            category = "human_required"
            proposed_owner = "human"
            savings_pct = 0.10

        # Get AI tool suggestions
        ai_tools = self.AI_TOOL_SUGGESTIONS.get(task_type, [])
        if not ai_tools and score >= 40:
            ai_tools = ["Custom AI Solution", "Workflow Automation"]

        # Calculate implementation effort
        if complexity == "low" and score >= 70:
            effort = "low"
        elif complexity == "high" or score < 40:
            effort = "high"
        else:
            effort = "medium"

        return {
            "task_id": task["task_id"],
            "name": task["name"],
            "task_type": task_type,
            "automation_score": score,
            "category": category,
            "proposed_owner": proposed_owner,
            "ai_tools": ai_tools,
            "estimated_savings_minutes": round(time_minutes * savings_pct, 1),
            "implementation_effort": effort,
            "analysis_factors": {
                "task_type_impact": task_type in self.AUTOMATION_INDICATORS["high"],
                "complexity": complexity,
                "decision_points": len(decision_points),
                "error_rate": error_rate,
            },
        }

    def _calculate_process_score(self, analyzed_tasks: list[dict]) -> int:
        """Calculate overall process automation score"""
        if not analyzed_tasks:
            return 0

        # Weighted average based on time
        total_weighted = 0
        total_weight = 0

        for task in analyzed_tasks:
            weight = 1  # Could use time_minutes as weight
            total_weighted += task["automation_score"] * weight
            total_weight += weight

        return round(total_weighted / total_weight) if total_weight > 0 else 0

    def _generate_process_recommendations(self, analyzed_tasks: list[dict], process: dict) -> list[str]:
        """Generate actionable recommendations for a process"""
        recommendations = []

        # Count categories
        fully_auto = [t for t in analyzed_tasks if t["category"] == "fully_automatable"]
        ai_assisted = [t for t in analyzed_tasks if t["category"] == "ai_assisted"]

        if len(fully_auto) > 0:
            recommendations.append(f"Start with {len(fully_auto)} fully automatable tasks for quick wins")

        if len(ai_assisted) > 0:
            recommendations.append(f"{len(ai_assisted)} tasks can be AI-assisted with human oversight")

        # High-value automation candidates
        high_time_tasks = sorted(analyzed_tasks, key=lambda t: t["estimated_savings_minutes"], reverse=True)[:3]
        if high_time_tasks:
            names = [t["name"] for t in high_time_tasks]
            recommendations.append(f"Highest ROI tasks to automate: {', '.join(names)}")

        return recommendations

    # ========== Workflow Design Methods ==========

    def design_workflow(self, process_id: int, automation_level: str = "balanced") -> dict:
        """
        Design an optimized human-AI workflow

        Args:
            process_id: Process to design workflow for
            automation_level: 'aggressive', 'balanced', or 'conservative'

        Returns:
            Designed workflow with steps, touchpoints, and estimates
        """
        process = self.db.get_process(process_id)
        if not process:
            return {"error": f"Process not found: {process_id}"}

        tasks = self.db.list_tasks(process_id)
        if not tasks:
            return {"error": "No tasks found. Analyze the process first."}

        # Build workflow steps
        steps = []
        human_touchpoints = 0
        ai_touchpoints = 0
        total_time = 0

        for i, task in enumerate(tasks, 1):
            category = task.get("automation_category", "human_required")
            proposed_owner = task.get("proposed_owner", "human")

            # Adjust based on automation level
            if automation_level == "conservative":
                if category == "ai_assisted":
                    proposed_owner = "human_with_ai_support"
            elif automation_level == "aggressive":
                if category == "ai_assisted":
                    proposed_owner = "ai_with_human_review"

            step = {
                "step": i,
                "name": task["name"],
                "owner": proposed_owner,
                "original_owner": task.get("current_owner"),
                "ai_tools": task.get("ai_tools_suggested", []),
                "time_minutes": task.get("time_minutes", 0),
                "automation_score": task.get("automation_score", 0),
            }

            if proposed_owner in ["ai", "ai_with_human_review"]:
                ai_touchpoints += 1
                step["time_minutes"] = step["time_minutes"] * 0.15  # 85% time reduction
            elif proposed_owner in ["hybrid", "human_with_ai_support"]:
                human_touchpoints += 1
                ai_touchpoints += 1
                step["time_minutes"] = step["time_minutes"] * 0.5  # 50% time reduction
            else:
                human_touchpoints += 1

            total_time += step["time_minutes"]
            steps.append(step)

        # Calculate metrics
        original_time = process.get("current_time_hours", 0) or 0
        original_cost = process.get("current_cost", 0) or 0
        optimized_time = total_time / 60  # Convert to hours

        automation_percentage = 0
        if original_time > 0:
            automation_percentage = ((original_time - optimized_time) / original_time) * 100

        # Estimate costs
        # Assume AI costs ~$20/hour equivalent, human ~$50/hour
        ai_cost_per_hour = 20
        human_cost_per_hour = 50
        ai_hours = sum(s["time_minutes"] for s in steps if s["owner"] in ["ai", "ai_with_human_review"]) / 60
        human_hours = optimized_time - ai_hours
        optimized_cost = (ai_hours * ai_cost_per_hour) + (human_hours * human_cost_per_hour)

        workflow_name = f"{process['name']} - {automation_level.title()} Workflow"

        # Save workflow
        workflow_id = self.db.add_workflow(
            process_id=process_id,
            name=workflow_name,
            steps=steps,
            workflow_type=automation_level,
            human_touchpoints=human_touchpoints,
            ai_touchpoints=ai_touchpoints,
            estimated_time_hours=optimized_time,
            estimated_cost=optimized_cost,
            automation_percentage=automation_percentage,
            quality_impact="improved" if automation_percentage > 30 else "maintained",
        )

        return {
            "workflow_id": workflow_id,
            "name": workflow_name,
            "process_name": process["name"],
            "automation_level": automation_level,
            "original_process": {"time_hours": original_time, "cost": original_cost},
            "optimized_workflow": {
                "time_hours": round(optimized_time, 2),
                "cost": round(optimized_cost, 2),
                "human_touchpoints": human_touchpoints,
                "ai_touchpoints": ai_touchpoints,
                "automation_percentage": round(automation_percentage, 1),
            },
            "savings": {
                "time_hours": round(original_time - optimized_time, 2),
                "time_percentage": round(automation_percentage, 1),
                "cost": round(original_cost - optimized_cost, 2) if original_cost > 0 else None,
            },
            "steps": steps,
        }

    # ========== Roadmap Methods ==========

    def generate_roadmap(self, project_id: int, timeline_months: int = 12, budget: float | None = None) -> dict:
        """
        Generate a migration roadmap with phases

        Args:
            project_id: Project ID
            timeline_months: Target timeline in months
            budget: Optional budget constraint

        Returns:
            Complete roadmap with phases, quick wins, and ROI
        """
        project = self.db.get_project(project_id)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        processes = self.db.list_processes(project_id)
        if not processes:
            return {"error": "No processes documented. Add processes first."}

        # Get all tasks and sort by ROI potential
        all_tasks = []
        for process in processes:
            tasks = self.db.list_tasks(process["process_id"])
            for task in tasks:
                task["process_name"] = process["name"]
                all_tasks.append(task)

        # Identify quick wins (high score, low effort)
        quick_wins = [
            t for t in all_tasks if t.get("automation_score", 0) >= 70 and t.get("implementation_effort") == "low"
        ]

        # Sort by potential savings
        quick_wins.sort(key=lambda t: t.get("estimated_savings_minutes", 0), reverse=True)

        # Save quick wins
        for qw in quick_wins[:10]:  # Top 10
            self.db.add_quick_win(
                project_id=project_id,
                name=qw["name"],
                task_id=qw["task_id"],
                description=f"Automate {qw['name']} in {qw['process_name']}",
                proposed_solution=", ".join(qw.get("ai_tools_suggested", ["Automation"])[:2]),
                effort_days=5,  # Estimate
                estimated_savings=qw.get("estimated_savings_minutes", 0) * 12,  # Annual
                risk_level="low",
                priority_score=qw.get("automation_score", 50),
            )

        # Build phases
        phases = self._build_phases(processes, all_tasks, timeline_months)

        # Calculate ROI
        total_investment = self._estimate_investment(phases)
        annual_savings = self._estimate_annual_savings(all_tasks)

        payback_months = 0
        if annual_savings > 0:
            payback_months = int((total_investment / annual_savings) * 12)

        roi_percentage = 0
        if total_investment > 0:
            roi_percentage = ((annual_savings * 3 - total_investment) / total_investment) * 100

        # Save roadmap
        roadmap_id = self.db.add_roadmap(
            project_id=project_id,
            name=f"{project['business_name']} AI Migration Roadmap",
            phases=phases,
            approach="phased",
            quick_wins=[qw["name"] for qw in quick_wins[:5]],
            total_investment=total_investment,
            projected_savings_year1=annual_savings,
            projected_savings_year3=annual_savings * 3,
            projected_savings_year5=annual_savings * 5,
            payback_months=payback_months,
            roi_percentage=round(roi_percentage, 1),
            risks=self._identify_risks(processes),
            success_metrics=self._define_metrics(),
        )

        return {
            "roadmap_id": roadmap_id,
            "project_name": project["business_name"],
            "timeline_months": timeline_months,
            "phases": phases,
            "quick_wins": [
                {
                    "name": qw["name"],
                    "process": qw["process_name"],
                    "savings_minutes": qw.get("estimated_savings_minutes", 0),
                }
                for qw in quick_wins[:5]
            ],
            "investment": {"total": round(total_investment, 2), "breakdown": self._investment_breakdown(phases)},
            "projected_roi": {
                "annual_savings": round(annual_savings, 2),
                "payback_months": payback_months,
                "roi_3_year": f"{round(roi_percentage, 1)}%",
            },
            "risks": self._identify_risks(processes),
            "success_metrics": self._define_metrics(),
        }

    def _build_phases(self, processes: list[dict], tasks: list[dict], timeline_months: int) -> list[dict]:
        """Build implementation phases"""
        phases = []

        # Phase 1: Quick Wins (Month 1-2)
        phases.append(
            {
                "phase": 1,
                "name": "Quick Wins",
                "duration_months": 2,
                "description": "Implement high-value, low-effort automations",
                "focus": "Fully automatable tasks with immediate ROI",
                "activities": [
                    "Deploy RPA for data entry tasks",
                    "Implement document processing automation",
                    "Set up notification and scheduling automation",
                ],
                "deliverables": ["5-10 automated tasks", "Initial efficiency gains"],
            }
        )

        # Phase 2: Core Automation (Month 3-6)
        phases.append(
            {
                "phase": 2,
                "name": "Core Automation",
                "duration_months": 4,
                "description": "Implement AI-assisted workflows for key processes",
                "focus": "Medium complexity automations with human oversight",
                "activities": [
                    "Deploy AI assistants for research and analysis",
                    "Implement workflow orchestration",
                    "Set up quality monitoring dashboards",
                ],
                "deliverables": ["3-5 optimized workflows", "AI integration complete"],
            }
        )

        # Phase 3: Advanced Integration (Month 7-9)
        phases.append(
            {
                "phase": 3,
                "name": "Advanced Integration",
                "duration_months": 3,
                "description": "Connect systems and optimize end-to-end flows",
                "focus": "Cross-process optimization and data integration",
                "activities": [
                    "System integrations and API connections",
                    "Advanced analytics and reporting",
                    "Exception handling automation",
                ],
                "deliverables": ["Integrated systems", "Automated reporting"],
            }
        )

        # Phase 4: Optimization & Scale (Month 10-12)
        phases.append(
            {
                "phase": 4,
                "name": "Optimization & Scale",
                "duration_months": 3,
                "description": "Refine, scale, and continuous improvement",
                "focus": "Performance optimization and knowledge transfer",
                "activities": [
                    "Performance tuning",
                    "Team training and documentation",
                    "Continuous improvement framework",
                ],
                "deliverables": ["Optimized performance", "Trained team", "Improvement roadmap"],
            }
        )

        return phases

    def _estimate_investment(self, phases: list[dict]) -> float:
        """Estimate total investment for roadmap"""
        # Rough estimates per phase
        phase_costs = {
            1: 15000,  # Quick wins
            2: 50000,  # Core automation
            3: 35000,  # Advanced integration
            4: 20000,  # Optimization
        }
        return sum(phase_costs.get(p["phase"], 25000) for p in phases)

    def _investment_breakdown(self, phases: list[dict]) -> dict:
        """Break down investment by category"""
        return {"software_tools": 40000, "implementation_services": 60000, "training": 10000, "contingency": 10000}

    def _estimate_annual_savings(self, tasks: list[dict]) -> float:
        """Estimate annual savings from automation"""
        total_savings_minutes = sum(t.get("estimated_savings_minutes", 0) or 0 for t in tasks)
        # Convert to annual (assuming monthly processes)
        annual_minutes = total_savings_minutes * 12
        # Convert to cost (assuming $50/hour labor)
        return (annual_minutes / 60) * 50

    def _identify_risks(self, processes: list[dict]) -> list[dict]:
        """Identify migration risks"""
        return [
            {
                "risk": "Change resistance",
                "impact": "medium",
                "mitigation": "Early stakeholder engagement and training",
            },
            {"risk": "Integration complexity", "impact": "high", "mitigation": "Phased approach with thorough testing"},
            {
                "risk": "Data quality issues",
                "impact": "medium",
                "mitigation": "Data cleansing and validation before automation",
            },
            {"risk": "Scope creep", "impact": "medium", "mitigation": "Clear phase boundaries and change control"},
        ]

    def _define_metrics(self) -> list[dict]:
        """Define success metrics"""
        return [
            {"metric": "Process time reduction", "target": "50%", "measurement": "Before/after time tracking"},
            {"metric": "Error rate reduction", "target": "80%", "measurement": "Quality monitoring"},
            {"metric": "Cost savings", "target": "30% of baseline", "measurement": "Financial tracking"},
            {"metric": "Employee satisfaction", "target": "Improvement", "measurement": "Survey scores"},
        ]

    # ========== ROI Methods ==========

    def project_roi(self, project_id: int, scenarios: list[str] | None = None) -> dict:
        """
        Calculate ROI projections for different scenarios

        Args:
            project_id: Project ID
            scenarios: List of scenarios ('conservative', 'moderate', 'aggressive')

        Returns:
            ROI projections for each scenario
        """
        if scenarios is None:
            scenarios = ["conservative", "moderate", "aggressive"]

        project = self.db.get_project(project_id)
        if not project:
            return {"error": f"Project not found: {project_id}"}

        processes = self.db.list_processes(project_id)
        all_tasks = []
        for process in processes:
            tasks = self.db.list_tasks(process["process_id"])
            all_tasks.extend(tasks)

        results = {"project_id": project_id, "scenarios": {}}

        # Scenario multipliers
        multipliers = {
            "conservative": {"savings": 0.6, "cost": 1.2},
            "moderate": {"savings": 0.8, "cost": 1.0},
            "aggressive": {"savings": 1.0, "cost": 0.9},
        }

        base_savings = self._estimate_annual_savings(all_tasks)
        base_investment = 120000  # Baseline investment estimate

        for scenario in scenarios:
            mult = multipliers.get(scenario, multipliers["moderate"])

            implementation_cost = base_investment * mult["cost"]
            annual_savings = base_savings * mult["savings"]
            ongoing_cost = implementation_cost * 0.15  # 15% annual maintenance

            year1_benefit = annual_savings - ongoing_cost
            year3_benefit = year1_benefit * 3
            year5_benefit = year1_benefit * 5

            payback = int((implementation_cost / annual_savings) * 12) if annual_savings > 0 else 999
            roi = ((year3_benefit - implementation_cost) / implementation_cost * 100) if implementation_cost > 0 else 0

            projection_id = self.db.add_roi_projection(
                project_id=project_id,
                scenario=scenario,
                implementation_cost=implementation_cost,
                ongoing_cost_annual=ongoing_cost,
                labor_savings_annual=annual_savings,
                total_benefits_year1=year1_benefit,
                total_benefits_year3=year3_benefit,
                total_benefits_year5=year5_benefit,
                payback_period_months=payback,
                confidence_level=scenario,
            )

            results["scenarios"][scenario] = {
                "projection_id": projection_id,
                "implementation_cost": round(implementation_cost, 2),
                "ongoing_cost_annual": round(ongoing_cost, 2),
                "annual_savings": round(annual_savings, 2),
                "net_benefit_year1": round(year1_benefit, 2),
                "net_benefit_year3": round(year3_benefit, 2),
                "net_benefit_year5": round(year5_benefit, 2),
                "payback_months": payback,
                "roi_3_year": f"{round(roi, 1)}%",
            }

        return results

    # ========== Quick Wins Methods ==========

    def identify_quick_wins(self, project_id: int, max_effort: str = "medium") -> dict:
        """Identify quick win automation opportunities"""
        processes = self.db.list_processes(project_id)
        quick_wins = []

        effort_threshold = {"low": 1, "medium": 2, "high": 3}
        max_threshold = effort_threshold.get(max_effort, 2)

        for process in processes:
            tasks = self.db.list_tasks(process["process_id"])
            for task in tasks:
                score = task.get("automation_score", 0) or 0
                effort = task.get("implementation_effort", "high")
                effort_value = effort_threshold.get(effort, 3)

                if score >= 70 and effort_value <= max_threshold:
                    quick_wins.append(
                        {
                            "task_id": task["task_id"],
                            "name": task["name"],
                            "process": process["name"],
                            "automation_score": score,
                            "effort": effort,
                            "savings_minutes": task.get("estimated_savings_minutes", 0),
                            "ai_tools": task.get("ai_tools_suggested", []),
                            "priority_score": score + (3 - effort_value) * 10,
                        }
                    )

        # Sort by priority
        quick_wins.sort(key=lambda x: x["priority_score"], reverse=True)

        return {
            "project_id": project_id,
            "total_quick_wins": len(quick_wins),
            "max_effort_filter": max_effort,
            "quick_wins": quick_wins[:15],
            "estimated_total_savings_minutes": sum(qw["savings_minutes"] for qw in quick_wins),
        }

    # ========== Report Generation ==========

    def generate_report(self, project_id: int, format: str = "markdown") -> dict:
        """Generate comprehensive migration report"""
        summary = self.get_assessment_summary(project_id)
        if "error" in summary:
            return summary

        project = self.db.get_project(project_id)
        processes = self.db.list_processes(project_id)
        roadmaps = self.db.list_roadmaps(project_id)
        quick_wins = self.db.list_quick_wins(project_id)
        self.db.list_roi_projections(project_id)

        report = f"""# AI Migration Assessment Report

## Business: {project["business_name"]}
**Industry:** {project.get("industry", "N/A")}
**Assessment Date:** {datetime.now().strftime("%Y-%m-%d")}

---

## Executive Summary

- **Processes Analyzed:** {summary["summary"]["total_processes"]}
- **Tasks Documented:** {summary["summary"]["total_tasks"]}
- **Average Automation Score:** {summary["summary"]["average_automation_score"]}/100
- **Current Monthly Hours:** {summary["summary"]["total_current_hours_monthly"]}

### Task Classification
- Fully Automatable: {summary["task_breakdown"]["fully_automatable"]}
- AI-Assisted: {summary["task_breakdown"]["ai_assisted"]}
- Human Required: {summary["task_breakdown"]["human_required"]}

---

## Processes Analyzed

"""
        for p in processes:
            report += f"""### {p["name"]}
- **Department:** {p.get("department", "N/A")}
- **Automation Score:** {p.get("automation_score", "N/A")}/100
- **Current Time:** {p.get("current_time_hours", 0)} hours/month
- **Status:** {p.get("status", "documented")}

"""

        if quick_wins:
            report += """## Quick Wins Identified

| Task | Process | Score | Effort | Monthly Savings |
|------|---------|-------|--------|-----------------|
"""
            for qw in quick_wins[:10]:
                report += f"| {qw['name']} | - | {qw.get('priority_score', '-')} | {qw.get('risk_level', '-')} | ${qw.get('estimated_savings', 0):.0f} |\n"

        if roadmaps:
            roadmap = roadmaps[0]
            report += f"""
## Migration Roadmap

**Total Investment:** ${roadmap.get("total_investment", 0):,.0f}
**Projected Annual Savings:** ${roadmap.get("projected_savings_year1", 0):,.0f}
**Payback Period:** {roadmap.get("payback_months", "N/A")} months
**3-Year ROI:** {roadmap.get("roi_percentage", 0):.1f}%

"""

        report += """
---
*Report generated by Agent Jumbo AI Migration Tool*
"""

        return {"project_id": project_id, "format": format, "report": report}
