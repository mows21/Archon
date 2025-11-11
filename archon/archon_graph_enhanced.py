"""
Enhanced LangGraph Workflow with Knowledge Management

This module provides a complete knowledge-aware workflow that integrates
knowledge management into Archon's project and task execution.

Workflow:
    1. Check knowledge coverage
    2. Acquire knowledge if needed (via universal_crawler)
    3. Link knowledge to tasks
    4. Decompose project into tasks
    5. Schedule tasks based on dependencies
    6. Execute tasks with knowledge context
    7. Store learnings

The workflow can be used standalone or integrated with the existing
archon_graph.py agent creation workflow.
"""

from __future__ import annotations

import os
import sys
from typing import Literal

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import knowledge workflow nodes
from archon.knowledge_workflow import (
    KnowledgeState,
    check_knowledge_node,
    acquire_knowledge_node,
    link_knowledge_node,
    decompose_project_node,
    schedule_tasks_node,
    execute_with_knowledge_node,
    route_based_on_coverage,
    route_based_on_project,
    route_after_crawl,
    initialize_knowledge_state
)

from utils.utils import write_to_log


# ============================================================================
# KNOWLEDGE WORKFLOW GRAPH
# ============================================================================

def build_knowledge_workflow() -> StateGraph:
    """
    Build the complete knowledge management workflow graph.

    This workflow:
    1. Checks knowledge coverage
    2. Acquires missing knowledge if needed
    3. Links knowledge to tasks
    4. Decomposes project into tasks
    5. Schedules tasks
    6. Executes tasks with knowledge context

    Returns:
        Compiled LangGraph workflow
    """
    # Create graph
    graph = StateGraph(KnowledgeState)

    # Add nodes
    graph.add_node("check_knowledge", check_knowledge_node)
    graph.add_node("acquire_knowledge", acquire_knowledge_node)
    graph.add_node("link_knowledge", link_knowledge_node)
    graph.add_node("decompose_project", decompose_project_node)
    graph.add_node("schedule_tasks", schedule_tasks_node)
    graph.add_node("execute_with_knowledge", execute_with_knowledge_node)

    # Set entry point
    graph.set_entry_point("check_knowledge")

    # Add conditional routing from check_knowledge
    graph.add_conditional_edges(
        "check_knowledge",
        route_based_on_coverage,
        {
            "acquire_knowledge": "acquire_knowledge",
            "continue": "decompose_project"
        }
    )

    # After acquiring knowledge, link it
    graph.add_edge("acquire_knowledge", "link_knowledge")

    # After linking, decompose project
    graph.add_edge("link_knowledge", "decompose_project")

    # After decomposing, schedule tasks
    graph.add_edge("decompose_project", "schedule_tasks")

    # After scheduling, execute (optional - can end here for planning only)
    graph.add_edge("schedule_tasks", END)

    # Optional execution path (if task_id provided)
    # graph.add_edge("schedule_tasks", "execute_with_knowledge")
    # graph.add_edge("execute_with_knowledge", END)

    return graph


def build_simple_knowledge_workflow() -> StateGraph:
    """
    Build a simplified knowledge workflow for quick operations.

    This workflow:
    1. Checks knowledge coverage
    2. Links existing knowledge (no crawling)
    3. Ends

    Useful for tasks where you just want to link existing knowledge
    without triggering the crawler.

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(KnowledgeState)

    # Add nodes
    graph.add_node("check_knowledge", check_knowledge_node)
    graph.add_node("link_knowledge", link_knowledge_node)

    # Set entry point
    graph.set_entry_point("check_knowledge")

    # Always link knowledge (no acquisition)
    graph.add_edge("check_knowledge", "link_knowledge")
    graph.add_edge("link_knowledge", END)

    return graph


def build_task_execution_workflow() -> StateGraph:
    """
    Build a workflow focused on executing a single task with knowledge.

    This workflow:
    1. Checks knowledge coverage for the task
    2. Acquires knowledge if needed
    3. Links knowledge to the task
    4. Executes the task with knowledge context

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(KnowledgeState)

    # Add nodes
    graph.add_node("check_knowledge", check_knowledge_node)
    graph.add_node("acquire_knowledge", acquire_knowledge_node)
    graph.add_node("link_knowledge", link_knowledge_node)
    graph.add_node("execute_with_knowledge", execute_with_knowledge_node)

    # Set entry point
    graph.set_entry_point("check_knowledge")

    # Conditional routing based on coverage
    graph.add_conditional_edges(
        "check_knowledge",
        route_based_on_coverage,
        {
            "acquire_knowledge": "acquire_knowledge",
            "continue": "link_knowledge"
        }
    )

    # After acquiring, link
    graph.add_edge("acquire_knowledge", "link_knowledge")

    # After linking, execute
    graph.add_edge("link_knowledge", "execute_with_knowledge")
    graph.add_edge("execute_with_knowledge", END)

    return graph


