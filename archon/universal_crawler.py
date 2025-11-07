"""
Universal Web Scraper Agent for Archon Knowledge Management System

This module provides a flexible, intelligent web scraper that can crawl any documentation
source and automatically tag, classify, and store content with enhanced metadata.

Features:
- Multi-source support (any URL, sitemap, or domain)
- Intelligent content extraction with auto-detection
- Smart tagging using LLM
- Framework and language detection
- Knowledge type classification
- Crawling profiles (deep, quick, api-only)
- Progress tracking with callbacks
- Retry logic and error handling
- Integration with Supabase enhanced schema
"""

import os
import sys
import asyncio
import threading
import requests
import json
import time
import re
from typing import List, Dict, Any, Optional, Callable, Literal
from xml.etree import ElementTree
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from dotenv import load_dotenv
from openai import AsyncOpenAI
import html2text
from bs4 import BeautifulSoup

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import get_env_var, get_clients

load_dotenv()

# Initialize clients
embedding_client, supabase = get_clients()

# Configuration
embedding_model = get_env_var('EMBEDDING_MODEL') or 'text-embedding-3-small'
primary_model = get_env_var('PRIMARY_MODEL') or 'gpt-4o-mini'

# LLM client setup
base_url = get_env_var('BASE_URL') or 'https://api.openai.com/v1'
api_key = get_env_var('LLM_API_KEY') or 'no-api-key-provided'
provider = get_env_var('LLM_PROVIDER') or 'OpenAI'

if provider == "Ollama":
    if api_key == "NOT_REQUIRED":
        api_key = "ollama"
    llm_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
else:
    llm_client = AsyncOpenAI(base_url=base_url, api_key=api_key)

# HTML to Markdown converter
html_converter = html2text.HTML2Text()
html_converter.ignore_links = False
html_converter.ignore_images = False
html_converter.ignore_tables = False
html_converter.body_width = 0


# ============================================================================
# CONFIGURATION CLASSES
# ============================================================================

@dataclass
class CrawlProfile:
    """Defines crawling behavior and extraction settings."""
    name: str
    depth: int = 1  # How many levels deep to crawl
    chunk_size: int = 5000  # Size of text chunks
    max_pages: int = 100  # Maximum pages to crawl
    extract_code: bool = True  # Whether to extract code blocks
    summary_only: bool = False  # Only extract summaries
    filter_pattern: Optional[str] = None  # URL pattern to filter (regex)
    max_concurrent: int = 5  # Concurrent requests
    retry_count: int = 3  # Number of retries on failure
    retry_delay: int = 2  # Delay between retries (seconds)
    request_delay: float = 1.0  # Delay between requests (seconds)


# Predefined crawling profiles
CRAWL_PROFILES = {
    "deep": CrawlProfile(
        name="deep",
        depth=5,
        chunk_size=5000,
        max_pages=500,
        extract_code=True,
        summary_only=False,
        max_concurrent=3,
        request_delay=2.0
    ),
    "quick": CrawlProfile(
        name="quick",
        depth=1,
        chunk_size=10000,
        max_pages=50,
        extract_code=False,
        summary_only=True,
        max_concurrent=10,
        request_delay=0.5
    ),
    "api-only": CrawlProfile(
        name="api-only",
        depth=2,
        chunk_size=3000,
        max_pages=200,
        extract_code=True,
        filter_pattern=r"/(api|reference)/",
        max_concurrent=5,
        request_delay=1.0
    ),
    "default": CrawlProfile(
        name="default",
        depth=2,
        chunk_size=5000,
        max_pages=100,
        extract_code=True,
        summary_only=False,
        max_concurrent=5,
        request_delay=1.0
    )
}


@dataclass
class SourceConfig:
    """Configuration for a knowledge source to crawl."""
    source_url: str
    source_type: Literal['documentation', 'github', 'tutorial', 'blog', 'api', 'other'] = 'documentation'
    framework: Optional[str] = None  # Auto-detected if None
    language: Optional[str] = None  # Auto-detected if None
    crawl_profile: str = 'default'
    sitemap_url: Optional[str] = None  # If different from source_url
    url_patterns: List[str] = field(default_factory=list)  # Additional URL patterns to include
    exclude_patterns: List[str] = field(default_factory=list)  # URL patterns to exclude
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata


