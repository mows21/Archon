# Universal Web Scraper Agent - Complete Guide

## Overview

The Universal Web Scraper Agent is a production-ready, intelligent crawler for Archon's knowledge management system. It can crawl any documentation source and automatically extract, tag, classify, and store content with rich metadata.

## Key Features

### 🎯 Multi-Source Support
- Accept any documentation URL, sitemap, or domain
- Auto-discover sitemaps from common locations
- Support for custom URL patterns and exclusions

### 🧠 Intelligent Extraction
- Auto-detect documentation structure
- Respect code blocks, paragraphs, and sections when chunking
- Extract clean, well-formatted markdown content

### 🏷️ Smart Tagging with LLM
- **Framework Detection**: Extract from URL (e.g., `fastapi.tiangolo.com` → `fastapi`)
- **Language Detection**: Analyze code blocks for Python, JavaScript, TypeScript, Go, Rust, etc.
- **Knowledge Type Classification**: `documentation`, `tutorial`, `api_reference`, `example`, `blog`
- **Tag Extraction**: Use LLM to extract 5-10 relevant technical tags per chunk

### 💾 Enhanced Storage
Store in Supabase with complete schema fields:
- `tags` (TEXT[]): Technical concept tags
- `framework` (TEXT): Framework name
- `knowledge_type` (TEXT): Content classification
- `language` (TEXT): Programming language
- `embedding` (VECTOR): For semantic search
- Full metadata and tracking

### 📊 Progress Tracking
- Real-time progress updates via callbacks
- Detailed logging and status reporting
- Phase tracking (Discovering, Crawling, Processing, Completed)

### ⚡ Crawling Profiles
Pre-configured profiles for different use cases:
- **deep**: Thorough crawl (depth: 5, 500 pages max)
- **quick**: Fast update (depth: 1, 50 pages max)
- **api-only**: API documentation focus (depth: 2, filters for `/api/`)
- **default**: Balanced approach (depth: 2, 100 pages max)

## Installation & Setup

### Prerequisites

```bash
# Required packages (already in Archon)
pip install crawl4ai beautifulsoup4 html2text openai supabase python-dotenv
```

### Database Setup

The Universal Crawler uses the enhanced knowledge schema. Run the migration:

```bash
# Connect to your Supabase database and run:
psql -h your-db-host -U postgres -d postgres -f utils/knowledge_schema.sql
```

This adds to the existing `site_pages` table:
- `tags TEXT[]` - Array of technical tags
- `knowledge_type TEXT` - Content classification
- `framework TEXT` - Framework identifier
- `language TEXT` - Programming language
- Indexes for efficient querying

### Environment Variables

Ensure your `.env` or environment configuration includes:

```bash
# LLM for tag extraction and classification
LLM_PROVIDER=OpenAI
LLM_API_KEY=your-api-key
BASE_URL=https://api.openai.com/v1
PRIMARY_MODEL=gpt-4o-mini

# Embeddings
EMBEDDING_PROVIDER=OpenAI
EMBEDDING_API_KEY=your-api-key
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_MODEL=text-embedding-3-small

# Supabase
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-service-key
```

## Usage Guide

### Basic Usage

```python
import asyncio
from archon.universal_crawler import SourceConfig, crawl_source

async def main():
    # Configure your source
    config = SourceConfig(
        source_url="https://fastapi.tiangolo.com",
        source_type="documentation",
        framework="fastapi",
        language="python"
    )

    # Run the crawl
    stats = await crawl_source(config, profile_name='quick')

    print(f"Crawled {stats['urls_succeeded']} pages")
    print(f"Created {stats['chunks_stored']} knowledge chunks")

asyncio.run(main())
```

### With Progress Tracking

```python
from archon.universal_crawler import start_crawl_async

def progress_callback(status):
    print(f"Progress: {status['progress_percentage']:.1f}%")
    print(f"Phase: {status['current_phase']}")
    print(f"Chunks stored: {status['chunks_stored']}")

# Start async crawl
tracker = start_crawl_async(
    config=config,
    profile_name='deep',
    progress_callback=progress_callback
)

# Wait for completion
while tracker.is_running:
    await asyncio.sleep(1)

# Get final status
final_status = tracker.get_status()
```

### Advanced Configuration