def build_project_planning_workflow() -> StateGraph:
    """
    Build a workflow focused on project planning without execution.

    This workflow:
    1. Checks knowledge coverage
    2. Acquires knowledge if needed
    3. Decomposes project into tasks
    4. Links knowledge to all tasks
    5. Schedules tasks

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(KnowledgeState)

    # Add nodes
    graph.add_node("check_knowledge", check_knowledge_node)
    graph.add_node("acquire_knowledge", acquire_knowledge_node)
    graph.add_node("decompose_project", decompose_project_node)
    graph.add_node("link_knowledge", link_knowledge_node)
    graph.add_node("schedule_tasks", schedule_tasks_node)

    # Set entry point
    graph.set_entry_point("check_knowledge")

    # Conditional routing based on coverage
    graph.add_conditional_edges(
        "check_knowledge",
        route_based_on_coverage,
        {
            "acquire_knowledge": "acquire_knowledge",
            "continue": "decompose_project"
        }
    )

    # After acquiring, decompose
    graph.add_edge("acquire_knowledge", "decompose_project")

    # After decomposing, link knowledge
    graph.add_edge("decompose_project", "link_knowledge")

    # After linking, schedule
    graph.add_edge("link_knowledge", "schedule_tasks")

    # End after scheduling
    graph.add_edge("schedule_tasks", END)

    return graph


# ============================================================================
# COMPILED WORKFLOWS
# ============================================================================

# Main knowledge workflow (with memory)
memory = MemorySaver()
knowledge_workflow = build_knowledge_workflow().compile(checkpointer=memory)

# Simple workflow (no memory needed for quick operations)
simple_knowledge_workflow = build_simple_knowledge_workflow().compile()

# Task execution workflow (with memory)
task_execution_workflow = build_task_execution_workflow().compile(checkpointer=memory)

# Project planning workflow (with memory)
project_planning_workflow = build_project_planning_workflow().compile(checkpointer=memory)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def run_knowledge_workflow(
    project_description: str,
    project_name: str = "New Project",
    min_coverage: float = 0.4,
    thread_id: str = "default"
) -> dict:
    """
    Run the complete knowledge workflow for a project.

    Args:
        project_description: Description of the project
        project_name: Name of the project
        min_coverage: Minimum knowledge coverage threshold (0-1)
        thread_id: Thread ID for checkpointing

    Returns:
        Final state of the workflow
    """
    write_to_log(f"Running knowledge workflow for: {project_name}")

    # Initialize state
    initial_state = initialize_knowledge_state(
        latest_user_message=project_description,
        project_name=project_name,
        project_description=project_description,
        min_coverage_threshold=min_coverage
    )

    # Run workflow
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await knowledge_workflow.ainvoke(initial_state, config)

    return final_state


async def run_simple_knowledge_workflow(
    task_id: str,
    thread_id: str = "default"
) -> dict:
    """
    Run the simple knowledge workflow to link existing knowledge to a task.

    Args:
        task_id: Task UUID
        thread_id: Thread ID

    Returns:
        Final state of the workflow
    """
    write_to_log(f"Running simple knowledge workflow for task: {task_id}")

    # Initialize state
    initial_state = initialize_knowledge_state(
        task_id=task_id
    )

    # Run workflow
    final_state = await simple_knowledge_workflow.ainvoke(initial_state)

    return final_state


async def run_task_execution_workflow(
    task_id: str,
    min_coverage: float = 0.4,
    thread_id: str = "default"
) -> dict:
    """
    Run the task execution workflow with knowledge injection.

    Args:
        task_id: Task UUID
        min_coverage: Minimum knowledge coverage threshold
        thread_id: Thread ID for checkpointing

    Returns:
        Final state of the workflow
    """
    write_to_log(f"Running task execution workflow for: {task_id}")

    # Initialize state
    initial_state = initialize_knowledge_state(
        task_id=task_id,
        min_coverage_threshold=min_coverage
    )

    # Run workflow
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await task_execution_workflow.ainvoke(initial_state, config)

    return final_state


async def run_project_planning_workflow(
    project_id: str,
    min_coverage: float = 0.4,
    thread_id: str = "default"
) -> dict:
    """
    Run the project planning workflow to create and schedule tasks.

    Args:
        project_id: Project UUID
        min_coverage: Minimum knowledge coverage threshold
        thread_id: Thread ID for checkpointing

    Returns:
        Final state of the workflow
    """
    write_to_log(f"Running project planning workflow for: {project_id}")

    # Initialize state
    initial_state = initialize_knowledge_state(
        project_id=project_id,
        min_coverage_threshold=min_coverage
    )

    # Run workflow
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await project_planning_workflow.ainvoke(initial_state, config)

    return final_state


# ============================================================================
# WORKFLOW VISUALIZATION
# ============================================================================

def visualize_workflow(workflow_type: Literal["full", "simple", "execution", "planning"] = "full"):
    """
    Generate a visual representation of the workflow.

    Args:
        workflow_type: Type of workflow to visualize

    Returns:
        Mermaid diagram string
    """
    if workflow_type == "full":
        return """
