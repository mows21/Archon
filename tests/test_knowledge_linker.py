"""
Tests for Knowledge Linker Agent

This module tests all functionality of the knowledge_linker module including:
- Task requirement analysis
- Tag extraction with LLM
- Vector search operations
- Relevance score calculation
- Deduplication logic
- Link type classification
- Coverage score calculation
- Crawl source suggestions
- Batch linking operations
- Refresh logic
- Error handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.knowledge_linker import (
    LinkType,
    TaskRequirements,
    KnowledgeChunk,
    LinkResult,
    analyze_task_requirements,
    search_relevant_knowledge,
    calculate_relevance_score,
    deduplicate_chunks,
    determine_link_type,
    link_knowledge_to_task,
    calculate_coverage_score,
    suggest_crawl_sources,
    update_task_metadata,
    auto_link_task_knowledge,
    refresh_task_knowledge,
    batch_link_tasks,
    get_task_linked_knowledge
)


# ============================================================================
# TASK ANALYSIS TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_task_requirements_basic(mock_openai_with_responses):
    """Test basic task requirement analysis."""
    mock_client = mock_openai_with_responses({
        "FastAPI": {
            "tags": ["fastapi", "authentication", "jwt"],
            "frameworks": ["fastapi"],
            "language": "python",
            "complexity": "medium",
            "suggested_knowledge_types": ["documentation", "tutorial"],
            "confidence": 0.85
        }
    })

    with patch('archon.knowledge_linker.llm_client', mock_client):
        description = "Build a FastAPI authentication system with JWT tokens"
        requirements = await analyze_task_requirements(description, "Auth Task")

        assert isinstance(requirements, TaskRequirements)
        assert "fastapi" in requirements.tags or "fastapi" in requirements.frameworks
        assert requirements.language == "python"
        assert requirements.complexity in ["simple", "medium", "complex"]
        assert requirements.confidence > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_task_requirements_complex(mock_openai_with_responses):
    """Test analysis of complex task description."""
    mock_client = mock_openai_with_responses({
        "microservices": {
            "tags": ["microservices", "docker", "kubernetes", "api-gateway"],
            "frameworks": ["fastapi", "docker"],
            "language": "python",
            "complexity": "complex",
            "suggested_knowledge_types": ["documentation", "tutorial", "example"],
            "confidence": 0.9
        }
    })

    with patch('archon.knowledge_linker.llm_client', mock_client):
        description = """
        Design and implement a microservices architecture with:
        - API Gateway
        - Docker containers
        - Kubernetes orchestration
        - Service mesh
        """
        requirements = await analyze_task_requirements(description)

        assert requirements.complexity == "complex"
        assert len(requirements.tags) > 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_analyze_task_requirements_error_handling(mock_openai):
    """Test error handling in task analysis."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")

    with patch('archon.knowledge_linker.llm_client', mock_client):
        requirements = await analyze_task_requirements("test description")

        # Should return default requirements on error
        assert isinstance(requirements, TaskRequirements)
        assert requirements.confidence == 0.0


# ============================================================================
# KNOWLEDGE SEARCH TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_relevant_knowledge(mock_supabase, sample_task_requirements):
    """Test searching for relevant knowledge."""
    # Setup mock response
    mock_supabase.set_rpc_response('match_knowledge_advanced', [
        {
            'id': 1,
            'url': 'https://example.com/doc1',
            'chunk_number': 0,
            'title': 'Auth Guide',
            'summary': 'Authentication guide',
            'content': 'Content about auth...',
            'tags': ['authentication', 'jwt'],
            'knowledge_type': 'documentation',
            'framework': 'fastapi',
            'language': 'python',
            'similarity': 0.9,
            'metadata': {}
        }
    ])

    embedding = [0.1] * 1536
    requirements = TaskRequirements(**sample_task_requirements)

    with patch('archon.knowledge_linker.supabase', mock_supabase):
        chunks = await search_relevant_knowledge(embedding, requirements)

        assert len(chunks) > 0
        assert all(isinstance(chunk, KnowledgeChunk) for chunk in chunks)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_relevant_knowledge_no_results(mock_supabase, sample_task_requirements):
    """Test search with no results."""
    mock_supabase.set_rpc_response('match_knowledge_advanced', [])

    embedding = [0.1] * 1536
    requirements = TaskRequirements(**sample_task_requirements)

    with patch('archon.knowledge_linker.supabase', mock_supabase):
        chunks = await search_relevant_knowledge(embedding, requirements)

        assert chunks == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_relevant_knowledge_with_filters(mock_supabase):
    """Test search with various filters."""
    mock_supabase.set_rpc_response('match_knowledge_advanced', [
        {
            'id': 1,
            'url': 'https://example.com/doc1',
            'chunk_number': 0,
            'title': 'Test',
            'summary': 'Test',
            'content': 'Test content',
            'tags': ['test'],
            'knowledge_type': 'documentation',
            'framework': 'fastapi',
            'language': 'python',
            'similarity': 0.85,
            'metadata': {}
        }
    ])

    requirements = TaskRequirements(
        tags=["fastapi", "auth"],
        frameworks=["fastapi"],
        language="python",
        complexity="medium",
        suggested_knowledge_types=["documentation"],
        confidence=0.8
    )

    embedding = [0.1] * 1536

    with patch('archon.knowledge_linker.supabase', mock_supabase):
        chunks = await search_relevant_knowledge(
            embedding,
            requirements,
            match_count=10,
            match_threshold=0.7
        )

        assert len(chunks) > 0