```python
config = SourceConfig(
    source_url="https://docs.example.com",
    source_type="documentation",
    framework="my-framework",  # Or None for auto-detection
    language="python",  # Or None for auto-detection
    crawl_profile="deep",

    # Custom sitemap if different from source_url
    sitemap_url="https://docs.example.com/sitemap.xml",

    # URL patterns to INCLUDE
    url_patterns=[
        r'/docs/',
        r'/api/',
        r'/guides/'
    ],

    # URL patterns to EXCLUDE
    exclude_patterns=[
        r'/blog/',
        r'/archive/',
        r'/old/'
    ],

    # Additional metadata
    metadata={
        "version": "2.0",
        "category": "backend",
        "priority": "high"
    }
)
```

### Custom Crawl Profile

```python
from archon.universal_crawler import CrawlProfile, CRAWL_PROFILES

# Define custom profile
custom = CrawlProfile(
    name="tutorial-focused",
    depth=3,
    chunk_size=4000,
    max_pages=150,
    extract_code=True,
    summary_only=False,
    filter_pattern=r'/(tutorial|guide)/',
    max_concurrent=8,
    retry_count=2,
    request_delay=0.8
)

# Add to profiles
CRAWL_PROFILES['tutorial-focused'] = custom

# Use it
stats = await crawl_source(config, profile_name='tutorial-focused')
```

### Integration with Knowledge Sources Table

```python
from archon.universal_crawler import crawl_from_config_dict

# Fetch from database
source = supabase.table("knowledge_sources").select("*").eq("id", source_id).single().execute()

# Crawl using DB configuration
stats = await crawl_from_config_dict(source.data)

# Database is automatically updated with:
# - crawl_status
# - total_pages_crawled
# - total_chunks_created
# - last_crawl_duration_seconds
```

## Crawl Profiles Explained

### Deep Profile
**Use when**: Building comprehensive knowledge base, initial setup
```python
{
    "depth": 5,
    "chunk_size": 5000,
    "max_pages": 500,
    "extract_code": True,
    "max_concurrent": 3,
    "request_delay": 2.0
}
```
- Thorough crawling with up to 5 levels deep
- Respectful rate limiting (2s delay)
- Smaller concurrency to avoid overwhelming servers

### Quick Profile
**Use when**: Regular updates, refreshing existing knowledge
```python
{
    "depth": 1,
    "chunk_size": 10000,
    "max_pages": 50,
    "extract_code": False,
    "max_concurrent": 10,
    "request_delay": 0.5
}
```
- Fast, shallow crawl
- Larger chunks, less detailed
- Higher concurrency for speed

### API-Only Profile
**Use when**: Focusing on API reference documentation
```python
{
    "depth": 2,
    "chunk_size": 3000,
    "max_pages": 200,
    "filter_pattern": r"/(api|reference)/",
    "extract_code": True,
    "max_concurrent": 5
}
```
- Filters for API-related URLs
- Smaller chunks for granular API documentation
- Preserves code examples

## Smart Features

### 1. Framework Auto-Detection

The crawler automatically detects frameworks from:
- **URL patterns**: `fastapi.tiangolo.com` → `fastapi`
- **Domain names**: `pytorch.org` → `pytorch`
- **Page content**: Analyzes title and content for framework mentions

Supported frameworks:
- Python: FastAPI, Pydantic, Django, Flask, Streamlit, Gradio
- JavaScript: React, Vue, Angular, Next.js, Express, Nest.js
- Data Science: PyTorch, TensorFlow, NumPy, Pandas, scikit-learn
- And many more...

### 2. Language Auto-Detection

Detects programming language from:
- **Code block markers**: ` ```python`, ` ```javascript`, etc.
- **Code patterns**: `def`, `import`, `function`, `class`, etc.
- **File extensions**: References to `.py`, `.js`, `.go`, etc.

Supported languages:
- Python, JavaScript, TypeScript, Java, Go, Rust, Ruby, PHP, and more

### 3. LLM-Powered Tag Extraction

For each chunk, the LLM extracts:
- **Technical tags**: `['authentication', 'jwt', 'security', 'oauth2']`
- **Knowledge type**: `documentation`, `tutorial`, `api_reference`, `example`, `blog`
- **Title**: Concise, descriptive title
- **Summary**: 2-3 sentence summary of main points

Example:
```python
{
    "tags": ["async", "dependency-injection", "fastapi", "routing"],
    "knowledge_type": "tutorial",
    "title": "Dependency Injection in FastAPI",
    "summary": "Learn how to use FastAPI's dependency injection system..."
}
```

### 4. Intelligent Chunking

