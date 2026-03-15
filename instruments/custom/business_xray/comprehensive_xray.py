from python.helpers.datetime_utils import isoformat_z, utc_now

#!/usr/bin/env python3
"""
Business X-Ray Comprehensive Analyzer
Performs complete business and life analysis with visual outputs
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class BusinessXRay:
    """
    Comprehensive business analysis system
    """

    def __init__(self, business_name: str, output_dir: str):
        self.business_name = business_name
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report = {"business_name": business_name, "analysis_date": isoformat_z(utc_now()), "modules": {}}

    def analyze_business_health(self) -> dict[str, Any]:
        """Analyze overall business health metrics"""
        print("🏥 Analyzing Business Health...")

        health_metrics = {
            "revenue": {
                "current_monthly": self._get_user_input("Monthly revenue ($)", float, 0),
                "growth_rate": self._get_user_input("Monthly growth rate (%)", float, 0),
                "target_revenue": self._get_user_input("Target monthly revenue ($)", float, 0),
            },
            "profitability": {
                "profit_margin": self._get_user_input("Profit margin (%)", float, 0),
                "operating_expenses": self._get_user_input("Monthly operating expenses ($)", float, 0),
                "burn_rate": 0,  # Calculated
            },
            "customers": {
                "total_customers": self._get_user_input("Total active customers", int, 0),
                "new_this_month": self._get_user_input("New customers this month", int, 0),
                "churn_rate": self._get_user_input("Monthly churn rate (%)", float, 0),
                "cac": self._get_user_input("Customer acquisition cost ($)", float, 0),
                "ltv": self._get_user_input("Customer lifetime value ($)", float, 0),
            },
            "team": {
                "team_size": self._get_user_input("Team size", int, 1),
                "productivity_score": self._get_user_input("Team productivity (1-10)", int, 7),
            },
        }

        # Calculate derived metrics
        health_metrics["profitability"]["burn_rate"] = (
            health_metrics["revenue"]["current_monthly"] - health_metrics["profitability"]["operating_expenses"]
        )

        # Generate health score
        health_score = self._calculate_health_score(health_metrics)
        health_metrics["overall_health_score"] = health_score

        # Generate visualization
        self._generate_health_diagram(health_metrics)

        return health_metrics

    def audit_time_usage(self) -> dict[str, Any]:
        """Audit time allocation and productivity"""
        print("\n⏰ Auditing Time Usage...")

        time_audit = {
            "weekly_hours": {
                "deep_work": self._get_user_input("Deep work hours/week", float, 20),
                "meetings": self._get_user_input("Meeting hours/week", float, 10),
                "email_admin": self._get_user_input("Email/admin hours/week", float, 10),
                "shallow_work": self._get_user_input("Other work hours/week", float, 10),
                "personal": self._get_user_input("Personal time hours/week", float, 20),
            },
            "productivity": {
                "peak_hours": self._get_user_input("Peak productivity time (e.g., 8-11am)", str, "9-12pm"),
                "context_switches_per_day": self._get_user_input("Context switches per day", int, 15),
                "focused_blocks_per_week": self._get_user_input("4+ hour focus blocks/week", int, 3),
            },
        }

        # Calculate efficiency score
        total_work = sum([v for k, v in time_audit["weekly_hours"].items() if k != "personal"])
        deep_work_ratio = time_audit["weekly_hours"]["deep_work"] / total_work if total_work > 0 else 0
        time_audit["efficiency_score"] = round(deep_work_ratio * 100, 1)

        # Generate visualization
        self._generate_time_diagram(time_audit)

        return time_audit

    def identify_automation_opportunities(self) -> list[dict[str, Any]]:
        """Identify processes that can be automated"""
        print("\n🤖 Identifying Automation Opportunities...")

        common_tasks = [
            {"name": "Invoice generation & follow-up", "hours_week": 8, "automation_potential": 95},
            {"name": "Social media content posting", "hours_week": 5, "automation_potential": 80},
            {"name": "Email responses (common questions)", "hours_week": 6, "automation_potential": 70},
            {"name": "Data entry & synchronization", "hours_week": 4, "automation_potential": 90},
            {"name": "Report generation", "hours_week": 4, "automation_potential": 85},
            {"name": "Appointment scheduling", "hours_week": 3, "automation_potential": 95},
            {"name": "Customer onboarding", "hours_week": 6, "automation_potential": 75},
            {"name": "Meeting notes & follow-ups", "hours_week": 3, "automation_potential": 80},
        ]

        print("\nReview common automation opportunities. Enter hours/week (0 to skip):")

        opportunities = []
        for task in common_tasks:
            hours = self._get_user_input(
                f"  {task['name']} (default {task['hours_week']}h/week)", float, 0, skip_zero=True
            )
            if hours > 0:
                hourly_rate = 50  # Average cost
                weekly_cost = hours * hourly_rate
                monthly_savings = weekly_cost * 4 * (task["automation_potential"] / 100)

                opportunities.append(
                    {
                        "task": task["name"],
                        "current_hours_week": hours,
                        "automation_potential": task["automation_potential"],
                        "monthly_savings": round(monthly_savings, 2),
                        "annual_savings": round(monthly_savings * 12, 2),
                        "implementation_effort": self._estimate_effort(task["name"]),
                        "priority_score": self._calculate_priority(monthly_savings, task["automation_potential"]),
                    }
                )

        # Sort by priority score
        opportunities.sort(key=lambda x: x["priority_score"], reverse=True)

        # Generate visualization
        self._generate_automation_diagram(opportunities)

        return opportunities

    def scan_revenue_opportunities(self) -> list[dict[str, Any]]:
        """Identify revenue growth opportunities"""
        print("\n💰 Scanning Revenue Opportunities...")

        current_revenue = self._get_user_input("Current annual revenue ($)", float, 0)

        opportunity_types = [
            "Price increase (underpriced services/products)",
            "Upsell to existing customers",
            "Cross-sell complementary services",
            "New market segment entry",
            "Subscription/recurring revenue model",
            "Digital product creation",
            "Partnership/referral program",
            "Premium tier offering",
            "Volume/bulk discounts",
            "Consulting/training services",
        ]

        opportunities = []
        print("\nFor each opportunity, estimate potential annual revenue increase:")

        for opp_type in opportunity_types:
            potential = self._get_user_input(f"  {opp_type} (+$)", float, 0, skip_zero=True)
            if potential > 0:
                opportunities.append(
                    {
                        "opportunity": opp_type,
                        "revenue_potential": potential,
                        "percentage_increase": round(
                            (potential / current_revenue * 100) if current_revenue > 0 else 0, 1
                        ),
                        "difficulty": self._get_user_input("    Implementation difficulty (1-10)", int, 5),
                        "timeframe": self._get_user_input("    Time to implement (months)", int, 3),
                    }
                )

        # Sort by revenue potential
        opportunities.sort(key=lambda x: x["revenue_potential"], reverse=True)

        # Generate visualization
        self._generate_revenue_diagram(current_revenue, opportunities)

        return opportunities

    def analyze_life_balance(self) -> dict[str, Any]:
        """Analyze work-life balance"""
        print("\n⚖️  Analyzing Life-Business Balance...")

        balance_metrics = {
            "work": {
                "hours_per_week": self._get_user_input("Work hours per week", float, 40),
                "ideal_hours": self._get_user_input("Ideal work hours per week", float, 40),
                "stress_level": self._get_user_input("Work stress level (1-10)", int, 5),
            },
            "health": {
                "exercise_hours_week": self._get_user_input("Exercise hours per week", float, 3),
                "sleep_hours_night": self._get_user_input("Average sleep hours per night", float, 7),
                "health_satisfaction": self._get_user_input("Health satisfaction (1-10)", int, 7),
            },
            "relationships": {
                "family_time_hours_week": self._get_user_input("Family time hours per week", float, 20),
                "social_time_hours_week": self._get_user_input("Social time hours per week", float, 5),
                "relationship_satisfaction": self._get_user_input("Relationship satisfaction (1-10)", int, 8),
            },
            "personal": {
                "hobby_time_hours_week": self._get_user_input("Hobby/recreation hours per week", float, 5),
                "learning_time_hours_week": self._get_user_input("Learning/development hours per week", float, 3),
                "life_satisfaction": self._get_user_input("Overall life satisfaction (1-10)", int, 7),
            },
        }

        # Calculate balance score
        balance_score = self._calculate_balance_score(balance_metrics)
        balance_metrics["balance_score"] = balance_score

        # Identify imbalances
        recommendations = self._generate_balance_recommendations(balance_metrics)
        balance_metrics["recommendations"] = recommendations

        # Generate visualization
        self._generate_balance_diagram(balance_metrics)

        return balance_metrics

    def generate_executive_summary(self) -> str:
        """Generate executive summary with key insights"""
        print("\n📊 Generating Executive Summary...")

        summary = f"""
