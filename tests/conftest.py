"""
Pytest configuration and shared fixtures for Archon Knowledge Management tests.

This module provides:
- Mock Supabase client
- Mock OpenAI client
- Test database setup/teardown
- Sample test data fixtures
- Mock environment variables
"""

import pytest
import asyncio
import os
import json
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "database: Database tests")
    config.addinivalue_line("markers", "ui: UI tests")


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# ENVIRONMENT FIXTURES
# ============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    env_vars = {
        'EMBEDDING_MODEL': 'text-embedding-3-small',
        'PRIMARY_MODEL': 'gpt-4o-mini',
        'BASE_URL': 'https://api.openai.com/v1',
        'LLM_API_KEY': 'test-api-key',
        'LLM_PROVIDER': 'OpenAI',
        'SUPABASE_URL': 'https://test.supabase.co',
        'SUPABASE_KEY': 'test-supabase-key'
    }

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    return env_vars


# ============================================================================
# SUPABASE MOCK FIXTURES
# ============================================================================

class MockSupabaseTable:
    """Mock Supabase table interface."""

    def __init__(self, table_name: str, data: Dict[str, List[Dict]] = None):
        self.table_name = table_name
        self.data = data or {}
        self._filter_key = None
        self._filter_value = None
        self._select_fields = "*"

    def select(self, fields: str = "*"):
        """Mock select operation."""
        self._select_fields = fields
        return self

    def insert(self, data: Dict[str, Any]):
        """Mock insert operation."""
        # Add ID if not present
        if 'id' not in data:
            data['id'] = f"test-{len(self.data.get(self.table_name, []))}"

        if self.table_name not in self.data:
            self.data[self.table_name] = []

        self.data[self.table_name].append(data)
        return MockSupabaseResponse([data])

    def update(self, data: Dict[str, Any]):
        """Mock update operation."""
        self._update_data = data
        return self

    def delete(self):
        """Mock delete operation."""
        return self

    def eq(self, key: str, value: Any):
        """Mock equality filter."""
        self._filter_key = key
        self._filter_value = value
        return self

    def like(self, key: str, pattern: str):
        """Mock LIKE filter."""
        self._filter_key = key
        self._filter_value = pattern
        return self

    def upsert(self, data: Dict[str, Any], on_conflict: str = None):
        """Mock upsert operation."""
        return self.insert(data)

    def execute(self):
        """Execute the query and return results."""
        if self.table_name not in self.data:
            return MockSupabaseResponse([])

        results = self.data[self.table_name]

        # Apply filters
        if self._filter_key and self._filter_value:
            results = [
                r for r in results
                if r.get(self._filter_key) == self._filter_value
            ]

        return MockSupabaseResponse(results)


class MockSupabaseResponse:
    """Mock Supabase response."""

    def __init__(self, data: List[Dict]):
        self.data = data


class MockSupabaseClient:
    """Mock Supabase client."""

    def __init__(self):
        self._data = {}
        self._rpc_responses = {}

    def table(self, table_name: str):
        """Get table interface."""
        return MockSupabaseTable(table_name, self._data)

    def rpc(self, function_name: str, params: Dict = None):
        """Mock RPC call."""
        return MockRPCResponse(self._rpc_responses.get(function_name, []))

    def set_rpc_response(self, function_name: str, response: List[Dict]):
        """Set mock RPC response."""
        self._rpc_responses[function_name] = response


class MockRPCResponse:
    """Mock RPC response."""

    def __init__(self, data: List[Dict]):
        self._data = data

    def execute(self):
        """Execute RPC and return results."""
        return MockSupabaseResponse(self._data)


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    return MockSupabaseClient()


# ============================================================================
# OPENAI MOCK FIXTURES
# ============================================================================

class MockEmbeddingResponse:
    """Mock OpenAI embedding response."""

    def __init__(self, embedding: List[float]):
        self.data = [MockEmbeddingData(embedding)]


class MockEmbeddingData:
    """Mock embedding data."""

    def __init__(self, embedding: List[float]):
        self.embedding = embedding