Chunks respect content structure:
1. **Code blocks** (highest priority): Never split in the middle
2. **Section headers** (`#`, `##`, etc.): Break at sections
3. **Paragraphs** (`\n\n`): Break at paragraph boundaries
4. **Sentences** (`. `): Break at sentence ends

Result: Coherent, meaningful chunks perfect for RAG.

## Error Handling & Retries

### Automatic Retries
```python
profile = CrawlProfile(
    retry_count=3,  # Retry failed URLs 3 times
    retry_delay=2   # Wait 2 seconds between retries
)
```

### Progress Tracking with Errors
```python
status = tracker.get_status()
print(f"Succeeded: {status['urls_succeeded']}")
print(f"Failed: {status['urls_failed']}")
print(f"Logs: {status['logs']}")  # Detailed error logs
```

### Graceful Degradation
- If LLM tag extraction fails → Falls back to basic metadata
- If embedding fails → Returns zero vector (can be updated later)
- If single URL fails → Continues with remaining URLs

## Performance Optimization

### Concurrency Control
```python
profile = CrawlProfile(
    max_concurrent=5,  # Max 5 simultaneous requests
    request_delay=1.0  # 1 second between requests
)
```

### Rate Limiting
- Respects `request_delay` between requests
- Adjustable per profile
- Built-in retry backoff

### Chunking Strategy
- **Large chunks** (10000): Faster processing, less granular
- **Small chunks** (3000): More granular, better for specific queries
- **Medium chunks** (5000): Balanced default

## Integration Examples

### 1. Streamlit UI Integration

```python
import streamlit as st
from archon.universal_crawler import start_crawl_async, SourceConfig

# UI form
url = st.text_input("Documentation URL")
profile = st.selectbox("Profile", ["quick", "deep", "api-only"])

if st.button("Start Crawl"):
    config = SourceConfig(source_url=url)

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_ui(status):
        progress_bar.progress(status['progress_percentage'] / 100)
        status_text.text(f"{status['current_phase']}: {status['chunks_stored']} chunks")

    tracker = start_crawl_async(config, profile, progress_callback=update_ui)

    # Streamlit will auto-update via callback
```

### 2. Scheduled Crawls

```python
import schedule
import time

def crawl_job():
    """Run scheduled knowledge updates."""
    sources = supabase.table("knowledge_sources")\
        .select("*")\
        .eq("crawl_frequency", "daily")\
        .execute()

    for source in sources.data:
        asyncio.run(crawl_from_config_dict(source))

# Schedule daily at 2 AM
schedule.every().day.at("02:00").do(crawl_job)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### 3. API Endpoint

```python
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

@app.post("/crawl")
async def trigger_crawl(source_url: str, background_tasks: BackgroundTasks):
    config = SourceConfig(source_url=source_url)

    async def run_crawl():
        await crawl_source(config)

    background_tasks.add_task(run_crawl)

    return {"status": "Crawl started", "url": source_url}
```

## Querying Crawled Knowledge

### Using Enhanced Search

```python
# Search with filters
results = supabase.rpc(
    'match_knowledge_advanced',
    {
        'query_embedding': embedding,
        'match_count': 10,
        'required_tags': ['authentication', 'fastapi'],
        'required_frameworks': ['fastapi'],
        'knowledge_types': ['tutorial', 'documentation'],
        'language_filter': 'python'
    }
).execute()

for result in results.data:
    print(f"Title: {result['title']}")
    print(f"Tags: {result['tags']}")
    print(f"Type: {result['knowledge_type']}")
    print(f"Framework: {result['framework']}")
    print(f"Similarity: {result['similarity']:.2f}")
```

### Get Knowledge by Framework

```python
# All FastAPI documentation
fastapi_docs = supabase.table("site_pages")\
    .select("*")\
    .eq("framework", "fastapi")\
    .eq("knowledge_type", "documentation")\
    .execute()
```

### Get Knowledge by Tags

```python
# All content about authentication
auth_content = supabase.table("site_pages")\
    .select("*")\
    .contains("tags", ["authentication"])\
    .execute()
```

## Best Practices

### 1. Start with Quick Profile
```python
# First, explore what's available
stats = await crawl_source(config, profile_name='quick')

# If content looks good, run deep crawl
if stats['chunks_stored'] > 10:
    await crawl_source(config, profile_name='deep')
```

### 2. Use Specific Framework Names
```python
# Good: Specific and consistent
config = SourceConfig(framework="fastapi")

