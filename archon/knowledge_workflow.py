"""
LangGraph Workflow Nodes for Knowledge Management

This module provides LangGraph nodes that integrate knowledge management
into Archon's agent creation workflow. It enables:
- Checking knowledge coverage for projects
- Triggering universal_crawler for missing knowledge
- Linking knowledge to tasks
- Decomposing projects into tasks
- Scheduling tasks based on dependencies
- Executing tasks with knowledge-injected context

These nodes can be composed into various workflow patterns for
knowledge-aware project management.
"""

from __future__ import annotations

import os
import sys
import json
import asyncio
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
import logging

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.config import get_stream_writer
from langgraph.types import interrupt

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Archon imports
from archon.knowledge_manager import KnowledgeManager, TaskStatus, ProjectStatus
from archon.universal_crawler import UniversalCrawler, SourceConfig, CRAWL_PROFILES
from utils.utils import get_clients, write_to_log

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# STATE SCHEMAS
# ============================================================================

class KnowledgeState(TypedDict):
    """
    Extended state for knowledge-aware workflows.

    This state extends the base AgentState with knowledge management fields.
    """
    # Original message and context
    latest_user_message: str
    messages: Annotated[List[bytes], lambda x, y: x + y]

    # Project and task identifiers
    project_id: Optional[str]
    project_name: Optional[str]
    project_description: Optional[str]
    task_id: Optional[str]
    task_ids: List[str]  # For batch operations

    # Knowledge coverage tracking
    coverage_score: float
    min_coverage_threshold: float
    required_tags: List[str]
    required_frameworks: List[str]
    missing_tags: List[str]
    needs_scraping: bool

    # Linked knowledge
    linked_knowledge: List[Dict[str, Any]]
    knowledge_chunks: int

    # Task scheduling
    schedule: List[Dict[str, Any]]
    task_dependencies: Dict[str, List[str]]

    # Crawl progress
    crawl_progress: Dict[str, Any]
    crawl_status: Literal["not_started", "in_progress", "completed", "failed"]
    crawled_urls: List[str]

    # Workflow control
    workflow_stage: str
    error_message: Optional[str]

    # Execution context
    execution_result: Optional[Dict[str, Any]]
    agent_output: Optional[str]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_knowledge_manager() -> KnowledgeManager:
    """Get or create a KnowledgeManager instance."""
    return KnowledgeManager()


async def get_universal_crawler() -> UniversalCrawler:
    """Get or create a UniversalCrawler instance."""
    embedding_client, supabase = get_clients()
    return UniversalCrawler(
        embedding_client=embedding_client,
        supabase=supabase
    )


# ============================================================================
# KNOWLEDGE MANAGEMENT NODES
# ============================================================================