# Business X-Ray Report: {self.business_name}
## Executive Summary
**Analysis Date:** {datetime.now().strftime("%B %d, %Y")}

### Key Metrics
"""

        if "business_health" in self.report["modules"]:
            health = self.report["modules"]["business_health"]
            summary += f"""
#### Business Health Score: {health.get("overall_health_score", "N/A")}/100

- Monthly Revenue: ${health["revenue"]["current_monthly"]:,.2f}
- Growth Rate: {health["revenue"]["growth_rate"]}%
- Profit Margin: {health["profitability"]["profit_margin"]}%
- Customer LTV/CAC Ratio: {health["customers"]["ltv"] / health["customers"]["cac"]:.1f}x
"""

        if "time_audit" in self.report["modules"]:
            time = self.report["modules"]["time_audit"]
            summary += f"""
#### Time Efficiency Score: {time.get("efficiency_score", "N/A")}%

- Deep Work: {time["weekly_hours"]["deep_work"]} hours/week
- Focus Blocks: {time["productivity"]["focused_blocks_per_week"]} per week
- Context Switches: {time["productivity"]["context_switches_per_day"]} per day
"""

        if "automation_opportunities" in self.report["modules"]:
            auto = self.report["modules"]["automation_opportunities"]
            if auto:
                total_savings = sum(opp["annual_savings"] for opp in auto)
                summary += f"""
