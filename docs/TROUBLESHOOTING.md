# Archon Knowledge Management - Troubleshooting Guide

This guide covers common issues you might encounter while using Archon and their solutions.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Database Connection Errors](#database-connection-errors)
- [LLM API Errors](#llm-api-errors)
- [Embedding Generation Issues](#embedding-generation-issues)
- [Crawling Failures](#crawling-failures)
- [Low Coverage Scores](#low-coverage-scores)
- [Task Creation Issues](#task-creation-issues)
- [Agent Service Issues](#agent-service-issues)
- [Docker Issues](#docker-issues)
- [Performance Issues](#performance-issues)

---

## Installation Issues

### Issue: "ModuleNotFoundError" when running Archon

**Symptom:**
```
ModuleNotFoundError: No module named 'pydantic_ai'
```

**Cause:** Dependencies not installed or virtual environment not activated.

**Solution:**

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Reinstall dependencies
pip install -r requirements.txt

# If using Docker, rebuild container
python run_docker.py
```

**Prevention:** Always activate your virtual environment before running Archon.

---

### Issue: "Python version not supported"

**Symptom:**
```
ERROR: This package requires Python 3.11+
```

**Cause:** Python version is too old.

**Solution:**

```bash
# Check Python version
python --version

# Install Python 3.11+ from python.org or use pyenv
pyenv install 3.11
pyenv local 3.11

# Recreate virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Prevention:** Use Python 3.11 or newer.

---

### Issue: Playwright installation fails

**Symptom:**
```
Error: Playwright browsers not installed
```

**Cause:** Playwright browsers need to be installed separately.

**Solution:**

```bash
# Install Playwright browsers
python -m playwright install

# If on Linux and getting dependency errors
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2
```

**Prevention:** Run playwright install after pip install.

---

## Database Connection Errors

### Issue: "Connection to Supabase failed"

**Symptom:**
```
Error: Could not connect to Supabase
supabase.exceptions.AuthError: Invalid API key
```

**Cause:** Invalid Supabase credentials or network issues.

**Solution:**

1. **Verify credentials:**
   ```bash
   # Check workbench/env_vars.json
   cat workbench/env_vars.json | grep SUPABASE
   ```

2. **Test connection:**
   ```python
   from utils.utils import get_clients
   _, supabase = get_clients()
   result = supabase.table('site_pages').select('*').limit(1).execute()
   print("Connection successful!" if result else "Connection failed")
   ```

3. **Common fixes:**
   - Ensure you're using the **Service Role Key**, not the anon key
   - Check that URL format is correct: `https://xxxxx.supabase.co`
   - Verify your Supabase project is running (not paused)
   - Check firewall/VPN settings

**Prevention:** Use the setup wizard to validate credentials before proceeding.

---

### Issue: "Table 'site_pages' does not exist"

**Symptom:**
```
postgrest.exceptions.APIError: relation "public.site_pages" does not exist
```

**Cause:** Database schema not created.

**Solution:**

1. **Via Streamlit UI (Recommended):**
   - Go to "Database" tab
   - Click "Get Setup Instructions for Knowledge Management"
   - Copy the SQL from `utils/knowledge_schema.sql`
   - Paste into Supabase SQL Editor and execute

2. **Via Supabase Dashboard:**
   - Open Supabase Dashboard
   - Go to SQL Editor
   - Copy contents of `utils/knowledge_schema.sql`
   - Execute the SQL

3. **Verify setup:**
   ```sql
   SELECT table_name FROM information_schema.tables
   WHERE table_schema = 'public'
   AND table_name IN ('site_pages', 'projects', 'tasks');
   ```

**Prevention:** Run the knowledge schema setup before crawling or creating projects.

---

### Issue: "Vector extension not enabled"

**Symptom:**
```
ERROR: type "vector" does not exist
```

**Cause:** pgvector extension not enabled in Supabase.

**Solution:**

1. **Enable in Supabase Dashboard:**
   - Go to Database → Extensions
   - Search for "vector"
   - Click "Enable" on pgvector

2. **Or via SQL:**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. **Verify:**
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

**Prevention:** The knowledge schema automatically enables this, but older Supabase projects might need manual activation.

---

## LLM API Errors

### Issue: "Invalid API key"

**Symptom:**
```
openai.AuthenticationError: Incorrect API key provided
```

**Cause:** Wrong or expired API key.

**Solution:**

1. **Check API key:**
   ```bash
   # View current key (redacted)
   python -c "from utils.utils import get_env_var; print(get_env_var('LLM_API_KEY')[:10] + '...')"
   ```

2. **Update API key:**
   - Via UI: Environment tab → Update LLM API Key
   - Via file: Edit `workbench/env_vars.json`

3. **Verify key works:**
   ```python
   from openai import OpenAI
   client = OpenAI(api_key="your-key-here")
   response = client.chat.completions.create(
       model="gpt-4o-mini",
       messages=[{"role": "user", "content": "test"}]
   )
   print("API key valid!")
   ```

**Prevention:** Test API keys immediately after entry using the setup wizard.

---

### Issue: "Rate limit exceeded"

**Symptom:**
```
openai.RateLimitError: Rate limit reached for requests
```

**Cause:** Too many API requests in a short time.

**Solution:**

1. **Wait and retry:**
   - Wait 60 seconds and try again
   - Check OpenAI usage dashboard for current limits

2. **Reduce concurrent requests:**
   ```python
   # When crawling, reduce concurrency
   await crawl_parallel_with_requests(urls, tracker, max_concurrent=3)  # Instead of 5
   ```

3. **Upgrade API tier:**
   - Check OpenAI pricing page for higher tiers
   - Consider using smaller models (gpt-4o-mini instead of gpt-4o)

**Prevention:** Use rate limit friendly models and adjust concurrency settings.

---

### Issue: "Model not found"

**Symptom:**
```
openai.NotFoundError: The model 'gpt-5' does not exist
```

**Cause:** Typo in model name or using unavailable model.

**Solution:**

1. **Check model name:**
   ```bash
   # View current model
   python -c "from utils.utils import get_env_var; print(get_env_var('PRIMARY_MODEL'))"
   ```

2. **Use valid model names:**
   - OpenAI: `gpt-4o-mini`, `gpt-4o`, `gpt-4-turbo`
   - Anthropic: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
   - Ollama: `llama3.1`, `mistral`, `codellama`

3. **Update model:**
   - Edit `workbench/env_vars.json`
   - Or use Environment tab in UI

**Prevention:** Use model names from official documentation.

---

## Embedding Generation Issues

### Issue: "Embedding dimension mismatch"

**Symptom:**
```
ERROR: expected 1536 dimensions, got 768
```

**Cause:** Using different embedding model than database expects.

**Solution:**

1. **Check current embedding model:**
   ```python
   from utils.utils import get_env_var
   print(get_env_var('EMBEDDING_MODEL'))
   ```

2. **Options:**

   **Option A:** Update schema to match your model
   ```sql
   -- For nomic-embed-text (768 dimensions)
   ALTER TABLE site_pages ALTER COLUMN embedding TYPE VECTOR(768);
   ALTER TABLE projects ALTER COLUMN knowledge_context_embedding TYPE VECTOR(768);
   ALTER TABLE tasks ALTER COLUMN task_context_embedding TYPE VECTOR(768);
   ```

   **Option B:** Use compatible model
   ```json
   // workbench/env_vars.json
   {
     "EMBEDDING_MODEL": "text-embedding-3-small",  // 1536 dimensions
     "EMBEDDING_PROVIDER": "OpenAI"
   }
   ```

3. **Rebuild indexes:**
   ```sql
   DROP INDEX IF EXISTS idx_projects_knowledge_embedding;
   CREATE INDEX idx_projects_knowledge_embedding
     ON projects USING ivfflat (knowledge_context_embedding vector_cosine_ops);
   ```

**Prevention:** Decide on embedding model before initial crawl.

---

### Issue: "Embedding API timeout"

**Symptom:**
```
TimeoutError: Request to embedding API timed out
```

**Cause:** Network issues or large batch sizes.

**Solution:**

1. **Reduce batch size:**
   ```python
   # Process embeddings in smaller batches
   for chunk in chunks[:10]:  # Process 10 at a time
       embedding = await get_embedding(chunk)
   ```

2. **Increase timeout:**
   ```python
   from openai import AsyncOpenAI
   client = AsyncOpenAI(timeout=60.0)  # Increase from default 30s
   ```

3. **Check network:**
   ```bash
   # Test connectivity
   curl -I https://api.openai.com
   ```

**Prevention:** Use reasonable batch sizes and stable network connection.

---

## Crawling Failures

### Issue: "Crawl fails immediately"

**Symptom:**
```
Crawling process started
No URLs found to crawl
Crawling process completed
```

**Cause:** Sitemap not accessible or empty.

**Solution:**

1. **Check sitemap URL:**
   ```python
   import requests
   response = requests.get("https://ai.pydantic.dev/sitemap.xml")
   print(f"Status: {response.status_code}")
   print(f"URLs found: {len(response.text)}")
   ```

2. **Verify sitemap format:**
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
     <url>
       <loc>https://example.com/page1</loc>
     </url>
   </urlset>
   ```

3. **Try alternative crawl methods:**
   ```python
   # Manually provide URLs
   urls = [
       "https://ai.pydantic.dev/",
       "https://ai.pydantic.dev/agents/",
       "https://ai.pydantic.dev/models/",
   ]
   await crawl_parallel_with_requests(urls, tracker)
   ```

**Prevention:** Test sitemap URL accessibility before starting crawl.

---

### Issue: "Pages fail to crawl (403/404 errors)"

**Symptom:**
```
Failed: https://example.com/page - 403 Forbidden
Failed: https://example.com/page - 404 Not Found
```

**Cause:** Access restrictions or broken links.

**Solution:**

1. **Check robots.txt:**
   ```bash
   curl https://example.com/robots.txt
   ```

2. **Update user agent:**
   ```python
   headers = {
       'User-Agent': 'Mozilla/5.0 (compatible; ArchonBot/1.0; +https://github.com/coleam00/archon)'
   }
   ```

3. **Respect rate limits:**
   ```python
   # Add delays between requests
   time.sleep(2)  # Already implemented in archon/crawl_pydantic_ai_docs.py
   ```

4. **Skip failed URLs:**
   - The crawler automatically continues on failures
   - Check `workbench/logs.txt` for failed URLs

**Prevention:** Respect robots.txt and use appropriate user agents.

---

### Issue: "Crawl is very slow"

**Symptom:**
```
Processing 100 URLs...
[After 30 minutes]: 5 URLs processed
```

**Cause:** Too much concurrency or API rate limits.

**Solution:**

1. **Adjust concurrency:**
   ```python
   # Increase concurrency (if API limits allow)
   await crawl_parallel_with_requests(urls, tracker, max_concurrent=10)

   # Or decrease if hitting rate limits
   await crawl_parallel_with_requests(urls, tracker, max_concurrent=2)
   ```

2. **Use faster models:**
   ```json
   {
     "PRIMARY_MODEL": "gpt-4o-mini",  // Faster than gpt-4o
     "EMBEDDING_MODEL": "text-embedding-3-small"  // Faster than large
   }
   ```

3. **Optimize chunk processing:**
   ```python
   # Process chunks in larger batches
   chunk_size = 8000  # Instead of 5000
   ```

**Prevention:** Start with default settings and adjust based on your API limits.

---

## Low Coverage Scores

### Issue: "Knowledge coverage always shows 0% or very low"

**Symptom:**
```
Knowledge Coverage: 0.15 (15%)
Missing Tags: ['authentication', 'jwt', 'oauth2']
```

**Cause:** Missing or mismatched tags in documentation.

**Solution:**

1. **Check available tags:**
   ```sql
   SELECT DISTINCT unnest(tags) as tag, COUNT(*)
   FROM site_pages
   GROUP BY tag
   ORDER BY COUNT(*) DESC;
   ```

2. **Update existing docs with tags:**
   ```sql
   -- Add tags to Pydantic AI docs
   UPDATE site_pages
   SET tags = ARRAY['pydantic', 'ai', 'agents', 'python'],
       framework = 'pydantic_ai',
       language = 'python'
   WHERE url LIKE '%ai.pydantic.dev%';
   ```

3. **Crawl additional documentation:**
   ```bash
   # Crawl FastAPI docs (coming soon)
   python scripts/universal_crawler.py https://fastapi.tiangolo.com
   ```

4. **Lower coverage threshold:**
   ```python
   # Accept lower coverage (30% instead of 40%)
   project = await km.create_project(
       ...,
       min_coverage=0.3
   )
   ```

**Prevention:** Ensure crawled documentation is properly tagged during crawl.

---

### Issue: "Scraper triggered but coverage doesn't improve"

**Symptom:**
```
⚠️ Triggering scraper to acquire missing knowledge...
[After scraper runs]
Coverage: Still 0.25 (25%)
```

**Cause:** Scraper placeholder not yet implemented or crawled wrong docs.

**Solution:**

1. **Manual crawl:**
   ```python
   # Currently, scraper triggering is a placeholder
   # Manually crawl the needed documentation

   # For authentication docs:
   python scripts/universal_crawler.py https://fastapi.tiangolo.com/tutorial/security/
   ```

2. **Check what was crawled:**
   ```sql
   SELECT url, tags, framework
   FROM site_pages
   WHERE created_at > NOW() - INTERVAL '1 hour'
   ORDER BY created_at DESC;
   ```

3. **Manually link knowledge:**
   ```python
   # Link specific documentation to task
   await km.link_task_knowledge(task_id, refresh=True, top_k=20)
   ```

**Prevention:** Phase 2 will implement automatic scraper triggering. For now, manually crawl needed docs.

---

## Task Creation Issues

### Issue: "Task created but no knowledge linked"

**Symptom:**
```
✓ Task created successfully!
📚 Linked Knowledge: 0 chunks
```

**Cause:** No matching knowledge in database or tags not extracted.

**Solution:**

1. **Check if knowledge exists:**
   ```sql
   SELECT COUNT(*)
   FROM site_pages
   WHERE tags && ARRAY['your', 'tags', 'here'];
   ```

2. **Manually add tags to task:**
   ```python
   await supabase.table('tasks').update({
       'required_knowledge_tags': ['fastapi', 'authentication', 'jwt']
   }).eq('id', task_id).execute()
   ```

3. **Re-link knowledge:**
   ```python
   from archon.knowledge_manager import KnowledgeManager
   km = KnowledgeManager()
   await km.link_task_knowledge(task_id, refresh=True)
   ```

4. **Check task description:**
   - Ensure description is detailed
   - Include framework and technology names
   - Example: "Implement JWT authentication using FastAPI and python-jose library"

**Prevention:** Use detailed descriptions with framework/technology names.

---

### Issue: "Project decomposition creates too many/few tasks"

**Symptom:**
```
Created 47 tasks (way too many!)
OR
Created 1 task (not enough breakdown)
```

**Cause:** LLM decomposition needs better prompting.

**Solution:**

1. **Manual task creation:**
   ```python
   # Instead of decompose_project, create tasks manually
   task1 = await km.create_task(project_id, name="Task 1", ...)
   task2 = await km.create_task(project_id, name="Task 2", ...)
   ```

2. **Adjust project description:**
   - Too many tasks: Make description more high-level
   - Too few tasks: Make description more detailed

3. **Specify decomposition strategy:**
   ```python
   tasks = await km.decompose_project(
       project_id,
       decomposition_strategy="sequential",  # or "parallel"
       auto_link_knowledge=True
   )
   ```

**Prevention:** Phase 3 will add a specialized decomposer agent with better control.

---

## Agent Service Issues

### Issue: "Agent service won't start"

**Symptom:**
```
Error: Address already in use: 0.0.0.0:8100
```

**Cause:** Port 8100 is already in use.

**Solution:**

1. **Find and kill existing process:**
   ```bash
   # Find process on port 8100
   lsof -i :8100

   # Kill it
   kill -9 <PID>
   ```

2. **Or use different port:**
   ```bash
   # Edit graph_service.py or pass as argument
   uvicorn graph_service:app --port 8101
   ```

**Prevention:** Check for running services before starting agent service.

---

### Issue: "Agent generates hallucinated code"

**Symptom:**
```
Agent suggests using non-existent FastAPI decorators or methods
```

**Cause:** Insufficient or wrong documentation in context.

**Solution:**

1. **Check linked knowledge:**
   ```python
   task = await km.get_task_with_knowledge(task_id)
   print(f"Linked chunks: {len(task['linked_knowledge'])}")
   for chunk in task['linked_knowledge']:
       print(f"- {chunk['title']} (relevance: {chunk['relevance_score']})")
   ```

2. **Manually link correct docs:**
   - View task → "Manage Knowledge Links"
   - Remove irrelevant chunks
   - Add specific documentation

3. **Provide better context in prompt:**
   ```
   "Build a FastAPI endpoint using ONLY the FastAPI documentation provided in the context. Do not use methods not documented."
   ```

**Prevention:** Ensure high coverage scores and review linked knowledge before execution.

---

## Docker Issues

### Issue: "Docker build fails"

**Symptom:**
```
ERROR: failed to solve: process "/bin/sh -c pip install -r requirements.txt" did not complete successfully
```

**Cause:** Network issues or dependency conflicts.

**Solution:**

1. **Rebuild from scratch:**
   ```bash
   # Remove existing containers and images
   docker rm -f $(docker ps -aq --filter "name=archon")
   docker rmi archon-main archon-mcp

   # Rebuild
   python run_docker.py
   ```

2. **Check Docker resources:**
   - Ensure Docker has enough memory (>4GB)
   - Check disk space: `docker system df`

3. **Build manually:**
   ```bash
   docker build -t archon-main .
   docker run -p 8501:8501 -p 8100:8100 archon-main
   ```

**Prevention:** Ensure stable network and adequate Docker resources.

---

### Issue: "Cannot connect to host.docker.internal on Linux"

**Symptom:**
```
Error: could not resolve host: host.docker.internal
```

**Cause:** Linux Docker doesn't support host.docker.internal by default.

**Solution:**

1. **Use host network mode:**
   ```bash
   docker run --network=host archon-main
   ```

2. **Or use bridge network with IP:**
   ```bash
   # Find host IP
   ip addr show docker0 | grep inet

   # Use that IP in container
   # (Already handled in run_docker.py for Linux)
   ```

**Prevention:** The run_docker.py script handles this automatically.

---

## Performance Issues

### Issue: "Streamlit UI is slow/laggy"

**Symptom:**
UI takes 5+ seconds to respond to clicks.

**Cause:** Too much data loaded or heavy computations in main thread.

**Solution:**

1. **Limit data queries:**
   ```python
   # Add .limit() to queries
   projects = supabase.table('projects').select('*').limit(50).execute()
   ```

2. **Use caching:**
   ```python
   @st.cache_data(ttl=300)  # Cache for 5 minutes
   def get_projects():
       return supabase.table('projects').select('*').execute()
   ```

3. **Paginate results:**
   - Display 20 items per page
   - Use Streamlit pagination components

**Prevention:** Use caching and pagination for large datasets.

---

### Issue: "High memory usage"

**Symptom:**
```
Python process using 4GB+ RAM
```

**Cause:** Large embeddings or documents in memory.

**Solution:**

1. **Process in batches:**
   ```python
   # Don't load all chunks at once
   for batch in chunks_generator(batch_size=100):
       process_batch(batch)
   ```

2. **Clear cache:**
   ```python
   # In Streamlit
   st.cache_data.clear()
   ```

3. **Restart services:**
   ```bash
   # Restart agent service
   pkill -f graph_service.py
   python graph_service.py
   ```

**Prevention:** Use batch processing and regular cache clearing.

---

## Getting Help

If your issue isn't covered here:

1. **Check logs:**
   ```bash
   tail -f workbench/logs.txt
   ```

2. **Enable debug mode:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Search existing issues:**
   - https://github.com/coleam00/archon/issues

4. **Ask in community:**
   - https://thinktank.ottomator.ai/c/archon/30

5. **Create new issue:**
   - Provide error logs
   - Include environment details
   - Share steps to reproduce

---

## Emergency Reset

If everything is broken:

```bash
# Complete reset (warning: deletes all data)

# 1. Stop all services
pkill -f streamlit
pkill -f graph_service
docker stop $(docker ps -q)

# 2. Clear local data
rm -rf workbench/
rm -rf .streamlit/

# 3. Clear database (in Supabase SQL Editor)
DROP TABLE IF EXISTS agent_schedules CASCADE;
DROP TABLE IF EXISTS knowledge_relationships CASCADE;
DROP TABLE IF EXISTS task_knowledge_links CASCADE;
DROP TABLE IF EXISTS task_dependencies CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS projects CASCADE;
DROP TABLE IF EXISTS knowledge_sources CASCADE;
DELETE FROM site_pages;

# 4. Reinstall
rm -rf venv/
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Run setup wizard
python scripts/setup_wizard.py
```

---

*Still stuck? We're here to help! Join the [community forum](https://thinktank.ottomator.ai/c/archon/30).*
