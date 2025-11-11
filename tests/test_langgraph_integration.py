"""
Comprehensive tests for LangGraph Knowledge Management Integration

This test suite covers:
- Individual node functionality
- Complete workflow execution
- Routing logic
- State management
- Error handling
- Integration with existing archon_graph
"""

import pytest
import asyncio
import json
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone

# Import nodes and workflows
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
    initialize_knowledge_state
)

from archon.archon_graph_enhanced import (
    build_knowledge_workflow,
    build_simple_knowledge_workflow,
    build_task_execution_workflow,
    build_project_planning_workflow,
    run_knowledge_workflow,
    run_simple_knowledge_workflow
)

from archon.integrated_workflow import (
    CombinedState,
    build_sequential_workflow,
    build_parallel_workflow,
    build_conditional_workflow,
    parse_user_intent_node,
    detect_intent_node
)


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def sample_knowledge_state() -> KnowledgeState:
    """Provide a sample KnowledgeState for testing."""
    return initialize_knowledge_state(
        latest_user_message="Build a FastAPI authentication system",
        project_description="Build a FastAPI auth system with JWT and OAuth2",
        min_coverage_threshold=0.4,
        required_tags=["authentication", "jwt", "oauth2"],
        required_frameworks=["fastapi", "pydantic"]
    )


@pytest.fixture
def sample_combined_state() -> CombinedState:
    """Provide a sample CombinedState for testing."""
    return {
        "latest_user_message": "Create an agent for authentication",
        "messages": [],
        "scope": "",
        "advisor_output": "",
        "file_list": [],
        "refined_prompt": "",
        "refined_tools": "",
        "refined_agent": "",
        "project_id": None,
        "project_name": "Test Project",
        "project_description": "Test project description",
        "task_id": None,
        "task_ids": [],
        "coverage_score": 0.0,
        "min_coverage_threshold": 0.4,
        "required_tags": ["test"],
        "required_frameworks": ["fastapi"],
        "linked_knowledge": [],
        "schedule": [],
        "crawl_status": "not_started",
        "workflow_mode": "agent_only",
        "create_project_after_agent": False,
        "agent_created": False,
        "project_created": False
    }


@pytest.fixture
def mock_knowledge_manager():
    """Mock KnowledgeManager for testing."""
    with patch('archon.knowledge_workflow.KnowledgeManager') as mock:
        km = AsyncMock()

        # Mock check_and_acquire_knowledge
        km.check_and_acquire_knowledge.return_value = Mock(
            total_chunks=10,
            coverage_score=0.6,
            missing_tags=["oauth2"],
            available_frameworks=["fastapi"],
            needs_scraping=False
        )

        # Mock _extract_tags_and_frameworks
        km._extract_tags_and_frameworks.return_value = (
            ["authentication", "jwt"],
            ["fastapi", "pydantic"]
        )

        # Mock create_project
        km.create_project.return_value = {
            "project": {"id": "test-project-123", "name": "Test Project"},
            "coverage": {"coverage_score": 0.6},
            "scraper_triggered": False
        }

        # Mock get_task
        km.get_task.return_value = {
            "id": "test-task-123",
            "name": "Test Task",
            "description": "Test task description",
            "status": "pending",
            "required_knowledge_tags": ["test"],
            "required_frameworks": ["fastapi"]
        }

        # Mock get_task_with_knowledge
        km.get_task_with_knowledge.return_value = {
            "task": {
                "id": "test-task-123",
                "name": "Test Task",
                "description": "Test description"
            },
            "linked_knowledge": [
                {"id": "k1", "content": "Knowledge 1", "relevance_score": 0.9},
                {"id": "k2", "content": "Knowledge 2", "relevance_score": 0.8}
            ]
        }

        # Mock link_task_knowledge
        km.link_task_knowledge.return_value = {
            "linked_knowledge": [
                {"id": "k1", "content": "Knowledge 1", "similarity": 0.9}
            ],
            "coverage_score": 0.7,
            "links_created": 1
        }

        # Mock decompose_project
        km.decompose_project.return_value = [
            {
                "task": {
                    "id": "task-1",
                    "name": "Setup FastAPI",
                    "description": "Initialize FastAPI project",
                    "status": "pending",
                    "priority": 1
                },
                "coverage_score": 0.8
            },
            {
                "task": {
                    "id": "task-2",
                    "name": "Implement JWT",
                    "description": "Add JWT authentication",
                    "status": "pending",
                    "priority": 2
                },
                "coverage_score": 0.7
            }
        ]

        # Mock update_task_status
        km.update_task_status.return_value = {"id": "test-task-123", "status": "in_progress"}

        # Mock supabase table operations
        km.supabase = Mock()
        km.supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        km.supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = Mock()

        mock.return_value = km
        yield km


