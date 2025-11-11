"""
LangGraph Knowledge Integration Examples

This file demonstrates various usage patterns for the LangGraph
knowledge management integration in Archon.

Run individual examples with:
    python examples/langgraph_integration_examples.py --example 1
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.knowledge_manager import KnowledgeManager
from archon.archon_graph_enhanced import (
    run_knowledge_workflow,
    run_simple_knowledge_workflow,
    run_task_execution_workflow,
    run_project_planning_workflow
)
from archon.integrated_workflow import run_integrated_workflow
from archon.knowledge_workflow import (
    initialize_knowledge_state,
    check_knowledge_node,
    acquire_knowledge_node,
    link_knowledge_node
)


# ============================================================================
# EXAMPLE 1: BASIC KNOWLEDGE WORKFLOW
# ============================================================================

async def example_1_basic_workflow():
    """
    Example 1: Run basic knowledge workflow for a new project.

    This shows:
    - Creating a project
    - Checking knowledge coverage
    - Automatic task creation
    - Task scheduling
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Knowledge Workflow")
    print("="*70 + "\n")

    # Run the workflow
    result = await run_knowledge_workflow(
        project_description="Build a REST API with FastAPI, PostgreSQL, and JWT authentication",
        project_name="FastAPI REST API",
        min_coverage=0.4,
        thread_id="example-1"
    )

    # Display results
    print(f"✓ Workflow Stage: {result['workflow_stage']}")
    print(f"✓ Knowledge Coverage: {result['coverage_score']:.2%}")
    print(f"✓ Tasks Created: {len(result['task_ids'])}")
    print(f"✓ Crawl Status: {result['crawl_status']}")

    if result.get('schedule'):
        print("\nTask Schedule:")
        for task in result['schedule'][:5]:  # Show first 5
            print(f"  - {task['task_name']} (Priority: {task['priority']})")


# ============================================================================
# EXAMPLE 2: LINK KNOWLEDGE TO EXISTING TASK
# ============================================================================

async def example_2_link_knowledge():
    """
    Example 2: Link knowledge to an existing task.

    This shows:
    - Creating a task manually
    - Linking relevant knowledge chunks
    - Viewing linked knowledge
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Link Knowledge to Task")
    print("="*70 + "\n")

    # First create a project and task
    km = KnowledgeManager()

    project = await km.create_project(
        name="Authentication System",
        description="Build JWT authentication with FastAPI",
        auto_discover=False
    )
    print(f"✓ Created project: {project['project']['id']}")

    task = await km.create_task(
        project_id=project['project']['id'],
        name="Implement JWT Token Generation",
        description="Create endpoints for generating and validating JWT tokens",
        auto_link=False  # We'll link manually
    )
    task_id = task['task']['id']
    print(f"✓ Created task: {task_id}")

    # Now link knowledge
    result = await run_simple_knowledge_workflow(
        task_id=task_id,
        thread_id="example-2"
    )

    print(f"\n✓ Linked {len(result['linked_knowledge'])} knowledge chunks")
    print(f"✓ Coverage Score: {result['coverage_score']:.2%}")

    # Show some linked knowledge
    if result['linked_knowledge']:
        print("\nTop Knowledge Chunks:")
        for i, chunk in enumerate(result['linked_knowledge'][:3], 1):
            print(f"\n  {i}. Relevance: {chunk.get('similarity', 0):.2%}")
            content = chunk.get('content', '')[:100]
            print(f"     {content}...")


# ============================================================================
# EXAMPLE 3: EXECUTE TASK WITH KNOWLEDGE
# ============================================================================

async def example_3_execute_with_knowledge():
    """
    Example 3: Execute a task with knowledge context injected.

    This shows:
    - Creating a task
    - Running execution workflow
    - Knowledge injected into agent context
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Execute Task with Knowledge Context")
    print("="*70 + "\n")

    # Create project and task
    km = KnowledgeManager()

    project = await km.create_project(
        name="FastAPI OAuth2",
        description="Implement OAuth2 authentication flow",
        auto_discover=False
    )

    task = await km.create_task(
        project_id=project['project']['id'],
        name="Setup OAuth2 Password Flow",
        description="Implement OAuth2 password grant flow with FastAPI",
        auto_link=False
    )

    task_id = task['task']['id']
    print(f"✓ Created task: {task_id}")

    # Execute with knowledge
    result = await run_task_execution_workflow(
        task_id=task_id,
        min_coverage=0.5,
        thread_id="example-3"
    )

    print(f"\n✓ Execution Stage: {result['workflow_stage']}")
    print(f"✓ Coverage Score: {result['coverage_score']:.2%}")

    if result.get('execution_result'):
        exec_result = result['execution_result']
        print(f"\n✓ Task: {exec_result['task_name']}")
        print(f"✓ Knowledge Chunks Used: {exec_result['knowledge_chunks_used']}")
        print(f"✓ Status: {exec_result['status']}")