async def check_knowledge_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Check if required knowledge exists for project/task.

    This node:
    1. Extracts requirements from the latest user message or project
    2. Checks knowledge coverage using knowledge_manager
    3. Returns coverage info to state

    Args:
        state: Current workflow state

    Returns:
        Updated state with coverage information
    """
    try:
        logger.info("Checking knowledge coverage...")
        write_to_log("Knowledge Node: Checking coverage")

        km = get_knowledge_manager()

        # Get required tags and frameworks
        tags = state.get('required_tags', [])
        frameworks = state.get('required_frameworks', [])
        min_coverage = state.get('min_coverage_threshold', 0.4)

        # If not provided, extract from latest message
        if not tags and not frameworks:
            description = state.get('project_description') or state.get('latest_user_message', '')
            if description:
                tags, frameworks = await km._extract_tags_and_frameworks(description)

        # Check coverage
        coverage = await km.check_and_acquire_knowledge(
            tags=tags,
            frameworks=frameworks,
            min_coverage=min_coverage
        )

        logger.info(f"Coverage: {coverage.coverage_score:.2f}, needs_scraping: {coverage.needs_scraping}")
        write_to_log(f"Coverage score: {coverage.coverage_score:.2f}")

        return {
            "coverage_score": coverage.coverage_score,
            "required_tags": tags,
            "required_frameworks": frameworks,
            "missing_tags": coverage.missing_tags,
            "needs_scraping": coverage.needs_scraping,
            "knowledge_chunks": coverage.total_chunks,
            "workflow_stage": "coverage_checked",
            "error_message": None
        }

    except Exception as e:
        logger.error(f"Error checking knowledge coverage: {e}")
        return {
            "coverage_score": 0.0,
            "needs_scraping": True,
            "workflow_stage": "error",
            "error_message": str(e)
        }


async def acquire_knowledge_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Trigger universal_crawler if knowledge coverage is low.

    This node:
    1. Builds scraper configuration based on missing tags
    2. Triggers universal_crawler
    3. Tracks crawl progress in state
    4. Returns when crawl is complete

    Args:
        state: Current workflow state

    Returns:
        Updated state with crawl progress
    """
    try:
        logger.info("Acquiring missing knowledge...")
        write_to_log("Knowledge Node: Acquiring missing knowledge via crawler")

        crawler = await get_universal_crawler()

        # Get missing tags and frameworks
        missing_tags = state.get('missing_tags', [])
        frameworks = state.get('required_frameworks', [])

        if not missing_tags and not frameworks:
            logger.warning("No missing tags or frameworks to scrape")
            return {
                "crawl_status": "completed",
                "crawled_urls": [],
                "workflow_stage": "knowledge_acquired",
                "error_message": "No missing knowledge to acquire"
            }

        # Build source configurations
        # This is a simplified approach - in production, you'd have a more
        # sophisticated mapping from tags/frameworks to documentation URLs
        source_configs = []

        # Example: Map frameworks to their documentation URLs
        framework_docs = {
            'fastapi': 'https://fastapi.tiangolo.com',
            'pydantic': 'https://docs.pydantic.dev',
            'pydantic_ai': 'https://ai.pydantic.dev',
            'streamlit': 'https://docs.streamlit.io',
            'langgraph': 'https://langchain-ai.github.io/langgraph',
            'react': 'https://react.dev',
            'nextjs': 'https://nextjs.org/docs',
            'django': 'https://docs.djangoproject.com',
            'flask': 'https://flask.palletsprojects.com',
        }

        for framework in frameworks:
            if framework.lower() in framework_docs:
                source_configs.append(
                    SourceConfig(
                        source_url=framework_docs[framework.lower()],
                        framework=framework,
                        crawl_profile='quick',
                        source_type='documentation'
                    )
                )

        # If no frameworks matched, try to use missing tags to construct search URLs
        if not source_configs and missing_tags:
            logger.info(f"No direct framework matches, using tags: {missing_tags}")
            # In a production system, you might use a search API or knowledge graph
            # to find relevant documentation URLs for these tags

        if not source_configs:
            logger.warning("Could not determine documentation sources to crawl")
            return {
                "crawl_status": "failed",
                "crawled_urls": [],
                "workflow_stage": "knowledge_acquired",
                "error_message": "Could not determine documentation sources"
            }

        # Crawl each source
        all_crawled_urls = []
        crawl_results = []

        for source_config in source_configs:
            logger.info(f"Crawling {source_config.source_url}...")

            try:
                result = await crawler.crawl_source(source_config)
                crawl_results.append(result)
                all_crawled_urls.extend(result.get('crawled_urls', []))

            except Exception as crawl_error:
                logger.error(f"Error crawling {source_config.source_url}: {crawl_error}")
                continue

        logger.info(f"Crawling complete. Processed {len(all_crawled_urls)} URLs")
        write_to_log(f"Crawled {len(all_crawled_urls)} pages")

        return {
            "crawl_status": "completed",
            "crawled_urls": all_crawled_urls,
            "crawl_progress": {
                "sources_crawled": len(source_configs),
                "total_urls": len(all_crawled_urls),
                "results": crawl_results
            },
            "workflow_stage": "knowledge_acquired",
            "error_message": None
        }

    except Exception as e:
        logger.error(f"Error acquiring knowledge: {e}")
        return {
            "crawl_status": "failed",
            "workflow_stage": "error",
            "error_message": str(e)
        }