# ============================================================================
# RELEVANCE SCORING TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_relevance_score_high(sample_task_requirements, sample_knowledge_chunk):
    """Test relevance score calculation with high match."""
    requirements = TaskRequirements(**sample_task_requirements)
    chunk = KnowledgeChunk(**sample_knowledge_chunk)

    score = await calculate_relevance_score("test task", requirements, chunk)

    assert 0 <= score <= 1
    assert score > chunk.similarity  # Should be boosted


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_relevance_score_tag_boost(sample_task_requirements):
    """Test relevance boost from tag overlap."""
    requirements = TaskRequirements(**sample_task_requirements)

    chunk = KnowledgeChunk(
        id=1,
        url="test.com",
        chunk_number=0,
        title="Test",
        summary="Test",
        content="Test",
        tags=["fastapi", "jwt"],  # Overlaps with requirements
        knowledge_type="documentation",
        framework="fastapi",
        language="python",
        similarity=0.7,
        metadata={}
    )

    score = await calculate_relevance_score("test", requirements, chunk)

    # Should have boost from tag overlap
    assert score > 0.7


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_relevance_score_framework_boost(sample_task_requirements):
    """Test relevance boost from framework match."""
    requirements = TaskRequirements(**sample_task_requirements)

    chunk = KnowledgeChunk(
        id=1,
        url="test.com",
        chunk_number=0,
        title="Test",
        summary="Test",
        content="Test",
        tags=[],
        knowledge_type="documentation",
        framework="fastapi",  # Matches requirements
        language="python",
        similarity=0.7,
        metadata={}
    )

    score = await calculate_relevance_score("test", requirements, chunk)

    assert score >= 0.7


# ============================================================================
# DEDUPLICATION TESTS
# ============================================================================

@pytest.mark.unit
def test_deduplicate_chunks_basic(sample_knowledge_chunks):
    """Test basic chunk deduplication."""
    chunks = [KnowledgeChunk(**c) for c in sample_knowledge_chunks]

    # Add duplicate URL with different chunk number
    chunks.append(KnowledgeChunk(
        id=3,
        url=sample_knowledge_chunks[0]["url"],  # Same URL
        chunk_number=1,
        title="Duplicate",
        summary="Duplicate",
        content="Duplicate",
        tags=[],
        knowledge_type="documentation",
        framework="fastapi",
        language="python",
        similarity=0.7,
        metadata={}
    ))

    deduplicated = deduplicate_chunks(chunks, max_chunks=10)

    # Should keep only the most relevant chunk per URL
    assert len(deduplicated) <= len(chunks)


@pytest.mark.unit
def test_deduplicate_chunks_max_limit():
    """Test deduplication respects max limit."""
    chunks = [
        KnowledgeChunk(
            id=i,
            url=f"https://example.com/doc{i}",
            chunk_number=0,
            title=f"Doc {i}",
            summary=f"Summary {i}",
            content=f"Content {i}",
            tags=[],
            knowledge_type="documentation",
            framework="test",
            language="python",
            similarity=0.9 - (i * 0.01),  # Descending relevance
            metadata={}
        )
        for i in range(20)
    ]

    deduplicated = deduplicate_chunks(chunks, max_chunks=10)

    assert len(deduplicated) <= 10


@pytest.mark.unit
def test_deduplicate_chunks_empty():
    """Test deduplication with empty list."""
    deduplicated = deduplicate_chunks([])
    assert deduplicated == []


# ============================================================================
# LINK TYPE CLASSIFICATION TESTS
# ============================================================================

@pytest.mark.unit
def test_determine_link_type_required():
    """Test required link type classification."""
    link_type = determine_link_type(relevance_score=0.9, has_tag_match=True)
    assert link_type == LinkType.REQUIRED