# ============================================================================
# EXAMPLE 4: PROJECT PLANNING WORKFLOW
# ============================================================================

async def example_4_project_planning():
    """
    Example 4: Complete project planning with knowledge.

    This shows:
    - Project decomposition into tasks
    - Automatic knowledge linking
    - Dependency-based scheduling
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Project Planning Workflow")
    print("="*70 + "\n")

    # Create project
    km = KnowledgeManager()

    project = await km.create_project(
        name="E-Commerce API",
        description="""
        Build a complete e-commerce REST API with:
        - Product catalog management
        - User authentication and authorization
        - Shopping cart functionality
        - Order processing
        - Payment integration
        - Admin dashboard
        """,
        priority=1,
        auto_discover=False
    )

    project_id = project['project']['id']
    print(f"✓ Created project: {project_id}")

    # Run planning workflow
    result = await run_project_planning_workflow(
        project_id=project_id,
        min_coverage=0.4,
        thread_id="example-4"
    )

    print(f"\n✓ Planning Stage: {result['workflow_stage']}")
    print(f"✓ Coverage Score: {result['coverage_score']:.2%}")
    print(f"✓ Tasks Created: {len(result['task_ids'])}")

    # Display schedule
    if result.get('schedule'):
        print("\nProject Schedule:")
        for task in result['schedule']:
            level = task.get('level', 0)
            indent = "  " * level
            print(f"{indent}• {task['task_name']}")
            print(f"{indent}  Priority: {task['priority']} | Level: {level}")


# ============================================================================
# EXAMPLE 5: INTEGRATED WORKFLOW - CONDITIONAL
# ============================================================================

async def example_5_integrated_conditional():
    """
    Example 5: Integrated workflow with automatic intent detection.

    This shows:
    - Intent detection from user message
    - Automatic routing to appropriate workflow
    - Handling different types of requests
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Integrated Workflow - Conditional Routing")
    print("="*70 + "\n")

    # Test different types of requests
    test_cases = [
        ("Create an agent for web scraping", "agent"),
        ("Plan a project to build a dashboard", "project"),
        ("Create an agent and plan a project for authentication", "combined")
    ]

    for message, expected in test_cases:
        print(f"\nUser: '{message}'")
        print(f"Expected: {expected}")

        result = await run_integrated_workflow(
            user_message=message,
            workflow_type="conditional",
            thread_id=f"example-5-{expected}"
        )

        print(f"✓ Detected Mode: {result.get('workflow_mode')}")
        print(f"✓ Agent Created: {result.get('agent_created')}")
        print(f"✓ Project Created: {result.get('project_created')}")


# ============================================================================
# EXAMPLE 6: USING INDIVIDUAL NODES
# ============================================================================

async def example_6_individual_nodes():
    """
    Example 6: Build custom workflow using individual nodes.

    This shows:
    - Using nodes directly
    - Custom workflow composition
    - Manual state management
    """
    print("\n" + "="*70)
    print("EXAMPLE 6: Custom Workflow with Individual Nodes")
    print("="*70 + "\n")

    # Initialize state
    state = initialize_knowledge_state(
        project_description="Build a GraphQL API with Strawberry and FastAPI",
        min_coverage_threshold=0.4
    )

    print("Step 1: Check Knowledge Coverage")
    coverage_result = await check_knowledge_node(state)
    state.update(coverage_result)

    print(f"✓ Coverage: {state['coverage_score']:.2%}")
    print(f"✓ Needs Scraping: {state['needs_scraping']}")
    print(f"✓ Required Tags: {state['required_tags']}")

    # Conditionally acquire knowledge
    if state['needs_scraping']:
        print("\nStep 2: Acquire Missing Knowledge")
        acquire_result = await acquire_knowledge_node(state)
        state.update(acquire_result)

        print(f"✓ Crawl Status: {state['crawl_status']}")
        print(f"✓ URLs Crawled: {len(state.get('crawled_urls', []))}")
    else:
        print("\nStep 2: Skipped (Coverage Sufficient)")

    print("\n✓ Custom workflow completed!")


# ============================================================================
# EXAMPLE 7: BATCH OPERATIONS
# ============================================================================

