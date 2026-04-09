#!/usr/bin/env python3
"""
Setup AI Solutioning Training for Operators

This script creates:
1. Skills for AI Solution Architects
2. Learning paths for operators
3. Training modules with practical exercises

Run: python scripts/setup_ai_solutioning_training.py
"""

import os
import re
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from python.helpers import files

# Mapping from module_id to content file
MODULE_CONTENT_FILES = {
    "discovery_fundamentals": "01-discovery-fundamentals.md",
    "solution_design_mastery": "02-solution-design.md",
    "sales_and_roi": "03-sales-and-roi.md",
    "implementation_excellence": "04-implementation.md",
    "deployment_operations": "05-deployment.md",
    "optimization_support": "06-optimization-support.md",
    # Hospitality Operations Manager path
    "guest_communication_mastery": "07-guest-communication.md",
    "cleaning_and_operations": "08-cleaning-ops.md",
    "revenue_and_reviews": "09-revenue-reviews.md",
    "hospitality_capstone": "10-hospitality-capstone.md",
    # Knowledge & Content Strategist path
    "knowledge_system_foundations": "11-knowledge-foundations.md",
    "digest_and_distribution": "12-digest-distribution.md",
    "advanced_knowledge_ops": "13-advanced-knowledge.md",
    "knowledge_capstone": "14-knowledge-capstone.md",
    # Workflow & Automation Engineer path
    "workflow_engine_deep_dive": "15-workflow-engine-deep.md",
    "scheduling_and_automation": "16-scheduling-automation.md",
    "integration_and_scaling": "17-integration-scaling.md",
    "automation_capstone": "18-automation-capstone.md",
    # Business Development Operator path
    "pipeline_management": "19-pipeline-management.md",
    "proposal_and_closing": "20-proposal-closing.md",
    "account_management": "21-account-management.md",
    # Platform Administrator path
    "platform_configuration": "22-platform-config.md",
    "security_and_monitoring": "23-security-monitoring.md",
    "admin_capstone": "24-admin-capstone.md",
}