@pytest.fixture
def mock_universal_crawler():
    """Mock UniversalCrawler for testing."""
    with patch('archon.knowledge_workflow.get_universal_crawler') as mock:
        crawler = AsyncMock()

        crawler.crawl_source.return_value = {
            "crawled_urls": [
                "https://example.com/page1",
                "https://example.com/page2"
            ],
            "chunks_created": 5,
            "status": "completed"
        }

        mock.return_value = crawler
        yield crawler


# ============================================================================
# NODE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_knowledge_node(sample_knowledge_state, mock_knowledge_manager):
    """Test check_knowledge_node functionality."""
    result = await check_knowledge_node(sample_knowledge_state)

    assert result['coverage_score'] == 0.6
    assert result['needs_scraping'] == False
    assert result['workflow_stage'] == 'coverage_checked'
    assert result['error_message'] is None
    assert 'required_tags' in result
    assert 'required_frameworks' in result


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_knowledge_node_error_handling(sample_knowledge_state, mock_knowledge_manager):
    """Test check_knowledge_node error handling."""
    # Make the mock raise an exception
    mock_knowledge_manager.check_and_acquire_knowledge.side_effect = Exception("Test error")

    result = await check_knowledge_node(sample_knowledge_state)

    assert result['coverage_score'] == 0.0
    assert result['needs_scraping'] == True
    assert result['workflow_stage'] == 'error'
    assert result['error_message'] == "Test error"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_knowledge_node(sample_knowledge_state, mock_universal_crawler):
    """Test acquire_knowledge_node functionality."""
    # Set up state to trigger acquisition
    sample_knowledge_state['missing_tags'] = ['oauth2']
    sample_knowledge_state['required_frameworks'] = ['fastapi']

    result = await acquire_knowledge_node(sample_knowledge_state)

    assert result['crawl_status'] in ['completed', 'failed']
    assert 'crawled_urls' in result
    assert result['workflow_stage'] in ['knowledge_acquired', 'error']


@pytest.mark.unit
@pytest.mark.asyncio
async def test_acquire_knowledge_node_no_missing(sample_knowledge_state):
    """Test acquire_knowledge_node with no missing knowledge."""
    sample_knowledge_state['missing_tags'] = []
    sample_knowledge_state['required_frameworks'] = []

    result = await acquire_knowledge_node(sample_knowledge_state)

    assert result['crawl_status'] == 'completed'
    assert result['crawled_urls'] == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_knowledge_node(sample_knowledge_state, mock_knowledge_manager):
    """Test link_knowledge_node functionality."""
    sample_knowledge_state['task_id'] = 'test-task-123'

    result = await link_knowledge_node(sample_knowledge_state)

    assert 'linked_knowledge' in result
    assert result['coverage_score'] > 0
    assert result['workflow_stage'] == 'knowledge_linked'
    assert result['error_message'] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_knowledge_node_no_tasks(sample_knowledge_state, mock_knowledge_manager):
    """Test link_knowledge_node with no tasks."""
    result = await link_knowledge_node(sample_knowledge_state)

    assert result['linked_knowledge'] == []
    assert 'No tasks' in result['error_message']


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decompose_project_node(sample_knowledge_state, mock_knowledge_manager):
    """Test decompose_project_node functionality."""
    sample_knowledge_state['project_id'] = 'test-project-123'

    result = await decompose_project_node(sample_knowledge_state)

    assert len(result['task_ids']) == 2
    assert len(result['schedule']) == 2
    assert result['workflow_stage'] == 'project_decomposed'
    assert result['error_message'] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decompose_project_node_no_project(sample_knowledge_state, mock_knowledge_manager):
    """Test decompose_project_node with no project ID."""
    result = await decompose_project_node(sample_knowledge_state)

    assert result['task_ids'] == []
    assert result['workflow_stage'] == 'error'
    assert 'No project ID' in result['error_message']


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schedule_tasks_node(sample_knowledge_state, mock_knowledge_manager):
    """Test schedule_tasks_node functionality."""
    sample_knowledge_state['task_ids'] = ['task-1', 'task-2']

    result = await schedule_tasks_node(sample_knowledge_state)

    assert len(result['schedule']) == 2
    assert result['workflow_stage'] == 'tasks_scheduled'
    assert all('scheduled_start' in task for task in result['schedule'])
    assert all('scheduled_end' in task for task in result['schedule'])


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schedule_tasks_node_no_tasks(sample_knowledge_state):
    """Test schedule_tasks_node with no tasks."""
    result = await schedule_tasks_node(sample_knowledge_state)

    assert result['schedule'] == []
    assert 'No tasks to schedule' in result['error_message']


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_with_knowledge_node(sample_knowledge_state, mock_knowledge_manager):
    """Test execute_with_knowledge_node functionality."""
    sample_knowledge_state['task_id'] = 'test-task-123'

    result = await execute_with_knowledge_node(sample_knowledge_state)

    assert result['execution_result'] is not None
    assert result['execution_result']['task_id'] == 'test-task-123'
    assert result['agent_output'] is not None
    assert result['workflow_stage'] == 'task_executed'
    assert result['error_message'] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_with_knowledge_node_no_task(sample_knowledge_state, mock_knowledge_manager):
    """Test execute_with_knowledge_node with no task."""
    result = await execute_with_knowledge_node(sample_knowledge_state)

    assert result['execution_result'] is None
    assert result['workflow_stage'] == 'error'
    assert 'No task ID' in result['error_message']


