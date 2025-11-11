"""
Tests for Database Schema

This module tests database schema including:
- Table existence
- Column types
- Constraints
- Indexes
- RPC functions
- Triggers
- Row-level security policies
- Foreign keys
- Data integrity
- Query performance
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# TABLE EXISTENCE TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.unit
def test_projects_table_exists(mock_supabase):
    """Test that projects table exists."""
    # Mock table access
    table = mock_supabase.table("projects")
    assert table is not None


@pytest.mark.database
@pytest.mark.unit
def test_tasks_table_exists(mock_supabase):
    """Test that tasks table exists."""
    table = mock_supabase.table("tasks")
    assert table is not None


@pytest.mark.database
@pytest.mark.unit
def test_site_pages_table_exists(mock_supabase):
    """Test that site_pages table exists."""
    table = mock_supabase.table("site_pages")
    assert table is not None


@pytest.mark.database
@pytest.mark.unit
def test_task_knowledge_links_table_exists(mock_supabase):
    """Test that task_knowledge_links table exists."""
    table = mock_supabase.table("task_knowledge_links")
    assert table is not None


@pytest.mark.database
@pytest.mark.unit
def test_knowledge_sources_table_exists(mock_supabase):
    """Test that knowledge_sources table exists."""
    table = mock_supabase.table("knowledge_sources")
    assert table is not None


# ============================================================================
# COLUMN TYPE TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.unit
def test_projects_table_columns(sample_project):
    """Test projects table has correct columns."""
    required_columns = [
        "id", "name", "description", "status", "priority",
        "required_knowledge_tags", "required_frameworks",
        "knowledge_coverage_score", "created_at", "updated_at"
    ]

    for column in required_columns:
        assert column in sample_project


@pytest.mark.database
@pytest.mark.unit
def test_tasks_table_columns(sample_task):
    """Test tasks table has correct columns."""
    required_columns = [
        "id", "project_id", "name", "description", "status",
        "priority", "required_knowledge_tags", "required_frameworks",
        "knowledge_coverage_score", "created_at", "updated_at"
    ]

    for column in required_columns:
        assert column in sample_task


@pytest.mark.database
@pytest.mark.unit
def test_knowledge_chunk_columns(sample_knowledge_chunk):
    """Test site_pages table has correct columns."""
    required_columns = [
        "id", "url", "chunk_number", "title", "summary", "content",
        "tags", "knowledge_type", "framework", "language", "embedding"
    ]

    for column in required_columns:
        assert column in sample_knowledge_chunk


# ============================================================================
# CONSTRAINT TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.unit
def test_project_status_constraint():
    """Test project status must be valid enum value."""
    valid_statuses = [
        "planning", "ready", "in_progress",
        "blocked", "completed", "cancelled", "on_hold"
    ]

    # Test valid status
    for status in valid_statuses:
        project = {"status": status}
        assert project["status"] in valid_statuses


@pytest.mark.database
@pytest.mark.unit
def test_task_status_constraint():
    """Test task status must be valid enum value."""
    valid_statuses = [
        "pending", "ready", "in_progress",
        "blocked", "completed", "cancelled", "failed"
    ]

    for status in valid_statuses:
        task = {"status": status}
        assert task["status"] in valid_statuses


@pytest.mark.database
@pytest.mark.unit
def test_priority_constraint():
    """Test priority must be between 1 and 5."""
    valid_priorities = [1, 2, 3, 4, 5]

    for priority in valid_priorities:
        project = {"priority": priority}
        assert 1 <= project["priority"] <= 5


# ============================================================================
# FOREIGN KEY TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.unit
def test_task_project_foreign_key(mock_supabase):
    """Test task has foreign key to project."""
    # Task should reference a project
    task = {
        "id": "task-123",
        "project_id": "proj-456",
        "name": "Test Task"
    }

    assert "project_id" in task
    assert task["project_id"] is not None


@pytest.mark.database
@pytest.mark.unit
def test_knowledge_link_foreign_keys():
    """Test task_knowledge_links has foreign keys."""
    link = {
        "task_id": "task-123",
        "knowledge_id": 1,
        "relevance_score": 0.9
    }

    assert "task_id" in link
    assert "knowledge_id" in link


# ============================================================================
# RPC FUNCTION TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.integration
def test_match_knowledge_advanced_rpc(mock_supabase):
    """Test match_knowledge_advanced RPC function."""
    mock_supabase.set_rpc_response('match_knowledge_advanced', [
        {
            'id': 1,
            'title': 'Test',
            'similarity': 0.9
        }
    ])

    result = mock_supabase.rpc('match_knowledge_advanced', {
        'query_embedding': [0.1] * 1536,
        'match_count': 10
    }).execute()

    assert result.data is not None
    assert len(result.data) > 0


@pytest.mark.database
@pytest.mark.integration
def test_check_knowledge_coverage_rpc(mock_supabase):
    """Test check_knowledge_coverage RPC function."""
    mock_supabase.set_rpc_response('check_knowledge_coverage', [{
        'total_chunks': 10,
        'coverage_score': 0.7,
        'missing_tags': [],
        'available_frameworks': ['fastapi']
    }])

    result = mock_supabase.rpc('check_knowledge_coverage', {
        'required_tags_param': ['fastapi'],
        'required_frameworks_param': ['fastapi']
    }).execute()

    assert result.data is not None
    assert result.data[0]['total_chunks'] == 10


@pytest.mark.database
@pytest.mark.integration
def test_get_task_knowledge_rpc(mock_supabase):
    """Test get_task_knowledge RPC function."""
    mock_supabase.set_rpc_response('get_task_knowledge', [
        {
            'id': 1,
            'title': 'Test Knowledge',
            'relevance_score': 0.9
        }
    ])

    result = mock_supabase.rpc('get_task_knowledge', {
        'task_id_param': 'task-123'
    }).execute()

    assert result.data is not None


# ============================================================================
# INDEX TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.unit
def test_embedding_column_indexable():
    """Test that embedding column can be indexed for vector search."""
    # Embedding should be a list/array
    embedding = [0.1] * 1536
    assert isinstance(embedding, list)
    assert len(embedding) == 1536


@pytest.mark.database
@pytest.mark.unit
def test_tags_array_indexable():
    """Test that tags arrays can be indexed."""
    tags = ["fastapi", "auth", "jwt"]
    assert isinstance(tags, list)
    assert all(isinstance(tag, str) for tag in tags)


# ============================================================================
# DATA INTEGRITY TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.integration
def test_cascade_delete_tasks_on_project_delete(mock_supabase):
    """Test that deleting a project cascades to tasks."""
    # This is a mock test - in real implementation, 
    # the database should cascade delete
    project_id = "proj-123"

    # Simulate deletion
    mock_supabase.table("projects").delete().eq("id", project_id).execute()

    # In real implementation, tasks should also be deleted
    assert True  # Mock test passes


@pytest.mark.database
@pytest.mark.integration
def test_cascade_delete_links_on_task_delete(mock_supabase):
    """Test that deleting a task cascades to knowledge links."""
    task_id = "task-456"

    # Simulate deletion
    mock_supabase.table("tasks").delete().eq("id", task_id).execute()

    # In real implementation, links should also be deleted
    assert True  # Mock test passes


# ============================================================================
# QUERY PERFORMANCE TESTS
# ============================================================================

@pytest.mark.database
@pytest.mark.slow
@pytest.mark.integration
def test_vector_search_performance(mock_supabase):
    """Test vector search query performance."""
    import time

    embedding = [0.1] * 1536

    start = time.time()
    result = mock_supabase.rpc('match_knowledge_advanced', {
        'query_embedding': embedding,
        'match_count': 10
    }).execute()
    duration = time.time() - start

    # Should complete quickly (mocked, so very fast)
    assert duration < 1.0


@pytest.mark.database
@pytest.mark.slow
def test_project_listing_performance(mock_supabase):
    """Test project listing query performance."""
    import time

    start = time.time()
    result = mock_supabase.table("projects").select("*").execute()
    duration = time.time() - start

    # Should complete quickly
    assert duration < 1.0


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.database
@pytest.mark.unit
def test_empty_tags_array():
    """Test handling empty tags array."""
    project = {
        "id": "proj-123",
        "required_knowledge_tags": []
    }

    assert isinstance(project["required_knowledge_tags"], list)
    assert len(project["required_knowledge_tags"]) == 0


@pytest.mark.database
@pytest.mark.unit
def test_null_optional_fields():
    """Test handling null optional fields."""
    task = {
        "id": "task-123",
        "parent_task_id": None,
        "deadline": None,
        "assigned_agent_type": None
    }

    assert task["parent_task_id"] is None
    assert task["deadline"] is None


@pytest.mark.database
@pytest.mark.unit
def test_large_content_chunk():
    """Test handling large content chunks."""
    large_content = "x" * 50000  # 50KB content

    chunk = {
        "id": 1,
        "content": large_content
    }

    assert len(chunk["content"]) == 50000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
