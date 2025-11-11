"""
Integrated Workflows: Combining Agent Creation with Knowledge Management

This module demonstrates how to integrate Archon's knowledge management
workflow with the existing agent creation workflow from archon_graph.py.

Three integration patterns are provided:
1. Sequential: Agent creation → Project management
2. Parallel: Both workflows run in parallel branches
3. Conditional: Route based on user intent

Each pattern serves different use cases and can be adapted for your needs.
"""

from __future__ import annotations

import os
import sys
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal

# LangGraph imports
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import existing workflows
from archon.archon_graph import (
    AgentState,
    define_scope_with_reasoner,
    advisor_with_examples,
    coder_agent,
    get_next_user_message,
    route_user_message,
    refine_prompt,
    refine_tools,
    refine_agent,
    finish_conversation
)

# Import knowledge workflows
from archon.knowledge_workflow import (
    KnowledgeState,
    check_knowledge_node,
    acquire_knowledge_node,
    link_knowledge_node,
    decompose_project_node,
    schedule_tasks_node,
    execute_with_knowledge_node,
    route_based_on_coverage
)

from archon.knowledge_manager import KnowledgeManager

from utils.utils import write_to_log


# ============================================================================
# COMBINED STATE SCHEMA
# ============================================================================

class CombinedState(TypedDict):
    """
    Combined state that includes both agent creation and knowledge management.

    This allows workflows to access fields from both systems.
    """
    # From AgentState (agent creation)
    latest_user_message: str
    messages: Annotated[List[bytes], lambda x, y: x + y]
    scope: str
    advisor_output: str
    file_list: List[str]
    refined_prompt: str
    refined_tools: str
    refined_agent: str

    # From KnowledgeState (knowledge management)
    project_id: Optional[str]
    project_name: Optional[str]
    project_description: Optional[str]
    task_id: Optional[str]
    task_ids: List[str]
    coverage_score: float
    min_coverage_threshold: float
    required_tags: List[str]
    required_frameworks: List[str]
    linked_knowledge: List[Dict[str, Any]]
    schedule: List[Dict[str, Any]]
    crawl_status: str

    # Integration control
    workflow_mode: Literal["agent_only", "project_only", "combined"]
    create_project_after_agent: bool
    agent_created: bool
    project_created: bool


# ============================================================================
# INTEGRATION PATTERN 1: SEQUENTIAL WORKFLOW
# ============================================================================

