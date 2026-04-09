"""
Customer Lifecycle Manager
Business logic for automating customer journey from lead to delivery
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from python.helpers.datetime_utils import isoformat_z, parse_iso_datetime, utc_now

from .lifecycle_db import CustomerLifecycleDatabase


class CustomerLifecycleManager:
    """Manages end-to-end customer lifecycle automation"""

    def __init__(self, db_path: str = "data/customer_lifecycle.db"):
        self.db = CustomerLifecycleDatabase(db_path)
        self.templates_dir = Path(__file__).parent / "templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    # Lead Capture & Qualification
    def capture_lead(
        self,
        name: str,
        company: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        industry: str | None = None,
        company_size: str | None = None,
        source: str | None = None,
        initial_notes: str | None = None,
    ) -> dict:
        """Capture new lead and initiate qualification"""
        # Create customer record
        customer_id = self.db.add_customer(
            name=name,
            company=company,
            email=email,
            phone=phone,
            industry=industry,
            company_size=company_size,
            source=source,
            metadata={"initial_notes": initial_notes} if initial_notes else None,
        )

        # Log initial interaction
        self._log_interaction(
            customer_id=customer_id,
            interaction_type="lead_capture",
            subject="New lead captured",
            notes=f"Lead from {source}" if source else "New lead",
            sentiment="neutral",
        )

        return {
            "customer_id": customer_id,
            "stage": "lead",
            "next_step": "qualification_interview",
            "message": f"Lead captured: {name} ({company or 'Individual'})",
        }

    def conduct_requirements_interview(
        self, customer_id: int, interview_questions: list[str] | None = None, responses: dict[str, str] | None = None
    ) -> dict:
        """Conduct structured requirements gathering interview"""
        customer = self.db.get_customer(customer_id)
        if not customer:
            return {"error": "Customer not found"}

        # Use default questions if not provided
        if not interview_questions:
            interview_questions = self._get_default_interview_questions()

        # Structure the interview data
        interview_data = {
            "date": isoformat_z(utc_now()),
            "customer": customer["name"],
            "company": customer.get("company"),
            "questions": interview_questions,
            "responses": responses or {},
        }

        # Extract structured requirements from responses
        structured_reqs = self._extract_requirements(responses) if responses else None
        pain_points = self._extract_pain_points(responses) if responses else None
        success_criteria = self._extract_success_criteria(responses) if responses else None

        # Save requirements
        req_id = self.db.add_requirements(
            customer_id=customer_id,
            raw_transcript=json.dumps(interview_data),
            structured_requirements=structured_reqs,
            pain_points=pain_points,
            success_criteria=success_criteria,
            interviewer="Agent Mahoo",
        )

        # Update customer stage
        self.db.update_customer_stage(customer_id, "prospect")

        # Log interaction
        self._log_interaction(
            customer_id=customer_id,
            interaction_type="requirements_interview",
            subject="Requirements gathering session",
            notes=f"Captured {len(responses) if responses else 0} responses",
            sentiment="positive",
        )

        return {
            "requirement_id": req_id,
            "customer_id": customer_id,
            "stage": "prospect",
            "next_step": "solution_design",
            "structured_requirements": structured_reqs,
            "pain_points": pain_points,
            "success_criteria": success_criteria,
        }

    def design_solution(
        self,
        customer_id: int,
        requirement_id: int | None = None,
        solution_name: str | None = None,
        architecture_preferences: dict | None = None,
    ) -> dict:
        """Design solution based on requirements"""
        customer = self.db.get_customer(customer_id)
        if not customer:
            return {"error": "Customer not found"}

        # Get requirements
        requirements = self.db.get_customer_requirements(customer_id)
        if not requirements and not requirement_id:
            return {"error": "No requirements found. Conduct interview first."}

        # Use most recent requirement if not specified
        if not requirement_id and requirements:
            requirement_id = requirements[0]["requirement_id"]

        # Generate solution design
        solution_design = self._generate_solution_architecture(
            customer=customer,
            requirements=next((r for r in requirements if r["requirement_id"] == requirement_id), None),
            preferences=architecture_preferences,
        )

        # Save solution
        solution_id = self.db.add_solution(
            customer_id=customer_id,
            requirement_id=requirement_id,
            solution_name=solution_name or f"Solution for {customer['name']}",
            architecture_type=solution_design.get("architecture_type"),
            tech_stack=solution_design.get("tech_stack"),
            components=solution_design.get("components"),
            created_by="Agent Mahoo",
        )

        return {
            "solution_id": solution_id,
            "customer_id": customer_id,
            "architecture": solution_design,
            "next_step": "create_proposal",
        }

    def generate_proposal(
        self,
        customer_id: int,
        solution_id: int | None = None,
        pricing_model: str = "fixed_price",
        discount_percentage: float = 0,
    ) -> dict:
        """Generate comprehensive customer proposal"""
        customer = self.db.get_customer(customer_id)
        if not customer:
            return {"error": "Customer not found"}

        # Get solution and requirements
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if solution_id:
            cursor.execute("SELECT * FROM solutions WHERE solution_id = ?", (solution_id,))
        else:
            cursor.execute(
                """
                SELECT * FROM solutions
                WHERE customer_id = ?
                ORDER BY created_at DESC LIMIT 1
            """,
                (customer_id,),
            )

        solution_row = cursor.fetchone()
        if not solution_row:
            conn.close()
            return {"error": "No solution found"}

        solution_cols = [desc[0] for desc in cursor.description]
        solution = dict(zip(solution_cols, solution_row))
        conn.close()

        # Generate proposal content
        proposal_content = self._build_proposal_content(
            customer=customer, solution=solution, pricing_model=pricing_model, discount=discount_percentage
        )

        # Calculate timeline and cost
        timeline_weeks = proposal_content.get("timeline_weeks", 12)
        total_cost = proposal_content.get("total_cost", 50000) * (1 - discount_percentage / 100)

        # Create proposal
        proposal_id = self.db.create_proposal(
            customer_id=customer_id,
            solution_id=solution["solution_id"],
            title=proposal_content.get("title"),
            scope_of_work=proposal_content.get("scope_of_work"),
            deliverables=proposal_content.get("deliverables"),
            timeline_weeks=timeline_weeks,
            total_cost=total_cost,
            pricing_model=pricing_model,
            valid_until=(datetime.now() + timedelta(days=30)).date().isoformat(),
        )

        # Log interaction
        self._log_interaction(
            customer_id=customer_id,
            interaction_type="proposal_sent",
            subject=f"Proposal generated: {proposal_content.get('title')}",
            notes=f"Value: ${total_cost:,.2f}, Timeline: {timeline_weeks} weeks",
            sentiment="positive",
        )

        return {
            "proposal_id": proposal_id,
            "customer_id": customer_id,
            "proposal_content": proposal_content,
            "total_cost": total_cost,
            "timeline_weeks": timeline_weeks,
            "next_step": "send_proposal",
        }

    def track_proposal(self, proposal_id: int, new_status: str | None = None) -> dict:
        """Track proposal status and follow-up"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT p.*, c.name, c.email, c.company
            FROM proposals p
            JOIN customers c ON p.customer_id = c.customer_id
            WHERE p.proposal_id = ?
        """,
            (proposal_id,),
        )

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": "Proposal not found"}

        cols = [desc[0] for desc in cursor.description]
        proposal = dict(zip(cols, row))
        conn.close()

        # Update status if provided
        if new_status:
            self.db.update_proposal_status(proposal_id, new_status)
            proposal["status"] = new_status

            # Update customer stage on acceptance
            if new_status == "accepted":
                self.db.update_customer_stage(proposal["customer_id"], "customer")

        # Calculate days since sent
        if proposal.get("sent_date"):
            sent_date = parse_iso_datetime(proposal["sent_date"])
            days_pending = (utc_now() - sent_date).days

            # Determine follow-up action
            if days_pending > 14 and proposal["status"] == "sent":
                follow_up_action = "Send follow-up reminder"
            elif days_pending > 30 and proposal["status"] == "sent":
                follow_up_action = "Schedule call to discuss concerns"
            else:
                follow_up_action = "No action needed yet"
        else:
            days_pending = 0
            follow_up_action = "Send proposal to customer"

        return {
            "proposal_id": proposal_id,
            "customer": proposal["name"],
            "company": proposal.get("company"),
            "status": proposal["status"],
            "total_cost": proposal.get("total_cost"),
            "days_pending": days_pending,
            "follow_up_action": follow_up_action,
        }

    def get_customer_health_score(self, customer_id: int) -> dict:
        """Calculate customer health score"""
        customer_360 = self.db.get_customer_360(customer_id)
        if not customer_360:
            return {"error": "Customer not found"}

        score = 100
        factors = []

        # Deduct for open tickets
        if customer_360.get("open_support_tickets", 0) > 3:
            score -= 20
            factors.append(f"High support load ({customer_360['open_support_tickets']} tickets)")

        # Reward for active projects
        if customer_360.get("active_projects", 0) > 0:
            score += 10
            factors.append(f"{customer_360['active_projects']} active project(s)")

        # Check project completion rate (only if there are projects)
        avg_completion = customer_360.get("avg_project_completion")
        if avg_completion is not None and avg_completion < 50:
            score -= 15
            factors.append("Projects behind schedule")

        # Determine health status
        if score >= 80:
            health = "healthy"
        elif score >= 60:
            health = "at_risk"
        else:
            health = "critical"

        return {
            "customer_id": customer_id,
            "customer_name": customer_360["name"],
            "health_score": max(0, min(100, score)),
            "health_status": health,
            "factors": factors,
            "recommendations": self._get_health_recommendations(health, factors),
        }

    # Helper methods
    def _log_interaction(self, customer_id: int, interaction_type: str, subject: str, notes: str, sentiment: str):
        """Log customer interaction"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO interactions
            (customer_id, interaction_type, subject, notes, sentiment, recorded_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (customer_id, interaction_type, subject, notes, sentiment, "Agent Mahoo"),
        )

        conn.commit()
        conn.close()

    def _get_default_interview_questions(self) -> list[str]:
        """Get standard requirements interview questions"""
        return [
            "What business problem are you trying to solve?",
            "Who are the primary users/stakeholders?",
            "What are your main pain points with current solutions?",
            "What does success look like for this project?",
            "What are your timeline expectations?",
            "What is your budget range?",
            "Are there any specific technical constraints or preferences?",
            "What integrations are required?",
            "What are your scalability requirements?",
            "What compliance/security requirements exist?",
        ]

    def _extract_requirements(self, responses: dict) -> str:
        """Extract structured requirements from interview responses"""
        if not responses:
            return None

        structured = []
        for question, answer in responses.items():
            if answer and len(str(answer).strip()) > 0:
                structured.append(f"**{question}**: {answer}")

        return "\n\n".join(structured)

    def _extract_pain_points(self, responses: dict) -> str:
        """Extract pain points from responses"""
        pain_keywords = ["pain", "problem", "issue", "challenge", "difficulty"]
        pain_points = []

        for question, answer in responses.items():
            if any(keyword in question.lower() for keyword in pain_keywords):
                pain_points.append(str(answer))

        return "; ".join(pain_points) if pain_points else None

    def _extract_success_criteria(self, responses: dict) -> str:
        """Extract success criteria from responses"""
        success_keywords = ["success", "goal", "objective", "outcome"]
        criteria = []

        for question, answer in responses.items():
            if any(keyword in question.lower() for keyword in success_keywords):
                criteria.append(str(answer))

        return "; ".join(criteria) if criteria else None

    def _generate_solution_architecture(
        self, customer: dict, requirements: dict, preferences: dict | None = None
    ) -> dict:
        """Generate solution architecture based on requirements"""
        # Default modern cloud-native architecture
        return {
            "architecture_type": "microservices",
            "tech_stack": [
                "React (Frontend)",
                "Node.js/Python (Backend)",
                "PostgreSQL (Database)",
                "Redis (Cache)",
                "Docker/Kubernetes (Infrastructure)",
                "Azure/AWS (Cloud Platform)",
            ],
            "components": [
                "API Gateway",
                "Authentication Service",
                "Business Logic Services",
                "Data Layer",
                "Frontend Application",
                "Background Job Processor",
                "Monitoring & Logging",
            ],
            "estimated_complexity": "medium-high",
            "deployment_model": "cloud_native",
        }

    def _build_proposal_content(self, customer: dict, solution: dict, pricing_model: str, discount: float) -> dict:
        """Build comprehensive proposal content"""
        return {
            "title": f"Solution Proposal for {customer.get('company') or customer['name']}",
            "scope_of_work": "Complete end-to-end solution development including architecture design, implementation, testing, deployment, and knowledge transfer.",
            "deliverables": [
                "Architecture design documentation",
                "Fully functional application",
                "Deployment automation scripts",
                "User documentation",
                "Technical documentation",
                "Training sessions",
                "3 months post-launch support",
            ],
            "timeline_weeks": 12,
            "total_cost": 50000,  # Base estimate
            "milestones": [
                "Week 2: Architecture approval",
                "Week 6: MVP demo",
                "Week 10: UAT completion",
                "Week 12: Production deployment",
            ],
        }

    def _get_health_recommendations(self, health: str, factors: list[str]) -> list[str]:
        """Get recommendations based on health status"""
        if health == "healthy":
            return ["Continue regular check-ins", "Explore upsell opportunities"]
        elif health == "at_risk":
            return ["Schedule executive alignment call", "Review project status", "Address support tickets"]
        else:
            return ["URGENT: Executive escalation needed", "Develop recovery plan", "Daily status updates"]

    # Email Automation Methods
    async def send_welcome_email(self, customer_id: int, email_tool) -> dict:
        """Send automated welcome email to new lead"""
        customer = self.db.get_customer(customer_id)
        if not customer or not customer.get("email"):
            return {"error": "Customer not found or no email address"}

        body = f"""Dear {customer["name"]},

Thank you for your interest in our AI solutions! We're excited to help transform your business with cutting-edge artificial intelligence.

We'll be reaching out shortly to schedule a requirements discussion and learn more about your specific needs.

In the meantime, feel free to reply to this email with any questions or additional information you'd like to share.

Best regards,
AI Solutions Team"""

        result = await email_tool.execute(
            action="send",
            to=customer["email"],
            subject="Welcome to AI Solutions!",
            body=body,
            from_name="AI Solutions Onboarding",
        )

        # Log interaction
        self._log_interaction(
            customer_id=customer_id,
            interaction_type="email",
            subject="Welcome email sent",
            notes=f"Sent to {customer['email']}",
            sentiment="positive",
        )

        return result

    async def send_proposal_email(self, proposal_id: int, email_tool, attachment_path: str | None = None) -> dict:
        """Send proposal document to customer via email"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT p.*, c.name, c.email, c.company
            FROM proposals p
            JOIN customers c ON p.customer_id = c.customer_id
            WHERE p.proposal_id = ?
        """,
            (proposal_id,),
        )

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": "Proposal not found"}

        cols = [desc[0] for desc in cursor.description]
        proposal = dict(zip(cols, row))
        conn.close()

        if not proposal.get("email"):
            return {"error": "Customer email not found"}

        # Build email body
        body = f"""Dear {proposal["name"]},

Thank you for the opportunity to present our solution for {proposal.get("company", "your organization")}.

{f"Please find attached your customized proposal: {proposal.get('title', 'AI Solution Proposal')}" if attachment_path else "We're preparing your detailed proposal and will send it shortly."}

**Key Highlights:**
- Timeline: {proposal.get("timeline_weeks", "TBD")} weeks
- Investment: ${proposal.get("total_cost", 0):,.2f}
- Pricing Model: {proposal.get("pricing_model", "Fixed Price").replace("_", " ").title()}

This proposal is valid until {proposal.get("valid_until", "TBD")}.

Please review and let us know if you have any questions or would like to schedule a call to discuss further.

Best regards,
AI Solutions Team"""

        # Send email
        result = await email_tool.execute(
            action="send",
            to=proposal["email"],
            subject=f"Your AI Solution Proposal - {proposal.get('company', proposal['name'])}",
            body=body,
            attachments=[attachment_path] if attachment_path else None,
            from_name="AI Solutions Team",
        )

        # Update proposal status
        self.db.update_proposal_status(proposal_id, "sent")

        # Log interaction
        self._log_interaction(
            customer_id=proposal["customer_id"],
            interaction_type="proposal_sent",
            subject=f"Proposal emailed: {proposal.get('title')}",
            notes=f"Sent to {proposal['email']}" + (f" with attachment: {attachment_path}" if attachment_path else ""),
            sentiment="positive",
        )

        return result

    async def send_proposal_followup(self, proposal_id: int, email_tool, days_since_sent: int | None = None) -> dict:
        """Send automated follow-up for pending proposals"""
        conn = self.db.get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT p.*, c.name, c.email, c.company
            FROM proposals p
            JOIN customers c ON p.customer_id = c.customer_id
            WHERE p.proposal_id = ?
        """,
            (proposal_id,),
        )

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {"error": "Proposal not found"}

        cols = [desc[0] for desc in cursor.description]
        proposal = dict(zip(cols, row))
        conn.close()

        if proposal["status"] not in ["sent", "reviewed"]:
            return {"error": f"Proposal status is {proposal['status']}, follow-up not applicable"}

        if not proposal.get("email"):
            return {"error": "Customer email not found"}

        # Build follow-up email
        body = f"""Dear {proposal["name"]},