class MockChatCompletionResponse:
    """Mock OpenAI chat completion response."""

    def __init__(self, content: str):
        self.choices = [MockChoice(content)]


class MockChoice:
    """Mock choice in completion."""

    def __init__(self, content: str):
        self.message = MockMessage(content)


class MockMessage:
    """Mock message."""

    def __init__(self, content: str):
        self.content = content


class MockEmbeddings:
    """Mock embeddings API."""

    async def create(self, model: str, input: str):
        """Create mock embedding."""
        # Return deterministic embedding based on input
        embedding = [0.1] * 1536
        return MockEmbeddingResponse(embedding)


class MockChatCompletions:
    """Mock chat completions API."""

    def __init__(self, responses: Dict[str, str] = None):
        self.responses = responses or {}
        self.default_response = {
            "tags": ["test", "example"],
            "frameworks": ["pytest"],
            "language": "python",
            "complexity": "medium",
            "suggested_knowledge_types": ["documentation"],
            "confidence": 0.8
        }

    async def create(self, model: str, messages: List[Dict], **kwargs):
        """Create mock completion."""
        # Check if there's a specific response for this query
        user_message = messages[-1].get("content", "")

        for key, response in self.responses.items():
            if key in user_message:
                if isinstance(response, str):
                    return MockChatCompletionResponse(response)
                else:
                    return MockChatCompletionResponse(json.dumps(response))

        # Return default response
        return MockChatCompletionResponse(json.dumps(self.default_response))


class MockChat:
    """Mock chat API."""

    def __init__(self, responses: Dict[str, str] = None):
        self.completions = MockChatCompletions(responses)


class MockOpenAIClient:
    """Mock OpenAI client."""

    def __init__(self, chat_responses: Dict[str, str] = None):
        self.embeddings = MockEmbeddings()
        self.chat = MockChat(chat_responses)


@pytest.fixture
def mock_openai():
    """Create a mock OpenAI client."""
    return MockOpenAIClient()