def build_sequential_workflow() -> StateGraph:
    """
    Sequential integration: Agent creation → Project management

    Flow:
    1. User requests an agent
    2. Agent is created using existing archon_graph workflow
    3. Ask user if they want to create a project
    4. If yes, run knowledge workflow to create project and tasks
    5. Generated agent code is linked to the project

    Use case: User wants to create an agent and then use it in a project

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(CombinedState)

    # ===== PHASE 1: AGENT CREATION =====

    # Add agent creation nodes
    graph.add_node("define_scope", define_scope_with_reasoner)
    graph.add_node("advisor", advisor_with_examples)
    graph.add_node("coder", coder_agent)
    graph.add_node("get_user_message", get_next_user_message)
    graph.add_node("refine_prompt", refine_prompt)
    graph.add_node("refine_tools", refine_tools)
    graph.add_node("refine_agent", refine_agent)
    graph.add_node("finish_agent", finish_conversation)

    # ===== PHASE 2: PROJECT CREATION =====

    # Add knowledge nodes
    graph.add_node("ask_create_project", ask_create_project_node)
    graph.add_node("create_project", create_project_from_agent_node)
    graph.add_node("check_knowledge", check_knowledge_node)
    graph.add_node("acquire_knowledge", acquire_knowledge_node)
    graph.add_node("decompose_project", decompose_project_node)
    graph.add_node("schedule_tasks", schedule_tasks_node)
    graph.add_node("link_agent_to_project", link_agent_to_project_node)

    # ===== EDGES FOR PHASE 1 =====

    graph.set_entry_point("define_scope")
    graph.add_edge(START, "advisor")
    graph.add_edge("define_scope", "coder")
    graph.add_edge("advisor", "coder")
    graph.add_edge("coder", "get_user_message")

    graph.add_conditional_edges(
        "get_user_message",
        route_user_message,
        ["coder", "finish_agent", "refine_prompt", "refine_tools", "refine_agent"]
    )

    graph.add_edge("refine_prompt", "coder")
    graph.add_edge("refine_tools", "coder")
    graph.add_edge("refine_agent", "coder")

    # Instead of ending, ask about project
    graph.add_edge("finish_agent", "ask_create_project")

    # ===== EDGES FOR PHASE 2 =====

    graph.add_conditional_edges(
        "ask_create_project",
        route_create_project,
        {
            "yes": "create_project",
            "no": END
        }
    )

    graph.add_edge("create_project", "check_knowledge")

    graph.add_conditional_edges(
        "check_knowledge",
        route_based_on_coverage,
        {
            "acquire_knowledge": "acquire_knowledge",
            "continue": "decompose_project"
        }
    )

    graph.add_edge("acquire_knowledge", "decompose_project")
    graph.add_edge("decompose_project", "schedule_tasks")
    graph.add_edge("schedule_tasks", "link_agent_to_project")
    graph.add_edge("link_agent_to_project", END)

    return graph


# ============================================================================
# INTEGRATION PATTERN 2: PARALLEL WORKFLOW
# ============================================================================

def build_parallel_workflow() -> StateGraph:
    """
    Parallel integration: Both workflows run simultaneously

    Flow:
    1. User provides request
    2. Parse intent (agent vs project vs both)
    3. Route to appropriate branch(es)
    4. Agent creation and project planning happen in parallel
    5. Merge results at the end

    Use case: User wants both an agent and a project created simultaneously

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(CombinedState)

    # Add routing node
    graph.add_node("parse_intent", parse_user_intent_node)

    # Add agent creation branch
    graph.add_node("agent_branch", agent_creation_branch_node)

    # Add project creation branch
    graph.add_node("project_branch", project_creation_branch_node)

    # Add merge node
    graph.add_node("merge_results", merge_results_node)

    # Set entry point
    graph.set_entry_point("parse_intent")

    # Conditional routing based on intent
    graph.add_conditional_edges(
        "parse_intent",
        route_by_intent,
        {
            "agent_only": "agent_branch",
            "project_only": "project_branch",
            "both": ["agent_branch", "project_branch"]
        }
    )

    # Merge branches
    graph.add_edge("agent_branch", "merge_results")
    graph.add_edge("project_branch", "merge_results")
    graph.add_edge("merge_results", END)

    return graph


# ============================================================================
# INTEGRATION PATTERN 3: CONDITIONAL WORKFLOW
# ============================================================================

def build_conditional_workflow() -> StateGraph:
    """
    Conditional integration: Route based on user intent

    Flow:
    1. Analyze user message
    2. If agent request → use agent workflow
    3. If project request → use knowledge workflow
    4. If both → use sequential workflow

    Use case: Flexible workflow that adapts to user intent

    Returns:
        Compiled LangGraph workflow
    """
    graph = StateGraph(CombinedState)

    # Add intent detection
    graph.add_node("detect_intent", detect_intent_node)

    # Add agent workflow
    graph.add_node("run_agent_workflow", run_agent_workflow_node)

    # Add knowledge workflow
    graph.add_node("run_knowledge_workflow", run_knowledge_workflow_node)

    # Add combined workflow
    graph.add_node("run_combined_workflow", run_combined_workflow_node)

    # Set entry point
    graph.set_entry_point("detect_intent")

    # Route based on detection
    graph.add_conditional_edges(
        "detect_intent",
        route_by_detected_intent,
        {
            "agent": "run_agent_workflow",
            "project": "run_knowledge_workflow",
            "combined": "run_combined_workflow"
        }
    )

    # All branches end
    graph.add_edge("run_agent_workflow", END)
    graph.add_edge("run_knowledge_workflow", END)
    graph.add_edge("run_combined_workflow", END)

    return graph


# ============================================================================
# HELPER NODES FOR SEQUENTIAL WORKFLOW
# ============================================================================

