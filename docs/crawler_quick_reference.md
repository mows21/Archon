# Universal Crawler - Quick Reference Card

## 🚀 Quick Start

### Minimal Example
```python
from archon.universal_crawler import SourceConfig, crawl_source
import asyncio

config = SourceConfig(source_url="https://fastapi.tiangolo.com")
stats = await crawl_source(config)
print(f"Stored {stats['chunks_stored']} chunks")
```

### CLI One-Liner
```bash
python archon/crawl_cli.py https://fastapi.tiangolo.com --profile quick
```

## 📋 Common Patterns

### 1. Quick Documentation Update
```python
config = SourceConfig(
    source_url="https://docs.example.com",
    framework="myframework"
)
await crawl_source(config, profile_name='quick')
```

### 2. Deep Initial Crawl
```python
config = SourceConfig(
    source_url="https://docs.example.com",
    framework="myframework",
    language="python"
)
await crawl_source(config, profile_name='deep')
```

### 3. API-Only Documentation
```python
config = SourceConfig(
    source_url="https://api.example.com",
    url_patterns=[r'/api/', r'/reference/'],
    exclude_patterns=[r'/guides/']
)
await crawl_source(config, profile_name='api-only')
```

### 4. With Progress Tracking
```python
def on_progress(status):
    print(f"{status['progress_percentage']:.1f}%")

tracker = start_crawl_async(
    config,
    profile_name='deep',
    progress_callback=on_progress
)
```

### 5. From Database
```python
source = supabase.table("knowledge_sources").select("*").eq("id", id).single()
stats = await crawl_from_config_dict(source.data)
```

## 🎯 Profiles Cheat Sheet

| Profile | Use Case | Speed | Depth | Pages |
|---------|----------|-------|-------|-------|
| `quick` | Updates | ⚡⚡⚡ | 1 | 50 |
| `default` | Balanced | ⚡⚡ | 2 | 100 |
| `deep` | Initial | ⚡ | 5 | 500 |
| `api-only` | API docs | ⚡⚡ | 2 | 200 |

## 🔧 Configuration Quick Reference

### SourceConfig
```python
SourceConfig(
    source_url="https://...",              # Required
    source_type="documentation",           # Optional
    framework="fastapi",                   # Optional, auto-detected
    language="python",                     # Optional, auto-detected
    crawl_profile="deep",                  # Optional
    sitemap_url="https://.../sitemap.xml", # Optional
    url_patterns=[r'/docs/'],              # Optional
    exclude_patterns=[r'/blog/'],          # Optional
    metadata={"key": "value"}              # Optional
)
```

### CrawlProfile
```python
CrawlProfile(
    name="custom",
    depth=3,                    # Crawl depth
    chunk_size=5000,            # Chunk size in chars
    max_pages=100,              # Max pages to crawl
    extract_code=True,          # Extract code blocks
    max_concurrent=5,           # Concurrent requests
    retry_count=3,              # Retry attempts
    request_delay=1.0           # Delay between requests (sec)
)
```

## 🏷️ Auto-Detection Features

### Frameworks (40+)
FastAPI, Pydantic, Django, Flask, React, Vue, Angular, Next.js, PyTorch, TensorFlow, NumPy, Pandas, and more...

### Languages (10+)
Python, JavaScript, TypeScript, Java, Go, Rust, Ruby, PHP, C++, C#, and more...

### Knowledge Types
- `documentation` - Reference docs
- `tutorial` - How-to guides
- `api_reference` - API docs
- `example` - Code examples
- `blog` - Blog posts
- `other` - Other content

## 📊 Enhanced Schema Fields

```python
{
    "url": str,
    "chunk_number": int,
    "title": str,
    "summary": str,
    "content": str,
    "tags": List[str],           # NEW: ['auth', 'jwt', 'security']
    "knowledge_type": str,       # NEW: 'tutorial'
    "framework": str,            # NEW: 'fastapi'
    "language": str,             # NEW: 'python'
    "metadata": dict,
    "embedding": List[float]
}
```

## 🔍 Querying Enhanced Knowledge

### By Framework
```python
supabase.table("site_pages")\
    .select("*")\
    .eq("framework", "fastapi")\
    .execute()
```

### By Tags
```python
supabase.table("site_pages")\
    .select("*")\
    .contains("tags", ["authentication"])\
    .execute()
```

### By Knowledge Type
```python
supabase.table("site_pages")\
    .select("*")\
    .eq("knowledge_type", "tutorial")\
    .execute()
```

