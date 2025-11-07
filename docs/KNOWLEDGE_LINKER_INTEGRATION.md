# Knowledge Linker Agent - Integration Guide

## Overview

The Knowledge Linker Agent automatically analyzes tasks and attaches relevant knowledge chunks from your knowledge base. It uses a combination of vector similarity search, tag matching, and LLM-based analysis to ensure tasks have the documentation and context they need.

## Quick Start

### 1. Basic Usage

```python
from archon.knowledge_linker import auto_link_task_knowledge

# Link knowledge to a task
result = await auto_link_task_knowledge(task_id="your-task-uuid")

print(f"Linked {result.links_created} knowledge chunks")
print(f"Coverage: {result.coverage_score:.2%}")
```

### 2. When Creating Tasks

```python
from archon.knowledge_linker import auto_link_task_knowledge
from utils.utils import get_clients

embedding_client, supabase = get_clients()

# Create task
task_data = {
    "name": "Build REST API",
    "description": "Create FastAPI endpoints with JWT auth...",
    "status": "pending"
}

result = supabase.table("tasks").insert(task_data).execute()
task_id = result.data[0]['id']

# Link knowledge immediately
link_result = await auto_link_task_knowledge(task_id)
```

### 3. Batch Processing

```python
from archon.knowledge_linker import batch_link_tasks

# Get all tasks needing knowledge
result = supabase.table("tasks")\
    .select("id")\
    .is_("knowledge_coverage_score", "null")\
    .execute()

task_ids = [t['id'] for t in result.data]

# Link in parallel
results = await batch_link_tasks(task_ids)
```

## Integration Points

### A. Task Creation Hook

Add knowledge linking when tasks are created:

```python
async def create_task_with_knowledge(task_data: dict) -> dict:
    """Create a task and link relevant knowledge"""

    # Create task
    result = supabase.table("tasks").insert(task_data).execute()
    task = result.data[0]

    # Link knowledge
    link_result = await auto_link_task_knowledge(task['id'])

    # Update task with coverage info
    task['knowledge_coverage'] = link_result.coverage_score
    task['is_ready'] = link_result.coverage_score >= 0.6

    return task
```

### B. Task Scheduler Integration

Check knowledge coverage before scheduling:

```python
async def schedule_task(task_id: str):
    """Schedule a task if it has sufficient knowledge"""

    # Ensure knowledge is linked
    result = await auto_link_task_knowledge(task_id)

    # Check coverage
    if result.coverage_score < 0.6:
        # Block task
        supabase.table("tasks").update({
            "is_blocked": True,
            "blocker_reason": f"Insufficient knowledge ({result.coverage_score:.0%})",
            "status": "blocked"
        }).eq("id", task_id).execute()

        return False

    # Task is ready - proceed with scheduling
    return True
```

### C. Knowledge Refresh Trigger

Re-link when task descriptions change:

```python
async def update_task_description(task_id: str, new_description: str):
    """Update task description and refresh knowledge links"""

    # Update description
    supabase.table("tasks").update({
        "description": new_description
    }).eq("id", task_id).execute()

    # Refresh knowledge links
    from archon.knowledge_linker import refresh_task_knowledge
    result = await refresh_task_knowledge(task_id)

    return result
```

### D. Agent Execution Context

Provide knowledge to agents before execution:

```python
from archon.knowledge_linker import get_task_linked_knowledge

async def execute_task_with_context(task_id: str, agent):
    """Execute a task with linked knowledge as context"""

    # Get task details
    task = supabase.table("tasks").select("*").eq("id", task_id).single().execute()

    # Get linked knowledge
    knowledge = await get_task_linked_knowledge(task_id)

    # Build context for agent
    context = build_knowledge_context(knowledge)

    # Execute with context
    result = await agent.run(
        task_description=task.data['description'],
        knowledge_context=context
    )

    return result

def build_knowledge_context(knowledge_chunks):
    """Format knowledge chunks for agent context"""

    required = [k for k in knowledge_chunks if k.metadata.get('link_type') == 'required']
    suggested = [k for k in knowledge_chunks if k.metadata.get('link_type') == 'suggested']

    context = "## Required Knowledge\n\n"
    for chunk in required:
        context += f"### {chunk.title}\n"
        context += f"{chunk.content[:500]}...\n\n"

    if suggested:
        context += "## Additional References\n\n"
        for chunk in suggested[:3]:  # Top 3 suggestions
            context += f"- {chunk.title}: {chunk.url}\n"

    return context
```