async def example_7_batch_operations():
    """
    Example 7: Batch operations for efficiency.

    This shows:
    - Creating multiple tasks
    - Batch linking knowledge
    - Parallel processing
    """
    print("\n" + "="*70)
    print("EXAMPLE 7: Batch Operations")
    print("="*70 + "\n")

    km = KnowledgeManager()

    # Create project
    project = await km.create_project(
        name="Microservices Architecture",
        description="Build microservices with FastAPI",
        auto_discover=False
    )

    project_id = project['project']['id']
    print(f"✓ Created project: {project_id}")

    # Create multiple tasks
    task_definitions = [
        {"name": "User Service", "description": "Microservice for user management"},
        {"name": "Product Service", "description": "Microservice for product catalog"},
        {"name": "Order Service", "description": "Microservice for order processing"},
        {"name": "Payment Service", "description": "Microservice for payment processing"},
        {"name": "API Gateway", "description": "API gateway for routing requests"}
    ]

    print(f"\nCreating {len(task_definitions)} tasks...")
    tasks = await km.batch_create_tasks(
        project_id=project_id,
        task_definitions=task_definitions,
        auto_link=False
    )

    task_ids = [task['task']['id'] for task in tasks]
    print(f"✓ Created {len(tasks)} tasks")

    # Batch link knowledge
    print("\nLinking knowledge to all tasks...")
    link_results = await km.batch_link_knowledge(task_ids)

    total_links = sum(result['links_created'] for result in link_results)
    avg_coverage = sum(result['coverage_score'] for result in link_results) / len(link_results)

    print(f"✓ Total Links Created: {total_links}")
    print(f"✓ Average Coverage: {avg_coverage:.2%}")


# ============================================================================
# EXAMPLE 8: COVERAGE CHECKING
# ============================================================================

async def example_8_coverage_checking():
    """
    Example 8: Check knowledge coverage for different topics.

    This shows:
    - Batch coverage checking
    - Identifying knowledge gaps
    - Coverage analysis
    """
    print("\n" + "="*70)
    print("EXAMPLE 8: Knowledge Coverage Analysis")
    print("="*70 + "\n")

    km = KnowledgeManager()

    # Check coverage for different technology stacks
    tech_stacks = [
        (["authentication", "jwt", "oauth2"], ["fastapi", "pydantic"]),
        (["websockets", "real-time"], ["fastapi", "socketio"]),
        (["graphql", "api"], ["strawberry", "fastapi"]),
        (["machine-learning", "inference"], ["pytorch", "fastapi"]),
    ]

    print("Checking coverage for different tech stacks...\n")

    coverages = await km.batch_check_coverage(tech_stacks, min_coverage=0.4)

    for (tags, frameworks), coverage in zip(tech_stacks, coverages):
        print(f"Stack: {frameworks[0] if frameworks else 'N/A'}")
        print(f"  Tags: {', '.join(tags)}")
        print(f"  Coverage: {coverage.coverage_score:.2%}")
        print(f"  Chunks: {coverage.total_chunks}")
        print(f"  Needs Scraping: {coverage.needs_scraping}")
        if coverage.missing_tags:
            print(f"  Missing: {', '.join(coverage.missing_tags)}")
        print()


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run examples based on command line argument."""
    import argparse

    parser = argparse.ArgumentParser(description="LangGraph Integration Examples")
    parser.add_argument(
        "--example",
        type=int,
        choices=range(1, 9),
        help="Example number to run (1-8), omit to run all"
    )

    args = parser.parse_args()

    examples = {
        1: ("Basic Knowledge Workflow", example_1_basic_workflow),
        2: ("Link Knowledge to Task", example_2_link_knowledge),
        3: ("Execute with Knowledge", example_3_execute_with_knowledge),
        4: ("Project Planning", example_4_project_planning),
        5: ("Integrated Conditional", example_5_integrated_conditional),
        6: ("Individual Nodes", example_6_individual_nodes),
        7: ("Batch Operations", example_7_batch_operations),
        8: ("Coverage Checking", example_8_coverage_checking)
    }

    if args.example:
        # Run specific example
        name, func = examples[args.example]
        print(f"\n🚀 Running Example {args.example}: {name}")
        await func()
    else:
        # Run all examples
        print("\n🚀 Running All Examples")
        for num, (name, func) in examples.items():
            try:
                await func()
                print(f"\n✅ Example {num} completed successfully")
            except Exception as e:
                print(f"\n❌ Example {num} failed: {e}")

    print("\n" + "="*70)
    print("✨ Examples Complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