#### Top Automation Opportunities

**Potential Annual Savings: ${total_savings:,.2f}**

Top 3 Priorities:
"""
                for i, opp in enumerate(auto[:3], 1):
                    summary += f"{i}. {opp['task']}: ${opp['annual_savings']:,.2f}/year\n"

        if "revenue_opportunities" in self.report["modules"]:
            rev = self.report["modules"]["revenue_opportunities"]
            if rev:
                total_potential = sum(opp["revenue_potential"] for opp in rev)
                summary += f"""
#### Revenue Growth Potential

**Total Identified Opportunities: ${total_potential:,.2f}/year**

Top 3 Opportunities:
"""
                for i, opp in enumerate(rev[:3], 1):
                    summary += f"{i}. {opp['opportunity']}: +${opp['revenue_potential']:,.2f}/year\n"

        if "life_balance" in self.report["modules"]:
            balance = self.report["modules"]["life_balance"]
            summary += f"""
#### Life-Business Balance Score: {balance.get("balance_score", "N/A")}/100

- Work Hours: {balance["work"]["hours_per_week"]}/week (ideal: {balance["work"]["ideal_hours"]})
- Life Satisfaction: {balance["personal"]["life_satisfaction"]}/10
- Health Satisfaction: {balance["health"]["health_satisfaction"]}/10
"""

        return summary

    def run_comprehensive_analysis(self):
        """Run all analysis modules"""
        print(f"\n{'=' * 60}")
        print(f"BUSINESS X-RAY ANALYSIS: {self.business_name}")
        print(f"{'=' * 60}\n")

        # Run all modules
        self.report["modules"]["business_health"] = self.analyze_business_health()
        self.report["modules"]["time_audit"] = self.audit_time_usage()
        self.report["modules"]["automation_opportunities"] = self.identify_automation_opportunities()
        self.report["modules"]["revenue_opportunities"] = self.scan_revenue_opportunities()
        self.report["modules"]["life_balance"] = self.analyze_life_balance()

        # Generate summary
        summary = self.generate_executive_summary()
        self.report["executive_summary"] = summary

        # Save report
        self._save_report()

        # Generate diagrams
        self._generate_comprehensive_diagrams()

        print(f"\n{'=' * 60}")
        print("ANALYSIS COMPLETE!")
        print(f"{'=' * 60}")
        print(f"\nReports saved to: {self.output_dir}")
        print(f"- JSON report: business_xray_{self.timestamp}.json")
        print("- Summary: executive_summary.md")
        print("- Diagrams: *.mmd files")
        print("\nNext steps:")
        print("1. Review executive summary")
        print("2. Prioritize top 3 action items")
        print("3. Create implementation timeline")
        print("4. Set up automated monitoring")

    # Helper methods

    def _get_user_input(self, prompt: str, dtype: type, default: Any, skip_zero: bool = False) -> Any:
        """Get user input with type validation"""
        while True:
            try:
                value = input(f"{prompt} [{default}]: ").strip()
                if not value:
                    return default
                result = dtype(value)
                if skip_zero and result == 0:
                    return 0
                return result
            except ValueError:
                print(f"Invalid input. Please enter a {dtype.__name__}.")

    def _calculate_health_score(self, metrics: dict) -> int:
        """Calculate overall business health score"""
        score = 0

        # Revenue growth (30 points)
        if metrics["revenue"]["growth_rate"] > 10:
            score += 30
        elif metrics["revenue"]["growth_rate"] > 5:
            score += 20
        elif metrics["revenue"]["growth_rate"] > 0:
            score += 10

        # Profitability (25 points)
        if metrics["profitability"]["profit_margin"] > 30:
            score += 25
        elif metrics["profitability"]["profit_margin"] > 20:
            score += 20
        elif metrics["profitability"]["profit_margin"] > 10:
            score += 15
        elif metrics["profitability"]["profit_margin"] > 0:
            score += 10

        # LTV/CAC ratio (25 points)
        if metrics["customers"]["cac"] > 0:
            ratio = metrics["customers"]["ltv"] / metrics["customers"]["cac"]
            if ratio > 3:
                score += 25
            elif ratio > 2:
                score += 20
            elif ratio > 1:
                score += 10

        # Churn rate (20 points)
        if metrics["customers"]["churn_rate"] < 5:
            score += 20
        elif metrics["customers"]["churn_rate"] < 10:
            score += 15
        elif metrics["customers"]["churn_rate"] < 15:
            score += 10

        return min(score, 100)

    def _calculate_balance_score(self, metrics: dict) -> int:
        """Calculate work-life balance score"""
        score = 0

        # Work hours balance (25 points)
        work_diff = abs(metrics["work"]["hours_per_week"] - metrics["work"]["ideal_hours"])
        if work_diff < 5:
            score += 25
        elif work_diff < 10:
            score += 15
        elif work_diff < 15:
            score += 5

        # Stress level (25 points)
        stress = metrics["work"]["stress_level"]
        if stress <= 3:
            score += 25
        elif stress <= 5:
            score += 15
        elif stress <= 7:
            score += 5

        # Health metrics (25 points)
        if metrics["health"]["exercise_hours_week"] >= 3:
            score += 10
        if metrics["health"]["sleep_hours_night"] >= 7:
            score += 10
        if metrics["health"]["health_satisfaction"] >= 7:
            score += 5

        # Life satisfaction (25 points)
        if metrics["personal"]["life_satisfaction"] >= 8:
            score += 25
        elif metrics["personal"]["life_satisfaction"] >= 6:
            score += 15
        elif metrics["personal"]["life_satisfaction"] >= 4:
            score += 5

        return min(score, 100)

    def _estimate_effort(self, task_name: str) -> str:
        """Estimate implementation effort"""
        low_effort = ["invoice", "scheduling", "posting"]
        medium_effort = ["email", "report", "data entry"]

        task_lower = task_name.lower()
        if any(word in task_lower for word in low_effort):
            return "Low (1-2 days)"
        elif any(word in task_lower for word in medium_effort):
            return "Medium (3-5 days)"
        else:
            return "High (1-2 weeks)"

    def _calculate_priority(self, savings: float, automation_potential: float) -> float:
        """Calculate priority score for automation"""
        return (savings / 1000) * (automation_potential / 100)

    def _generate_balance_recommendations(self, metrics: dict) -> list[str]:
        """Generate balance improvement recommendations"""
        recs = []

        if metrics["work"]["hours_per_week"] > metrics["work"]["ideal_hours"] + 5:
            recs.append("Reduce work hours through delegation or automation")

        if metrics["health"]["exercise_hours_week"] < 3:
            recs.append("Increase exercise to at least 3 hours per week")

        if metrics["health"]["sleep_hours_night"] < 7:
            recs.append("Prioritize 7-8 hours of sleep per night")

        if metrics["work"]["stress_level"] > 7:
            recs.append("Implement stress reduction techniques (meditation, breaks)")

        if metrics["relationships"]["family_time_hours_week"] < 15:
            recs.append("Schedule dedicated family time blocks")

        if metrics["personal"]["hobby_time_hours_week"] < 3:
            recs.append("Make time for hobbies and recreation")

        return recs

    def _generate_health_diagram(self, metrics: dict):
        """Generate business health diagram"""
        diagram = f"""```mermaid
graph TB
    subgraph "Revenue Health"
        R1[Monthly Revenue: ${metrics["revenue"]["current_monthly"]:,.0f}]
        R2[Growth Rate: {metrics["revenue"]["growth_rate"]}%]
        R3[Target: ${metrics["revenue"]["target_revenue"]:,.0f}]
    end
    subgraph "Profitability"
        P1[Profit Margin: {metrics["profitability"]["profit_margin"]}%]
        P2[Burn Rate: ${metrics["profitability"]["burn_rate"]:,.0f}/mo]
    end
    subgraph "Customers"
        C1[Total: {metrics["customers"]["total_customers"]}]
        C2[LTV/CAC: {metrics["customers"]["ltv"] / metrics["customers"]["cac"]:.1f}x]
        C3[Churn: {metrics["customers"]["churn_rate"]}%]
    end

    R1 --> Score[Health Score: {metrics["overall_health_score"]}/100]
    P1 --> Score
    C2 --> Score
```"""

        output_file = self.output_dir / "business_health.mmd"
        with open(output_file, "w") as f:
            f.write(diagram)

    def _generate_time_diagram(self, audit: dict):
        """Generate time usage diagram"""
        hours = audit["weekly_hours"]
        total = sum(hours.values())

        diagram = f"""```mermaid
pie title Weekly Time Distribution ({total:.0f} hours)
    "Deep Work ({hours["deep_work"]:.0f}h)" : {hours["deep_work"]}
    "Meetings ({hours["meetings"]:.0f}h)" : {hours["meetings"]}
    "Email/Admin ({hours["email_admin"]:.0f}h)" : {hours["email_admin"]}
    "Shallow Work ({hours["shallow_work"]:.0f}h)" : {hours["shallow_work"]}
    "Personal ({hours["personal"]:.0f}h)" : {hours["personal"]}
```