### E. Automatic Background Linking

Set up periodic knowledge linking:

```python
import asyncio
from archon.knowledge_linker import batch_link_tasks

async def background_knowledge_linker():
    """Continuously monitor and link knowledge to tasks"""

    while True:
        try:
            # Find tasks without knowledge
            result = supabase.table("tasks")\
                .select("id")\
                .is_("knowledge_coverage_score", "null")\
                .in_("status", ["pending", "ready"])\
                .execute()

            if result.data:
                task_ids = [t['id'] for t in result.data]
                print(f"Linking knowledge for {len(task_ids)} tasks...")

                await batch_link_tasks(task_ids)

                print("Knowledge linking complete")

        except Exception as e:
            print(f"Error in background linker: {e}")

        # Run every 5 minutes
        await asyncio.sleep(300)

# Start in background
asyncio.create_task(background_knowledge_linker())
```

## Advanced Features

### 1. Custom Relevance Scoring

You can extend the relevance scoring logic:

```python
from archon.knowledge_linker import calculate_relevance_score

# The function already considers:
# - Vector similarity
# - Tag overlap
# - Framework matches
# - Language matches
# - Knowledge type preferences

# You can wrap it to add custom logic:
async def custom_relevance_score(task, requirements, chunk):
    base_score = await calculate_relevance_score(
        task['description'],
        requirements,
        chunk
    )

    # Add custom boosts
    if chunk.metadata.get('quality_score', 0) > 0.9:
        base_score += 0.05

    if chunk.metadata.get('last_updated_days', 999) < 30:
        base_score += 0.03  # Recent docs

    return min(1.0, base_score)
```

### 2. Coverage-Based Task Prioritization

Prioritize tasks based on knowledge availability:

```python
async def prioritize_tasks_by_knowledge():
    """Prioritize tasks with better knowledge coverage"""

    # Get all pending tasks
    result = supabase.table("tasks")\
        .select("id, name, priority, knowledge_coverage_score")\
        .eq("status", "pending")\
        .execute()

    tasks = result.data

    # Sort by coverage (descending) then original priority
    tasks.sort(
        key=lambda t: (
            -(t.get('knowledge_coverage_score', 0) or 0),  # Higher coverage first
            t['priority']  # Then by priority
        )
    )

    # Update priorities
    for idx, task in enumerate(tasks):
        new_priority = idx + 1
        supabase.table("tasks").update({
            "priority": new_priority
        }).eq("id", task['id']).execute()
```

### 3. Knowledge Gap Analysis

Identify missing documentation across your project:

```python
from collections import Counter

async def analyze_project_knowledge_gaps(project_id: str):
    """Identify missing knowledge across a project"""

    # Get all tasks in project
    result = supabase.table("tasks")\
        .select("id, required_knowledge_tags")\
        .eq("project_id", project_id)\
        .execute()

    # Aggregate missing knowledge
    all_missing = []

    for task in result.data:
        task_id = task['id']
        link_result = await auto_link_task_knowledge(task_id)
        all_missing.extend(link_result.missing_knowledge)

    # Find most common gaps
    gap_counts = Counter(all_missing)

    print("Top Knowledge Gaps:")
    for topic, count in gap_counts.most_common(10):
        print(f"  {topic}: {count} tasks affected")

    return gap_counts
```

### 4. Suggested Crawl Source Management

Track and execute suggested crawls:

```python
async def handle_crawl_suggestions(task_id: str):
    """Process crawl suggestions for low-coverage tasks"""

    result = await auto_link_task_knowledge(task_id)

    if result.coverage_score < 0.4 and result.suggested_crawl_sources:
        print(f"Low coverage detected: {result.coverage_score:.2%}")
        print(f"Suggested sources:")

        for source in result.suggested_crawl_sources:
            print(f"  - {source}")

            # Option 1: Store for manual review
            supabase.table("knowledge_sources").insert({
                "source_url": extract_url(source),
                "source_type": "documentation",
                "crawl_status": "pending",
                "metadata": {
                    "suggested_for_task": task_id,
                    "suggestion_reason": source
                }
            }).execute()

            # Option 2: Auto-crawl if high priority
            if "[HIGH]" in source:
                await trigger_crawl(extract_url(source))

def extract_url(source_string: str) -> str:
    """Extract URL from formatted suggestion"""
    import re
    match = re.search(r'(https?://[^\s]+)', source_string)
    return match.group(1) if match else ""
```