async def ask_create_project_node(state: CombinedState) -> Dict[str, Any]:
    """Ask user if they want to create a project for the agent."""
    write_to_log("Asking user if they want to create a project")

    # In a real implementation, this would interrupt and wait for user input
    # For now, we'll check state for a flag
    create_project = state.get('create_project_after_agent', False)

    return {
        "agent_created": True,
        "create_project_after_agent": create_project
    }


async def create_project_from_agent_node(state: CombinedState) -> Dict[str, Any]:
    """Create a project based on the agent that was just created."""
    try:
        write_to_log("Creating project from agent scope")

        km = KnowledgeManager()

        # Extract project details from agent scope
        scope = state.get('scope', '')
        agent_message = state.get('latest_user_message', '')

        # Create project
        project_name = f"Project for: {agent_message[:50]}"
        project_description = f"Project created from agent request: {agent_message}\n\nScope:\n{scope}"

        project_result = await km.create_project(
            name=project_name,
            description=project_description,
            priority=2,
            auto_discover=False  # Will be done by workflow
        )

        project_id = project_result['project']['id']

        write_to_log(f"Created project: {project_id}")

        return {
            "project_id": project_id,
            "project_name": project_name,
            "project_description": project_description,
            "project_created": True
        }

    except Exception as e:
        write_to_log(f"Error creating project: {e}")
        return {
            "project_created": False,
            "error_message": str(e)
        }


async def link_agent_to_project_node(state: CombinedState) -> Dict[str, Any]:
    """Link the generated agent code to the project as a knowledge artifact."""
    try:
        write_to_log("Linking agent to project")

        # In a full implementation, you would:
        # 1. Store the generated agent code in the knowledge base
        # 2. Tag it with the project ID
        # 3. Link it to relevant tasks

        # For now, just mark as complete
        return {
            "agent_linked": True
        }

    except Exception as e:
        write_to_log(f"Error linking agent: {e}")
        return {
            "agent_linked": False
        }


def route_create_project(state: CombinedState) -> str:
    """Route: Should we create a project?"""
    if state.get('create_project_after_agent', False):
        return "yes"
    return "no"


# ============================================================================
# HELPER NODES FOR PARALLEL WORKFLOW
# ============================================================================

async def parse_user_intent_node(state: CombinedState) -> Dict[str, Any]:
    """Parse user intent to determine workflow mode."""
    message = state.get('latest_user_message', '').lower()

    # Simple keyword detection (in production, use LLM for better intent detection)
    has_agent_keywords = any(word in message for word in ['agent', 'create agent', 'build agent', 'code'])
    has_project_keywords = any(word in message for word in ['project', 'tasks', 'plan', 'schedule'])

    if has_agent_keywords and has_project_keywords:
        mode = "combined"
    elif has_agent_keywords:
        mode = "agent_only"
    elif has_project_keywords:
        mode = "project_only"
    else:
        mode = "agent_only"  # Default

    write_to_log(f"Detected workflow mode: {mode}")

    return {
        "workflow_mode": mode
    }


async def agent_creation_branch_node(state: CombinedState) -> Dict[str, Any]:
    """Execute the agent creation workflow in a branch."""
    from archon.archon_graph import agentic_flow

    write_to_log("Running agent creation branch")

    # This would run the full agent workflow
    # For simplicity, we'll just mark it as done
    return {
        "agent_created": True,
        "scope": "Agent created via parallel branch"
    }


async def project_creation_branch_node(state: CombinedState) -> Dict[str, Any]:
    """Execute the project creation workflow in a branch."""
    from archon.archon_graph_enhanced import run_project_planning_workflow

    write_to_log("Running project creation branch")

    # Create project first
    km = KnowledgeManager()
    project_result = await km.create_project(
        name=state.get('project_name', 'New Project'),
        description=state.get('project_description', state.get('latest_user_message', '')),
        auto_discover=False
    )

    project_id = project_result['project']['id']

    # Run workflow
    result = await run_project_planning_workflow(
        project_id=project_id,
        min_coverage=state.get('min_coverage_threshold', 0.4)
    )

    return {
        "project_created": True,
        "project_id": project_id,
        "task_ids": result.get('task_ids', []),
        "schedule": result.get('schedule', [])
    }