**Efficiency Score: {audit["efficiency_score"]}%**
- Peak Productivity: {audit["productivity"]["peak_hours"]}
- Focus Blocks: {audit["productivity"]["focused_blocks_per_week"]}/week
- Context Switches: {audit["productivity"]["context_switches_per_day"]}/day"""

        output_file = self.output_dir / "time_audit.mmd"
        with open(output_file, "w") as f:
            f.write(diagram)

    def _generate_automation_diagram(self, opportunities: list[dict]):
        """Generate automation opportunities diagram"""
        if not opportunities:
            return

        diagram = "# Top Automation Opportunities\n\n"
        diagram += "| Priority | Task | Annual Savings | Effort |\n"
        diagram += "|----------|------|-----------------|--------|\n"

        for i, opp in enumerate(opportunities[:10], 1):
            diagram += f"| {i} | {opp['task']} | ${opp['annual_savings']:,.0f} | {opp['implementation_effort']} |\n"

        total_savings = sum(opp["annual_savings"] for opp in opportunities)
        diagram += f"\n**Total Potential Savings: ${total_savings:,.2f}/year**"

        output_file = self.output_dir / "automation_opportunities.md"
        with open(output_file, "w") as f:
            f.write(diagram)

    def _generate_revenue_diagram(self, current: float, opportunities: list[dict]):
        """Generate revenue opportunities diagram"""
        if not opportunities:
            return

        diagram = f"""```mermaid
graph LR
    Current[Current Revenue<br/>${current:,.0f}/year]
"""

        for i, opp in enumerate(opportunities[:5], 1):
            diagram += f"    Current --> O{i}[{opp['opportunity'][:30]}<br/>+${opp['revenue_potential']:,.0f}]\n"

        total_potential = sum(opp["revenue_potential"] for opp in opportunities)
        target = current + total_potential

        for i in range(1, min(len(opportunities), 5) + 1):
            diagram += f"    O{i} --> Target\n"

        diagram += f"    Target[Target Revenue<br/>${target:,.0f}/year]\n```"

        output_file = self.output_dir / "revenue_opportunities.mmd"
        with open(output_file, "w") as f:
            f.write(diagram)

    def _generate_balance_diagram(self, metrics: dict):
        """Generate work-life balance diagram"""
        diagram = f"""# Work-Life Balance Analysis

**Balance Score: {metrics["balance_score"]}/100**

## Current State

```mermaid
graph TB
    subgraph "Work ({metrics["work"]["hours_per_week"]:.0f}h/week)"
        W1[Stress: {metrics["work"]["stress_level"]}/10]
        W2[Ideal: {metrics["work"]["ideal_hours"]:.0f}h]
    end
    subgraph "Health"
        H1[Exercise: {metrics["health"]["exercise_hours_week"]:.0f}h/week]
        H2[Sleep: {metrics["health"]["sleep_hours_night"]:.0f}h/night]
        H3[Satisfaction: {metrics["health"]["health_satisfaction"]}/10]
    end
    subgraph "Relationships"
        R1[Family: {metrics["relationships"]["family_time_hours_week"]:.0f}h/week]
        R2[Social: {metrics["relationships"]["social_time_hours_week"]:.0f}h/week]
        R3[Satisfaction: {metrics["relationships"]["relationship_satisfaction"]}/10]
    end
    subgraph "Personal"
        P1[Hobbies: {metrics["personal"]["hobby_time_hours_week"]:.0f}h/week]
        P2[Learning: {metrics["personal"]["learning_time_hours_week"]:.0f}h/week]
        P3[Life Satisfaction: {metrics["personal"]["life_satisfaction"]}/10]
    end
```

## Recommendations

"""
        for i, rec in enumerate(metrics.get("recommendations", []), 1):
            diagram += f"{i}. {rec}\n"

        output_file = self.output_dir / "life_balance.md"
        with open(output_file, "w") as f:
            f.write(diagram)

    def _generate_comprehensive_diagrams(self):
        """Generate overview dashboard diagram"""
        diagram = f"""# {self.business_name} - Business X-Ray Dashboard

## Overview

```mermaid
graph TB
    Business[{self.business_name}]

    Business --> Health[Business Health]
    Business --> Time[Time Efficiency]
    Business --> Auto[Automation]
    Business --> Revenue[Revenue Growth]
    Business --> Balance[Life Balance]

    Health --> HS[Score: {self.report["modules"].get("business_health", {}).get("overall_health_score", "N/A")}/100]
    Time --> TS[Score: {self.report["modules"].get("time_audit", {}).get("efficiency_score", "N/A")}%]
    Balance --> BS[Score: {self.report["modules"].get("life_balance", {}).get("balance_score", "N/A")}/100]

    style Business fill:#e1f5ff
    style Health fill:#ffe1e1
    style Time fill:#e1ffe1
    style Auto fill:#fff4e1
    style Revenue fill:#f0e1ff
    style Balance fill:#e1f5ff
```

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""

        output_file = self.output_dir / "dashboard.md"
        with open(output_file, "w") as f:
            f.write(diagram)

    def _save_report(self):
        """Save JSON report"""
        output_file = self.output_dir / f"business_xray_{self.timestamp}.json"
        with open(output_file, "w") as f:
            json.dump(self.report, f, indent=2)

        # Save executive summary
        summary_file = self.output_dir / "executive_summary.md"
        with open(summary_file, "w") as f:
            f.write(self.report["executive_summary"])


def main():
    parser = argparse.ArgumentParser(
        description="Business X-Ray Comprehensive Analyzer", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--business-name", required=True, help="Name of your business")
    parser.add_argument(
        "--output-dir",
        default="/tmp/business_xray",  # nosec B108 - CLI default, overridable
        help="Output directory for reports",
    )
    parser.add_argument("--quick", action="store_true", help="Run quick analysis with defaults")

    args = parser.parse_args()

    xray = BusinessXRay(args.business_name, args.output_dir)
    xray.run_comprehensive_analysis()


if __name__ == "__main__":
    main()
