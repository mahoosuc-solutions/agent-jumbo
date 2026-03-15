"""
Sales Generator Manager - Business logic for generating sales materials
Creates proposals, demos, ROI analyses, case studies, and business cases
"""

from datetime import datetime

from .sales_db import SalesGeneratorDatabase


class SalesGeneratorManager:
    """Manager for sales material generation"""

    # Proposal templates
    PROPOSAL_SECTIONS = [
        "executive_summary",
        "understanding_needs",
        "proposed_solution",
        "deliverables",
        "timeline",
        "pricing",
        "terms",
        "next_steps",
    ]

    # ROI calculation defaults
    DEFAULT_DISCOUNT_RATE = 0.10  # 10% for NPV calculations

    def __init__(self, db_path: str):
        self.db = SalesGeneratorDatabase(db_path)

    # ========== Proposal Operations ==========

    def generate_proposal(
        self,
        title: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        solution_summary: str | None = None,
        items: list | None = None,
        valid_days: int = 30,
        include_terms: bool = True,
    ) -> dict:
        """Generate a full proposal document"""

        # Create proposal record
        proposal_id = self.db.create_proposal(
            title=title,
            customer_id=customer_id,
            customer_name=customer_name,
            solution_summary=solution_summary,
            valid_days=valid_days,
        )

        # Add line items
        total = 0
        if items:
            for item in items:
                self.db.add_proposal_item(
                    proposal_id=proposal_id,
                    name=item.get("name", "Service"),
                    description=item.get("description"),
                    quantity=item.get("quantity", 1),
                    unit_price=item.get("unit_price", 0),
                    item_type=item.get("type", "service"),
                )
                total += item.get("quantity", 1) * item.get("unit_price", 0)

        # Generate proposal content
        content = self._generate_proposal_content(
            title=title,
            customer_name=customer_name,
            solution_summary=solution_summary,
            items=items or [],
            total=total,
            include_terms=include_terms,
        )

        self.db.update_proposal_content(proposal_id, content)

        return {
            "proposal_id": proposal_id,
            "title": title,
            "customer_name": customer_name,
            "total": total,
            "status": "draft",
            "content": content,
        }

    def _generate_proposal_content(
        self, title: str, customer_name: str, solution_summary: str, items: list, total: float, include_terms: bool
    ) -> str:
        """Generate proposal markdown content"""
        lines = []

        # Header
        lines.append(f"# Proposal: {title}")
        lines.append("")
        lines.append(f"**Prepared for:** {customer_name or 'Valued Customer'}")
        lines.append(f"**Date:** {datetime.now().strftime('%B %d, %Y')}")
        lines.append("")

        # Executive Summary
        lines.append("## Executive Summary")
        lines.append("")
        if solution_summary:
            lines.append(solution_summary)
        else:
            lines.append("We are pleased to present this proposal for your consideration.")
        lines.append("")

        # Proposed Solution
        lines.append("## Proposed Solution")
        lines.append("")
        lines.append("Our solution addresses your requirements with the following deliverables:")
        lines.append("")

        # Deliverables/Items
        lines.append("## Deliverables & Pricing")
        lines.append("")
        lines.append("| Item | Description | Qty | Unit Price | Total |")
        lines.append("|------|-------------|-----|------------|-------|")

        for item in items:
            name = item.get("name", "Service")
            desc = item.get("description", "")[:50] if item.get("description") else ""
            qty = item.get("quantity", 1)
            unit = item.get("unit_price", 0)
            item_total = qty * unit
            lines.append(f"| {name} | {desc} | {qty} | ${unit:,.2f} | ${item_total:,.2f} |")

        lines.append(f"| **Total** | | | | **${total:,.2f}** |")
        lines.append("")

        # Timeline
        lines.append("## Timeline")
        lines.append("")
        lines.append("Project timeline to be determined based on scope finalization.")
        lines.append("")

        # Terms
        if include_terms:
            lines.append("## Terms & Conditions")
            lines.append("")
            lines.append("- Payment terms: 50% upon signing, 50% upon completion")
            lines.append("- Proposal valid for 30 days from date of issue")
            lines.append("- Changes to scope may affect pricing and timeline")
            lines.append("")

        # Next Steps
        lines.append("## Next Steps")
        lines.append("")
        lines.append("1. Review this proposal")
        lines.append("2. Schedule a call to discuss any questions")
        lines.append("3. Sign and return to proceed")
        lines.append("")

        return "\n".join(lines)

    def get_proposal(self, proposal_id: int) -> dict:
        """Get proposal details"""
        return self.db.get_proposal(proposal_id)

    def list_proposals(self, customer_id: int | None = None, status: str | None = None) -> list:
        """List proposals"""
        return self.db.list_proposals(customer_id, status)

    def update_proposal_status(self, proposal_id: int, status: str) -> dict:
        """Update proposal status"""
        self.db.update_proposal_status(proposal_id, status)
        return {"proposal_id": proposal_id, "status": status}

    # ========== Demo Operations ==========

    def create_demo(
        self,
        title: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        demo_type: str = "interactive",
        features: list | None = None,
        description: str | None = None,
    ) -> dict:
        """Create a demo specification"""

        demo_id = self.db.create_demo(
            title=title, customer_id=customer_id, customer_name=customer_name, demo_type=demo_type, features=features
        )

        # Generate demo content
        content = self._generate_demo_content(
            title=title,
            customer_name=customer_name,
            demo_type=demo_type,
            features=features or [],
            description=description,
        )

        self.db.update_demo_content(demo_id, content)

        return {
            "demo_id": demo_id,
            "title": title,
            "demo_type": demo_type,
            "features_count": len(features or []),
            "content": content,
        }

    def _generate_demo_content(
        self, title: str, customer_name: str, demo_type: str, features: list, description: str
    ) -> str:
        """Generate demo script/specification"""
        lines = []

        lines.append(f"# Demo: {title}")
        lines.append("")
        lines.append(f"**Type:** {demo_type}")
        if customer_name:
            lines.append(f"**For:** {customer_name}")
        lines.append("")

        if description:
            lines.append("## Overview")
            lines.append(description)
            lines.append("")

        lines.append("## Features to Demonstrate")
        lines.append("")
        for i, feature in enumerate(features, 1):
            if isinstance(feature, dict):
                lines.append(f"### {i}. {feature.get('name', 'Feature')}")
                if feature.get("description"):
                    lines.append(feature["description"])
                if feature.get("steps"):
                    lines.append("\n**Steps:**")
                    for step in feature["steps"]:
                        lines.append(f"- {step}")
            else:
                lines.append(f"{i}. {feature}")
            lines.append("")

        lines.append("## Demo Script")
        lines.append("")
        lines.append("1. **Introduction** - Welcome and set context")
        lines.append("2. **Pain Points** - Acknowledge current challenges")
        lines.append("3. **Solution Overview** - High-level capabilities")
        lines.append("4. **Live Demo** - Walk through features")
        lines.append("5. **Q&A** - Address questions")
        lines.append("6. **Next Steps** - Propose follow-up actions")

        return "\n".join(lines)

    def get_demo(self, demo_id: int) -> dict:
        """Get demo details"""
        return self.db.get_demo(demo_id)

    def list_demos(self, customer_id: int | None = None) -> list:
        """List demos"""
        return self.db.list_demos(customer_id)

    # ========== ROI Operations ==========

    def calculate_roi(
        self,
        title: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        current_costs: dict | None = None,
        projected_savings: dict | None = None,
        implementation_cost: float = 0,
        years: int = 3,
    ) -> dict:
        """Calculate ROI with projections"""

        current_costs = current_costs or {}
        projected_savings = projected_savings or {}

        # Calculate totals
        annual_current_cost = sum(current_costs.values())
        annual_savings = sum(projected_savings.values())

        # Implementation costs breakdown
        impl_costs = {
            "implementation": implementation_cost,
            "training": implementation_cost * 0.1,
            "contingency": implementation_cost * 0.15,
        }
        total_investment = sum(impl_costs.values())

        # Calculate payback period
        if annual_savings > 0:
            payback_months = int((total_investment / annual_savings) * 12)
        else:
            payback_months = 0

        # Calculate ROI percentage
        total_savings_over_period = annual_savings * years
        if total_investment > 0:
            roi_percentage = ((total_savings_over_period - total_investment) / total_investment) * 100
        else:
            roi_percentage = 0

        # Calculate NPV
        npv = -total_investment
        for year in range(1, years + 1):
            npv += annual_savings / ((1 + self.DEFAULT_DISCOUNT_RATE) ** year)

        # Generate projections for each scenario
        projections = {
            "conservative": self._generate_projection(annual_savings * 0.5, total_investment, years),
            "moderate": self._generate_projection(annual_savings * 0.75, total_investment, years),
            "aggressive": self._generate_projection(annual_savings, total_investment, years),
        }

        # Store in database
        roi_id = self.db.create_roi_calculation(
            title=title,
            customer_id=customer_id,
            customer_name=customer_name,
            current_costs=current_costs,
            projected_savings=projected_savings,
            implementation_costs=impl_costs,
        )

        self.db.update_roi_results(roi_id, payback_months, roi_percentage, npv, projections)

        return {
            "roi_id": roi_id,
            "title": title,
            "summary": {
                "annual_current_cost": annual_current_cost,
                "annual_savings": annual_savings,
                "total_investment": total_investment,
                "payback_months": payback_months,
                "roi_percentage": round(roi_percentage, 1),
                "npv": round(npv, 2),
            },
            "projections": projections,
        }

    def _generate_projection(self, annual_savings: float, investment: float, years: int) -> dict:
        """Generate year-by-year projection"""
        projection = {"annual_savings": round(annual_savings, 2), "years": {}}

        cumulative = -investment
        for year in range(1, years + 1):
            cumulative += annual_savings
            projection["years"][f"year_{year}"] = {
                "savings": round(annual_savings, 2),
                "cumulative": round(cumulative, 2),
                "positive": cumulative > 0,
            }

        # Calculate payback
        if annual_savings > 0:
            projection["payback_months"] = int((investment / annual_savings) * 12)
        else:
            projection["payback_months"] = 0

        return projection

    def get_roi_calculation(self, roi_id: int) -> dict:
        """Get ROI calculation"""
        return self.db.get_roi_calculation(roi_id)

    def list_roi_calculations(self, customer_id: int | None = None) -> list:
        """List ROI calculations"""
        return self.db.list_roi_calculations(customer_id)

    # ========== Case Study Operations ==========

    def generate_case_study(
        self,
        project_name: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        industry: str | None = None,
        challenge: str | None = None,
        solution: str | None = None,
        results: str | None = None,
        metrics: dict | None = None,
        testimonial: str | None = None,
    ) -> dict:
        """Generate a case study"""

        case_study_id = self.db.create_case_study(
            project_name=project_name,
            customer_id=customer_id,
            customer_name=customer_name,
            industry=industry,
            challenge=challenge,
            solution=solution,
            results=results,
            metrics=metrics,
            testimonial=testimonial,
        )

        # Format content
        content = self._generate_case_study_content(
            project_name=project_name,
            customer_name=customer_name,
            industry=industry,
            challenge=challenge,
            solution=solution,
            results=results,
            metrics=metrics or {},
            testimonial=testimonial,
        )

        return {"case_study_id": case_study_id, "project_name": project_name, "industry": industry, "content": content}

    def _generate_case_study_content(
        self,
        project_name: str,
        customer_name: str,
        industry: str,
        challenge: str,
        solution: str,
        results: str,
        metrics: dict,
        testimonial: str,
    ) -> str:
        """Generate case study markdown"""
        lines = []

        lines.append(f"# Case Study: {project_name}")
        lines.append("")

        if industry:
            lines.append(f"**Industry:** {industry}")
        if customer_name:
            lines.append(f"**Client:** {customer_name}")
        lines.append("")

        if challenge:
            lines.append("## The Challenge")
            lines.append(challenge)
            lines.append("")

        if solution:
            lines.append("## Our Solution")
            lines.append(solution)
            lines.append("")

        if results:
            lines.append("## Results")
            lines.append(results)
            lines.append("")

        if metrics:
            lines.append("## Key Metrics")
            lines.append("")
            for metric, value in metrics.items():
                lines.append(f"- **{metric}:** {value}")
            lines.append("")

        if testimonial:
            lines.append("## Client Testimonial")
            lines.append("")
            lines.append(f"> {testimonial}")
            lines.append("")

        return "\n".join(lines)

    def get_case_study(self, case_study_id: int) -> dict:
        """Get case study"""
        return self.db.get_case_study(case_study_id)

    def list_case_studies(self, industry: str | None = None, status: str | None = None) -> list:
        """List case studies"""
        return self.db.list_case_studies(industry, status)

    # ========== Portfolio Showcase Operations ==========

    def generate_portfolio_showcase(
        self,
        title: str,
        description: str | None = None,
        projects: list | None = None,
        target_industry: str | None = None,
    ) -> dict:
        """Generate a portfolio showcase"""

        showcase_id = self.db.create_showcase(
            title=title, description=description, projects=projects, target_industry=target_industry
        )

        content = self._generate_showcase_content(
            title=title, description=description, projects=projects or [], target_industry=target_industry
        )

        self.db.update_showcase_content(showcase_id, content)

        return {"showcase_id": showcase_id, "title": title, "projects_count": len(projects or []), "content": content}

    def _generate_showcase_content(self, title: str, description: str, projects: list, target_industry: str) -> str:
        """Generate showcase markdown"""
        lines = []

        lines.append(f"# {title}")
        lines.append("")

        if description:
            lines.append(description)
            lines.append("")

        if target_industry:
            lines.append(f"*Curated for the {target_industry} industry*")
            lines.append("")

        lines.append("## Featured Projects")
        lines.append("")

        for i, project in enumerate(projects, 1):
            if isinstance(project, dict):
                lines.append(f"### {i}. {project.get('name', 'Project')}")
                if project.get("description"):
                    lines.append(project["description"])
                if project.get("tech_stack"):
                    lines.append(f"\n**Technologies:** {', '.join(project['tech_stack'])}")
                if project.get("outcomes"):
                    lines.append(f"\n**Outcomes:** {project['outcomes']}")
            else:
                lines.append(f"### {i}. {project}")
            lines.append("")

        lines.append("---")
        lines.append("")
        lines.append("*Contact us to learn more about how we can help with your project.*")

        return "\n".join(lines)

    def get_showcase(self, showcase_id: int) -> dict:
        """Get showcase"""
        return self.db.get_showcase(showcase_id)

    def list_showcases(self, target_industry: str | None = None) -> list:
        """List showcases"""
        return self.db.list_showcases(target_industry)

    # ========== Business Case Operations ==========

    def build_business_case(
        self,
        title: str,
        customer_id: int | None = None,
        customer_name: str | None = None,
        problem_statement: str | None = None,
        proposed_solution: str | None = None,
        benefits: list | None = None,
        risks: list | None = None,
        timeline: str | None = None,
        investment_required: float | None = None,
        recommendation: str | None = None,
    ) -> dict:
        """Build a comprehensive business case"""

        # Generate executive summary
        executive_summary = self._generate_executive_summary(
            problem_statement=problem_statement,
            proposed_solution=proposed_solution,
            benefits=benefits or [],
            investment=investment_required,
        )

        case_id = self.db.create_business_case(
            title=title,
            customer_id=customer_id,
            customer_name=customer_name,
            executive_summary=executive_summary,
            problem_statement=problem_statement,
            proposed_solution=proposed_solution,
            benefits=benefits,
            risks=risks,
            timeline=timeline,
            investment_required=investment_required,
            recommendation=recommendation,
        )

        return {
            "case_id": case_id,
            "title": title,
            "executive_summary": executive_summary,
            "benefits_count": len(benefits or []),
            "risks_count": len(risks or []),
            "investment_required": investment_required,
        }

    def _generate_executive_summary(
        self, problem_statement: str, proposed_solution: str, benefits: list, investment: float
    ) -> str:
        """Generate executive summary for business case"""
        lines = []

        if problem_statement:
            lines.append(f"This business case addresses the following challenge: {problem_statement[:200]}")

        if proposed_solution:
            lines.append(f"The proposed solution involves: {proposed_solution[:200]}")

        if benefits:
            top_benefits = benefits[:3]
            lines.append(f"Key benefits include: {', '.join(str(b) for b in top_benefits)}")

        if investment:
            lines.append(f"Total investment required: ${investment:,.2f}")

        return " ".join(lines)

    def get_business_case(self, case_id: int) -> dict:
        """Get business case"""
        return self.db.get_business_case(case_id)

    def list_business_cases(self, customer_id: int | None = None) -> list:
        """List business cases"""
        return self.db.list_business_cases(customer_id)

    # ========== Comparison Operations ==========

    def create_comparison(
        self, title: str, our_solution: str, competitors: list | None = None, criteria: list | None = None
    ) -> dict:
        """Create competitive comparison"""

        comparison_id = self.db.create_comparison(
            title=title, our_solution=our_solution, competitors=competitors, criteria=criteria
        )

        # Generate analysis
        analysis = self._generate_comparison_analysis(
            our_solution=our_solution, competitors=competitors or [], criteria=criteria or []
        )

        self.db.update_comparison_analysis(comparison_id, analysis)

        return {
            "comparison_id": comparison_id,
            "title": title,
            "competitors_count": len(competitors or []),
            "criteria_count": len(criteria or []),
            "analysis": analysis,
        }

    def _generate_comparison_analysis(self, our_solution: str, competitors: list, criteria: list) -> str:
        """Generate comparison analysis markdown"""
        lines = []

        lines.append("## Competitive Analysis")
        lines.append("")

        # Comparison table header
        header = ["Criteria", our_solution, *competitors]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")

        # Add criteria rows (placeholder - would be filled with actual data)
        for criterion in criteria:
            if isinstance(criterion, dict):
                name = criterion.get("name", "Criterion")
                our_score = criterion.get("our_score", "TBD")
                row = [name, str(our_score)]
                for comp in competitors:
                    row.append("TBD")
            else:
                row = [str(criterion), "TBD"] + ["TBD"] * len(competitors)
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")
        lines.append("## Key Differentiators")
        lines.append("")
        lines.append(f"**{our_solution}** stands out through:")
        lines.append("- [Differentiator 1]")
        lines.append("- [Differentiator 2]")
        lines.append("- [Differentiator 3]")

        return "\n".join(lines)

    def get_comparison(self, comparison_id: int) -> dict:
        """Get comparison"""
        return self.db.get_comparison(comparison_id)

    def list_comparisons(self) -> list:
        """List comparisons"""
        return self.db.list_comparisons()

    # ========== Statistics ==========

    def get_stats(self) -> dict:
        """Get overall statistics"""
        proposals = self.db.list_proposals()
        demos = self.db.list_demos()
        roi_calcs = self.db.list_roi_calculations()
        case_studies = self.db.list_case_studies()
        showcases = self.db.list_showcases()
        business_cases = self.db.list_business_cases()
        comparisons = self.db.list_comparisons()

        # Status breakdown for proposals
        proposal_status = {}
        for p in proposals:
            status = p.get("status", "unknown")
            proposal_status[status] = proposal_status.get(status, 0) + 1

        return {
            "totals": {
                "proposals": len(proposals),
                "demos": len(demos),
                "roi_calculations": len(roi_calcs),
                "case_studies": len(case_studies),
                "showcases": len(showcases),
                "business_cases": len(business_cases),
                "comparisons": len(comparisons),
            },
            "proposal_status": proposal_status,
            "recent_proposals": proposals[:5] if proposals else [],
        }
