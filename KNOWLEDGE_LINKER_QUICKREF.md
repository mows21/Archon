# Knowledge Linker Agent - Quick Reference

## 🚀 Quick Start

```python
from archon.knowledge_linker import auto_link_task_knowledge

# Link knowledge to a task
result = await auto_link_task_knowledge(task_id="your-uuid")

print(f"✓ Linked {result.links_created} chunks")
print(f"✓ Coverage: {result.coverage_score:.2%}")
```

## 📋 Common Operations

### Link Single Task
```python
from archon.knowledge_linker import auto_link_task_knowledge

result = await auto_link_task_knowledge(task_id)
```

### Link Multiple Tasks
```python
from archon.knowledge_linker import batch_link_tasks

task_ids = ["uuid1", "uuid2", "uuid3"]
results = await batch_link_tasks(task_ids)
```

### Refresh Links
```python
from archon.knowledge_linker import refresh_task_knowledge

result = await refresh_task_knowledge(task_id)
```

### Get Linked Knowledge
```python
from archon.knowledge_linker import get_task_linked_knowledge

knowledge = await get_task_linked_knowledge(task_id)
for chunk in knowledge:
    print(f"{chunk.title} - {chunk.url}")
```

## 🎯 Coverage Thresholds

| Score | Status | Action |
|-------|--------|--------|
| ≥ 0.7 | ✅ High | Ready to start |
| 0.4-0.7 | ⚠️ Medium | Proceed with caution |
| < 0.4 | ❌ Low | Block until knowledge added |

## 🔗 Link Types

| Type | Relevance | Meaning |
|------|-----------|---------|
| **required** | > 0.8 + tag match | Critical for task |
| **suggested** | 0.6 - 0.8 | Helpful for task |
| **reference** | < 0.6 | Related but optional |
| **learned** | N/A | Created during execution |

## 📊 LinkResult Fields

```python
result = await auto_link_task_knowledge(task_id)

result.task_id                    # Task UUID
result.total_chunks_found         # Number found in search
result.links_created              # Number linked
result.coverage_score             # 0-1 coverage score
result.missing_knowledge          # List of missing topics
result.suggested_crawl_sources    # URLs to crawl
```

## 🔧 Configuration

### Environment Variables
```bash
PRIMARY_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
SUPABASE_URL=your-url
SUPABASE_SERVICE_KEY=your-key
```

### Tuning Parameters
```python
# More results
await search_relevant_knowledge(
    task_embedding,
    requirements,
    match_count=20,         # Default: 15
    match_threshold=0.6     # Default: 0.7
)

# Limit links
deduplicate_chunks(chunks, max_chunks=20)  # Default: 15
```

## 💡 Common Patterns

### Pattern 1: Check Before Starting
```python
result = await auto_link_task_knowledge(task_id)

if result.coverage_score >= 0.6:
    start_task(task_id)
else:
    block_task(task_id, f"Low coverage: {result.coverage_score:.2%}")
```

### Pattern 2: Link on Creation
```python
async def create_task(task_data):
    task = supabase.table("tasks").insert(task_data).execute()
    task_id = task.data[0]['id']

    await auto_link_task_knowledge(task_id)
    return task_id
```

### Pattern 3: Background Linking
```python
async def background_linker():
    while True:
        # Get unlinked tasks
        result = supabase.table("tasks")\
            .select("id")\
            .is_("knowledge_coverage_score", "null")\
            .execute()

        if result.data:
            task_ids = [t['id'] for t in result.data]
            await batch_link_tasks(task_ids)

        await asyncio.sleep(300)  # Every 5 minutes
```

### Pattern 4: Update on Change
```python
async def update_task_description(task_id, new_desc):
    # Update task
    supabase.table("tasks").update({
        "description": new_desc
    }).eq("id", task_id).execute()

    # Refresh knowledge
    await refresh_task_knowledge(task_id)
```

## 🐛 Troubleshooting

### No Knowledge Found
```python
# Lower threshold
result = await search_relevant_knowledge(
    embedding,
    requirements,
    match_threshold=0.5  # Lower from 0.7
)
```

### Low Coverage
```python
# Check what's missing
result = await auto_link_task_knowledge(task_id)
print(f"Missing: {result.missing_knowledge}")
print(f"Suggested sources:")
for source in result.suggested_crawl_sources:
    print(f"  {source}")
```

### Slow Performance
```python
# Use batch processing
await batch_link_tasks(task_ids)  # Parallel

# Or reduce match_count
await search_relevant_knowledge(
    embedding,
    requirements,
    match_count=10  # Fewer results
)
```

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `/archon/knowledge_linker.py` | Core implementation |
| `/examples/knowledge_linker_usage.py` | 8 complete examples |
| `/docs/KNOWLEDGE_LINKER_INTEGRATION.md` | Integration guide |
| `/test_knowledge_linker.py` | Test suite |
| `KNOWLEDGE_LINKER_SUMMARY.md` | Full documentation |

## 🧪 Testing

```bash
# Run test suite
python test_knowledge_linker.py

# Test with real task
python archon/knowledge_linker.py <task-uuid>

# Run example
python examples/knowledge_linker_usage.py single
```

## 📖 Database Queries

### Get Task Coverage
```sql
SELECT
    id,
    name,
    knowledge_coverage_score,
    array_length(attached_knowledge_ids, 1) as num_links
FROM tasks
WHERE knowledge_coverage_score IS NOT NULL
ORDER BY knowledge_coverage_score DESC;
```

### Find Low Coverage Tasks
```sql
SELECT id, name, knowledge_coverage_score
FROM tasks
WHERE knowledge_coverage_score < 0.4
AND status = 'pending';
```

### Get Linked Knowledge
```sql
SELECT * FROM get_task_knowledge('task-uuid');
```

## 🔄 Workflow Integration

```
Task Created
    ↓
auto_link_task_knowledge()
    ↓
├─→ High Coverage (≥0.7)  → Mark as READY
├─→ Med Coverage (0.4-0.7) → Keep as PENDING
└─→ Low Coverage (<0.4)    → Mark as BLOCKED
    ↓
Suggest Crawl Sources
    ↓
Trigger Crawls
    ↓
Re-link Tasks
```

## 🎓 Learning Resources

1. **Quick Start**: Run `python test_knowledge_linker.py`
2. **Examples**: See `/examples/knowledge_linker_usage.py`
3. **Integration**: Read `/docs/KNOWLEDGE_LINKER_INTEGRATION.md`
4. **Full Docs**: See `KNOWLEDGE_LINKER_SUMMARY.md`

## 💬 Support

- **Logs**: Check `workbench/logs.txt`
- **Database**: Review Supabase dashboard
- **Test**: Run test suite to verify setup
- **Examples**: Try the 8 examples in usage file

---

**Ready to use!** Start with `python test_knowledge_linker.py` then try linking real tasks.