async def merge_results_node(state: CombinedState) -> Dict[str, Any]:
    """Merge results from parallel branches."""
    write_to_log("Merging results from parallel branches")

    return {
        "workflow_mode": "completed",
        "agent_created": state.get('agent_created', False),
        "project_created": state.get('project_created', False)
    }


def route_by_intent(state: CombinedState) -> str | List[str]:
    """Route based on parsed intent."""
    mode = state.get('workflow_mode', 'agent_only')

    if mode == "both":
        return ["agent_branch", "project_branch"]
    elif mode == "agent_only":
        return "agent_only"
    else:
        return "project_only"


# ============================================================================
# HELPER NODES FOR CONDITIONAL WORKFLOW
# ============================================================================

async def detect_intent_node(state: CombinedState) -> Dict[str, Any]:
    """Use LLM to detect user intent."""
    from openai import AsyncOpenAI
    from utils.utils import get_env_var

    write_to_log("Detecting user intent")

    # Get LLM client
    base_url = get_env_var('BASE_URL') or 'https://api.openai.com/v1'
    api_key = get_env_var('LLM_API_KEY') or 'no-api-key'
    primary_model = get_env_var('PRIMARY_MODEL') or 'gpt-4o-mini'
    llm_client = AsyncOpenAI(base_url=base_url, api_key=api_key)

    message = state.get('latest_user_message', '')

    prompt = f"""Analyze this user message and determine their intent:

Message: {message}

Respond with exactly one of these words:
- "agent" if they want to create an AI agent
- "project" if they want to plan/manage a project or tasks
- "combined" if they want both

Intent:"""

    response = await llm_client.chat.completions.create(
        model=primary_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    intent = response.choices[0].message.content.strip().lower()

    if intent not in ["agent", "project", "combined"]:
        intent = "agent"  # Default

    write_to_log(f"Detected intent: {intent}")

    return {
        "workflow_mode": intent
    }


async def run_agent_workflow_node(state: CombinedState) -> Dict[str, Any]:
    """Run the complete agent creation workflow."""
    write_to_log("Running agent workflow")

    # This would invoke the full agentic_flow
    # For now, placeholder
    return {
        "agent_created": True
    }


async def run_knowledge_workflow_node(state: CombinedState) -> Dict[str, Any]:
    """Run the complete knowledge workflow."""
    write_to_log("Running knowledge workflow")

    # This would invoke the full knowledge workflow
    # For now, placeholder
    return {
        "project_created": True
    }


async def run_combined_workflow_node(state: CombinedState) -> Dict[str, Any]:
    """Run both workflows in sequence."""
    write_to_log("Running combined workflow")

    # Run agent workflow first
    agent_result = await run_agent_workflow_node(state)

    # Then run knowledge workflow
    knowledge_result = await run_knowledge_workflow_node(state)

    return {
        **agent_result,
        **knowledge_result
    }


def route_by_detected_intent(state: CombinedState) -> str:
    """Route based on detected intent."""
    mode = state.get('workflow_mode', 'agent')
    return mode


# ============================================================================
# COMPILED WORKFLOWS
# ============================================================================

# Compile workflows with memory
memory = MemorySaver()

sequential_workflow = build_sequential_workflow().compile(checkpointer=memory)
parallel_workflow = build_parallel_workflow().compile(checkpointer=memory)
conditional_workflow = build_conditional_workflow().compile(checkpointer=memory)


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def run_integrated_workflow(
    user_message: str,
    workflow_type: Literal["sequential", "parallel", "conditional"] = "conditional",
    thread_id: str = "default"
) -> dict:
    """
    Run an integrated workflow.

    Args:
        user_message: User's request
        workflow_type: Type of integration pattern to use
        thread_id: Thread ID for checkpointing

    Returns:
        Final state
    """
    write_to_log(f"Running integrated workflow: {workflow_type}")

    # Initialize state
    initial_state = {
        "latest_user_message": user_message,
        "messages": [],
        "scope": "",
        "advisor_output": "",
        "file_list": [],
        "refined_prompt": "",
        "refined_tools": "",
        "refined_agent": "",
        "project_id": None,
        "project_name": None,
        "project_description": None,
        "task_id": None,
        "task_ids": [],
        "coverage_score": 0.0,
        "min_coverage_threshold": 0.4,
        "required_tags": [],
        "required_frameworks": [],
        "linked_knowledge": [],
        "schedule": [],
        "crawl_status": "not_started",
        "workflow_mode": "combined",
        "create_project_after_agent": False,
        "agent_created": False,
        "project_created": False
    }

    # Select workflow
    if workflow_type == "sequential":
        workflow = sequential_workflow
    elif workflow_type == "parallel":
        workflow = parallel_workflow
    else:
        workflow = conditional_workflow

    # Run
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await workflow.ainvoke(initial_state, config)

    return final_state


# ============================================================================
# WORKFLOW DIAGRAMS
# ============================================================================

SEQUENTIAL_DIAGRAM = """
# Sequential Workflow

graph TD
    START([User Request]) --> SCOPE[Define Scope]
    START --> ADVISOR[Get Advisor Recommendations]
    SCOPE --> CODER[Coder Agent]
    ADVISOR --> CODER
    CODER --> GET[Get User Feedback]
    GET --> ROUTE{User Intent}
    ROUTE -->|Continue| CODER
    ROUTE -->|Refine| REFINE[Refine Agent]
    ROUTE -->|Finish| FINISH[Finish Agent Creation]
    REFINE --> CODER
    FINISH --> ASK{Create Project?}
    ASK -->|Yes| CREATE[Create Project]
    ASK -->|No| END1([End])
    CREATE --> CHECK[Check Knowledge]
    CHECK -->|Low Coverage| ACQUIRE[Acquire Knowledge]
    CHECK -->|OK| DECOMPOSE[Decompose Project]
    ACQUIRE --> DECOMPOSE
    DECOMPOSE --> SCHEDULE[Schedule Tasks]
    SCHEDULE --> LINK[Link Agent to Project]
    LINK --> END2([End])
"""

PARALLEL_DIAGRAM = """
# Parallel Workflow

graph TD
    START([User Request]) --> PARSE[Parse Intent]
    PARSE -->|Agent + Project| AGENT[Agent Branch]
    PARSE -->|Agent + Project| PROJECT[Project Branch]
    PARSE -->|Agent Only| AGENT
    PARSE -->|Project Only| PROJECT
    AGENT --> MERGE[Merge Results]
    PROJECT --> MERGE
    MERGE --> END([End])
"""

CONDITIONAL_DIAGRAM = """
# Conditional Workflow

graph TD
    START([User Request]) --> DETECT[Detect Intent with LLM]
    DETECT -->|Agent| AGENT_FLOW[Run Agent Workflow]
    DETECT -->|Project| PROJECT_FLOW[Run Project Workflow]
    DETECT -->|Combined| COMBINED_FLOW[Run Both Workflows]
    AGENT_FLOW --> END([End])
    PROJECT_FLOW --> END
    COMBINED_FLOW --> END
"""


# ============================================================================
# MAIN (for testing)
# ============================================================================

async def main():
    """Test integrated workflows."""
    import asyncio

    # Test conditional workflow with different intents

    print("\n=== Test 1: Agent Request ===")
    result = await run_integrated_workflow(
        "Create an agent that scrapes documentation",
        workflow_type="conditional",
        thread_id="test-1"
    )
    print(f"Agent Created: {result.get('agent_created')}")
    print(f"Project Created: {result.get('project_created')}")

    print("\n=== Test 2: Project Request ===")
    result = await run_integrated_workflow(
        "Plan a project to build a REST API with authentication",
        workflow_type="conditional",
        thread_id="test-2"
    )
    print(f"Agent Created: {result.get('agent_created')}")
    print(f"Project Created: {result.get('project_created')}")

    print("\n=== Test 3: Combined Request ===")
    result = await run_integrated_workflow(
        "Create an agent and set up a project to build a FastAPI application",
        workflow_type="conditional",
        thread_id="test-3"
    )
    print(f"Agent Created: {result.get('agent_created')}")
    print(f"Project Created: {result.get('project_created')}")

    # Print diagrams
    print("\n=== Sequential Workflow Diagram ===")
    print(SEQUENTIAL_DIAGRAM)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