I wanted to follow up on the proposal we sent for {proposal.get("title", "your AI solution")}.

Have you had a chance to review it? I'd be happy to schedule a call to answer any questions or discuss any adjustments you might need.

**Quick Reminder:**
- Timeline: {proposal.get("timeline_weeks", "TBD")} weeks
- Investment: ${proposal.get("total_cost", 0):,.2f}
- Valid Until: {proposal.get("valid_until", "TBD")}

Looking forward to hearing from you!

Best regards,
AI Solutions Team"""

        result = await email_tool.execute(
            action="send",
            to=proposal["email"],
            subject=f"Following up: {proposal.get('title', 'Your Proposal')}",
            body=body,
            from_name="AI Solutions Team",
        )

        # Log interaction
        self._log_interaction(
            customer_id=proposal["customer_id"],
            interaction_type="follow_up",
            subject="Proposal follow-up sent",
            notes=f"Follow-up sent to {proposal['email']}",
            sentiment="neutral",
        )

        return result

    async def monitor_customer_responses(self, email_tool, customer_id: int | None = None) -> dict:
        """Monitor inbox for customer responses and categorize them"""
        # Read unread emails
        result = await email_tool.execute(action="read", filter={"unread": True})

        if not result or "message" not in result:
            return {"error": "Failed to read emails"}

        # Get all customers for matching
        conn = self.db.get_connection()
        cursor = conn.cursor()

        if customer_id:
            cursor.execute("SELECT customer_id, name, email FROM customers WHERE customer_id = ?", (customer_id,))
        else:
            cursor.execute("SELECT customer_id, name, email FROM customers WHERE email IS NOT NULL")

        customers = {row[2].lower(): {"id": row[0], "name": row[1]} for row in cursor.fetchall()}
        conn.close()

        # Parse email response (simplified - would need full email parsing)
        matched_responses = []
        # This would parse the result.message to extract email details
        # For now, return structure for integration

        return {
            "checked": len(customers),
            "matched_responses": matched_responses,
            "next_step": "Process and log interactions",
        }