@pytest.mark.unit
def test_determine_link_type_suggested():
    """Test suggested link type classification."""
    link_type = determine_link_type(relevance_score=0.75, has_tag_match=False)
    assert link_type == LinkType.SUGGESTED


@pytest.mark.unit
def test_determine_link_type_reference():
    """Test reference link type classification."""
    link_type = determine_link_type(relevance_score=0.65, has_tag_match=False)
    assert link_type == LinkType.REFERENCE


@pytest.mark.unit
def test_determine_link_type_edge_cases():
    """Test link type at boundary values."""
    # Exactly at threshold
    link_type = determine_link_type(relevance_score=0.8, has_tag_match=True)
    assert link_type == LinkType.REQUIRED

    # Just below threshold
    link_type = determine_link_type(relevance_score=0.79, has_tag_match=False)
    assert link_type == LinkType.SUGGESTED


# ============================================================================
# LINK CREATION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_knowledge_to_task(mock_supabase):
    """Test creating a knowledge link."""
    with patch('archon.knowledge_linker.supabase', mock_supabase):
        success = await link_knowledge_to_task(
            task_id="task-123",
            knowledge_id=1,
            relevance_score=0.85,
            link_type=LinkType.REQUIRED,
            link_reason="Test link"
        )

        assert success is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_link_knowledge_to_task_error(mock_supabase):
    """Test error handling in link creation."""
    # Make the insert fail
    mock_supabase_error = MagicMock()
    mock_supabase_error.table().upsert().execute.side_effect = Exception("DB Error")

    with patch('archon.knowledge_linker.supabase', mock_supabase_error):
        success = await link_knowledge_to_task(
            task_id="task-123",
            knowledge_id=1,
            relevance_score=0.85,
            link_type=LinkType.REQUIRED
        )

        assert success is False