@dataclass
class ProcessedChunk:
    """Represents a processed documentation chunk ready for storage."""
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str
    tags: List[str]
    knowledge_type: str
    framework: Optional[str]
    language: Optional[str]
    metadata: Dict[str, Any]
    embedding: List[float]


# ============================================================================
# PROGRESS TRACKING
# ============================================================================

class CrawlProgressTracker:
    """Tracks and reports crawling progress with callback support."""

    def __init__(self, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.progress_callback = progress_callback
        self.urls_found = 0
        self.urls_processed = 0
        self.urls_succeeded = 0
        self.urls_failed = 0
        self.chunks_stored = 0
        self.logs = []
        self.is_running = False
        self.start_time = None
        self.end_time = None
        self.current_phase = "Initializing"

    def log(self, message: str):
        """Add a log message and trigger callback."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.logs.append(log_entry)
        print(message)

        if self.progress_callback:
            self.progress_callback(self.get_status())

    def set_phase(self, phase: str):
        """Update the current phase."""
        self.current_phase = phase
        self.log(f"Phase: {phase}")

    def start(self):
        """Mark crawling as started."""
        self.is_running = True
        self.start_time = datetime.now()
        self.log("Crawling process started")

        if self.progress_callback:
            self.progress_callback(self.get_status())

    def complete(self):
        """Mark crawling as completed."""
        self.is_running = False
        self.end_time = datetime.now()
        duration = self.end_time - self.start_time if self.start_time else None
        duration_str = str(duration).split('.')[0] if duration else "unknown"
        self.log(f"Crawling completed in {duration_str}")

        if self.progress_callback:
            self.progress_callback(self.get_status())

    def get_status(self) -> Dict[str, Any]:
        """Get current crawling status."""
        return {
            "is_running": self.is_running,
            "current_phase": self.current_phase,
            "urls_found": self.urls_found,
            "urls_processed": self.urls_processed,
            "urls_succeeded": self.urls_succeeded,
            "urls_failed": self.urls_failed,
            "chunks_stored": self.chunks_stored,
            "progress_percentage": (self.urls_processed / self.urls_found * 100) if self.urls_found > 0 else 0,
            "logs": self.logs[-50:],  # Last 50 logs
            "start_time": self.start_time,
            "end_time": self.end_time
        }


# ============================================================================
# FRAMEWORK AND LANGUAGE DETECTION
# ============================================================================

def detect_framework_from_url(url: str) -> Optional[str]:
    """Extract framework name from URL patterns."""
    url_lower = url.lower()

    # Common framework URL patterns
    patterns = {
        'fastapi': r'fastapi',
        'pydantic': r'pydantic',
        'django': r'django',
        'flask': r'flask',
        'react': r'react',
        'vue': r'vue',
        'angular': r'angular',
        'nextjs': r'nextjs',
        'express': r'express',
        'nestjs': r'nestjs',
        'spring': r'spring',
        'laravel': r'laravel',
        'rails': r'rubyonrails',
        'pytorch': r'pytorch',
        'tensorflow': r'tensorflow',
        'numpy': r'numpy',
        'pandas': r'pandas',
        'scikit-learn': r'scikit-learn|sklearn',
        'streamlit': r'streamlit',
        'gradio': r'gradio',
    }

    for framework, pattern in patterns.items():
        if re.search(pattern, url_lower):
            return framework

    # Try to extract from domain
    domain = urlparse(url).netloc
    if domain:
        # Remove common suffixes
        name = domain.replace('www.', '').split('.')[0]
        if name and len(name) > 2:
            return name

    return None


def detect_framework_from_content(content: str, title: str = "") -> Optional[str]:
    """Detect framework from page content and title."""
    combined = (title + " " + content[:2000]).lower()

    frameworks = [
        'fastapi', 'pydantic', 'django', 'flask', 'react', 'vue', 'angular',
        'nextjs', 'express', 'nestjs', 'spring', 'laravel', 'rails',
        'pytorch', 'tensorflow', 'numpy', 'pandas', 'scikit-learn',
        'streamlit', 'gradio', 'svelte', 'tailwind', 'bootstrap'
    ]

    for framework in frameworks:
        if framework in combined:
            return framework

    return None


def detect_language_from_code(content: str) -> Optional[str]:
    """Detect programming language from code blocks in content."""
    # Extract code blocks
    code_blocks = re.findall(r'```(\w+)\n', content)

    if code_blocks:
        # Return most common language
        from collections import Counter
        lang_counts = Counter(code_blocks)
        return lang_counts.most_common(1)[0][0] if lang_counts else None

    # Fallback: Look for language indicators in content
    indicators = {
        'python': [r'def \w+\(', r'import \w+', r'from \w+ import', r'class \w+:', r'\.py\b'],
        'javascript': [r'function \w+\(', r'const \w+ =', r'let \w+ =', r'=>', r'\.js\b'],
        'typescript': [r'interface \w+', r'type \w+ =', r': \w+\[\]', r'\.ts\b'],
        'java': [r'public class', r'private void', r'@Override', r'\.java\b'],
        'go': [r'func \w+\(', r'package main', r'import \(', r'\.go\b'],
        'rust': [r'fn \w+\(', r'impl \w+', r'pub struct', r'\.rs\b'],
        'ruby': [r'def \w+', r'class \w+ <', r'\.rb\b'],
        'php': [r'<\?php', r'function \w+\(', r'\$\w+', r'\.php\b'],
    }

    content_sample = content[:3000]
    scores = {}

    for lang, patterns in indicators.items():
        score = sum(1 for pattern in patterns if re.search(pattern, content_sample, re.IGNORECASE))
        if score > 0:
            scores[lang] = score

    if scores:
        return max(scores.items(), key=lambda x: x[1])[0]

    return None


# ============================================================================
# LLM-BASED EXTRACTION
# ============================================================================

async def extract_tags_and_classify(content: str, url: str, framework: Optional[str] = None) -> Dict[str, Any]:
    """Use LLM to extract tags and classify knowledge type."""

    # Prepare context
    context = f"URL: {url}\n"
    if framework:
        context += f"Framework: {framework}\n"
    context += f"\nContent Preview:\n{content[:2000]}"

    system_prompt = """You are an AI that analyzes technical documentation and extracts metadata.

Given a documentation chunk, extract:
1. tags: 5-10 relevant technical tags (e.g., ['authentication', 'jwt', 'security', 'oauth2'])
2. knowledge_type: One of: documentation, tutorial, api_reference, example, blog, other
3. title: Concise title for this content
4. summary: 2-3 sentence summary of the main points

Return ONLY a JSON object with these exact keys: tags, knowledge_type, title, summary.
Tags should be lowercase, single words or short phrases.
Focus on technical concepts, features, and topics."""

    try:
        response = await llm_client.chat.completions.create(
            model=primary_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )

        result = json.loads(response.choices[0].message.content)

        # Validate and normalize
        return {
            "tags": result.get("tags", [])[:10],  # Limit to 10 tags
            "knowledge_type": result.get("knowledge_type", "documentation"),
            "title": result.get("title", "Untitled"),
            "summary": result.get("summary", "No summary available")
        }

    except Exception as e:
        print(f"Error in LLM extraction: {e}")
        return {
            "tags": [],
            "knowledge_type": "documentation",
            "title": "Error processing title",
            "summary": "Error processing summary"
        }


async def get_embedding(text: str) -> List[float]:
    """Generate embedding vector for text."""
    try:
        response = await embedding_client.embeddings.create(
            model=embedding_model,
            input=text[:8000]  # Limit input size
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        # Return zero vector on error
        return [0.0] * 1536


# ============================================================================
# CONTENT EXTRACTION AND CHUNKING
# ============================================================================

def chunk_text(text: str, chunk_size: int = 5000, extract_code: bool = True) -> List[str]:
    """Split text into intelligent chunks respecting code blocks and structure."""
    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size

        if end >= text_length:
            chunks.append(text[start:].strip())
            break

        # Try to find natural break points
        chunk = text[start:end]

        # Priority 1: Code block boundary
        if extract_code:
            code_block = chunk.rfind('```')
            if code_block != -1 and code_block > chunk_size * 0.3:
                end = start + code_block

        # Priority 2: Section header
        if end == start + chunk_size:  # No code block found
            header = re.search(r'\n#{1,6} .+\n', chunk[::-1])
            if header:
                header_pos = len(chunk) - header.start()
                if header_pos > chunk_size * 0.3:
                    end = start + header_pos

        # Priority 3: Paragraph boundary
        if end == start + chunk_size:  # No header found
            last_break = chunk.rfind('\n\n')
            if last_break > chunk_size * 0.3:
                end = start + last_break

        # Priority 4: Sentence boundary
        if end == start + chunk_size:  # No paragraph break
            last_period = chunk.rfind('. ')
            if last_period > chunk_size * 0.3:
                end = start + last_period + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        start = max(start + 1, end)

    return chunks


def clean_markdown(markdown: str) -> str:
    """Clean and normalize markdown content."""
    # Remove excessive newlines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)

    # Remove navigation/menu artifacts
    markdown = re.sub(r'\[\s*\]\([^)]*\)\s*{[^}]*}', '', markdown)

    # Clean up code block markers
    markdown = re.sub(r'```\s*\n\s*```', '', markdown)

    return markdown.strip()


# ============================================================================
# WEB CRAWLING
# ============================================================================

def fetch_url_content(url: str) -> tuple[str, str]:
    """Fetch URL and convert to markdown. Returns (markdown, raw_html)."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; ArchonBot/1.0; +https://github.com/archon)'
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        # Convert HTML to Markdown
        markdown = html_converter.handle(response.text)
        markdown = clean_markdown(markdown)

        return markdown, response.text

    except Exception as e:
        raise Exception(f"Error fetching {url}: {str(e)}")


def extract_links_from_html(html: str, base_url: str) -> List[str]:
    """Extract all links from HTML content."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        links = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Convert relative URLs to absolute
            absolute_url = urljoin(base_url, href)
            # Remove fragments
            absolute_url = absolute_url.split('#')[0]
            links.append(absolute_url)

        return list(set(links))  # Remove duplicates

    except Exception as e:
        print(f"Error extracting links: {e}")
        return []


def get_sitemap_urls(sitemap_url: str) -> List[str]:
    """Extract URLs from XML sitemap."""
    try:
        response = requests.get(sitemap_url, timeout=30)
        response.raise_for_status()

        root = ElementTree.fromstring(response.content)
        namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = [loc.text for loc in root.findall('.//ns:loc', namespace)]

        return urls

    except Exception as e:
        print(f"Error fetching sitemap: {e}")
        return []


def filter_urls(urls: List[str], config: SourceConfig, profile: CrawlProfile) -> List[str]:
    """Filter URLs based on configuration and profile."""
    filtered = []

    for url in urls:
        # Apply profile filter pattern
        if profile.filter_pattern:
            if not re.search(profile.filter_pattern, url):
                continue

        # Apply exclude patterns
        if any(re.search(pattern, url) for pattern in config.exclude_patterns):
            continue

        # Apply include patterns (if specified)
        if config.url_patterns:
            if not any(re.search(pattern, url) for pattern in config.url_patterns):
                continue

        filtered.append(url)

    return filtered[:profile.max_pages]


# ============================================================================
# CHUNK PROCESSING
# ============================================================================

async def process_chunk(
    chunk: str,
    chunk_number: int,
    url: str,
    config: SourceConfig,
    profile: CrawlProfile
) -> ProcessedChunk:
    """Process a single chunk with all metadata extraction."""

    # Extract tags and classify using LLM
    llm_result = await extract_tags_and_classify(chunk, url, config.framework)

    # Detect framework if not provided
    framework = config.framework
    if not framework:
        framework = detect_framework_from_url(url)
        if not framework:
            framework = detect_framework_from_content(chunk, llm_result['title'])

    # Detect language if not provided
    language = config.language
    if not language:
        language = detect_language_from_code(chunk)

    # Get embedding
    embedding = await get_embedding(chunk)

    # Build metadata
    metadata = {
        "source_type": config.source_type,
        "crawl_profile": profile.name,
        "chunk_size": len(chunk),
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "url_path": urlparse(url).path,
        **config.metadata  # Include any additional metadata
    }

    return ProcessedChunk(
        url=url,
        chunk_number=chunk_number,
        title=llm_result['title'],
        summary=llm_result['summary'],
        content=chunk,
        tags=llm_result['tags'],
        knowledge_type=llm_result['knowledge_type'],
        framework=framework,
        language=language,
        metadata=metadata,
        embedding=embedding
    )


async def insert_chunk(chunk: ProcessedChunk) -> bool:
    """Insert processed chunk into Supabase."""
    try:
        data = {
            "url": chunk.url,
            "chunk_number": chunk.chunk_number,
            "title": chunk.title,
            "summary": chunk.summary,
            "content": chunk.content,
            "tags": chunk.tags,
            "knowledge_type": chunk.knowledge_type,
            "framework": chunk.framework,
            "language": chunk.language,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding
        }

        result = supabase.table("site_pages").insert(data).execute()
        return True

    except Exception as e:
        print(f"Error inserting chunk: {e}")
        return False


async def process_and_store_document(
    url: str,
    markdown: str,
    config: SourceConfig,
    profile: CrawlProfile,
    tracker: Optional[CrawlProgressTracker] = None
):
    """Process a document into chunks and store them."""

    # Split into chunks
    chunks = chunk_text(markdown, profile.chunk_size, profile.extract_code)

    if tracker:
        tracker.log(f"Split {url} into {len(chunks)} chunks")

    # Process chunks in parallel
    tasks = [
        process_chunk(chunk, i, url, config, profile)
        for i, chunk in enumerate(chunks)
    ]
    processed_chunks = await asyncio.gather(*tasks)

    if tracker:
        tracker.log(f"Processed {len(processed_chunks)} chunks for {url}")

    # Store chunks
    insert_tasks = [insert_chunk(chunk) for chunk in processed_chunks]
    results = await asyncio.gather(*insert_tasks)

    successful = sum(1 for r in results if r)

    if tracker:
        tracker.chunks_stored += successful
        tracker.log(f"Stored {successful}/{len(results)} chunks for {url}")


# ============================================================================
# MAIN CRAWLER
# ============================================================================

async def crawl_url_with_retry(
    url: str,
    config: SourceConfig,
    profile: CrawlProfile,
    tracker: Optional[CrawlProgressTracker] = None
) -> bool:
    """Crawl a single URL with retry logic."""

    for attempt in range(profile.retry_count):
        try:
            if tracker:
                tracker.log(f"Crawling: {url} (attempt {attempt + 1}/{profile.retry_count})")

            # Fetch content
            markdown, html = fetch_url_content(url)

            if not markdown or len(markdown) < 100:
                if tracker:
                    tracker.log(f"Skipping {url}: Insufficient content")
                return False

            # Process and store
            await process_and_store_document(url, markdown, config, profile, tracker)

            return True

        except Exception as e:
            if tracker:
                tracker.log(f"Attempt {attempt + 1} failed for {url}: {str(e)}")

            if attempt < profile.retry_count - 1:
                await asyncio.sleep(profile.retry_delay)
            else:
                if tracker:
                    tracker.log(f"Failed to crawl {url} after {profile.retry_count} attempts")
                return False


async def crawl_parallel(
    urls: List[str],
    config: SourceConfig,
    profile: CrawlProfile,
    tracker: Optional[CrawlProgressTracker] = None
):
    """Crawl multiple URLs in parallel with concurrency control."""

    semaphore = asyncio.Semaphore(profile.max_concurrent)

    async def process_with_semaphore(url: str):
        async with semaphore:
            success = await crawl_url_with_retry(url, config, profile, tracker)

            if tracker:
                tracker.urls_processed += 1
                if success:
                    tracker.urls_succeeded += 1
                else:
                    tracker.urls_failed += 1

                if tracker.progress_callback:
                    tracker.progress_callback(tracker.get_status())

            # Delay between requests
            await asyncio.sleep(profile.request_delay)

    # Process all URLs
    await asyncio.gather(*[process_with_semaphore(url) for url in urls])


async def crawl_source(
    config: SourceConfig,
    profile_name: str = 'default',
    tracker: Optional[CrawlProgressTracker] = None,
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main crawling function for a knowledge source.

    Args:
        config: Source configuration
        profile_name: Name of crawling profile to use
        tracker: Progress tracker (optional)
        source_id: Knowledge source ID in database (optional)

    Returns:
        Dictionary with crawl statistics
    """

    # Get profile
    profile = CRAWL_PROFILES.get(profile_name, CRAWL_PROFILES['default'])

    # Initialize tracker
    if tracker:
        tracker.start()
        tracker.set_phase("Discovering URLs")

    # Update source status in database
    if source_id and supabase:
        try:
            supabase.table("knowledge_sources").update({
                "crawl_status": "in-progress",
                "last_crawled": datetime.now(timezone.utc).isoformat()
            }).eq("id", source_id).execute()
        except Exception as e:
            print(f"Error updating source status: {e}")

    # Discover URLs
    urls = []

    # Try sitemap first
    if config.sitemap_url:
        if tracker:
            tracker.log(f"Fetching sitemap: {config.sitemap_url}")
        sitemap_urls = get_sitemap_urls(config.sitemap_url)
        urls.extend(sitemap_urls)

    # If no sitemap or no URLs found, try auto-discovery
    if not urls:
        # Check for common sitemap locations
        domain = urlparse(config.source_url).scheme + "://" + urlparse(config.source_url).netloc
        common_sitemaps = [
            f"{domain}/sitemap.xml",
            f"{domain}/sitemap_index.xml",
            f"{config.source_url}/sitemap.xml"
        ]

        for sitemap_url in common_sitemaps:
            if tracker:
                tracker.log(f"Trying: {sitemap_url}")
            sitemap_urls = get_sitemap_urls(sitemap_url)
            if sitemap_urls:
                urls.extend(sitemap_urls)
                break

    # Fallback: Just crawl the source URL
    if not urls:
        if tracker:
            tracker.log("No sitemap found, using source URL only")
        urls = [config.source_url]

    # Filter URLs
    urls = filter_urls(urls, config, profile)

    if tracker:
        tracker.urls_found = len(urls)
        tracker.log(f"Found {len(urls)} URLs to crawl")
        tracker.set_phase("Crawling and Processing")

    # Clear existing records for this source
    if source_id and supabase:
        try:
            # Delete by framework or URL pattern
            if config.framework:
                supabase.table("site_pages").delete().eq("framework", config.framework).execute()
            else:
                # Delete by URL domain
                domain = urlparse(config.source_url).netloc
                supabase.table("site_pages").delete().like("url", f"%{domain}%").execute()

            if tracker:
                tracker.log("Cleared existing records for this source")
        except Exception as e:
            print(f"Error clearing existing records: {e}")

    # Crawl URLs
    start_time = datetime.now()
    await crawl_parallel(urls, config, profile, tracker)
    end_time = datetime.now()

    # Calculate stats
    duration_seconds = int((end_time - start_time).total_seconds())

    stats = {
        "urls_found": len(urls),
        "urls_processed": tracker.urls_processed if tracker else len(urls),
        "urls_succeeded": tracker.urls_succeeded if tracker else 0,
        "urls_failed": tracker.urls_failed if tracker else 0,
        "chunks_stored": tracker.chunks_stored if tracker else 0,
        "duration_seconds": duration_seconds
    }

    # Update source in database
    if source_id and supabase:
        try:
            supabase.table("knowledge_sources").update({
                "crawl_status": "completed",
                "total_pages_crawled": stats['urls_succeeded'],
                "total_chunks_created": stats['chunks_stored'],
                "last_crawl_duration_seconds": duration_seconds,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", source_id).execute()
        except Exception as e:
            print(f"Error updating source stats: {e}")

    if tracker:
        tracker.set_phase("Completed")
        tracker.complete()

    return stats


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def start_crawl_async(
    config: SourceConfig,
    profile_name: str = 'default',
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    source_id: Optional[str] = None
) -> CrawlProgressTracker:
    """
    Start crawling in a background thread and return tracker.

    Args:
        config: Source configuration
        profile_name: Crawling profile name
        progress_callback: Function to call with progress updates
        source_id: Knowledge source ID (optional)

    Returns:
        CrawlProgressTracker instance
    """

    tracker = CrawlProgressTracker(progress_callback)

    def run_crawl():
        try:
            asyncio.run(crawl_source(config, profile_name, tracker, source_id))
        except Exception as e:
            print(f"Error in crawl thread: {e}")
            tracker.log(f"Crawl error: {str(e)}")
            tracker.complete()

    thread = threading.Thread(target=run_crawl, daemon=True)
    thread.start()

    return tracker


async def crawl_from_config_dict(
    config_dict: Dict[str, Any],
    tracker: Optional[CrawlProgressTracker] = None
) -> Dict[str, Any]:
    """
    Crawl from a configuration dictionary (e.g., from database).

    Args:
        config_dict: Configuration dictionary with keys matching SourceConfig
        tracker: Progress tracker (optional)

    Returns:
        Crawl statistics
    """

    config = SourceConfig(
        source_url=config_dict['source_url'],
        source_type=config_dict.get('source_type', 'documentation'),
        framework=config_dict.get('framework'),
        language=config_dict.get('language'),
        crawl_profile=config_dict.get('crawl_config', {}).get('profile', 'default'),
        sitemap_url=config_dict.get('crawl_config', {}).get('sitemap_url'),
        url_patterns=config_dict.get('crawl_config', {}).get('url_patterns', []),
        exclude_patterns=config_dict.get('crawl_config', {}).get('exclude_patterns', []),
        metadata=config_dict.get('metadata', {})
    )

    profile_name = config_dict.get('crawl_config', {}).get('profile', 'default')
    source_id = config_dict.get('id')

    return await crawl_source(config, profile_name, tracker, source_id)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example of how to use the universal crawler."""

    # Example 1: Crawl FastAPI documentation
    fastapi_config = SourceConfig(
        source_url="https://fastapi.tiangolo.com",
        source_type="documentation",
        framework="fastapi",
        language="python",
        crawl_profile="deep"
    )

    # Example 2: Crawl with custom sitemap
    custom_config = SourceConfig(
        source_url="https://docs.example.com",
        sitemap_url="https://docs.example.com/sitemap.xml",
        crawl_profile="quick",
        exclude_patterns=[r'/archive/', r'/old/']
    )

    # Example 3: API documentation only
    api_config = SourceConfig(
        source_url="https://api.example.com/docs",
        crawl_profile="api-only",
        url_patterns=[r'/api/', r'/reference/']
    )

    # Run crawler with progress tracking
    def progress_handler(status):
        print(f"Progress: {status['progress_percentage']:.1f}% - {status['current_phase']}")

    tracker = start_crawl_async(fastapi_config, progress_callback=progress_handler)

    # Wait for completion
    while tracker.is_running:
        await asyncio.sleep(1)

    print(f"Crawl completed! Stored {tracker.chunks_stored} chunks")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