def load_lesson_content(module_id: str, lesson_title: str) -> str:
    """Load lesson content from markdown file by extracting the section for this lesson.

    Content files use '## Lesson: {title}' as section headers.
    Returns everything between the matching header and the next '## Lesson:' or EOF.
    Falls back to the original one-liner if the file or section is not found.
    """
    filename = MODULE_CONTENT_FILES.get(module_id)
    if not filename:
        return lesson_title  # fallback

    content_dir = os.path.join(os.path.dirname(__file__), "..", "training", "content")
    content_path = os.path.join(content_dir, filename)

    if not os.path.exists(content_path):
        print(f"  ⚠ Content file not found: {content_path}")
        return lesson_title  # fallback

    with open(content_path, encoding="utf-8") as f:
        full_text = f.read()

    # Extract section between ## Lesson: {title} and next ## Lesson: or end of file
    pattern = re.compile(
        r"^## Lesson:\s*" + re.escape(lesson_title) + r"\s*\n(.*?)(?=^## Lesson:|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(full_text)
    if match:
        return match.group(1).strip()

    print(f"  ⚠ Lesson section not found: '{lesson_title}' in {filename}")
    return lesson_title  # fallback


def setup_training():
    """Setup complete AI Solutioning training program"""

    # Import workflow manager
    from instruments.custom.workflow_engine.workflow_manager import WorkflowEngineManager

    db_path = files.get_abs_path("./instruments/custom/workflow_engine/data/workflow.db")
    manager = WorkflowEngineManager(db_path)

    print("=" * 60)
    print("Setting up AI Solutioning Training Program")
    print("=" * 60)

    # ========================================
    # CATEGORY 1: Discovery & Assessment Skills
    # ========================================
    discovery_skills = [
        {
            "skill_id": "customer_intake",
            "name": "Customer Intake & Qualification",
            "category": "discovery",
            "description": "Effectively capture customer information, qualify leads, and set up customer records",
            "prerequisites": [],
            "learning_resources": ["Customer Lifecycle Tool Documentation", "CRM Best Practices Guide"],
        },
        {
            "skill_id": "business_analysis",
            "name": "Business Analysis & X-Ray",
            "category": "discovery",
            "description": "Use Business X-Ray tool to analyze customer's business processes, identify pain points, and score AI opportunities",
            "prerequisites": ["customer_intake"],
            "learning_resources": ["Business X-Ray Tool Guide", "Process Mapping Techniques"],
        },
        {
            "skill_id": "requirements_gathering",
            "name": "Requirements Gathering",
            "category": "discovery",
            "description": "Capture detailed technical and business requirements, define success criteria",
            "prerequisites": ["customer_intake"],
            "learning_resources": ["Requirements Engineering Guide", "User Story Writing"],
        },
        {
            "skill_id": "ai_readiness_assessment",
            "name": "AI Readiness Assessment",
            "category": "discovery",
            "description": "Evaluate customer's data quality, infrastructure, and team capabilities for AI adoption",
            "prerequisites": ["business_analysis"],
            "learning_resources": ["AI Readiness Checklist", "Data Quality Assessment Guide"],
        },
    ]

    # ========================================
    # CATEGORY 2: Solution Design Skills
    # ========================================
    design_skills = [
        {
            "skill_id": "task_classification",
            "name": "Task Classification (Human/AI/Hybrid)",
            "category": "solution_design",
            "description": "Classify tasks as fully automatable, AI-assisted, or human-required using AI Migration tool",
            "prerequisites": ["business_analysis"],
            "learning_resources": ["AI Migration Tool Guide", "Automation Scoring Methodology"],
        },
        {
            "skill_id": "workflow_design",
            "name": "Workflow & Logic Design",
            "category": "solution_design",
            "description": "Design sequential and parallel workflows for complex AI agent operations",
            "prerequisites": ["business_analysis"],
            "learning_resources": ["Workflow Engine Documentation", "Logic Tree Best Practices"],
        },
        {
            "skill_id": "tradeoff_analysis",
            "name": "Architectural Trade-off Analysis",
            "category": "solution_design",
            "description": "Perform ATAM-based analysis comparing Cost, Latency, and Scalability for proposed solutions.",
            "prerequisites": ["workflow_design"],
            "learning_resources": ["ATAM Methodology Guide", "CAP Theorem Reference", "PERFORMANCE_REPORT.md"],
        },
        {
            "skill_id": "human_ai_workflow",
            "name": "Human-AI Workflow Design",
            "category": "solution_design",
            "description": "Design optimized workflows that combine human judgment with AI automation",
            "prerequisites": ["task_classification"],
            "learning_resources": ["Workflow Design Patterns", "Human-in-the-Loop Architectures"],
        },
        {
            "skill_id": "architecture_design",
            "name": "AI Solution Architecture",
            "category": "solution_design",
            "description": "Design technical architectures for AI solutions using Diagram Architect",
            "prerequisites": ["workflow_design", "tradeoff_analysis"],
            "learning_resources": ["Diagram Architect Tool Guide", "Cloud Architecture Patterns"],
        },
        {
            "skill_id": "prompt_engineering",
            "name": "Prompt Engineering",
            "category": "solution_design",
            "description": "Design effective prompts for AI models to achieve desired outputs",
            "prerequisites": [],
            "learning_resources": ["Prompt Engineering Guide", "Claude Best Practices"],
        },
    ]

    # ========================================
    # CATEGORY 3: Sales & ROI Skills
    # ========================================
    sales_skills = [
        {
            "skill_id": "roi_calculation",
            "name": "ROI Calculation & Projection",
            "category": "sales",
            "description": "Calculate and project ROI for AI solutions at 1, 3, and 5 year horizons",
            "prerequisites": ["task_classification"],
            "learning_resources": ["ROI Calculation Guide", "AI Investment Analysis"],
        },
        {
            "skill_id": "proposal_creation",
            "name": "Proposal Creation",
            "category": "sales",
            "description": "Generate professional proposals with pricing, timelines, and deliverables",
            "prerequisites": ["roi_calculation", "architecture_design"],
            "learning_resources": ["Sales Generator Tool Guide", "Proposal Writing Best Practices"],
        },
        {
            "skill_id": "roadmap_planning",
            "name": "Migration Roadmap Planning",
            "category": "sales",
            "description": "Create phased implementation roadmaps for AI migrations",
            "prerequisites": ["workflow_design"],
            "learning_resources": ["Roadmap Planning Guide", "Agile Release Planning"],
        },
    ]

    # ========================================
    # CATEGORY 4: Implementation Skills
    # ========================================
    implementation_skills = [
        {
            "skill_id": "project_scaffolding",
            "name": "Project Scaffolding",
            "category": "implementation",
            "description": "Generate project structures from templates using Project Scaffold tool",
            "prerequisites": ["architecture_design"],
            "learning_resources": ["Project Scaffold Tool Guide", "Project Structure Best Practices"],
        },
        {
            "skill_id": "ai_integration",
            "name": "AI Model Integration",
            "category": "implementation",
            "description": "Integrate AI models (Claude, OpenAI, local models) into solutions",
            "prerequisites": ["prompt_engineering"],
            "learning_resources": ["Claude API Documentation", "Model Integration Patterns"],
        },
        {
            "skill_id": "testing",
            "name": "AI Solution Testing",
            "category": "implementation",
            "description": "Write comprehensive tests for AI solutions including edge cases",
            "prerequisites": ["ai_integration"],
            "learning_resources": ["Testing AI Systems Guide", "pytest Best Practices"],
        },
    ]

    # ========================================
    # CATEGORY 5: Deployment Skills
    # ========================================
    deployment_skills = [
        {
            "skill_id": "cicd_setup",
            "name": "CI/CD Pipeline Setup",
            "category": "deployment",
            "description": "Configure automated build, test, and deployment pipelines",
            "prerequisites": ["testing"],
            "learning_resources": ["Deployment Orchestrator Guide", "GitHub Actions Tutorial"],
        },
        {
            "skill_id": "containerization",
            "name": "Docker Containerization",
            "category": "deployment",
            "description": "Create Docker images and compose files for AI solutions",
            "prerequisites": [],
            "learning_resources": ["Docker Best Practices", "Container Security Guide"],
        },
        {
            "skill_id": "cloud_deployment",
            "name": "Cloud Deployment",
            "category": "deployment",
            "description": "Deploy AI solutions to cloud environments (AWS, GCP, Azure)",
            "prerequisites": ["cicd_setup", "containerization"],
            "learning_resources": ["Cloud Deployment Guide", "Infrastructure as Code"],
        },
    ]

    # ========================================
    # CATEGORY 6: Support & Optimization Skills
    # ========================================
    support_skills = [
        {
            "skill_id": "performance_monitoring",
            "name": "AI Performance Monitoring",
            "category": "support",
            "description": "Monitor AI accuracy, latency, costs, and user satisfaction",
            "prerequisites": ["cloud_deployment"],
            "learning_resources": ["Observability Guide", "AI Metrics Dashboard"],
        },
        {
            "skill_id": "prompt_optimization",
            "name": "Prompt Optimization",
            "category": "support",
            "description": "Refine prompts based on production data to improve AI performance",
            "prerequisites": ["prompt_engineering", "performance_monitoring"],
            "learning_resources": ["Prompt Iteration Guide", "A/B Testing Prompts"],
        },
        {
            "skill_id": "customer_success",
            "name": "Customer Success Management",
            "category": "support",
            "description": "Manage ongoing customer relationships and ensure success",
            "prerequisites": ["customer_intake"],
            "learning_resources": ["Customer Lifecycle Guide", "Support Best Practices"],
        },
    ]

    # ========================================
    # CATEGORY 7: Hospitality Skills
    # ========================================
    hospitality_skills = [
        {
            "skill_id": "guest_messaging",
            "name": "Guest Messaging & Approval Workflows",
            "category": "hospitality",
            "description": "Draft, review, and send guest communications using approval workflow patterns",
            "prerequisites": ["prompt_engineering"],
            "learning_resources": ["Hospitality Ops SKILL.md", "Approval Workflow SKILL.md"],
        },
        {
            "skill_id": "cleaning_dispatch",
            "name": "Cleaning Dispatch Automation",
            "category": "hospitality",
            "description": "Automate cleaning scheduling based on PMS checkout/checkin data and priority tiers",
            "prerequisites": [],
            "learning_resources": ["Hospitality Ops SKILL.md", "Daily Ops Rhythm SKILL.md"],
        },
        {
            "skill_id": "pms_interpretation",
            "name": "PMS Data Interpretation",
            "category": "hospitality",
            "description": "Read and act on property management system data: bookings, rates, availability, guest profiles",
            "prerequisites": [],
            "learning_resources": ["PMS Integration Guide", "Hospitality Ops SKILL.md"],
        },
        {
            "skill_id": "review_management",
            "name": "Review Solicitation & Management",
            "category": "hospitality",
            "description": "Automate review collection, monitor ratings, and respond to guest feedback",
            "prerequisites": ["guest_messaging"],
            "learning_resources": ["Hospitality Ops SKILL.md", "Review Platform Guides"],
        },
    ]

    # ========================================
    # CATEGORY 8: Knowledge & Content Skills
    # ========================================
    knowledge_skills = [
        {
            "skill_id": "knowledge_ingestion",
            "name": "Knowledge Ingestion & RAG",
            "category": "knowledge",
            "description": "Ingest documents, build knowledge bases, and configure retrieval-augmented generation pipelines",
            "prerequisites": [],
            "learning_resources": ["Knowledge Base Tool Guide", "RAG Architecture Patterns"],
        },
        {
            "skill_id": "digest_design",
            "name": "Digest Design & Distribution",
            "category": "knowledge",
            "description": "Design automated digests and intelligence briefs delivered via Telegram or other channels",
            "prerequisites": ["knowledge_ingestion"],
            "learning_resources": ["Daily Ops Rhythm SKILL.md", "Telegram Formatting Guide"],
        },
        {
            "skill_id": "rag_optimization",
            "name": "RAG Quality Optimization",
            "category": "knowledge",
            "description": "Tune retrieval quality, chunk sizing, embedding strategies, and relevance scoring",
            "prerequisites": ["knowledge_ingestion"],
            "learning_resources": ["RAG Tuning Guide", "Embedding Model Comparison"],
        },
        {
            "skill_id": "content_governance",
            "name": "Content Governance & Lifecycle",
            "category": "knowledge",
            "description": "Manage content freshness, archival policies, taxonomy maintenance, and quality audits",
            "prerequisites": ["knowledge_ingestion"],
            "learning_resources": ["Content Lifecycle Guide", "Taxonomy Best Practices"],
        },
    ]

    # ========================================
    # CATEGORY 9: Automation & Workflow Skills
    # ========================================
    automation_skills = [
        {
            "skill_id": "workflow_engineering",
            "name": "Workflow Engineering",
            "category": "automation",
            "description": "Design and build multi-stage workflows with branching, looping, and error recovery",
            "prerequisites": ["workflow_design"],
            "learning_resources": ["Workflow Engine Documentation", "Stage Design Patterns"],
        },
        {
            "skill_id": "scheduler_management",
            "name": "Scheduler & Task Management",
            "category": "automation",
            "description": "Configure scheduled tasks, cron expressions, and recurring automation triggers",
            "prerequisites": [],
            "learning_resources": ["Scheduler Configuration Guide", "Cron Expression Reference"],
        },
        {
            "skill_id": "agent_orchestration",
            "name": "Agent Orchestration",
            "category": "automation",
            "description": "Coordinate multiple AI agents across workflows with handoff, escalation, and parallel execution",
            "prerequisites": ["workflow_engineering"],
            "learning_resources": ["Agent Orchestration Guide", "Multi-Agent Patterns"],
        },
        {
            "skill_id": "integration_design",
            "name": "External Integration Design",
            "category": "automation",
            "description": "Design integrations with external services: APIs, webhooks, Telegram, and third-party platforms",
            "prerequisites": [],
            "learning_resources": ["Integration Patterns Guide", "Webhook Configuration"],
        },
    ]

    # ========================================
    # CATEGORY 10: Business Development Skills
    # ========================================
    bizdev_skills = [
        {
            "skill_id": "pipeline_analytics",
            "name": "Pipeline Analytics & Forecasting",
            "category": "bizdev",
            "description": "Track deal pipeline health, forecast revenue, and identify conversion bottlenecks",
            "prerequisites": ["customer_intake"],
            "learning_resources": ["Pipeline Dashboard Guide", "Revenue Forecasting Methods"],
        },
        {
            "skill_id": "proposal_automation",
            "name": "Proposal Automation Pipelines",
            "category": "bizdev",
            "description": "Automate proposal generation from business analysis data with dynamic pricing and scope",
            "prerequisites": ["proposal_creation"],
            "learning_resources": ["Sales Generator Tool Guide", "Proposal Template Library"],
        },
        {
            "skill_id": "account_health_monitoring",
            "name": "Account Health Monitoring",
            "category": "bizdev",
            "description": "Monitor client health scores, predict churn risk, and identify expansion opportunities",
            "prerequisites": ["customer_success"],
            "learning_resources": ["Customer Lifecycle Guide", "Health Score Methodology"],
        },
    ]

    # ========================================
    # CATEGORY 11: Platform Administration Skills
    # ========================================
    admin_skills = [
        {
            "skill_id": "platform_configuration",
            "name": "Platform Configuration",
            "category": "administration",
            "description": "Configure platform dashboards, instruments, tools, and system settings",
            "prerequisites": [],
            "learning_resources": ["Platform Architecture Guide", "Dashboard Configuration"],
        },
        {
            "skill_id": "security_administration",
            "name": "Security & Access Management",
            "category": "administration",
            "description": "Manage API keys, access controls, environment security, and audit logging",
            "prerequisites": [],
            "learning_resources": ["Security Configuration Guide", "Access Control Patterns"],
        },
        {
            "skill_id": "observability_ops",
            "name": "Observability & Monitoring",
            "category": "administration",
            "description": "Configure health checks, performance monitoring, alerting, and operational dashboards",
            "prerequisites": ["platform_configuration"],
            "learning_resources": ["Observability Guide", "Health Check Configuration"],
        },
    ]

    # Register all skills
    all_skills = (
        discovery_skills
        + design_skills
        + sales_skills
        + implementation_skills
        + deployment_skills
        + support_skills
        + hospitality_skills
        + knowledge_skills
        + automation_skills
        + bizdev_skills
        + admin_skills
    )

    print(f"\n📚 Registering {len(all_skills)} skills...")
    for skill in all_skills:
        manager.register_skill(
            skill_id=skill["skill_id"],
            name=skill["name"],
            category=skill["category"],
            description=skill.get("description", ""),
            prerequisites=skill.get("prerequisites", []),
            related_tools=skill.get("learning_resources", []),  # Map to related_tools
        )
        print(f"  ✓ {skill['name']} ({skill['category']})")

    # ========================================
    # LEARNING PATHS
    # ========================================
    learning_paths = [
        {
            "path_id": "ai_solution_architect",
            "name": "AI Solution Architect",
            "description": "Complete path to become an AI Solution Architect - from discovery through deployment",
            "target_role": "operator",
            "modules": [
                {
                    "module_id": "discovery_fundamentals",
                    "name": "Discovery Fundamentals",
                    "description": "Master customer discovery and business analysis",
                    "skills": [
                        "customer_intake",
                        "business_analysis",
                        "requirements_gathering",
                        "ai_readiness_assessment",
                    ],
                    "lessons": [
                        {
                            "title": "Introduction to AI Solutioning",
                            "content": "Overview of the AI solutioning process",
                        },
                        {
                            "title": "Using Customer Lifecycle Tool",
                            "content": "Hands-on: Add a customer and capture requirements",
                        },
                        {"title": "Business X-Ray Analysis", "content": "Hands-on: Run a full business analysis"},
                        {"title": "AI Readiness Assessment", "content": "Evaluate customer readiness for AI adoption"},
                    ],
                    "estimated_hours": 4,
                },
                {
                    "module_id": "solution_design_mastery",
                    "name": "Solution Design Mastery",
                    "description": "Design effective AI solutions with human-AI workflows",
                    "skills": ["task_classification", "workflow_design", "architecture_design", "prompt_engineering"],
                    "lessons": [
                        {"title": "Task Classification Framework", "content": "Classify tasks as human/AI/hybrid"},
                        {"title": "Workflow Design Patterns", "content": "Design human-in-the-loop workflows"},
                        {"title": "Architecture with Diagram Architect", "content": "Generate system diagrams"},
                        {"title": "Prompt Engineering Basics", "content": "Write effective AI prompts"},
                    ],
                    "estimated_hours": 6,
                },
                {
                    "module_id": "sales_and_roi",
                    "name": "Sales & ROI",
                    "description": "Create compelling proposals with clear ROI",
                    "skills": ["roi_calculation", "proposal_creation", "roadmap_planning"],
                    "lessons": [
                        {"title": "ROI Calculation Methods", "content": "Calculate 1/3/5 year ROI projections"},
                        {"title": "Using Sales Generator", "content": "Generate professional proposals"},
                        {"title": "Roadmap Planning", "content": "Create phased implementation plans"},
                    ],
                    "estimated_hours": 3,
                },
                {
                    "module_id": "implementation_excellence",
                    "name": "Implementation Excellence",
                    "description": "Build production-ready AI solutions",
                    "skills": ["project_scaffolding", "ai_integration", "testing"],
                    "lessons": [
                        {"title": "Project Setup", "content": "Scaffold projects from templates"},
                        {"title": "AI Model Integration", "content": "Connect Claude and other AI models"},
                        {"title": "Testing AI Solutions", "content": "Write comprehensive tests"},
                    ],
                    "estimated_hours": 8,
                },
                {
                    "module_id": "deployment_operations",
                    "name": "Deployment & Operations",
                    "description": "Deploy and operate AI solutions in production",
                    "skills": ["cicd_setup", "containerization", "cloud_deployment"],
                    "lessons": [
                        {"title": "CI/CD Pipeline Setup", "content": "Configure automated deployments"},
                        {"title": "Docker Containerization", "content": "Package applications for deployment"},
                        {"title": "Cloud Deployment", "content": "Deploy to production environments"},
                    ],
                    "estimated_hours": 5,
                },
                {
                    "module_id": "optimization_support",
                    "name": "Optimization & Support",
                    "description": "Optimize AI performance and ensure customer success",
                    "skills": ["performance_monitoring", "prompt_optimization", "customer_success"],
                    "lessons": [
                        {"title": "Monitoring AI Performance", "content": "Track metrics and KPIs"},
                        {"title": "Prompt Iteration", "content": "Improve prompts based on data"},
                        {"title": "Customer Success", "content": "Manage ongoing relationships"},
                    ],
                    "estimated_hours": 4,
                },
            ],
            "certification": {
                "name": "Certified AI Solution Architect",
                "requirements": [
                    "Complete all modules",
                    "Achieve Intermediate level in all skills",
                    "Complete one end-to-end AI Solutioning project",
                ],
            },
            "total_hours": 30,
        },
        {
            "path_id": "quick_start_operator",
            "name": "Quick Start for Operators",
            "description": "Fast-track path to start delivering AI solutions",
            "target_role": "operator",
            "modules": [
                {
                    "module_id": "essentials",
                    "name": "Essential Skills",
                    "description": "Core skills to start AI solutioning",
                    "skills": ["customer_intake", "business_analysis", "task_classification", "prompt_engineering"],
                    "lessons": [
                        {"title": "AI Solutioning Overview", "content": "Quick intro to the process"},
                        {"title": "Essential Tools", "content": "Customer Lifecycle + Business X-Ray + AI Migration"},
                        {"title": "Quick Win Identification", "content": "Find fast automation opportunities"},
                    ],
                    "estimated_hours": 2,
                },
                {
                    "module_id": "first_project",
                    "name": "Your First AI Project",
                    "description": "End-to-end walkthrough of a simple AI solution",
                    "skills": ["workflow_design", "proposal_creation", "project_scaffolding"],
                    "lessons": [
                        {"title": "Project Walkthrough", "content": "From discovery to deployment"},
                        {"title": "Using Workflow Templates", "content": "Start from AI Solutioning template"},
                        {"title": "Hands-on Exercise", "content": "Build a simple AI automation"},
                    ],
                    "estimated_hours": 4,
                },
            ],
            "certification": {
                "name": "AI Solutioning Quickstart Certificate",
                "requirements": ["Complete both modules", "Achieve Beginner level in essential skills"],
            },
            "total_hours": 6,
        },
        # ========================================
        # PATH 3: Hospitality Operations Manager
        # ========================================
        {
            "path_id": "hospitality_ops_manager",
            "name": "Hospitality Operations Manager",
            "description": "Master guest communications, cleaning operations, and revenue optimization for vacation rental management",
            "target_role": "pm",
            "modules": [
                {
                    "module_id": "guest_communication_mastery",
                    "name": "Guest Communication Mastery",
                    "description": "Master the art of guest messaging across the entire stay lifecycle",
                    "skills": ["guest_messaging", "prompt_engineering"],
                    "lessons": [
                        {"title": "Guest Messaging Fundamentals", "content": "placeholder"},
                        {"title": "Automated Guest Lifecycle", "content": "placeholder"},
                        {"title": "Handling Escalations", "content": "placeholder"},
                        {"title": "Multi-Property at Scale", "content": "placeholder"},
                    ],
                    "estimated_hours": 5,
                },
                {
                    "module_id": "cleaning_and_operations",
                    "name": "Cleaning & Operations",
                    "description": "Automate cleaning dispatch and daily operations workflows",
                    "skills": ["cleaning_dispatch", "pms_interpretation"],
                    "lessons": [
                        {"title": "PMS Data Interpretation", "content": "placeholder"},
                        {"title": "Cleaning Dispatch Automation", "content": "placeholder"},
                        {"title": "Daily Operations Rhythm", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
                {
                    "module_id": "revenue_and_reviews",
                    "name": "Revenue & Reviews",
                    "description": "Optimize revenue through review management and pricing strategies",
                    "skills": ["review_management", "performance_monitoring"],
                    "lessons": [
                        {"title": "Review Solicitation Strategy", "content": "placeholder"},
                        {"title": "Revenue Monitoring", "content": "placeholder"},
                        {"title": "Seasonal Pricing", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
                {
                    "module_id": "hospitality_capstone",
                    "name": "Hospitality Capstone",
                    "description": "Apply everything in a comprehensive multi-property project",
                    "skills": ["guest_messaging", "cleaning_dispatch", "pms_interpretation", "review_management"],
                    "lessons": [
                        {"title": "Multi-Property Setup Project", "content": "placeholder"},
                        {"title": "Operations Playbook Creation", "content": "placeholder"},
                        {"title": "Performance Review", "content": "placeholder"},
                    ],
                    "estimated_hours": 5,
                },
            ],
            "certification": {
                "name": "Certified Hospitality Operations Manager",
                "requirements": [
                    "Complete all modules",
                    "Achieve Intermediate level in hospitality skills",
                    "Complete multi-property capstone project",
                ],
            },
            "total_hours": 18,
        },
        # ========================================
        # PATH 4: Knowledge & Content Strategist
        # ========================================
        {
            "path_id": "knowledge_content_strategist",
            "name": "Knowledge & Content Strategist",
            "description": "Build and manage knowledge systems, automated digests, and content pipelines",
            "target_role": "analyst",
            "modules": [
                {
                    "module_id": "knowledge_system_foundations",
                    "name": "Knowledge System Foundations",
                    "description": "Understand knowledge architecture and document ingestion",
                    "skills": ["knowledge_ingestion"],
                    "lessons": [
                        {"title": "Knowledge Architecture Overview", "content": "placeholder"},
                        {"title": "Document Ingestion Workflows", "content": "placeholder"},
                        {"title": "Organizing Knowledge Taxonomies", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
                {
                    "module_id": "digest_and_distribution",
                    "name": "Digest & Distribution",
                    "description": "Design and deliver automated intelligence digests",
                    "skills": ["digest_design", "prompt_engineering"],
                    "lessons": [
                        {"title": "Digest Builder Fundamentals", "content": "placeholder"},
                        {"title": "Telegram Digest Delivery", "content": "placeholder"},
                        {"title": "Research Agent Workflows", "content": "placeholder"},
                        {"title": "Content Pipeline Automation", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
                {
                    "module_id": "advanced_knowledge_ops",
                    "name": "Advanced Knowledge Ops",
                    "description": "Optimize RAG quality and establish content governance",
                    "skills": ["rag_optimization", "content_governance", "prompt_optimization"],
                    "lessons": [
                        {"title": "RAG Quality Optimization", "content": "placeholder"},
                        {"title": "Brand Voice and Writing Standards", "content": "placeholder"},
                        {"title": "Knowledge Governance", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
                {
                    "module_id": "knowledge_capstone",
                    "name": "Knowledge Capstone",
                    "description": "Build a complete knowledge system from scratch",
                    "skills": ["knowledge_ingestion", "digest_design", "rag_optimization", "content_governance"],
                    "lessons": [
                        {"title": "Knowledge Base Build-Out", "content": "placeholder"},
                        {"title": "Automated Intelligence Brief", "content": "placeholder"},
                        {"title": "Knowledge System Audit", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
            ],
            "certification": {
                "name": "Certified Knowledge Strategist",
                "requirements": [
                    "Complete all modules",
                    "Achieve Intermediate level in knowledge skills",
                    "Complete knowledge system capstone project",
                ],
            },
            "total_hours": 16,
        },
        # ========================================
        # PATH 5: Workflow & Automation Engineer
        # ========================================
        {
            "path_id": "workflow_automation_engineer",
            "name": "Workflow & Automation Engineer",
            "description": "Design, build, and operate complex multi-stage automations and agent orchestrations",
            "target_role": "devops",
            "modules": [
                {
                    "module_id": "workflow_engine_deep_dive",
                    "name": "Workflow Engine Deep Dive",
                    "description": "Master the workflow engine internals and stage design",
                    "skills": ["workflow_engineering", "workflow_design"],
                    "lessons": [
                        {"title": "Workflow Engine Architecture", "content": "placeholder"},
                        {"title": "Stage Design and Transitions", "content": "placeholder"},
                        {"title": "Execution Tracking and History", "content": "placeholder"},
                        {"title": "Workflow Templates and Reuse", "content": "placeholder"},
                    ],
                    "estimated_hours": 5,
                },
                {
                    "module_id": "scheduling_and_automation",
                    "name": "Scheduling & Automation",
                    "description": "Configure schedulers, approval workflows, and agent orchestration",
                    "skills": ["scheduler_management", "agent_orchestration"],
                    "lessons": [
                        {"title": "Scheduler Deep Dive", "content": "placeholder"},
                        {"title": "Approval Workflow Patterns", "content": "placeholder"},
                        {"title": "Agent Orchestration", "content": "placeholder"},
                        {"title": "Error Handling and Recovery", "content": "placeholder"},
                    ],
                    "estimated_hours": 5,
                },
                {
                    "module_id": "integration_and_scaling",
                    "name": "Integration & Scaling",
                    "description": "Connect external services and scale operations",
                    "skills": ["integration_design", "cicd_setup"],
                    "lessons": [
                        {"title": "Telegram Integration Patterns", "content": "placeholder"},
                        {"title": "External Service Integration", "content": "placeholder"},
                        {"title": "Multi-Dashboard Operations", "content": "placeholder"},
                    ],
                    "estimated_hours": 5,
                },
                {
                    "module_id": "automation_capstone",
                    "name": "Automation Capstone",
                    "description": "Build and optimize a production automation end-to-end",
                    "skills": [
                        "workflow_engineering",
                        "scheduler_management",
                        "agent_orchestration",
                        "integration_design",
                    ],
                    "lessons": [
                        {"title": "End-to-End Automation Build", "content": "placeholder"},
                        {"title": "Load Testing and Optimization", "content": "placeholder"},
                        {"title": "Automation Governance", "content": "placeholder"},
                    ],
                    "estimated_hours": 5,
                },
            ],
            "certification": {
                "name": "Certified Automation Engineer",
                "requirements": [
                    "Complete all modules",
                    "Achieve Intermediate level in automation skills",
                    "Complete end-to-end automation capstone project",
                ],
            },
            "total_hours": 20,
        },
        # ========================================
        # PATH 6: Business Development Operator
        # ========================================
        {
            "path_id": "bizdev_operator",
            "name": "Business Development Operator",
            "description": "Master pipeline management, proposal automation, and account health monitoring for sales operations",
            "target_role": "analyst",
            "modules": [
                {
                    "module_id": "pipeline_management",
                    "name": "Pipeline Management",
                    "description": "Track deals, forecast revenue, and gather competitive intelligence",
                    "skills": ["pipeline_analytics", "customer_intake", "business_analysis"],
                    "lessons": [
                        {"title": "Customer Lifecycle Mastery", "content": "placeholder"},
                        {"title": "Pipeline Analytics and Forecasting", "content": "placeholder"},
                        {"title": "Competitive Intelligence Gathering", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
                {
                    "module_id": "proposal_and_closing",
                    "name": "Proposal & Closing",
                    "description": "Automate proposal generation and optimize deal closing",
                    "skills": ["proposal_automation", "roi_calculation", "proposal_creation"],
                    "lessons": [
                        {"title": "Business X-Ray for Sales", "content": "placeholder"},
                        {"title": "Proposal Generation Pipeline", "content": "placeholder"},
                        {"title": "Follow-Up Automation", "content": "placeholder"},
                        {"title": "Objection Handling with Data", "content": "placeholder"},
                    ],
                    "estimated_hours": 5,
                },
                {
                    "module_id": "account_management",
                    "name": "Account Management",
                    "description": "Monitor account health and drive expansion",
                    "skills": ["account_health_monitoring", "customer_success"],
                    "lessons": [
                        {"title": "Client Health Monitoring", "content": "placeholder"},
                        {"title": "Expansion and Upsell Identification", "content": "placeholder"},
                        {"title": "Renewal Automation", "content": "placeholder"},
                    ],
                    "estimated_hours": 5,
                },
            ],
            "certification": {
                "name": "Certified BizDev Operator",
                "requirements": [
                    "Complete all modules",
                    "Achieve Intermediate level in bizdev skills",
                    "Complete account management capstone exercises",
                ],
            },
            "total_hours": 14,
        },
        # ========================================
        # PATH 7: Platform Administrator
        # ========================================
        {
            "path_id": "platform_admin",
            "name": "Platform Administrator",
            "description": "Configure, secure, and monitor the Agent Mahoo platform for production operations",
            "target_role": "devops",
            "modules": [
                {
                    "module_id": "platform_configuration",
                    "name": "Platform Configuration",
                    "description": "Understand platform architecture and configure dashboards and tools",
                    "skills": ["platform_configuration"],
                    "lessons": [
                        {"title": "Platform Architecture Overview", "content": "placeholder"},
                        {"title": "Dashboard Configuration", "content": "placeholder"},
                        {"title": "Instrument and Tool Management", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
                {
                    "module_id": "security_and_monitoring",
                    "name": "Security & Monitoring",
                    "description": "Configure security, observability, and backup systems",
                    "skills": ["security_administration", "observability_ops", "performance_monitoring"],
                    "lessons": [
                        {"title": "Security Configuration", "content": "placeholder"},
                        {"title": "Observability and Health Monitoring", "content": "placeholder"},
                        {"title": "Backup and Recovery", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
                {
                    "module_id": "admin_capstone",
                    "name": "Admin Capstone",
                    "description": "Apply administration skills in real-world scenarios",
                    "skills": [
                        "platform_configuration",
                        "security_administration",
                        "observability_ops",
                        "containerization",
                    ],
                    "lessons": [
                        {"title": "Platform Health Audit", "content": "placeholder"},
                        {"title": "Onboarding New Operators", "content": "placeholder"},
                        {"title": "Capacity Planning", "content": "placeholder"},
                    ],
                    "estimated_hours": 4,
                },
            ],
            "certification": {
                "name": "Certified Platform Administrator",
                "requirements": [
                    "Complete all modules",
                    "Achieve Intermediate level in administration skills",
                    "Complete platform health audit capstone",
                ],
            },
            "total_hours": 12,
        },
    ]

    # Load rich content from markdown files into lesson definitions
    print("\n📝 Loading lesson content from training/content/ files...")
    for path in learning_paths:
        for module in path.get("modules", []):
            module_id = module["module_id"]
            for lesson in module.get("lessons", []):
                rich_content = load_lesson_content(module_id, lesson["title"])
                if rich_content != lesson["title"]:
                    lesson["content"] = rich_content
                    print(f"  ✓ Loaded: {lesson['title']}")
                else:
                    print(f"  - Kept placeholder: {lesson['title']}")

    print(f"\n📖 Creating {len(learning_paths)} learning paths...")
    for path in learning_paths:
        manager.create_learning_path(
            path_id=path["path_id"],
            name=path["name"],
            description=path["description"],
            target_role=path["target_role"],
            modules=path["modules"],
            certification=path["certification"],
        )
        print(f"  ✓ {path['name']} ({path['total_hours']} hours)")
        for module in path["modules"]:
            print(f"      - {module['name']}")

    # ========================================
    # SUMMARY
    # ========================================
    print("\n" + "=" * 60)
    print("AI Solutioning Training Setup Complete!")
    print("=" * 60)

    manager.get_stats()
    print(f"""
Summary:
  Skills registered: {len(all_skills)}
  Learning paths: {len(learning_paths)}

Skill Categories:
  - Discovery & Assessment: {len(discovery_skills)}
  - Solution Design: {len(design_skills)}
  - Sales & ROI: {len(sales_skills)}
  - Implementation: {len(implementation_skills)}
  - Deployment: {len(deployment_skills)}
  - Support & Optimization: {len(support_skills)}
  - Hospitality: {len(hospitality_skills)}
  - Knowledge & Content: {len(knowledge_skills)}
  - Automation & Workflow: {len(automation_skills)}
  - Business Development: {len(bizdev_skills)}
  - Platform Administration: {len(admin_skills)}

Learning Paths:
  1. AI Solution Architect (30 hours) - Complete certification path
  2. Quick Start for Operators (6 hours) - Fast-track intro
  3. Hospitality Operations Manager (18 hours) - Guest comms & property ops
  4. Knowledge & Content Strategist (16 hours) - Knowledge systems & digests
  5. Workflow & Automation Engineer (20 hours) - Workflow design & orchestration
  6. Business Development Operator (14 hours) - Pipeline & account management
  7. Platform Administrator (12 hours) - Platform config & security

Next Steps:
  1. Start the AI Solutioning workflow:
     {{workflow_engine(action="create_from_template", template_path="templates/ai_solutioning.json", name="My First AI Project")}}

  2. Enroll in a learning path:
     {{workflow_training(action="enroll_path", path_id="quick_start_operator", agent_id="operator_1")}}

  3. Track skill progress:
     {{workflow_training(action="assess_skill", skill_id="customer_intake", agent_id="operator_1", score=85)}}

  4. View training dashboard in UI:
     Settings → Workflows → Training tab
""")

    return {"skills": len(all_skills), "paths": len(learning_paths), "categories": 11}


if __name__ == "__main__":
    result = setup_training()
    print("\n✅ Training setup successful!")
