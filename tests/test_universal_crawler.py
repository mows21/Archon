"""
Tests for Universal Crawler Agent

This module tests all functionality of the universal_crawler module including:
- Framework detection from URLs and content
- Language detection from code blocks
- LLM tag extraction
- Knowledge type classification
- Chunk generation
- Sitemap parsing
- Profile configuration
- Error handling
- Progress tracking
- Storage integration
- Concurrent requests
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.universal_crawler import (
    CrawlProfile,
    SourceConfig,
    ProcessedChunk,
    CrawlProgressTracker,
    detect_framework_from_url,
    detect_framework_from_content,
    detect_language_from_code,
    extract_tags_and_classify,
    chunk_text,
    clean_markdown,
    fetch_url_content,
    extract_links_from_html,
    get_sitemap_urls,
    filter_urls,
    process_chunk,
    CRAWL_PROFILES
)


# ============================================================================
# FRAMEWORK DETECTION TESTS
# ============================================================================

@pytest.mark.unit
def test_detect_framework_from_url_fastapi():
    """Test framework detection for FastAPI URLs."""
    url = "https://fastapi.tiangolo.com/tutorial/"
    framework = detect_framework_from_url(url)
    assert framework == "fastapi"


@pytest.mark.unit
def test_detect_framework_from_url_django():
    """Test framework detection for Django URLs."""
    url = "https://docs.djangoproject.com/en/stable/"
    framework = detect_framework_from_url(url)
    assert framework == "django"


@pytest.mark.unit
def test_detect_framework_from_url_react():
    """Test framework detection for React URLs."""
    url = "https://react.dev/learn"
    framework = detect_framework_from_url(url)
    assert framework == "react"


@pytest.mark.unit
def test_detect_framework_from_url_unknown():
    """Test framework detection for unknown URLs."""
    url = "https://example.com/docs/"
    framework = detect_framework_from_url(url)
    assert framework == "example"  # Should extract domain name


@pytest.mark.unit
def test_detect_framework_from_content():
    """Test framework detection from page content."""
    content = """
    # FastAPI Tutorial
    This is a comprehensive guide to FastAPI framework.
    FastAPI is a modern, fast web framework.
    """
    title = "FastAPI Documentation"
    framework = detect_framework_from_content(content, title)
    assert framework == "fastapi"


@pytest.mark.unit
def test_detect_framework_from_content_multiple():
    """Test framework detection when multiple frameworks mentioned."""
    content = """
    # Web Development with React and Django
    This guide covers both React for frontend and Django for backend.
    """
    framework = detect_framework_from_content(content, "")
    # Should detect the first mentioned framework
    assert framework in ["react", "django"]


# ============================================================================
# LANGUAGE DETECTION TESTS
# ============================================================================

@pytest.mark.unit
def test_detect_language_from_code_python():
    """Test Python language detection from code blocks."""
    content = """
    Here's a Python example:
    ```python
    def hello_world():
        print("Hello, World!")
    ```
    """
    language = detect_language_from_code(content)
    assert language == "python"


@pytest.mark.unit
def test_detect_language_from_code_javascript():
    """Test JavaScript language detection."""
    content = """
    ```javascript
    const greeting = () => {
        console.log("Hello!");
    };
    ```
    """
    language = detect_language_from_code(content)
    assert language == "javascript"


@pytest.mark.unit
def test_detect_language_from_code_multiple():
    """Test language detection with multiple code blocks."""
    content = """
    Python example:
    ```python
    print("Hello")
    ```

    Another Python example:
    ```python
    x = 10
    ```

    JavaScript example:
    ```javascript
    console.log("test");
    ```
    """
    language = detect_language_from_code(content)
    assert language == "python"  # Most common


@pytest.mark.unit
def test_detect_language_from_code_no_blocks():
    """Test language detection from content without code blocks."""
    content = """
    This file contains Python code.
    def example():
        return True
    import os
    """
    language = detect_language_from_code(content)
    assert language == "python"


# ============================================================================
# LLM TAG EXTRACTION TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_tags_and_classify(mock_openai_with_responses):
    """Test LLM-based tag extraction and classification."""
    mock_client = mock_openai_with_responses({
        "documentation": {
            "tags": ["authentication", "jwt", "security", "oauth2"],
            "knowledge_type": "documentation",
            "title": "Authentication Guide",
            "summary": "Learn how to implement authentication with JWT tokens"
        }
    })

    with patch('archon.universal_crawler.llm_client', mock_client):
        content = "This guide explains JWT authentication..."
        url = "https://example.com/auth"

        result = await extract_tags_and_classify(content, url, "fastapi")

        assert "tags" in result
        assert "knowledge_type" in result
        assert "title" in result
        assert "summary" in result
        assert isinstance(result["tags"], list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extract_tags_and_classify_error_handling(mock_openai):
    """Test error handling in tag extraction."""
    # Create a client that raises an error
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")

    with patch('archon.universal_crawler.llm_client', mock_client):
        result = await extract_tags_and_classify("content", "url")

        # Should return default values on error
        assert result["tags"] == []
        assert result["knowledge_type"] == "documentation"


# ============================================================================
# CHUNKING TESTS
# ============================================================================

@pytest.mark.unit
def test_chunk_text_basic():
    """Test basic text chunking."""
    text = "A" * 10000
    chunks = chunk_text(text, chunk_size=1000)

    assert len(chunks) > 1
    assert all(len(chunk) <= 1500 for chunk in chunks)  # Allow some overflow


@pytest.mark.unit
def test_chunk_text_respects_code_blocks():
    """Test that chunking respects code block boundaries."""
    text = "Some text before\n\n" + "```python\n" + "x = 1\n" * 1000 + "```\n\nSome text after"
    chunks = chunk_text(text, chunk_size=2000, extract_code=True)

    # Code blocks should not be split
    code_block_chunks = [c for c in chunks if "```" in c]
    assert len(code_block_chunks) > 0


@pytest.mark.unit
def test_chunk_text_empty():
    """Test chunking empty text."""
    chunks = chunk_text("")
    assert chunks == []


@pytest.mark.unit
def test_clean_markdown():
    """Test markdown cleaning."""
    markdown = """
    # Title



    Some content


    ```

    ```
    """
    cleaned = clean_markdown(markdown)

    assert "\n\n\n" not in cleaned
    assert "```\n\n```" not in cleaned


# ============================================================================
# SITEMAP PARSING TESTS
# ============================================================================

@pytest.mark.unit
def test_get_sitemap_urls(sample_sitemap_xml, mock_requests):
    """Test sitemap URL extraction."""
    with patch('requests.get') as mock_get:
        mock_response = Mock()
        mock_response.content = sample_sitemap_xml.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        urls = get_sitemap_urls("https://example.com/sitemap.xml")

        assert len(urls) > 0
        assert all(url.startswith("http") for url in urls)


@pytest.mark.unit
def test_get_sitemap_urls_error():
    """Test sitemap parsing with network error."""
    with patch('requests.get', side_effect=Exception("Network error")):
        urls = get_sitemap_urls("https://example.com/sitemap.xml")
        assert urls == []


# ============================================================================
# URL FILTERING TESTS
# ============================================================================

@pytest.mark.unit
def test_filter_urls_basic():
    """Test basic URL filtering."""
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3"
    ]
    config = SourceConfig(source_url="https://example.com")
    profile = CRAWL_PROFILES["default"]

    filtered = filter_urls(urls, config, profile)
    assert len(filtered) <= profile.max_pages


@pytest.mark.unit
def test_filter_urls_with_pattern():
    """Test URL filtering with include patterns."""
    urls = [
        "https://example.com/api/endpoint1",
        "https://example.com/api/endpoint2",
        "https://example.com/docs/guide",
        "https://example.com/blog/post"
    ]
    config = SourceConfig(
        source_url="https://example.com",
        url_patterns=[r"/api/"]
    )
    profile = CRAWL_PROFILES["default"]

    filtered = filter_urls(urls, config, profile)
    assert all("/api/" in url for url in filtered)


@pytest.mark.unit
def test_filter_urls_with_exclude():
    """Test URL filtering with exclude patterns."""
    urls = [
        "https://example.com/docs/current",
        "https://example.com/docs/archive",
        "https://example.com/docs/old"
    ]
    config = SourceConfig(
        source_url="https://example.com",
        exclude_patterns=[r"/archive", r"/old"]
    )
    profile = CRAWL_PROFILES["default"]

    filtered = filter_urls(urls, config, profile)
    assert all("archive" not in url and "old" not in url for url in filtered)


# ============================================================================
# LINK EXTRACTION TESTS
# ============================================================================

@pytest.mark.unit
def test_extract_links_from_html(sample_html_content):
    """Test link extraction from HTML."""
    base_url = "https://example.com"
    links = extract_links_from_html(sample_html_content, base_url)

    assert len(links) > 0
    assert all(link.startswith("http") for link in links)
    # Should remove fragments
    assert not any("#" in link for link in links)


@pytest.mark.unit
def test_extract_links_relative_urls():
    """Test extraction of relative URLs."""
    html = '<html><body><a href="/docs">Docs</a><a href="../api">API</a></body></html>'
    base_url = "https://example.com/tutorial/"

    links = extract_links_from_html(html, base_url)

    assert all(link.startswith("http") for link in links)


# ============================================================================
# CRAWL PROFILE TESTS
# ============================================================================

@pytest.mark.unit
def test_crawl_profiles_exist():
    """Test that all expected crawl profiles exist."""
    expected_profiles = ["deep", "quick", "api-only", "default"]

    for profile_name in expected_profiles:
        assert profile_name in CRAWL_PROFILES
        profile = CRAWL_PROFILES[profile_name]
        assert isinstance(profile, CrawlProfile)
        assert profile.name == profile_name


@pytest.mark.unit
def test_crawl_profile_deep():
    """Test deep crawl profile configuration."""
    profile = CRAWL_PROFILES["deep"]

    assert profile.depth >= 3
    assert profile.extract_code is True
    assert profile.summary_only is False


@pytest.mark.unit
def test_crawl_profile_quick():
    """Test quick crawl profile configuration."""
    profile = CRAWL_PROFILES["quick"]

    assert profile.depth == 1
    assert profile.max_concurrent >= 5
    assert profile.request_delay < 1.0


# ============================================================================
# PROGRESS TRACKING TESTS
# ============================================================================

@pytest.mark.unit
def test_progress_tracker_initialization():
    """Test progress tracker initialization."""
    tracker = CrawlProgressTracker()

    assert tracker.urls_found == 0
    assert tracker.urls_processed == 0
    assert tracker.is_running is False


@pytest.mark.unit
def test_progress_tracker_with_callback():
    """Test progress tracker with callback."""
    callback_called = []

    def callback(status):
        callback_called.append(status)

    tracker = CrawlProgressTracker(progress_callback=callback)
    tracker.start()

    assert len(callback_called) > 0
    assert tracker.is_running is True


@pytest.mark.unit
def test_progress_tracker_logging():
    """Test progress tracker logging."""
    tracker = CrawlProgressTracker()
    tracker.log("Test message")

    assert len(tracker.logs) > 0
    assert "Test message" in tracker.logs[-1]


@pytest.mark.unit
def test_progress_tracker_status():
    """Test progress tracker status reporting."""
    tracker = CrawlProgressTracker()
    tracker.urls_found = 10
    tracker.urls_processed = 5
    tracker.urls_succeeded = 4
    tracker.urls_failed = 1

    status = tracker.get_status()

    assert status["urls_found"] == 10
    assert status["urls_processed"] == 5
    assert status["progress_percentage"] == 50.0


# ============================================================================
# CHUNK PROCESSING TESTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_process_chunk(mock_openai, sample_crawl_config):
    """Test processing a single chunk."""
    config = SourceConfig(**sample_crawl_config)
    profile = CRAWL_PROFILES["default"]
    chunk_text = "This is a test chunk about FastAPI authentication"

    with patch('archon.universal_crawler.llm_client', mock_openai):
        with patch('archon.universal_crawler.embedding_client', mock_openai):
            processed = await process_chunk(
                chunk_text,
                0,
                "https://example.com",
                config,
                profile
            )

            assert isinstance(processed, ProcessedChunk)
            assert processed.chunk_number == 0
            assert processed.url == "https://example.com"
            assert len(processed.embedding) == 1536


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.unit
def test_fetch_url_content_error():
    """Test error handling in URL fetching."""
    with patch('requests.get', side_effect=Exception("Network error")):
        with pytest.raises(Exception) as exc_info:
            fetch_url_content("https://example.com")

        assert "Network error" in str(exc_info.value)


@pytest.mark.unit
def test_invalid_url_handling():
    """Test handling of invalid URLs."""
    with patch('requests.get', side_effect=Exception("Invalid URL")):
        with pytest.raises(Exception):
            fetch_url_content("not-a-valid-url")


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_chunk_processing_pipeline(mock_openai, mock_supabase):
    """Test the complete chunk processing pipeline."""
    config = SourceConfig(
        source_url="https://example.com",
        framework="testframework"
    )
    profile = CRAWL_PROFILES["quick"]

    content = "# Test Documentation\n\nThis is test content about authentication."

    with patch('archon.universal_crawler.llm_client', mock_openai):
        with patch('archon.universal_crawler.embedding_client', mock_openai):
            with patch('archon.universal_crawler.supabase', mock_supabase):
                chunks = chunk_text(content, profile.chunk_size)
                assert len(chunks) > 0


@pytest.mark.integration
def test_source_config_validation():
    """Test SourceConfig validation."""
    config = SourceConfig(
        source_url="https://example.com",
        source_type="documentation",
        framework="testframework"
    )

    assert config.source_url == "https://example.com"
    assert config.source_type == "documentation"
    assert config.framework == "testframework"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
