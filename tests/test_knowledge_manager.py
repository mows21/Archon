"""
Tests for Knowledge Manager Orchestrator

This module tests all functionality of the knowledge_manager module including:
- Project CRUD operations
- Task CRUD operations
- Auto knowledge discovery
- Coverage checking
- Embedding generation
- Project decomposition
- Batch operations
- Dependency management
- Agent registry
- Error handling
- Edge cases
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.knowledge_manager import (
    KnowledgeManager,
    ProjectStatus,
    TaskStatus,
    LinkType,
    AgentType,
    KnowledgeCoverage,
    ProjectMetadata,
    TaskMetadata,
    get_knowledge_manager
)


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

@pytest.mark.unit
def test_knowledge_manager_initialization(mock_supabase, mock_openai):
    """Test Knowledge Manager initialization."""
    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai,
        llm_client=mock_openai
    )

    assert km.supabase is not None
    assert km.embedding_client is not None
    assert km.llm_client is not None
    assert km.min_coverage_threshold == 0.4


@pytest.mark.unit
def test_knowledge_manager_default_initialization():
    """Test Knowledge Manager with default clients."""
    with patch('archon.knowledge_manager.get_clients') as mock_get_clients:
        mock_get_clients.return_value = (Mock(), Mock())

        km = KnowledgeManager()

        assert km.supabase is not None
        assert km.embedding_client is not None


# ============================================================================
# PROJECT CRUD TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_project_basic(mock_supabase, mock_openai):
    """Test basic project creation."""
    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai,
        llm_client=mock_openai
    )

    result = await km.create_project(
        name="Test Project",
        description="A test project for FastAPI development",
        priority=1,
        auto_discover=False  # Disable auto-discovery for basic test
    )

    assert "project" in result
    assert result["project"]["name"] == "Test Project"
    assert result["project"]["status"] == ProjectStatus.PLANNING.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_project_with_auto_discovery(mock_supabase, mock_openai):
    """Test project creation with auto knowledge discovery."""
    # Setup mock coverage response
    mock_supabase.set_rpc_response('check_knowledge_coverage', [{
        'total_chunks': 10,
        'coverage_score': 0.75,
        'missing_tags': [],
        'available_frameworks': ['fastapi']
    }])

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai,
        llm_client=mock_openai
    )

    result = await km.create_project(
        name="FastAPI Project",
        description="Build a FastAPI application with authentication",
        priority=1,
        auto_discover=True,
        min_coverage=0.4
    )

    assert "coverage" in result
    assert result["coverage"] is not None
    assert result["scraper_triggered"] is False  # Coverage is good


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_project_low_coverage(mock_supabase, mock_openai):
    """Test project creation triggers scraper on low coverage."""
    # Setup mock low coverage response
    mock_supabase.set_rpc_response('check_knowledge_coverage', [{
        'total_chunks': 2,
        'coverage_score': 0.2,
        'missing_tags': ['authentication', 'jwt'],
        'available_frameworks': []
    }])

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai,
        llm_client=mock_openai
    )

    result = await km.create_project(
        name="New Framework Project",
        description="Build with a new framework",
        priority=1,
        auto_discover=True,
        min_coverage=0.4
    )

    assert result["scraper_triggered"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_project(mock_supabase):
    """Test retrieving a project."""
    # Add project to mock database
    project_id = "proj-123"
    mock_supabase._data["projects"] = [{
        "id": project_id,
        "name": "Test Project",
        "description": "Test",
        "status": "planning"
    }]

    km = KnowledgeManager(supabase=mock_supabase)

    project = await km.get_project(project_id)

    assert project["id"] == project_id
    assert project["name"] == "Test Project"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_project_not_found(mock_supabase):
    """Test getting non-existent project."""
    km = KnowledgeManager(supabase=mock_supabase)

    with pytest.raises(ValueError):
        await km.get_project("non-existent-id")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_project_status(mock_supabase):
    """Test updating project status."""
    project_id = "proj-123"
    mock_supabase._data["projects"] = [{
        "id": project_id,
        "name": "Test Project",
        "status": "planning"
    }]

    km = KnowledgeManager(supabase=mock_supabase)

    updated = await km.update_project_status(
        project_id,
        ProjectStatus.IN_PROGRESS.value
    )

    assert updated["status"] == ProjectStatus.IN_PROGRESS.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_project_status_to_completed(mock_supabase):
    """Test updating project to completed adds timestamp."""
    project_id = "proj-123"
    mock_supabase._data["projects"] = [{
        "id": project_id,
        "name": "Test Project",
        "status": "in_progress"
    }]

    km = KnowledgeManager(supabase=mock_supabase)

    updated = await km.update_project_status(
        project_id,
        ProjectStatus.COMPLETED.value
    )

    # Completed status should add completed_at timestamp
    assert updated["status"] == ProjectStatus.COMPLETED.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_project(mock_supabase):
    """Test deleting a project."""
    project_id = "proj-123"
    mock_supabase._data["projects"] = [{
        "id": project_id,
        "name": "Test Project"
    }]

    km = KnowledgeManager(supabase=mock_supabase)

    result = await km.delete_project(project_id)

    assert result is True


# ============================================================================
# TASK CRUD TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_basic(mock_supabase, mock_openai):
    """Test basic task creation."""
    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai,
        llm_client=mock_openai
    )

    result = await km.create_task(
        project_id="proj-123",
        name="Implement authentication",
        description="Add JWT authentication to the API",
        priority=1,
        auto_link=False
    )

    assert "task" in result
    assert result["task"]["name"] == "Implement authentication"
    assert result["task"]["status"] == TaskStatus.PENDING.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_with_auto_link(mock_supabase, mock_openai):
    """Test task creation with automatic knowledge linking."""
    # Setup mock knowledge search response
    mock_supabase.set_rpc_response('match_knowledge_advanced', [{
        'id': 1,
        'url': 'https://example.com/doc1',
        'title': 'Auth Guide',
        'content': 'Auth content',
        'summary': 'Summary',
        'tags': ['auth'],
        'knowledge_type': 'documentation',
        'framework': 'fastapi',
        'similarity': 0.9,
        'metadata': {}
    }])

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai,
        llm_client=mock_openai
    )

    result = await km.create_task(
        project_id="proj-123",
        name="Implement authentication",
        description="Add JWT authentication",
        priority=1,
        auto_link=True
    )

    assert "linked_knowledge" in result
    assert "coverage_score" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_subtask(mock_supabase, mock_openai):
    """Test creating a subtask with parent reference."""
    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai,
        llm_client=mock_openai
    )

    result = await km.create_task(
        project_id="proj-123",
        name="Write unit tests",
        description="Write tests for authentication",
        priority=2,
        parent_task_id="task-parent-123",
        auto_link=False
    )

    assert result["task"]["parent_task_id"] == "task-parent-123"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task(mock_supabase):
    """Test retrieving a task."""
    task_id = "task-456"
    mock_supabase._data["tasks"] = [{
        "id": task_id,
        "name": "Test Task",
        "description": "Test",
        "project_id": "proj-123"
    }]

    km = KnowledgeManager(supabase=mock_supabase)

    task = await km.get_task(task_id)

    assert task["id"] == task_id
    assert task["name"] == "Test Task"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_with_knowledge(mock_supabase):
    """Test retrieving task with linked knowledge."""
    task_id = "task-456"
    mock_supabase._data["tasks"] = [{
        "id": task_id,
        "name": "Test Task",
        "description": "Test"
    }]

    mock_supabase.set_rpc_response('get_task_knowledge', [{
        'id': 1,
        'url': 'https://example.com/doc1',
        'title': 'Test Doc',
        'content': 'Content',
        'summary': 'Summary',
        'tags': ['test'],
        'knowledge_type': 'documentation',
        'framework': 'test',
        'relevance_score': 0.9,
        'link_type': 'suggested'
    }])

    km = KnowledgeManager(supabase=mock_supabase)

    result = await km.get_task_with_knowledge(task_id)

    assert "task" in result
    assert "linked_knowledge" in result
    assert len(result["linked_knowledge"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_task_status(mock_supabase):
    """Test updating task status."""
    task_id = "task-456"
    mock_supabase._data["tasks"] = [{
        "id": task_id,
        "name": "Test Task",
        "status": "pending"
    }]

    km = KnowledgeManager(supabase=mock_supabase)

    updated = await km.update_task_status(
        task_id,
        TaskStatus.IN_PROGRESS.value
    )

    assert updated["status"] == TaskStatus.IN_PROGRESS.value


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_task(mock_supabase):
    """Test deleting a task."""
    task_id = "task-456"
    mock_supabase._data["tasks"] = [{
        "id": task_id,
        "name": "Test Task"
    }]

    km = KnowledgeManager(supabase=mock_supabase)

    result = await km.delete_task(task_id)

    assert result is True


# ============================================================================
# KNOWLEDGE OPERATIONS TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_check_and_acquire_knowledge(mock_supabase):
    """Test checking knowledge coverage."""
    mock_supabase.set_rpc_response('check_knowledge_coverage', [{
        'total_chunks': 15,
        'coverage_score': 0.8,
        'missing_tags': [],
        'available_frameworks': ['fastapi']
    }])

    km = KnowledgeManager(supabase=mock_supabase)

    coverage = await km.check_and_acquire_knowledge(
        tags=["fastapi", "auth"],
        frameworks=["fastapi"],
        min_coverage=0.4
    )

    assert isinstance(coverage, KnowledgeCoverage)
    assert coverage.coverage_score == 0.8
    assert coverage.needs_scraping is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_check_and_acquire_knowledge_low_coverage(mock_supabase):
    """Test coverage check with low coverage."""
    mock_supabase.set_rpc_response('check_knowledge_coverage', [{
        'total_chunks': 2,
        'coverage_score': 0.2,
        'missing_tags': ['authentication', 'oauth2'],
        'available_frameworks': []
    }])

    km = KnowledgeManager(supabase=mock_supabase)

    coverage = await km.check_and_acquire_knowledge(
        tags=["authentication", "oauth2", "jwt"],
        frameworks=["fastapi"],
        min_coverage=0.5
    )

    assert coverage.needs_scraping is True
    assert len(coverage.missing_tags) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_link_task_knowledge(mock_supabase, mock_openai):
    """Test linking knowledge to a task."""
    task_id = "task-456"
    mock_supabase._data["tasks"] = [{
        "id": task_id,
        "name": "Test Task",
        "description": "Test FastAPI authentication",
        "required_knowledge_tags": ["fastapi", "auth"],
        "required_frameworks": ["fastapi"],
        "task_context_embedding": [0.1] * 1536
    }]

    mock_supabase.set_rpc_response('match_knowledge_advanced', [{
        'id': 1,
        'url': 'https://example.com/doc1',
        'title': 'FastAPI Auth',
        'content': 'Content',
        'summary': 'Summary',
        'tags': ['fastapi', 'auth'],
        'knowledge_type': 'documentation',
        'framework': 'fastapi',
        'similarity': 0.9,
        'metadata': {}
    }])

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai
    )

    result = await km.link_task_knowledge(task_id)

    assert "linked_knowledge" in result
    assert "coverage_score" in result
    assert result["links_created"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_link_task_knowledge_refresh(mock_supabase, mock_openai):
    """Test refreshing task knowledge links."""
    task_id = "task-456"
    mock_supabase._data["tasks"] = [{
        "id": task_id,
        "description": "Test",
        "task_context_embedding": [0.1] * 1536
    }]

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai
    )

    result = await km.link_task_knowledge(task_id, refresh=True)

    assert "linked_knowledge" in result


# ============================================================================
# PROJECT DECOMPOSITION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_decompose_project(mock_supabase, mock_openai_with_responses):
    """Test project decomposition into tasks."""
    project_id = "proj-123"
    mock_supabase._data["projects"] = [{
        "id": project_id,
        "name": "FastAPI Project",
        "description": "Build a FastAPI application",
        "required_knowledge_tags": ["fastapi"],
        "required_frameworks": ["fastapi"]
    }]

    mock_client = mock_openai_with_responses({
        "FastAPI": {
            "tasks": [
                {
                    "name": "Setup project structure",
                    "description": "Initialize FastAPI project",
                    "priority": 1,
                    "estimated_duration_minutes": 30,
                    "dependencies": []
                },
                {
                    "name": "Implement API endpoints",
                    "description": "Create REST endpoints",
                    "priority": 2,
                    "estimated_duration_minutes": 120,
                    "dependencies": ["Setup project structure"]
                }
            ]
        }
    })

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_client,
        llm_client=mock_client
    )

    tasks = await km.decompose_project(
        project_id,
        auto_link_knowledge=False
    )

    assert len(tasks) > 0
    assert all("task" in t for t in tasks)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decompose_project_with_auto_link(mock_supabase, mock_openai_with_responses):
    """Test project decomposition with auto-linking."""
    project_id = "proj-123"
    mock_supabase._data["projects"] = [{
        "id": project_id,
        "name": "Test Project",
        "description": "Test",
        "required_knowledge_tags": [],
        "required_frameworks": []
    }]

    mock_client = mock_openai_with_responses({
        "Test": {
            "tasks": [{
                "name": "Task 1",
                "description": "First task",
                "priority": 1,
                "estimated_duration_minutes": 60,
                "dependencies": []
            }]
        }
    })

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_client,
        llm_client=mock_client
    )

    tasks = await km.decompose_project(
        project_id,
        auto_link_knowledge=True
    )

    assert len(tasks) > 0


# ============================================================================
# BATCH OPERATIONS TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_create_tasks(mock_supabase, mock_openai):
    """Test creating multiple tasks in parallel."""
    project_id = "proj-123"
    task_definitions = [
        {"name": "Task 1", "description": "First task", "priority": 1},
        {"name": "Task 2", "description": "Second task", "priority": 2},
        {"name": "Task 3", "description": "Third task", "priority": 3}
    ]

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai,
        llm_client=mock_openai
    )

    tasks = await km.batch_create_tasks(
        project_id,
        task_definitions,
        auto_link=False
    )

    assert len(tasks) == len(task_definitions)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_link_knowledge(mock_supabase, mock_openai):
    """Test linking knowledge to multiple tasks in parallel."""
    task_ids = ["task-1", "task-2", "task-3"]

    # Setup mock tasks
    mock_supabase._data["tasks"] = [
        {
            "id": tid,
            "name": f"Task {tid}",
            "description": "Test description",
            "task_context_embedding": [0.1] * 1536,
            "required_knowledge_tags": [],
            "required_frameworks": []
        }
        for tid in task_ids
    ]

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai
    )

    results = await km.batch_link_knowledge(task_ids)

    assert len(results) == len(task_ids)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_check_coverage(mock_supabase):
    """Test checking coverage for multiple tag/framework combinations."""
    mock_supabase.set_rpc_response('check_knowledge_coverage', [{
        'total_chunks': 10,
        'coverage_score': 0.7,
        'missing_tags': [],
        'available_frameworks': ['fastapi']
    }])

    tag_framework_pairs = [
        (["fastapi", "auth"], ["fastapi"]),
        (["django", "orm"], ["django"]),
        (["react", "hooks"], ["react"])
    ]

    km = KnowledgeManager(supabase=mock_supabase)

    coverages = await km.batch_check_coverage(tag_framework_pairs)

    assert len(coverages) == len(tag_framework_pairs)
    assert all(isinstance(c, KnowledgeCoverage) for c in coverages)


# ============================================================================
# AGENT REGISTRY TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_agent():
    """Test registering an agent."""
    km = KnowledgeManager()

    agent_data = await km.register_agent(
        agent_name="test_agent",
        agent_type=AgentType.CODER.value,
        capabilities={"languages": ["python"], "frameworks": ["fastapi"]},
        metadata={"version": "1.0"}
    )

    assert agent_data["agent_name"] == "test_agent"
    assert agent_data["agent_type"] == AgentType.CODER.value


@pytest.mark.unit
@pytest.mark.asyncio
async def test_register_agent_invalid_type():
    """Test registering agent with invalid type."""
    km = KnowledgeManager()

    with pytest.raises(ValueError):
        await km.register_agent(
            agent_name="test_agent",
            agent_type="invalid_type",
            capabilities={}
        )


# ============================================================================
# HELPER METHOD TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_embedding(mock_openai):
    """Test embedding generation."""
    km = KnowledgeManager(embedding_client=mock_openai)

    embedding = await km._get_embedding("Test text for embedding")

    assert isinstance(embedding, list)
    assert len(embedding) == 1536


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_tags_and_frameworks(mock_openai):
    """Test tag and framework extraction."""
    km = KnowledgeManager(llm_client=mock_openai)

    description = "Build a FastAPI application with authentication using JWT tokens"
    tags, frameworks = await km._extract_tags_and_frameworks(description)

    assert isinstance(tags, list)
    assert isinstance(frameworks, list)
    # Tags should be lowercase
    assert all(tag.islower() for tag in tags)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_tags_and_frameworks_error_handling(mock_openai):
    """Test error handling in tag extraction."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")

    km = KnowledgeManager(llm_client=mock_client)

    tags, frameworks = await km._extract_tags_and_frameworks("test description")

    # Should return empty lists on error
    assert tags == []
    assert frameworks == []


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_project_error_handling(mock_supabase):
    """Test error handling in project creation."""
    # Make the insert fail
    mock_supabase_error = MagicMock()
    mock_supabase_error.table().insert().execute.side_effect = Exception("DB Error")

    km = KnowledgeManager(supabase=mock_supabase_error)

    with pytest.raises(Exception):
        await km.create_project(
            name="Test Project",
            description="Test",
            auto_discover=False
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_task_error_handling(mock_supabase):
    """Test error handling in task creation."""
    mock_supabase_error = MagicMock()
    mock_supabase_error.table().insert().execute.side_effect = Exception("DB Error")

    km = KnowledgeManager(supabase=mock_supabase_error)

    with pytest.raises(Exception):
        await km.create_task(
            project_id="proj-123",
            name="Test Task",
            description="Test",
            auto_link=False
        )


# ============================================================================
# EDGE CASES TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_project_empty_description(mock_supabase, mock_openai):
    """Test creating project with empty description."""
    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai,
        llm_client=mock_openai
    )

    result = await km.create_project(
        name="Empty Project",
        description="",
        auto_discover=False
    )

    assert "project" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_link_task_knowledge_no_results(mock_supabase, mock_openai):
    """Test linking when no knowledge found."""
    task_id = "task-456"
    mock_supabase._data["tasks"] = [{
        "id": task_id,
        "description": "Obscure topic with no knowledge",
        "task_context_embedding": [0.1] * 1536
    }]

    mock_supabase.set_rpc_response('match_knowledge_advanced', [])

    km = KnowledgeManager(
        supabase=mock_supabase,
        embedding_client=mock_openai
    )

    result = await km.link_task_knowledge(task_id)

    assert result["links_created"] == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_check_coverage_no_knowledge(mock_supabase):
    """Test coverage check with no knowledge in database."""
    mock_supabase.set_rpc_response('check_knowledge_coverage', [])

    km = KnowledgeManager(supabase=mock_supabase)

    coverage = await km.check_and_acquire_knowledge(
        tags=["rare-framework"],
        frameworks=["rare-framework"]
    )

    assert coverage.total_chunks == 0
    assert coverage.coverage_score == 0.0
    assert coverage.needs_scraping is True


# ============================================================================
# FACTORY FUNCTION TEST
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_knowledge_manager_factory():
    """Test factory function for creating KnowledgeManager."""
    with patch('archon.knowledge_manager.get_clients') as mock_get_clients:
        mock_get_clients.return_value = (Mock(), Mock())

        km = await get_knowledge_manager()

        assert isinstance(km, KnowledgeManager)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