# ============================================================================
# ROUTING TESTS
# ============================================================================

@pytest.mark.unit
def test_route_based_on_coverage_low():
    """Test routing when coverage is below threshold."""
    state = initialize_knowledge_state(
        coverage_score=0.3,
        min_coverage_threshold=0.4
    )

    result = route_based_on_coverage(state)
    assert result == "acquire_knowledge"


@pytest.mark.unit
def test_route_based_on_coverage_high():
    """Test routing when coverage is above threshold."""
    state = initialize_knowledge_state(
        coverage_score=0.6,
        min_coverage_threshold=0.4
    )

    result = route_based_on_coverage(state)
    assert result == "continue"


@pytest.mark.unit
def test_route_based_on_project_with_project():
    """Test routing with project ID."""
    state = initialize_knowledge_state(
        project_id="test-project-123"
    )

    result = route_based_on_project(state)
    assert result == "decompose_project"


@pytest.mark.unit
def test_route_based_on_project_with_task():
    """Test routing with task ID."""
    state = initialize_knowledge_state(
        task_id="test-task-123"
    )

    result = route_based_on_project(state)
    assert result == "execute_task"


@pytest.mark.unit
def test_route_based_on_project_none():
    """Test routing with neither project nor task."""
    state = initialize_knowledge_state()

    result = route_based_on_project(state)
    assert result == "skip"


# ============================================================================
# WORKFLOW TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_knowledge_workflow():
    """Test building the knowledge workflow graph."""
    graph = build_knowledge_workflow()

    assert graph is not None
    compiled = graph.compile()
    assert compiled is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_simple_knowledge_workflow():
    """Test building the simple knowledge workflow."""
    graph = build_simple_knowledge_workflow()

    assert graph is not None
    compiled = graph.compile()
    assert compiled is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_task_execution_workflow():
    """Test building the task execution workflow."""
    graph = build_task_execution_workflow()

    assert graph is not None
    compiled = graph.compile()
    assert compiled is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_project_planning_workflow():
    """Test building the project planning workflow."""
    graph = build_project_planning_workflow()

    assert graph is not None
    compiled = graph.compile()
    assert compiled is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_initialize_knowledge_state():
    """Test state initialization."""
    state = initialize_knowledge_state(
        project_name="Test Project",
        min_coverage_threshold=0.5
    )

    assert state['project_name'] == "Test Project"
    assert state['min_coverage_threshold'] == 0.5
    assert state['coverage_score'] == 0.0
    assert state['task_ids'] == []
    assert state['workflow_stage'] == 'initialized'


# ============================================================================
# INTEGRATED WORKFLOW TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_sequential_workflow():
    """Test building the sequential integrated workflow."""
    graph = build_sequential_workflow()

    assert graph is not None
    compiled = graph.compile()
    assert compiled is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_parallel_workflow():
    """Test building the parallel integrated workflow."""
    graph = build_parallel_workflow()

    assert graph is not None
    compiled = graph.compile()
    assert compiled is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_build_conditional_workflow():
    """Test building the conditional integrated workflow."""
    graph = build_conditional_workflow()

    assert graph is not None
    compiled = graph.compile()
    assert compiled is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_user_intent_agent():
    """Test parsing user intent for agent creation."""
    state = {
        "latest_user_message": "Create an agent to scrape documentation",
        "workflow_mode": "agent_only"
    }

    result = await parse_user_intent_node(state)
    assert result['workflow_mode'] in ['agent_only', 'combined']


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_user_intent_project():
    """Test parsing user intent for project creation."""
    state = {
        "latest_user_message": "Plan a project to build an API",
        "workflow_mode": "project_only"
    }

    result = await parse_user_intent_node(state)
    assert result['workflow_mode'] in ['project_only', 'combined']