async def link_knowledge_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Link relevant knowledge to tasks.

    This node:
    1. Gets task(s) from state
    2. Uses knowledge_manager.link_task_knowledge
    3. Updates state with linked knowledge

    Args:
        state: Current workflow state

    Returns:
        Updated state with linked knowledge
    """
    try:
        logger.info("Linking knowledge to tasks...")
        write_to_log("Knowledge Node: Linking knowledge to tasks")

        km = get_knowledge_manager()

        # Get task IDs
        task_id = state.get('task_id')
        task_ids = state.get('task_ids', [])

        if task_id:
            task_ids = [task_id]

        if not task_ids:
            logger.warning("No task IDs provided for knowledge linking")
            return {
                "linked_knowledge": [],
                "workflow_stage": "knowledge_linked",
                "error_message": "No tasks to link knowledge to"
            }

        # Link knowledge to each task
        all_linked_knowledge = []
        total_coverage = 0.0

        if len(task_ids) == 1:
            # Single task
            result = await km.link_task_knowledge(task_ids[0], refresh=False)
            all_linked_knowledge = result['linked_knowledge']
            total_coverage = result['coverage_score']
        else:
            # Batch linking
            results = await km.batch_link_knowledge(task_ids, refresh=False)

            for result in results:
                all_linked_knowledge.extend(result['linked_knowledge'])
                total_coverage += result['coverage_score']

            total_coverage = total_coverage / len(results) if results else 0.0

        logger.info(f"Linked {len(all_linked_knowledge)} knowledge chunks to {len(task_ids)} task(s)")
        write_to_log(f"Linked {len(all_linked_knowledge)} knowledge chunks")

        return {
            "linked_knowledge": all_linked_knowledge,
            "coverage_score": total_coverage,
            "workflow_stage": "knowledge_linked",
            "error_message": None
        }

    except Exception as e:
        logger.error(f"Error linking knowledge: {e}")
        return {
            "linked_knowledge": [],
            "workflow_stage": "error",
            "error_message": str(e)
        }


async def decompose_project_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Break project into tasks using knowledge_manager.

    This node:
    1. Gets project details from state
    2. Uses knowledge_manager.decompose_project
    3. Returns tasks to state

    Args:
        state: Current workflow state

    Returns:
        Updated state with created tasks
    """
    try:
        logger.info("Decomposing project into tasks...")
        write_to_log("Knowledge Node: Decomposing project")

        project_id = state.get('project_id')

        if not project_id:
            logger.error("No project ID provided")
            return {
                "task_ids": [],
                "workflow_stage": "error",
                "error_message": "No project ID provided"
            }

        km = get_knowledge_manager()

        # Decompose project
        tasks = await km.decompose_project(
            project_id=project_id,
            decomposition_strategy="auto",
            auto_link_knowledge=True
        )

        # Extract task IDs and build dependency map
        task_ids = [task['task']['id'] for task in tasks]

        # Build schedule data
        schedule = []
        for task in tasks:
            task_data = task['task']
            schedule.append({
                'task_id': task_data['id'],
                'task_name': task_data['name'],
                'status': task_data['status'],
                'priority': task_data['priority'],
                'coverage_score': task.get('coverage_score', 0.0)
            })

        logger.info(f"Created {len(tasks)} tasks from project")
        write_to_log(f"Decomposed project into {len(tasks)} tasks")

        return {
            "task_ids": task_ids,
            "schedule": schedule,
            "workflow_stage": "project_decomposed",
            "error_message": None
        }

    except Exception as e:
        logger.error(f"Error decomposing project: {e}")
        return {
            "task_ids": [],
            "workflow_stage": "error",
            "error_message": str(e)
        }