## Configuration

### Environment Variables

The Knowledge Linker uses these environment variables:

```bash
# LLM for task analysis
PRIMARY_MODEL=gpt-4o-mini
LLM_API_KEY=your-api-key
BASE_URL=https://api.openai.com/v1

# Embeddings for vector search
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=your-api-key
EMBEDDING_BASE_URL=https://api.openai.com/v1

# Database
SUPABASE_URL=your-supabase-url
SUPABASE_SERVICE_KEY=your-service-key
```

### Tuning Parameters

You can adjust these parameters in your code:

```python
# Search parameters
result = await auto_link_task_knowledge(
    task_id=task_id,
    match_count=20,        # More chunks to search
    match_threshold=0.6,   # Lower threshold = more results
    max_chunks=15          # Maximum chunks to link
)

# Coverage thresholds
MIN_COVERAGE_READY = 0.7    # Task is ready to start
MIN_COVERAGE_OK = 0.4       # Task can proceed with caution
MIN_COVERAGE_BLOCK = 0.4    # Below this, block the task
```

## Best Practices

### 1. Link Early and Often

- Link knowledge when tasks are created
- Re-link when descriptions change significantly
- Periodically refresh for long-running tasks

### 2. Monitor Coverage Scores

- Track average coverage across projects
- Investigate tasks with low coverage
- Use coverage as a readiness signal

### 3. Act on Missing Knowledge

- Review suggested crawl sources
- Add missing documentation proactively
- Create internal knowledge for proprietary topics

### 4. Provide Context to Agents

- Always fetch linked knowledge before agent execution
- Format knowledge appropriately for the agent
- Include both required and suggested knowledge

### 5. Keep Knowledge Fresh

- Re-crawl documentation periodically
- Update tags and metadata
- Remove outdated knowledge

## Troubleshooting

### No Knowledge Found

**Problem**: `auto_link_task_knowledge` returns 0 chunks

**Solutions**:
1. Check if knowledge exists in database:
   ```sql
   SELECT COUNT(*) FROM site_pages;
   ```
2. Verify embeddings are generated for task
3. Lower match_threshold (default 0.6)
4. Check if tags/frameworks are too specific

### Low Coverage Scores

**Problem**: Coverage consistently below 0.5

**Solutions**:
1. Crawl more documentation sources
2. Check task descriptions - too vague or too specific?
3. Verify tag extraction is working correctly
4. Review suggested crawl sources

### Slow Performance

**Problem**: Linking takes too long

**Solutions**:
1. Use batch linking for multiple tasks
2. Reduce match_count parameter
3. Ensure database indexes are created
4. Cache embeddings for repeated tasks

### Incorrect Links

**Problem**: Linked knowledge isn't relevant

**Solutions**:
1. Check task description quality
2. Review LLM's tag extraction
3. Adjust relevance scoring weights
4. Manually review and adjust links

## API Reference

### Main Functions

#### `auto_link_task_knowledge(task_id, task_name="", task_description="", force_refresh=False)`

Main function to link knowledge to a task.

**Returns**: `LinkResult` with:
- `total_chunks_found`: Number of relevant chunks found
- `links_created`: Number of links created
- `coverage_score`: 0-1 score of knowledge coverage
- `missing_knowledge`: List of missing topics
- `suggested_crawl_sources`: Recommended docs to crawl

#### `refresh_task_knowledge(task_id)`

Remove existing links and re-link with current knowledge base.

#### `batch_link_tasks(task_ids)`

Link knowledge for multiple tasks in parallel.

**Returns**: `Dict[str, LinkResult]`

#### `get_task_linked_knowledge(task_id)`

Get all knowledge currently linked to a task.

**Returns**: `List[KnowledgeChunk]`

## Next Steps

1. **Set up database schema**: Run `utils/knowledge_schema.sql`
2. **Crawl initial knowledge**: Use `crawl_pydantic_ai_docs.py` as example
3. **Integrate into workflow**: Add hooks in task creation
4. **Monitor coverage**: Track knowledge gaps
5. **Iterate**: Adjust thresholds and parameters based on results

## Support

For issues or questions:
- Check logs in `workbench/logs.txt`
- Review database state in Supabase dashboard
- Refer to examples in `examples/knowledge_linker_usage.py`