@pytest.fixture
def mock_openai_with_responses():
    """Create a mock OpenAI client with custom responses."""
    def _create(responses: Dict[str, str]):
        return MockOpenAIClient(chat_responses=responses)
    return _create


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_project():
    """Sample project data."""
    return {
        "id": "proj-123",
        "name": "FastAPI Authentication System",
        "description": "Build a complete authentication system using FastAPI with JWT tokens",
        "status": "planning",
        "priority": 1,
        "required_knowledge_tags": ["fastapi", "jwt", "authentication", "security"],
        "required_frameworks": ["fastapi", "pydantic"],
        "knowledge_coverage_score": 0.75,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_task():
    """Sample task data."""
    return {
        "id": "task-456",
        "project_id": "proj-123",
        "name": "Implement JWT token generation",
        "description": "Create a function to generate JWT tokens with proper expiration",
        "status": "pending",
        "priority": 1,
        "required_knowledge_tags": ["jwt", "tokens", "security"],
        "required_frameworks": ["fastapi"],
        "knowledge_coverage_score": 0.8,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


@pytest.fixture
def sample_knowledge_chunk():
    """Sample knowledge chunk data."""
    return {
        "id": 1,
        "url": "https://fastapi.tiangolo.com/tutorial/security/",
        "chunk_number": 0,
        "title": "Security - First Steps",
        "summary": "FastAPI provides several tools to help with security in a straightforward way.",
        "content": "# Security - First Steps\n\nFastAPI provides several tools...",
        "tags": ["fastapi", "security", "authentication", "oauth2"],
        "knowledge_type": "documentation",
        "framework": "fastapi",
        "language": "python",
        "metadata": {
            "source_type": "documentation",
            "crawled_at": datetime.now(timezone.utc).isoformat()
        },
        "embedding": [0.1] * 1536,
        "similarity": 0.85
    }


@pytest.fixture
def sample_crawl_config():
    """Sample crawler configuration."""
    return {
        "source_url": "https://fastapi.tiangolo.com",
        "source_type": "documentation",
        "framework": "fastapi",
        "language": "python",
        "crawl_profile": "default",
        "sitemap_url": None,
        "url_patterns": [],
        "exclude_patterns": [],
        "metadata": {}
    }


@pytest.fixture
def sample_html_content():
    """Sample HTML content for crawler testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>FastAPI Tutorial</title>
    </head>
    <body>
        <h1>Getting Started with FastAPI</h1>
        <p>FastAPI is a modern, fast web framework for building APIs.</p>
        <pre><code class="language-python">
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}
        </code></pre>
        <a href="/tutorial/first-steps">First Steps</a>
        <a href="/tutorial/path-params">Path Parameters</a>
    </body>
    </html>
    """


@pytest.fixture
def sample_sitemap_xml():
    """Sample sitemap XML."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://fastapi.tiangolo.com/</loc>
        </url>
        <url>
            <loc>https://fastapi.tiangolo.com/tutorial/</loc>
        </url>
        <url>
            <loc>https://fastapi.tiangolo.com/tutorial/first-steps/</loc>
        </url>
    </urlset>
    """


@pytest.fixture
def sample_task_requirements():
    """Sample task requirements."""
    return {
        "tags": ["fastapi", "jwt", "authentication"],
        "frameworks": ["fastapi"],
        "language": "python",
        "complexity": "medium",
        "suggested_knowledge_types": ["documentation", "tutorial"],
        "confidence": 0.85
    }


@pytest.fixture
def sample_knowledge_chunks():
    """Sample list of knowledge chunks."""
    return [
        {
            "id": 1,
            "url": "https://fastapi.tiangolo.com/tutorial/security/",
            "chunk_number": 0,
            "title": "Security - First Steps",
            "summary": "FastAPI security basics",
            "content": "# Security\n\nFastAPI provides tools for security...",
            "tags": ["fastapi", "security", "oauth2"],
            "knowledge_type": "documentation",
            "framework": "fastapi",
            "language": "python",
            "metadata": {},
            "similarity": 0.9
        },
        {
            "id": 2,
            "url": "https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/",
            "chunk_number": 0,
            "title": "OAuth2 with Password and JWT",
            "summary": "Implementing JWT authentication",
            "content": "# OAuth2 with JWT\n\nLearn how to implement JWT...",
            "tags": ["fastapi", "jwt", "oauth2", "authentication"],
            "knowledge_type": "documentation",
            "framework": "fastapi",
            "language": "python",
            "metadata": {},
            "similarity": 0.95
        }
    ]


# ============================================================================
# MOCK REQUESTS FIXTURES
# ============================================================================

@pytest.fixture
def mock_requests(monkeypatch):
    """Mock requests library."""
    class MockResponse:
        def __init__(self, text: str, status_code: int = 200):
            self.text = text
            self.content = text.encode('utf-8')
            self.status_code = status_code

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

    def mock_get(url: str, **kwargs):
        if 'sitemap' in url:
            return MockResponse("""<?xml version="1.0" encoding="UTF-8"?>
            <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
                <url><loc>https://example.com/</loc></url>
            </urlset>""")
        else:
            return MockResponse("<html><body><h1>Test Page</h1></body></html>")

    monkeypatch.setattr("requests.get", mock_get)
    return mock_get


# ============================================================================
# HELPER FIXTURES
# ============================================================================

@pytest.fixture
def sample_embedding():
    """Sample embedding vector."""
    return [0.1] * 1536


@pytest.fixture
def temp_test_files(tmp_path):
    """Create temporary test files."""
    test_dir = tmp_path / "test_data"
    test_dir.mkdir()

    # Create sample JSON files
    (test_dir / "sample_project.json").write_text(json.dumps({
        "name": "Test Project",
        "description": "Test description"
    }))

    return test_dir


@pytest.fixture
def mock_progress_callback():
    """Mock progress callback function."""
    return Mock()


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup after each test."""
    yield
    # Add any necessary cleanup here