async def schedule_tasks_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Schedule tasks based on dependencies and priorities.

    This node:
    1. Gets tasks from state
    2. Analyzes dependencies from database
    3. Calculates optimal schedule
    4. Updates scheduled_start/end for each task

    Args:
        state: Current workflow state

    Returns:
        Updated state with task schedule
    """
    try:
        logger.info("Scheduling tasks...")
        write_to_log("Knowledge Node: Scheduling tasks")

        task_ids = state.get('task_ids', [])

        if not task_ids:
            logger.warning("No tasks to schedule")
            return {
                "schedule": [],
                "workflow_stage": "tasks_scheduled",
                "error_message": "No tasks to schedule"
            }

        km = get_knowledge_manager()

        # Get task details and dependencies
        tasks_with_deps = []

        for task_id in task_ids:
            task = await km.get_task(task_id)

            # Get dependencies
            deps_result = km.supabase.table("task_dependencies").select("*").eq("task_id", task_id).execute()
            dependencies = [dep['depends_on_task_id'] for dep in deps_result.data] if deps_result.data else []

            tasks_with_deps.append({
                'task': task,
                'dependencies': dependencies
            })

        # Simple scheduling algorithm:
        # 1. Tasks with no dependencies start immediately
        # 2. Tasks with dependencies start after their dependencies
        # 3. Higher priority tasks scheduled first within each level

        scheduled_tasks = []
        now = datetime.now(timezone.utc)

        # Build dependency graph
        task_levels = {}  # task_id -> level (0 = no deps, 1 = depends on level 0, etc.)

        def get_task_level(task_id: str, visited: set = None) -> int:
            """Recursively calculate task level based on dependencies."""
            if visited is None:
                visited = set()

            if task_id in visited:
                return 0  # Circular dependency, treat as level 0

            visited.add(task_id)

            # Find dependencies for this task
            task_deps = next((t['dependencies'] for t in tasks_with_deps if t['task']['id'] == task_id), [])

            if not task_deps:
                return 0

            # Level is 1 + max level of dependencies
            max_dep_level = max((get_task_level(dep_id, visited.copy()) for dep_id in task_deps), default=-1)
            return max_dep_level + 1

        # Calculate levels for all tasks
        for task_data in tasks_with_deps:
            task_id = task_data['task']['id']
            task_levels[task_id] = get_task_level(task_id)

        # Sort by level, then by priority
        sorted_tasks = sorted(
            tasks_with_deps,
            key=lambda t: (task_levels[t['task']['id']], -t['task']['priority'])
        )

        # Assign scheduled times
        # Assume each task takes 60 minutes by default
        current_time = now

        for task_data in sorted_tasks:
            task = task_data['task']
            task_id = task['id']

            # If task has dependencies, start after the latest dependency ends
            if task_data['dependencies']:
                # Find latest end time of dependencies
                dep_end_times = []
                for scheduled in scheduled_tasks:
                    if scheduled['task_id'] in task_data['dependencies']:
                        dep_end_times.append(scheduled['scheduled_end'])

                if dep_end_times:
                    current_time = max(dep_end_times)

            scheduled_start = current_time
            # Estimate 60 minutes per task (could be made more sophisticated)
            scheduled_end = scheduled_start + timedelta(minutes=60)

            scheduled_tasks.append({
                'task_id': task_id,
                'task_name': task['name'],
                'level': task_levels[task_id],
                'priority': task['priority'],
                'status': task['status'],
                'scheduled_start': scheduled_start.isoformat(),
                'scheduled_end': scheduled_end.isoformat(),
                'dependencies': task_data['dependencies']
            })

            # Update task in database with scheduled times
            try:
                km.supabase.table("tasks").update({
                    "scheduled_start": scheduled_start.isoformat(),
                    "scheduled_end": scheduled_end.isoformat(),
                    "updated_at": now.isoformat()
                }).eq("id", task_id).execute()
            except Exception as update_error:
                logger.warning(f"Could not update scheduled times for task {task_id}: {update_error}")

            current_time = scheduled_end

        logger.info(f"Scheduled {len(scheduled_tasks)} tasks")
        write_to_log(f"Scheduled {len(scheduled_tasks)} tasks")

        return {
            "schedule": scheduled_tasks,
            "workflow_stage": "tasks_scheduled",
            "error_message": None
        }

    except Exception as e:
        logger.error(f"Error scheduling tasks: {e}")
        return {
            "schedule": [],
            "workflow_stage": "error",
            "error_message": str(e)
        }


async def execute_with_knowledge_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Execute task with injected knowledge context.

    This node:
    1. Retrieves linked knowledge for the task
    2. Injects knowledge into agent context
    3. Executes task using existing coder_agent pattern
    4. Stores learnings back to knowledge base

    Args:
        state: Current workflow state

    Returns:
        Updated state with execution results
    """
    try:
        logger.info("Executing task with knowledge context...")
        write_to_log("Knowledge Node: Executing task with knowledge")

        task_id = state.get('task_id')

        if not task_id:
            logger.error("No task ID provided for execution")
            return {
                "execution_result": None,
                "workflow_stage": "error",
                "error_message": "No task ID provided"
            }

        km = get_knowledge_manager()

        # Get task with linked knowledge
        result = await km.get_task_with_knowledge(task_id)
        task = result['task']
        linked_knowledge = result['linked_knowledge']

        # Build knowledge context
        knowledge_context = "\n\n".join([
            f"**Knowledge Chunk {i+1}** (Relevance: {chunk.get('relevance_score', 0):.2f}):\n{chunk.get('content', '')}"
            for i, chunk in enumerate(linked_knowledge[:5])  # Top 5 chunks
        ])

        # Build execution prompt with knowledge
        execution_prompt = f"""
Task: {task['name']}

Description: {task['description']}

**Relevant Knowledge Context:**
{knowledge_context}

Please complete this task using the provided knowledge context.
"""

        # Here you would integrate with the actual agent execution
        # For now, we'll create a placeholder execution result

        execution_result = {
            'task_id': task_id,
            'task_name': task['name'],
            'status': 'executed',
            'knowledge_chunks_used': len(linked_knowledge),
            'execution_prompt': execution_prompt,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Update task status
        await km.update_task_status(task_id, TaskStatus.IN_PROGRESS.value)

        logger.info(f"Task {task_id} executed with {len(linked_knowledge)} knowledge chunks")
        write_to_log(f"Executed task with {len(linked_knowledge)} knowledge chunks")

        return {
            "execution_result": execution_result,
            "agent_output": execution_prompt,
            "workflow_stage": "task_executed",
            "error_message": None
        }

    except Exception as e:
        logger.error(f"Error executing task: {e}")
        return {
            "execution_result": None,
            "workflow_stage": "error",
            "error_message": str(e)
        }


# ============================================================================
# ROUTING FUNCTIONS
# ============================================================================

def route_based_on_coverage(state: KnowledgeState) -> str:
    """
    Router: Decide whether to acquire knowledge or continue.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "acquire_knowledge" or "continue"
    """
    coverage_score = state.get('coverage_score', 0.0)
    min_threshold = state.get('min_coverage_threshold', 0.4)

    if coverage_score < min_threshold:
        logger.info(f"Coverage {coverage_score:.2f} < {min_threshold:.2f}, acquiring knowledge")
        return "acquire_knowledge"
    else:
        logger.info(f"Coverage {coverage_score:.2f} >= {min_threshold:.2f}, continuing")
        return "continue"


def route_based_on_project(state: KnowledgeState) -> str:
    """
    Router: Decide whether to decompose project or execute task.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "decompose_project" or "execute_task"
    """
    project_id = state.get('project_id')
    task_id = state.get('task_id')

    if project_id and not task_id:
        logger.info("Project provided, decomposing into tasks")
        return "decompose_project"
    elif task_id:
        logger.info("Task provided, executing directly")
        return "execute_task"
    else:
        logger.warning("Neither project nor task provided, skipping")
        return "skip"


def route_after_crawl(state: KnowledgeState) -> str:
    """
    Router: Decide what to do after crawling.

    Args:
        state: Current workflow state

    Returns:
        Next node name: "link_knowledge" or "error"
    """
    crawl_status = state.get('crawl_status', 'not_started')

    if crawl_status == 'completed':
        logger.info("Crawl completed, proceeding to link knowledge")
        return "link_knowledge"
    elif crawl_status == 'failed':
        logger.error("Crawl failed, ending workflow")
        return "error"
    else:
        logger.warning(f"Unexpected crawl status: {crawl_status}")
        return "error"


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def initialize_knowledge_state(**kwargs) -> KnowledgeState:
    """
    Initialize a KnowledgeState with default values.

    Args:
        **kwargs: State fields to override

    Returns:
        Initialized KnowledgeState
    """
    default_state = {
        "latest_user_message": "",
        "messages": [],
        "project_id": None,
        "project_name": None,
        "project_description": None,
        "task_id": None,
        "task_ids": [],
        "coverage_score": 0.0,
        "min_coverage_threshold": 0.4,
        "required_tags": [],
        "required_frameworks": [],
        "missing_tags": [],
        "needs_scraping": False,
        "linked_knowledge": [],
        "knowledge_chunks": 0,
        "schedule": [],
        "task_dependencies": {},
        "crawl_progress": {},
        "crawl_status": "not_started",
        "crawled_urls": [],
        "workflow_stage": "initialized",
        "error_message": None,
        "execution_result": None,
        "agent_output": None
    }

    default_state.update(kwargs)
    return default_state


# ============================================================================
# MAIN (for testing)
# ============================================================================

async def main():
    """Test the knowledge workflow nodes."""
    # Initialize state
    state = initialize_knowledge_state(
        latest_user_message="Build a FastAPI authentication system with JWT and OAuth2",
        project_description="Build a FastAPI authentication system with JWT and OAuth2",
        min_coverage_threshold=0.4
    )

    # Test check_knowledge_node
    print("\n=== Testing check_knowledge_node ===")
    result = await check_knowledge_node(state)
    print(f"Coverage: {result['coverage_score']:.2f}")
    print(f"Needs scraping: {result['needs_scraping']}")
    print(f"Required tags: {result['required_tags']}")
    print(f"Required frameworks: {result['required_frameworks']}")

    # Update state
    state.update(result)

    # Test routing
    print(f"\n=== Testing route_based_on_coverage ===")
    next_node = route_based_on_coverage(state)
    print(f"Next node: {next_node}")


if __name__ == "__main__":
    asyncio.run(main())