# ============================================================================
# COVERAGE CALCULATION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_coverage_score_full(sample_knowledge_chunks):
    """Test coverage calculation with full coverage."""
    required_tags = ["fastapi", "security", "jwt"]
    required_frameworks = ["fastapi"]
    chunks = [KnowledgeChunk(**c) for c in sample_knowledge_chunks]

    coverage, missing = await calculate_coverage_score(
        required_tags,
        required_frameworks,
        chunks
    )

    assert 0 <= coverage <= 1
    assert isinstance(missing, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_coverage_score_partial():
    """Test coverage calculation with partial coverage."""
    required_tags = ["fastapi", "jwt", "oauth2", "testing"]
    required_frameworks = ["fastapi", "pytest"]

    chunks = [
        KnowledgeChunk(
            id=1,
            url="test.com",
            chunk_number=0,
            title="Test",
            summary="Test",
            content="Test",
            tags=["fastapi", "jwt"],  # Only 2 of 4 tags
            knowledge_type="documentation",
            framework="fastapi",  # Only 1 of 2 frameworks
            language="python",
            similarity=0.9,
            metadata={}
        )
    ]

    coverage, missing = await calculate_coverage_score(
        required_tags,
        required_frameworks,
        chunks
    )

    assert coverage < 1.0
    assert len(missing) > 0
    assert "testing" in missing or "pytest" in missing


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_coverage_score_no_requirements():
    """Test coverage calculation with no requirements."""
    coverage, missing = await calculate_coverage_score([], [], [])

    # No requirements means full coverage if any knowledge exists
    assert coverage >= 0
    assert missing == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_calculate_coverage_score_no_knowledge():
    """Test coverage calculation with no knowledge."""
    required_tags = ["fastapi", "jwt"]
    required_frameworks = ["fastapi"]

    coverage, missing = await calculate_coverage_score(
        required_tags,
        required_frameworks,
        []
    )

    assert coverage == 0.0
    assert len(missing) > 0


# ============================================================================
# CRAWL SOURCE SUGGESTION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggest_crawl_sources(mock_openai_with_responses, sample_task_requirements):
    """Test crawl source suggestions."""
    mock_client = mock_openai_with_responses({
        "missing": {
            "sources": [
                {
                    "url": "https://fastapi.tiangolo.com/tutorial/security/",
                    "reason": "Official FastAPI security documentation",
                    "priority": "high"
                }
            ]
        }
    })

    requirements = TaskRequirements(**sample_task_requirements)
    missing = ["authentication", "oauth2"]

    with patch('archon.knowledge_linker.llm_client', mock_client):
        suggestions = await suggest_crawl_sources(missing, requirements)

        assert isinstance(suggestions, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_suggest_crawl_sources_empty():
    """Test suggestions with no missing knowledge."""
    requirements = TaskRequirements(
        tags=[],
        frameworks=[],
        language=None,
        complexity="simple",
        suggested_knowledge_types=[],
        confidence=0.8
    )

    suggestions = await suggest_crawl_sources([], requirements)

    assert suggestions == []


# ============================================================================
# TASK METADATA UPDATE TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_update_task_metadata(mock_supabase, sample_task_requirements):
    """Test updating task metadata."""
    requirements = TaskRequirements(**sample_task_requirements)

    with patch('archon.knowledge_linker.supabase', mock_supabase):
        success = await update_task_metadata(
            task_id="task-123",
            attached_knowledge_ids=[1, 2, 3],
            coverage_score=0.85,
            requirements=requirements
        )

        assert success is True


# ============================================================================
# AUTO-LINKING ORCHESTRATION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_link_task_knowledge_full_flow(mock_supabase, mock_openai, sample_task):
    """Test complete auto-linking workflow."""
    # Setup mocks
    mock_supabase.set_rpc_response('match_knowledge_advanced', [
        {
            'id': 1,
            'url': 'https://example.com/doc1',
            'chunk_number': 0,
            'title': 'Auth Guide',
            'summary': 'Authentication guide',
            'content': 'Content about auth...',
            'tags': ['authentication', 'jwt'],
            'knowledge_type': 'documentation',
            'framework': 'fastapi',
            'language': 'python',
            'similarity': 0.9,
            'metadata': {}
        }
    ])

    # Add task to mock database
    mock_supabase._data["tasks"] = [sample_task]

    with patch('archon.knowledge_linker.supabase', mock_supabase):
        with patch('archon.knowledge_linker.embedding_client', mock_openai):
            with patch('archon.knowledge_linker.llm_client', mock_openai):
                result = await auto_link_task_knowledge(
                    task_id=sample_task["id"],
                    task_name=sample_task["name"],
                    task_description=sample_task["description"]
                )

                assert isinstance(result, LinkResult)
                assert result.task_id == sample_task["id"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auto_link_task_knowledge_no_description(mock_supabase):
    """Test auto-linking with no task description."""
    mock_supabase._data["tasks"] = [{
        "id": "task-123",
        "name": "Test Task",
        "description": ""
    }]

    with patch('archon.knowledge_linker.supabase', mock_supabase):
        result = await auto_link_task_knowledge(task_id="task-123")

        assert result.links_created == 0
        assert "No task description" in result.missing_knowledge


# ============================================================================
# BATCH OPERATIONS TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_link_tasks(mock_supabase, mock_openai):
    """Test linking knowledge to multiple tasks in parallel."""
    task_ids = ["task-1", "task-2", "task-3"]

    # Add tasks to mock database
    mock_supabase._data["tasks"] = [
        {
            "id": tid,
            "name": f"Task {tid}",
            "description": "Test description"
        }
        for tid in task_ids
    ]

    with patch('archon.knowledge_linker.supabase', mock_supabase):
        with patch('archon.knowledge_linker.embedding_client', mock_openai):
            with patch('archon.knowledge_linker.llm_client', mock_openai):
                results = await batch_link_tasks(task_ids)

                assert len(results) == len(task_ids)
                assert all(task_id in results for task_id in task_ids)


# ============================================================================
# REFRESH TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_task_knowledge(mock_supabase, mock_openai):
    """Test refreshing task knowledge links."""
    task_id = "task-123"

    mock_supabase._data["tasks"] = [{
        "id": task_id,
        "name": "Test Task",
        "description": "Test description with FastAPI"
    }]

    with patch('archon.knowledge_linker.supabase', mock_supabase):
        with patch('archon.knowledge_linker.embedding_client', mock_openai):
            with patch('archon.knowledge_linker.llm_client', mock_openai):
                result = await refresh_task_knowledge(task_id)

                assert isinstance(result, LinkResult)
                assert result.task_id == task_id


# ============================================================================
# RETRIEVAL TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_task_linked_knowledge(mock_supabase):
    """Test retrieving linked knowledge for a task."""
    task_id = "task-123"

    mock_supabase.set_rpc_response('get_task_knowledge', [
        {
            'id': 1,
            'url': 'https://example.com/doc1',
            'title': 'Test Doc',
            'summary': 'Test summary',
            'content': 'Test content',
            'tags': ['test'],
            'knowledge_type': 'documentation',
            'framework': 'test',
            'relevance_score': 0.9,
            'link_type': 'suggested'
        }
    ])

    with patch('archon.knowledge_linker.supabase', mock_supabase):
        chunks = await get_task_linked_knowledge(task_id)

        assert len(chunks) > 0
        assert all(isinstance(chunk, KnowledgeChunk) for chunk in chunks)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
