"""
End-to-End Demo: Building a FastAPI Authentication System

This demo shows the complete Archon Knowledge Management workflow:
1. Crawling FastAPI documentation
2. Creating a knowledge-aware project
3. Auto decomposition into tasks
4. Knowledge linking
5. Coverage analysis
6. Task execution with knowledge context
7. Learning storage

Usage:
    python demos/end_to_end_demo.py

Requirements:
    - Supabase connection configured
    - OpenAI API key configured
    - Knowledge management database schema deployed
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.knowledge_manager import KnowledgeManager
from archon.universal_crawler import SourceConfig, crawl_source, CrawlProgressTracker
from archon.knowledge_linker import auto_link_task_knowledge, get_task_linked_knowledge
from utils.utils import get_clients

# ============================================================================
# DEMO CONFIGURATION
# ============================================================================

PROJECT_NAME = "FastAPI Authentication System"
PROJECT_DESCRIPTION = """
Build a complete authentication system with JWT tokens, OAuth2, and password reset
functionality using FastAPI and PostgreSQL. The system should include:

- User registration with email verification
- Login with JWT token generation
- Password hashing with bcrypt
- Protected routes using dependencies
- Refresh token mechanism
- OAuth2 integration (Google, GitHub)
- Password reset flow with email
- User profile management
- Role-based access control