### Advanced Search (RPC)
```python
supabase.rpc('match_knowledge_advanced', {
    'query_embedding': embedding,
    'required_tags': ['authentication'],
    'required_frameworks': ['fastapi'],
    'knowledge_types': ['tutorial'],
    'language_filter': 'python'
}).execute()
```

## 🎨 CLI Examples

### Basic
```bash
python archon/crawl_cli.py URL --profile PROFILE
```

### With Options
```bash
python archon/crawl_cli.py https://docs.example.com \
    --framework myframework \
    --language python \
    --profile deep \
    --include "/docs/" \
    --exclude "/blog/"
```

### From Database
```bash
python archon/crawl_cli.py --from-db SOURCE_ID --verbose
```

### List Profiles
```bash
python archon/crawl_cli.py --list-profiles
```

## 📈 Progress Status Fields

```python
{
    "is_running": bool,
    "current_phase": str,
    "urls_found": int,
    "urls_processed": int,
    "urls_succeeded": int,
    "urls_failed": int,
    "chunks_stored": int,
    "progress_percentage": float,
    "logs": List[str],
    "start_time": datetime,
    "end_time": datetime
}
```

## ⚡ Performance Tips

### Fast Updates
```python
profile = CrawlProfile(
    max_concurrent=10,
    request_delay=0.5,
    chunk_size=10000
)
```

### Respectful Crawling
```python
profile = CrawlProfile(
    max_concurrent=3,
    request_delay=2.0,
    chunk_size=5000
)
```

### Memory Efficient
```python
profile = CrawlProfile(
    max_concurrent=3,
    chunk_size=3000
)
```

## 🔑 Required Environment Variables

```bash
# LLM
LLM_PROVIDER=OpenAI
LLM_API_KEY=sk-...
PRIMARY_MODEL=gpt-4o-mini

# Embeddings
EMBEDDING_PROVIDER=OpenAI
EMBEDDING_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small

# Database
SUPABASE_URL=https://...
SUPABASE_SERVICE_KEY=...
```

## 🐛 Common Issues & Fixes

### No URLs Found
```python
config = SourceConfig(
    source_url="https://...",
    sitemap_url="https://.../sitemap.xml"  # Explicit sitemap
)
```

### Too Many URLs
```python
config = SourceConfig(
    url_patterns=[r'/docs/'],  # Filter
    exclude_patterns=[r'/archive/']  # Exclude
)
```

### Rate Limiting
```python
profile = CrawlProfile(
    request_delay=3.0,  # Slower
    max_concurrent=2    # Less parallel
)
```

### Poor Tags
```python
# Use better model
PRIMARY_MODEL=gpt-4  # Instead of gpt-4o-mini
```

## 📚 Files Location

| File | Purpose |
|------|---------|
| `archon/universal_crawler.py` | Core module |
| `archon/crawl_cli.py` | CLI tool |
| `examples/universal_crawler_examples.py` | Examples |
| `docs/universal_crawler_guide.md` | Full guide |
| `utils/knowledge_schema.sql` | Database schema |

## 💡 Integration Snippets

### Streamlit
```python
url = st.text_input("URL")
if st.button("Crawl"):
    config = SourceConfig(source_url=url)
    tracker = start_crawl_async(config, progress_callback=st.write)
```

### FastAPI
```python
@app.post("/crawl")
async def crawl(url: str, bg: BackgroundTasks):
    config = SourceConfig(source_url=url)
    bg.add_task(lambda: asyncio.run(crawl_source(config)))
    return {"status": "started"}
```

### Scheduled
```python
import schedule
schedule.every().day.at("02:00").do(
    lambda: asyncio.run(crawl_source(config, 'quick'))
)
```

## 🎯 Best Practices

1. **Start with quick profile** to test
2. **Use specific framework names** for consistency
3. **Set appropriate delays** based on site size
4. **Monitor progress** for long crawls
5. **Regular updates** with quick profile
6. **Deep crawls** for initial setup only
7. **Use URL patterns** to focus crawling
8. **Check logs** for failures

## ✅ Checklist

- [ ] Database schema updated (`knowledge_schema.sql`)
- [ ] Environment variables configured
- [ ] Dependencies installed
- [ ] Test crawl with quick profile
- [ ] Verify data in Supabase
- [ ] Set up scheduled updates (optional)
- [ ] Integrate with Archon agents (optional)

---

**Universal Crawler Quick Reference v1.0**
For detailed documentation, see: `docs/universal_crawler_guide.md`
