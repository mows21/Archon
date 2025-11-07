"""
KNOWLEDGE LINKER AGENT - USAGE EXAMPLES

This file demonstrates how to use the Knowledge Linker Agent in various scenarios.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.knowledge_linker import (
    auto_link_task_knowledge,
    refresh_task_knowledge,
    batch_link_tasks,
    get_task_linked_knowledge,
    LinkResult,
    KnowledgeChunk
)
from utils.utils import get_clients

# Initialize clients
embedding_client, supabase = get_clients()


# ============================================================================
# EXAMPLE 1: Link knowledge to a single task
# ============================================================================

async def example_single_task():
    """Example: Link knowledge to a single task by ID"""

    task_id = "your-task-uuid-here"

    print("Linking knowledge to task...")
    result = await auto_link_task_knowledge(task_id)

    print(f"\nResults:")
    print(f"  - Found {result.total_chunks_found} relevant chunks")
    print(f"  - Created {result.links_created} links")
    print(f"  - Coverage score: {result.coverage_score:.2%}")

    if result.missing_knowledge:
        print(f"\n  Missing knowledge areas:")
        for item in result.missing_knowledge:
            print(f"    • {item}")

    if result.suggested_crawl_sources:
        print(f"\n  Suggested sources to crawl:")
        for source in result.suggested_crawl_sources[:3]:
            print(f"    • {source}")


# ============================================================================
# EXAMPLE 2: Link knowledge when creating a new task
# ============================================================================

async def example_create_task_with_knowledge():
    """Example: Create a task and immediately link knowledge"""

    # Create a new task
    task_data = {
        "name": "Implement OAuth2 authentication",
        "description": """
        Build an OAuth2 authentication flow using FastAPI.
        Requirements:
        - Google OAuth2 provider
        - Session management with secure cookies
        - User profile storage in PostgreSQL
        - Protected API endpoints
        """,
        "status": "pending",
        "priority": 2,
        "estimated_duration_minutes": 480
    }

    print("Creating task...")
    result = supabase.table("tasks").insert(task_data).execute()

    if not result.data:
        print("Failed to create task")
        return

    task_id = result.data[0]['id']
    print(f"Created task: {task_id}")

    # Link knowledge immediately
    print("\nLinking knowledge...")
    link_result = await auto_link_task_knowledge(task_id)

    print(f"\nLinked {link_result.links_created} knowledge chunks")
    print(f"Coverage: {link_result.coverage_score:.2%}")

    # Retrieve and display linked knowledge
    knowledge = await get_task_linked_knowledge(task_id)
    print(f"\nLinked knowledge ({len(knowledge)} items):")
    for chunk in knowledge[:5]:  # Show first 5
        link_type = chunk.metadata.get('link_type', 'unknown')
        print(f"  [{link_type.upper()}] {chunk.title}")
        print(f"    URL: {chunk.url}")
        print(f"    Relevance: {chunk.similarity:.2f}")
        print()


# ============================================================================
# EXAMPLE 3: Batch link multiple tasks
# ============================================================================

async def example_batch_link():
    """Example: Link knowledge to multiple tasks at once"""

    # Get all pending tasks that don't have knowledge linked
    result = supabase.table("tasks").select("id, name").eq("status", "pending").execute()

    if not result.data:
        print("No pending tasks found")
        return

    task_ids = [task['id'] for task in result.data]
    print(f"Found {len(task_ids)} pending tasks")

    # Link knowledge to all tasks in parallel
    print("Linking knowledge in batch...")
    results = await batch_link_tasks(task_ids)

    # Summarize results
    total_links = sum(r.links_created for r in results.values())
    avg_coverage = sum(r.coverage_score for r in results.values()) / len(results)

    print(f"\nBatch Results:")
    print(f"  - Total tasks processed: {len(results)}")
    print(f"  - Total links created: {total_links}")
    print(f"  - Average coverage: {avg_coverage:.2%}")

    # Show tasks with low coverage
    low_coverage_tasks = [
        (task_id, r.coverage_score)
        for task_id, r in results.items()
        if r.coverage_score < 0.5
    ]

    if low_coverage_tasks:
        print(f"\nTasks with low coverage (<50%):")
        for task_id, coverage in low_coverage_tasks:
            print(f"  - Task {task_id}: {coverage:.2%}")


# ============================================================================
# EXAMPLE 4: Refresh knowledge when task description changes
# ============================================================================

async def example_refresh_on_update():
    """Example: Refresh knowledge links when task is updated"""

    task_id = "your-task-uuid-here"

    # Update task description
    print("Updating task description...")
    new_description = """
    Extended requirements:
    - Add WebSocket support for real-time updates
    - Implement Redis caching for session data
    - Add rate limiting with Redis
    - Include Prometheus metrics
    """

    supabase.table("tasks").update({
        "description": new_description
    }).eq("id", task_id).execute()

    # Refresh knowledge links
    print("Refreshing knowledge links...")
    result = await refresh_task_knowledge(task_id)

    print(f"\nRefresh Results:")
    print(f"  - New links created: {result.links_created}")
    print(f"  - Updated coverage: {result.coverage_score:.2%}")


# ============================================================================
# EXAMPLE 5: Check knowledge coverage before starting a task
# ============================================================================

async def example_check_coverage_before_start():
    """Example: Verify knowledge coverage before allowing task to start"""

    task_id = "your-task-uuid-here"

    # Link knowledge if not already linked
    result = await auto_link_task_knowledge(task_id)

    # Check if we have sufficient coverage
    MIN_COVERAGE = 0.6  # 60% coverage required

    if result.coverage_score < MIN_COVERAGE:
        print(f"⚠️  Insufficient knowledge coverage: {result.coverage_score:.2%}")
        print(f"   Required: {MIN_COVERAGE:.2%}")
        print(f"\n   Missing knowledge:")
        for item in result.missing_knowledge:
            print(f"   • {item}")

        if result.suggested_crawl_sources:
            print(f"\n   Recommended actions:")
            print(f"   1. Crawl these documentation sources:")
            for source in result.suggested_crawl_sources[:3]:
                print(f"      • {source}")
            print(f"   2. Or manually add knowledge chunks")
            print(f"   3. Or proceed with caution")

        # Update task status to blocked
        supabase.table("tasks").update({
            "is_blocked": True,
            "blocker_reason": f"Insufficient knowledge coverage ({result.coverage_score:.2%}). "
                            f"Missing: {', '.join(result.missing_knowledge[:3])}"
        }).eq("id", task_id).execute()

        print(f"\n   Task marked as blocked until knowledge is available.")
    else:
        print(f"✓ Sufficient knowledge coverage: {result.coverage_score:.2%}")
        print(f"  Task is ready to start!")

        # Update task status to ready
        supabase.table("tasks").update({
            "is_blocked": False,
            "status": "ready"
        }).eq("id", task_id).execute()


# ============================================================================
# EXAMPLE 6: Integration with task scheduler
# ============================================================================

async def example_scheduler_integration():
    """Example: Use Knowledge Linker in a task scheduler"""

    # Get all tasks that need knowledge linking
    result = supabase.table("tasks").select("id, name, description").is_("knowledge_coverage_score", "null").execute()

    if not result.data:
        print("All tasks have knowledge linked")
        return

    print(f"Found {len(result.data)} tasks needing knowledge links")

    # Process each task
    for task in result.data:
        task_id = task['id']
        task_name = task['name']

        print(f"\nProcessing: {task_name}")

        # Link knowledge
        link_result = await auto_link_task_knowledge(task_id)

        # Determine if task is ready based on coverage
        if link_result.coverage_score >= 0.7:
            status = "ready"
            print(f"  ✓ High coverage ({link_result.coverage_score:.2%}) - marked as READY")
        elif link_result.coverage_score >= 0.4:
            status = "pending"
            print(f"  ⚠ Medium coverage ({link_result.coverage_score:.2%}) - kept as PENDING")
        else:
            status = "blocked"
            print(f"  ✗ Low coverage ({link_result.coverage_score:.2%}) - marked as BLOCKED")

        # Update task status
        supabase.table("tasks").update({
            "status": status,
            "is_blocked": (status == "blocked"),
            "blocker_reason": f"Low knowledge coverage" if status == "blocked" else None
        }).eq("id", task_id).execute()


# ============================================================================
# EXAMPLE 7: Get and display linked knowledge for a task
# ============================================================================

async def example_display_task_knowledge():
    """Example: Retrieve and display all knowledge linked to a task"""

    task_id = "your-task-uuid-here"

    # Get linked knowledge
    knowledge = await get_task_linked_knowledge(task_id)

    if not knowledge:
        print("No knowledge linked to this task")
        return

    # Group by link type
    required = [k for k in knowledge if k.metadata.get('link_type') == 'required']
    suggested = [k for k in knowledge if k.metadata.get('link_type') == 'suggested']
    reference = [k for k in knowledge if k.metadata.get('link_type') == 'reference']

    print(f"Task Knowledge Summary")
    print("=" * 80)

    if required:
        print(f"\n📌 REQUIRED ({len(required)} items)")
        for chunk in required:
            print(f"  • {chunk.title}")
            print(f"    {chunk.url}")
            print(f"    Relevance: {chunk.similarity:.2f} | Tags: {', '.join(chunk.tags[:3])}")

    if suggested:
        print(f"\n💡 SUGGESTED ({len(suggested)} items)")
        for chunk in suggested:
            print(f"  • {chunk.title}")
            print(f"    {chunk.url}")

    if reference:
        print(f"\n📚 REFERENCE ({len(reference)} items)")
        for chunk in reference:
            print(f"  • {chunk.title}")


# ============================================================================
# EXAMPLE 8: Monitor knowledge linking across projects
# ============================================================================

async def example_project_knowledge_monitor():
    """Example: Monitor knowledge coverage across all tasks in a project"""

    project_id = "your-project-uuid-here"

    # Get all tasks in the project
    result = supabase.table("tasks").select(
        "id, name, knowledge_coverage_score, status"
    ).eq("project_id", project_id).execute()

    if not result.data:
        print("No tasks found in project")
        return

    tasks = result.data

    # Calculate statistics
    total_tasks = len(tasks)
    linked_tasks = [t for t in tasks if t['knowledge_coverage_score'] is not None]
    avg_coverage = sum(t['knowledge_coverage_score'] for t in linked_tasks) / len(linked_tasks) if linked_tasks else 0

    print(f"Project Knowledge Report")
    print("=" * 80)
    print(f"Total tasks: {total_tasks}")
    print(f"Tasks with knowledge: {len(linked_tasks)}")
    print(f"Average coverage: {avg_coverage:.2%}")

    # Show tasks by coverage level
    high_coverage = [t for t in linked_tasks if t['knowledge_coverage_score'] >= 0.7]
    medium_coverage = [t for t in linked_tasks if 0.4 <= t['knowledge_coverage_score'] < 0.7]
    low_coverage = [t for t in linked_tasks if t['knowledge_coverage_score'] < 0.4]

    print(f"\nCoverage Distribution:")
    print(f"  High (≥70%):   {len(high_coverage)} tasks")
    print(f"  Medium (40-70%): {len(medium_coverage)} tasks")
    print(f"  Low (<40%):    {len(low_coverage)} tasks")

    if low_coverage:
        print(f"\n⚠️  Tasks needing attention:")
        for task in low_coverage[:5]:
            print(f"  • {task['name']} - {task['knowledge_coverage_score']:.2%} coverage")


# ============================================================================
# MAIN - Run examples
# ============================================================================

async def main():
    """Run example based on command line argument"""

    if len(sys.argv) < 2:
        print("Knowledge Linker Usage Examples")
        print("=" * 80)
        print("\nAvailable examples:")
        print("  1. single       - Link knowledge to a single task")
        print("  2. create       - Create task and link knowledge")
        print("  3. batch        - Batch link multiple tasks")
        print("  4. refresh      - Refresh knowledge on update")
        print("  5. coverage     - Check coverage before starting")
        print("  6. scheduler    - Scheduler integration")
        print("  7. display      - Display linked knowledge")
        print("  8. monitor      - Project knowledge monitoring")
        print("\nUsage: python knowledge_linker_usage.py <example_number>")
        return

    example = sys.argv[1]

    examples = {
        "1": example_single_task,
        "single": example_single_task,
        "2": example_create_task_with_knowledge,
        "create": example_create_task_with_knowledge,
        "3": example_batch_link,
        "batch": example_batch_link,
        "4": example_refresh_on_update,
        "refresh": example_refresh_on_update,
        "5": example_check_coverage_before_start,
        "coverage": example_check_coverage_before_start,
        "6": example_scheduler_integration,
        "scheduler": example_scheduler_integration,
        "7": example_display_task_knowledge,
        "display": example_display_task_knowledge,
        "8": example_project_knowledge_monitor,
        "monitor": example_project_knowledge_monitor,
    }

    if example not in examples:
        print(f"Unknown example: {example}")
        return

    await examples[example]()


if __name__ == "__main__":
    asyncio.run(main())