graph TD
    START([Start]) --> CHECK[Check Knowledge Coverage]
    CHECK -->|Coverage < Threshold| ACQUIRE[Acquire Knowledge]
    CHECK -->|Coverage OK| DECOMPOSE[Decompose Project]
    ACQUIRE --> LINK[Link Knowledge]
    LINK --> DECOMPOSE
    DECOMPOSE --> SCHEDULE[Schedule Tasks]
    SCHEDULE --> END([End])

    style CHECK fill:#4A90E2
    style ACQUIRE fill:#E24A4A
    style LINK fill:#4AE2A8
    style DECOMPOSE fill:#E2A84A
    style SCHEDULE fill:#A84AE2
"""
    elif workflow_type == "simple":
        return """
graph TD
    START([Start]) --> CHECK[Check Knowledge Coverage]
    CHECK --> LINK[Link Knowledge]
    LINK --> END([End])

    style CHECK fill:#4A90E2
    style LINK fill:#4AE2A8
"""
    elif workflow_type == "execution":
        return """
graph TD
    START([Start]) --> CHECK[Check Knowledge Coverage]
    CHECK -->|Coverage < Threshold| ACQUIRE[Acquire Knowledge]
    CHECK -->|Coverage OK| LINK[Link Knowledge]
    ACQUIRE --> LINK
    LINK --> EXECUTE[Execute Task with Knowledge]
    EXECUTE --> END([End])

    style CHECK fill:#4A90E2
    style ACQUIRE fill:#E24A4A
    style LINK fill:#4AE2A8
    style EXECUTE fill:#A84AE2
"""
    elif workflow_type == "planning":
        return """
graph TD
    START([Start]) --> CHECK[Check Knowledge Coverage]
    CHECK -->|Coverage < Threshold| ACQUIRE[Acquire Knowledge]
    CHECK -->|Coverage OK| DECOMPOSE[Decompose Project]
    ACQUIRE --> DECOMPOSE
    DECOMPOSE --> LINK[Link Knowledge]
    LINK --> SCHEDULE[Schedule Tasks]
    SCHEDULE --> END([End])

    style CHECK fill:#4A90E2
    style ACQUIRE fill:#E24A4A
    style DECOMPOSE fill:#E2A84A
    style LINK fill:#4AE2A8
    style SCHEDULE fill:#A84AE2
"""


# ============================================================================
# MAIN (for testing)
# ============================================================================

async def main():
    """Test the enhanced knowledge workflow."""
    import asyncio
    from archon.knowledge_manager import KnowledgeManager

    # Initialize knowledge manager
    km = KnowledgeManager()

    # Test 1: Create a project and run full workflow
    print("\n=== Test 1: Full Knowledge Workflow ===")

    project_result = await km.create_project(
        name="FastAPI Auth System",
        description="Build a complete authentication system with FastAPI, JWT tokens, OAuth2, and PostgreSQL",
        priority=1,
        auto_discover=False  # We'll use the workflow instead
    )

    project_id = project_result['project']['id']
    print(f"Created project: {project_id}")

    # Run knowledge workflow
    final_state = await run_project_planning_workflow(
        project_id=project_id,
        min_coverage=0.4,
        thread_id="test-1"
    )

    print(f"\nWorkflow Stage: {final_state['workflow_stage']}")
    print(f"Coverage Score: {final_state['coverage_score']:.2f}")
    print(f"Tasks Created: {len(final_state['task_ids'])}")
    print(f"Crawl Status: {final_state['crawl_status']}")

    # Print schedule
    if final_state.get('schedule'):
        print("\n=== Task Schedule ===")
        for task in final_state['schedule']:
            print(f"- {task['task_name']} (Priority: {task['priority']}, Level: {task.get('level', 0)})")

    # Test 2: Simple workflow for existing task
    if final_state.get('task_ids'):
        print("\n=== Test 2: Simple Workflow for Task ===")
        task_id = final_state['task_ids'][0]

        simple_state = await run_simple_knowledge_workflow(
            task_id=task_id,
            thread_id="test-2"
        )

        print(f"Linked Knowledge: {len(simple_state['linked_knowledge'])} chunks")
        print(f"Coverage Score: {simple_state['coverage_score']:.2f}")

    # Print visualization
    print("\n=== Workflow Visualization ===")
    print(visualize_workflow("full"))


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