# Avoid: Generic or inconsistent
config = SourceConfig(framework="FastAPI Framework Docs")
```

### 3. Set Appropriate Delays
```python
# For large public sites
profile = CrawlProfile(request_delay=2.0, max_concurrent=3)

# For your own documentation
profile = CrawlProfile(request_delay=0.5, max_concurrent=10)
```

### 4. Monitor Progress
```python
# Always use progress tracking for long crawls
tracker = start_crawl_async(config, progress_callback=log_progress)

# Check for failures
if tracker.urls_failed > 0:
    print(f"Warning: {tracker.urls_failed} URLs failed")
```

### 5. Regular Updates
```python
# Use quick profile for regular refreshes
schedule.every().week.do(lambda: crawl_source(config, 'quick'))
```

## Troubleshooting

### Issue: No URLs Found
**Solution**: Provide explicit sitemap_url or check URL patterns
```python
config = SourceConfig(
    source_url="https://docs.example.com",
    sitemap_url="https://docs.example.com/sitemap.xml"
)
```

### Issue: Too Many URLs
**Solution**: Use filter patterns or reduce max_pages
```python
config = SourceConfig(
    url_patterns=[r'/docs/'],  # Only /docs/ pages
    exclude_patterns=[r'/archive/']  # Skip archive
)
```

### Issue: Poor Tag Quality
**Solution**: Switch to a better LLM model
```python
# In your .env
PRIMARY_MODEL=gpt-4  # More accurate than gpt-4o-mini
```

### Issue: Rate Limiting
**Solution**: Increase delays and reduce concurrency
```python
profile = CrawlProfile(
    request_delay=3.0,  # Slower requests
    max_concurrent=2    # Fewer parallel requests
)
```

### Issue: Large Memory Usage
**Solution**: Reduce chunk size and max_concurrent
```python
profile = CrawlProfile(
    chunk_size=3000,     # Smaller chunks
    max_concurrent=3     # Less parallelism
)
```

## API Reference

### SourceConfig
```python
@dataclass
class SourceConfig:
    source_url: str                          # Required: Base URL to crawl
    source_type: str = 'documentation'       # Type of source
    framework: Optional[str] = None          # Framework name (auto-detected if None)
    language: Optional[str] = None           # Programming language (auto-detected)
    crawl_profile: str = 'default'           # Profile to use
    sitemap_url: Optional[str] = None        # Explicit sitemap URL
    url_patterns: List[str] = []             # URL patterns to include (regex)
    exclude_patterns: List[str] = []         # URL patterns to exclude (regex)
    metadata: Dict[str, Any] = {}            # Additional metadata
```

### CrawlProfile
```python
@dataclass
class CrawlProfile:
    name: str                                # Profile name
    depth: int = 1                           # Crawl depth (levels)
    chunk_size: int = 5000                   # Text chunk size
    max_pages: int = 100                     # Maximum pages to crawl
    extract_code: bool = True                # Extract code blocks
    summary_only: bool = False               # Only summaries, not full content
    filter_pattern: Optional[str] = None     # URL filter regex
    max_concurrent: int = 5                  # Concurrent requests
    retry_count: int = 3                     # Retry attempts
    retry_delay: int = 2                     # Retry delay (seconds)
    request_delay: float = 1.0               # Request delay (seconds)
```

### Main Functions

```python
async def crawl_source(
    config: SourceConfig,
    profile_name: str = 'default',
    tracker: Optional[CrawlProgressTracker] = None,
    source_id: Optional[str] = None
) -> Dict[str, Any]:
    """Main crawling function. Returns statistics."""

def start_crawl_async(
    config: SourceConfig,
    profile_name: str = 'default',
    progress_callback: Optional[Callable] = None,
    source_id: Optional[str] = None
) -> CrawlProgressTracker:
    """Start crawl in background thread. Returns tracker."""

async def crawl_from_config_dict(
    config_dict: Dict[str, Any],
    tracker: Optional[CrawlProgressTracker] = None
) -> Dict[str, Any]:
    """Crawl from database configuration dictionary."""
```

## Examples

See `/home/user/Archon/examples/universal_crawler_examples.py` for comprehensive examples including:
- Simple documentation crawl
- Deep crawl with progress tracking
- API-only crawling
- Custom profiles
- Database integration
- Multiple sources
- Error handling
- Quick updates

## License

Part of the Archon project. See main project LICENSE.