@pytest.mark.integration
@pytest.mark.asyncio
async def test_parse_user_intent_combined():
    """Test parsing user intent for combined workflow."""
    state = {
        "latest_user_message": "Create an agent and plan a project for authentication",
        "workflow_mode": "combined"
    }

    result = await parse_user_intent_node(state)
    assert result['workflow_mode'] == 'combined'


# ============================================================================
# STATE MANAGEMENT TESTS
# ============================================================================

@pytest.mark.unit
def test_knowledge_state_structure():
    """Test KnowledgeState has all required fields."""
    state = initialize_knowledge_state()

    required_fields = [
        'latest_user_message',
        'messages',
        'project_id',
        'task_id',
        'coverage_score',
        'required_tags',
        'required_frameworks',
        'linked_knowledge',
        'schedule',
        'crawl_status',
        'workflow_stage'
    ]

    for field in required_fields:
        assert field in state


@pytest.mark.unit
def test_combined_state_structure(sample_combined_state):
    """Test CombinedState has all required fields."""
    required_fields = [
        'latest_user_message',
        'scope',
        'project_id',
        'coverage_score',
        'workflow_mode',
        'agent_created',
        'project_created'
    ]

    for field in required_fields:
        assert field in sample_combined_state


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_node_error_handling(mock_knowledge_manager):
    """Test that nodes handle errors gracefully."""
    # Force an error
    mock_knowledge_manager.check_and_acquire_knowledge.side_effect = Exception("Database error")

    state = initialize_knowledge_state()
    result = await check_knowledge_node(state)

    assert result['workflow_stage'] == 'error'
    assert result['error_message'] is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_knowledge_with_invalid_task(mock_knowledge_manager):
    """Test linking knowledge with invalid task ID."""
    mock_knowledge_manager.get_task.side_effect = ValueError("Task not found")

    state = initialize_knowledge_state(task_id="invalid-task")
    result = await link_knowledge_node(state)

    assert result['workflow_stage'] == 'error'


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

@pytest.mark.slow
@pytest.mark.asyncio
async def test_parallel_task_linking(mock_knowledge_manager):
    """Test linking knowledge to multiple tasks in parallel."""
    state = initialize_knowledge_state(
        task_ids=['task-1', 'task-2', 'task-3', 'task-4', 'task-5']
    )

    import time
    start = time.time()
    result = await link_knowledge_node(state)
    duration = time.time() - start

    # Should complete reasonably fast even with multiple tasks
    assert duration < 10  # 10 seconds
    assert 'linked_knowledge' in result


# ============================================================================
# INTEGRATION WITH EXISTING WORKFLOW TESTS
# ============================================================================

@pytest.mark.integration
def test_state_compatibility():
    """Test that KnowledgeState is compatible with AgentState."""
    knowledge_state = initialize_knowledge_state(
        latest_user_message="Test message"
    )

    # Should be able to access AgentState fields
    assert 'latest_user_message' in knowledge_state
    assert 'messages' in knowledge_state


@pytest.mark.integration
def test_combined_state_compatibility(sample_combined_state):
    """Test that CombinedState includes both AgentState and KnowledgeState fields."""
    # AgentState fields
    assert 'scope' in sample_combined_state
    assert 'advisor_output' in sample_combined_state
    assert 'refined_prompt' in sample_combined_state

    # KnowledgeState fields
    assert 'project_id' in sample_combined_state
    assert 'coverage_score' in sample_combined_state
    assert 'linked_knowledge' in sample_combined_state


# ============================================================================
# WORKFLOW EXECUTION TESTS (END-TO-END)
# ============================================================================

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_workflow_execution(mock_knowledge_manager, mock_universal_crawler):
    """Test complete workflow execution from start to end."""
    # This is a mock test - in a real environment, you'd test against actual services
    state = initialize_knowledge_state(
        project_description="Build a FastAPI auth system",
        min_coverage_threshold=0.4
    )

    # Simulate workflow steps
    step1 = await check_knowledge_node(state)
    state.update(step1)

    # Based on coverage, either acquire or continue
    if state['needs_scraping']:
        step2 = await acquire_knowledge_node(state)
        state.update(step2)

    # Verify workflow completed key stages
    assert state['workflow_stage'] in ['coverage_checked', 'knowledge_acquired']


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