The implementation should follow FastAPI best practices, be fully async,
and include comprehensive tests.
"""

FASTAPI_SOURCE = "https://fastapi.tiangolo.com"

# ============================================================================
# DEMO HELPERS
# ============================================================================

def print_header(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_step(step: int, title: str):
    """Print a formatted step header."""
    print(f"\n{'─' * 80}")
    print(f"  Step {step}: {title}")
    print('─' * 80 + "\n")


def print_success(message: str):
    """Print a success message."""
    print(f"✓ {message}")


def print_info(message: str, indent: int = 0):
    """Print an info message."""
    prefix = "  " * indent
    print(f"{prefix}• {message}")


def print_data(label: str, value: Any, indent: int = 1):
    """Print labeled data."""
    prefix = "  " * indent
    if isinstance(value, (list, dict)):
        print(f"{prefix}{label}:")
        if isinstance(value, list):
            for item in value[:5]:  # Limit to 5 items
                print(f"{prefix}  - {item}")
            if len(value) > 5:
                print(f"{prefix}  ... and {len(value) - 5} more")
        else:
            for k, v in list(value.items())[:5]:
                print(f"{prefix}  {k}: {v}")
    else:
        print(f"{prefix}{label}: {value}")


def format_coverage_score(score: float) -> str:
    """Format coverage score with color indicator."""
    percentage = score * 100
    if score >= 0.8:
        return f"{percentage:.1f}% (Excellent)"
    elif score >= 0.6:
        return f"{percentage:.1f}% (Good)"
    elif score >= 0.4:
        return f"{percentage:.1f}% (Fair)"
    else:
        return f"{percentage:.1f}% (Poor)"


# ============================================================================
# DEMO WORKFLOW FUNCTIONS
# ============================================================================

async def step1_crawl_documentation(km: KnowledgeManager) -> Dict[str, Any]:
    """Step 1: Crawl FastAPI documentation."""
    print_step(1, "Crawling FastAPI Documentation")

    print_info("Configuring crawler for FastAPI docs...")

    # Configure the source
    config = SourceConfig(
        source_url=FASTAPI_SOURCE,
        source_type="documentation",
        framework="fastapi",
        language="python",
        crawl_profile="quick"  # Use quick profile for demo
    )

    print_info(f"Source URL: {config.source_url}")
    print_info(f"Framework: {config.framework}")
    print_info(f"Crawl Profile: {config.crawl_profile}")

    # Create progress tracker
    def progress_callback(status: Dict[str, Any]):
        if status['urls_processed'] % 10 == 0:  # Update every 10 URLs
            progress = status['progress_percentage']
            phase = status['current_phase']
            print(f"  Progress: {progress:.1f}% - {phase}")

    tracker = CrawlProgressTracker(progress_callback=progress_callback)

    print_info("Starting crawl (this may take a few minutes)...")

    # Run the crawler
    stats = await crawl_source(config, profile_name="quick", tracker=tracker)

    print_success("Documentation crawling completed!")
    print_data("URLs Processed", stats['urls_processed'])
    print_data("URLs Succeeded", stats['urls_succeeded'])
    print_data("URLs Failed", stats['urls_failed'])
    print_data("Chunks Stored", stats['chunks_stored'])
    print_data("Duration", f"{stats['duration_seconds']} seconds")

    return stats


async def step2_create_project(km: KnowledgeManager) -> Dict[str, Any]:
    """Step 2: Create knowledge-aware project."""
    print_step(2, "Creating Knowledge-Aware Project")

    print_info("Creating project with automatic knowledge discovery...")

    result = await km.create_project(
        name=PROJECT_NAME,
        description=PROJECT_DESCRIPTION,
        priority=1,
        deadline=datetime.now(timezone.utc) + timedelta(days=30),
        auto_discover=True,
        min_coverage=0.4
    )

    project = result['project']
    coverage = result['coverage']

    print_success("Project created successfully!")
    print_data("Project ID", project['id'])
    print_data("Project Name", project['name'])
    print_data("Status", project['status'])
    print_data("Priority", project['priority'])

    if coverage:
        print("\n  Knowledge Coverage Analysis:")
        print_data("Coverage Score", format_coverage_score(coverage['coverage_score']))
        print_data("Total Chunks Available", coverage['total_chunks'])
        print_data("Available Frameworks", coverage['available_frameworks'])
        if coverage['missing_tags']:
            print_data("Missing Knowledge", coverage['missing_tags'])
        print_data("Needs Scraping", "Yes" if coverage['needs_scraping'] else "No")

    return result


async def step3_decompose_project(km: KnowledgeManager, project_id: str) -> List[Dict[str, Any]]:
    """Step 3: Decompose project into tasks."""
    print_step(3, "Decomposing Project into Tasks")

    print_info("Using LLM to break down project into actionable tasks...")

    tasks = await km.decompose_project(
        project_id=project_id,
        decomposition_strategy="auto",
        auto_link_knowledge=True
    )

    print_success(f"Project decomposed into {len(tasks)} tasks!")

    for i, task_result in enumerate(tasks[:5], 1):  # Show first 5 tasks
        task = task_result['task']
        coverage = task_result.get('coverage_score', 0)
        links = task_result.get('linked_knowledge', [])

        print(f"\n  Task {i}: {task['name']}")
        print_data("Description", task['description'][:100] + "...", indent=2)
        print_data("Priority", task['priority'], indent=2)
        print_data("Status", task['status'], indent=2)
        print_data("Knowledge Links", len(links), indent=2)
        print_data("Coverage", format_coverage_score(coverage), indent=2)

    if len(tasks) > 5:
        print(f"\n  ... and {len(tasks) - 5} more tasks")

    return tasks


async def step4_analyze_coverage(km: KnowledgeManager, tasks: List[Dict[str, Any]]):
    """Step 4: Analyze knowledge coverage across all tasks."""
    print_step(4, "Analyzing Knowledge Coverage")

    print_info("Calculating coverage metrics for all tasks...")

    total_tasks = len(tasks)
    total_links = sum(len(t.get('linked_knowledge', [])) for t in tasks)
    avg_coverage = sum(t.get('coverage_score', 0) for t in tasks) / total_tasks if total_tasks > 0 else 0

    # Count tasks by coverage level
    excellent = sum(1 for t in tasks if t.get('coverage_score', 0) >= 0.8)
    good = sum(1 for t in tasks if 0.6 <= t.get('coverage_score', 0) < 0.8)
    fair = sum(1 for t in tasks if 0.4 <= t.get('coverage_score', 0) < 0.6)
    poor = sum(1 for t in tasks if t.get('coverage_score', 0) < 0.4)

    print_success("Coverage analysis complete!")
    print_data("Total Tasks", total_tasks)
    print_data("Total Knowledge Links", total_links)
    print_data("Average Coverage", format_coverage_score(avg_coverage))

    print("\n  Coverage Distribution:")
    print_data("Excellent (≥80%)", f"{excellent} tasks", indent=2)
    print_data("Good (60-80%)", f"{good} tasks", indent=2)
    print_data("Fair (40-60%)", f"{fair} tasks", indent=2)
    print_data("Poor (<40%)", f"{poor} tasks", indent=2)


async def step5_demonstrate_task_execution(km: KnowledgeManager, task_id: str):
    """Step 5: Demonstrate task execution with knowledge context."""
    print_step(5, "Executing Task with Knowledge Context")

    print_info("Fetching task with linked knowledge...")

    # Get task with all linked knowledge
    result = await km.get_task_with_knowledge(task_id)
    task = result['task']
    knowledge = result['linked_knowledge']

    print_success("Task retrieved with knowledge context!")
    print_data("Task Name", task['name'])
    print_data("Task Description", task['description'][:150] + "...")
    print_data("Linked Knowledge Chunks", len(knowledge))

    print("\n  Top 3 Most Relevant Knowledge Chunks:")
    for i, chunk in enumerate(knowledge[:3], 1):
        print(f"\n    {i}. {chunk.get('title', 'Untitled')}")
        print_data("URL", chunk.get('url', 'N/A'), indent=3)
        print_data("Relevance", f"{chunk.get('relevance_score', 0):.2%}", indent=3)
        print_data("Tags", chunk.get('tags', [])[:5], indent=3)
        print_data("Summary", chunk.get('summary', 'No summary')[:100] + "...", indent=3)

    # Simulate using knowledge in agent prompt
    print("\n  Knowledge Context for Agent:")
    print("  " + "─" * 76)

    context = "Relevant documentation chunks:\n\n"
    for i, chunk in enumerate(knowledge[:3], 1):
        context += f"{i}. {chunk.get('title', 'Untitled')}\n"
        context += f"   {chunk.get('summary', 'No summary')}\n\n"

    print(f"  {context[:300]}...")
    print("  " + "─" * 76)


async def step6_show_analytics(km: KnowledgeManager, project_id: str):
    """Step 6: Show project analytics."""
    print_step(6, "Project Analytics & Insights")

    print_info("Gathering project analytics...")

    # Get project
    project = await km.get_project(project_id)

    # Calculate metrics
    embedding_client, supabase = get_clients()

    # Get all tasks for project
    tasks_result = supabase.table("tasks").select("*").eq("project_id", project_id).execute()
    tasks = tasks_result.data

    # Calculate statistics
    total_tasks = len(tasks)
    completed = sum(1 for t in tasks if t['status'] == 'completed')
    in_progress = sum(1 for t in tasks if t['status'] == 'in_progress')
    pending = sum(1 for t in tasks if t['status'] == 'pending')

    # Get knowledge stats
    all_tags = set()
    all_frameworks = set()
    for task in tasks:
        all_tags.update(task.get('required_knowledge_tags', []))
        all_frameworks.update(task.get('required_frameworks', []))

    print_success("Analytics generated!")

    print("\n  Project Status:")
    print_data("Total Tasks", total_tasks, indent=2)
    print_data("Completed", f"{completed} ({completed/total_tasks*100:.1f}%)" if total_tasks > 0 else 0, indent=2)
    print_data("In Progress", in_progress, indent=2)
    print_data("Pending", pending, indent=2)

    print("\n  Knowledge Requirements:")
    print_data("Unique Tags", len(all_tags), indent=2)
    print_data("Frameworks", list(all_frameworks), indent=2)
    print_data("Overall Coverage", format_coverage_score(project.get('knowledge_coverage_score', 0)), indent=2)


# ============================================================================
# MAIN DEMO ORCHESTRATION
# ============================================================================

async def run_demo(skip_crawl: bool = False):
    """Run the complete end-to-end demo."""

    print_header("Archon Knowledge Management - End-to-End Demo")
    print("This demo showcases the complete knowledge management workflow:")
    print("  1. Crawl documentation sources")
    print("  2. Create knowledge-aware projects")
    print("  3. Auto-decompose into tasks")
    print("  4. Link relevant knowledge")
    print("  5. Analyze coverage")
    print("  6. Execute tasks with context")
    print("  7. Track project analytics")

    print(f"\nDemo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize Knowledge Manager
    print_info("Initializing Knowledge Manager...")
    km = KnowledgeManager()
    print_success("Knowledge Manager initialized!")

    # Store results
    results = {}

    try:
        # Step 1: Crawl documentation (optional - skip if already crawled)
        if not skip_crawl:
            results['crawl'] = await step1_crawl_documentation(km)
        else:
            print_step(1, "Crawling FastAPI Documentation")
            print_info("Skipping crawl (using existing knowledge base)")

        # Step 2: Create project
        results['project'] = await step2_create_project(km)
        project_id = results['project']['project']['id']

        # Step 3: Decompose project
        results['tasks'] = await step3_decompose_project(km, project_id)

        # Step 4: Analyze coverage
        await step4_analyze_coverage(km, results['tasks'])

        # Step 5: Demonstrate task execution (use first task)
        if results['tasks']:
            first_task_id = results['tasks'][0]['task']['id']
            await step5_demonstrate_task_execution(km, first_task_id)

        # Step 6: Show analytics
        await step6_show_analytics(km, project_id)

        # Summary
        print_header("Demo Complete!")
        print_success("All steps executed successfully!")

        print("\n  Key Results:")
        if 'crawl' in results:
            print_data("Knowledge Chunks Stored", results['crawl']['chunks_stored'], indent=2)
        print_data("Project Created", results['project']['project']['name'], indent=2)
        print_data("Tasks Generated", len(results['tasks']), indent=2)
        print_data("Average Coverage",
                   format_coverage_score(
                       sum(t.get('coverage_score', 0) for t in results['tasks']) / len(results['tasks'])
                   ) if results['tasks'] else "N/A", indent=2)

        print(f"\n  Project ID: {project_id}")
        print("  You can view this project in the Archon UI or query it programmatically.")

        return results

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        return None


async def quick_demo():
    """Run a quick demo that skips the crawling step."""
    print("Running QUICK DEMO (skipping crawl, using existing knowledge)...\n")
    return await run_demo(skip_crawl=True)


async def full_demo():
    """Run the full demo including crawling."""
    print("Running FULL DEMO (including documentation crawl)...\n")
    return await run_demo(skip_crawl=False)


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Archon Knowledge Management End-to-End Demo"
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run full demo including crawling (slower)'
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help='Run quick demo without crawling (default)'
    )

    args = parser.parse_args()

    if args.full:
        asyncio.run(full_demo())
    else:
        asyncio.run(quick_demo())


if __name__ == "__main__":
    main()
