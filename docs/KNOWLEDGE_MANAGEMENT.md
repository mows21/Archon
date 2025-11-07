# Archon Knowledge Management System

## Overview

The Archon Knowledge Management System extends Archon's capabilities with **Motion-inspired AI project management** and **knowledge-aware task execution**. This system enables Archon to:

- Automatically attach relevant documentation to tasks
- Manage complex projects with dependencies
- Schedule tasks based on knowledge availability
- Build knowledge graphs showing relationships between concepts
- Learn from task completions and store insights

## Architecture

### Core Concept: Knowledge-Aware Agents

Instead of building project management as a separate feature, we use **Archon itself** to build specialized agents that handle project management, task scheduling, and knowledge linking. This recursive approach makes the system incredibly powerful and flexible.

```
User: "Build a FastAPI authentication system"
    ↓
Scraper Agent (built by Archon) → Crawls FastAPI + OAuth docs
    ↓
Project Decomposer Agent → Creates tasks with knowledge requirements
    ↓
Knowledge Linker Agent → Attaches relevant docs to each task
    ↓
Executor Agent → Runs task with injected knowledge context
    ↓
Learning System → Stores insights back to knowledge base
```

## Database Schema

### Enhanced `site_pages` Table

The existing table now includes:

```sql
tags TEXT[]                  -- e.g., ['fastapi', 'authentication', 'jwt']
knowledge_type TEXT          -- 'documentation', 'tutorial', 'api_reference', etc.
framework TEXT               -- 'fastapi', 'react', 'pydantic_ai', etc.
language TEXT                -- 'python', 'javascript', 'typescript', etc.
last_updated TIMESTAMP       -- When this knowledge was last crawled
```

### New Tables

#### `knowledge_sources`
Tracks external documentation sources and crawl schedules.

```sql
source_url TEXT              -- URL to crawl
framework TEXT               -- Framework/library name
crawl_frequency TEXT         -- 'daily', 'weekly', 'monthly', 'on-demand'
last_crawled TIMESTAMP
```

#### `projects`
Projects with knowledge context and auto-scheduling.

```sql
name TEXT
description TEXT
required_knowledge_tags TEXT[]      -- ['fastapi', 'authentication']
required_frameworks TEXT[]          -- ['fastapi', 'pydantic']
knowledge_context_embedding VECTOR  -- For semantic search
knowledge_coverage_score FLOAT      -- 0-1, how much knowledge we have
```

#### `tasks`
Tasks with attached knowledge and agent assignment.

```sql
project_id UUID
name TEXT
description TEXT
required_knowledge_tags TEXT[]
task_context_embedding VECTOR       -- For matching to knowledge
attached_knowledge_ids BIGINT[]     -- References to site_pages
learned_knowledge_ids BIGINT[]      -- Knowledge created during task
assigned_agent_type TEXT            -- 'coder', 'scraper', 'refiner'
```

#### `task_knowledge_links`
Many-to-many relationship between tasks and knowledge.

```sql
task_id UUID
knowledge_id BIGINT                 -- References site_pages
relevance_score FLOAT               -- 0-1, how relevant
link_type TEXT                      -- 'required', 'suggested', 'learned'
linked_by TEXT                      -- 'auto', 'user', agent name
```

#### `task_dependencies`
Defines dependencies for task scheduling.

```sql
task_id UUID
depends_on_task_id UUID
dependency_type TEXT                -- 'finish_to_start', 'start_to_start'
lag_minutes INTEGER                 -- Time gap between tasks
```

#### `knowledge_relationships`
Knowledge graph - relationships between knowledge chunks.

```sql
from_knowledge_id BIGINT
to_knowledge_id BIGINT
relationship_type TEXT              -- 'depends_on', 'related_to', 'example_of'
confidence FLOAT                    -- 0-1
```

#### `agent_schedules`
Tracks agent execution schedules and results.

```sql
agent_name TEXT
task_id UUID
scheduled_start TIMESTAMP
actual_start TIMESTAMP
status TEXT                         -- 'scheduled', 'running', 'completed'
result JSONB
```

## Setup Instructions

### 1. Database Schema Setup

1. Navigate to the **Database** tab in Archon's Streamlit UI
2. Scroll to the "Knowledge Management Schema" section
3. Click "Get Setup Instructions for Knowledge Management"
4. Follow the instructions to execute the SQL in Supabase
5. Click "Verify Setup" to confirm

**Or via CLI:**

```bash
cd /home/user/Archon
python utils/knowledge_db_setup.py
```

### 2. Verify Installation

The setup utility will check:
- All tables are created
- Enhanced columns added to site_pages
- RPC functions are working
- Indexes are in place

### 3. Create Sample Data (Optional)

```python
from utils.knowledge_db_setup import KnowledgeDBSetup

setup = KnowledgeDBSetup()
setup.create_sample_data()
```

Or click "Create Sample Project & Tasks" in the Database tab.

## Key Features

### 1. Automatic Knowledge Discovery

When a task is created, the system automatically:
- Extracts technology tags from the description
- Searches the vector database for relevant knowledge
- Creates links with relevance scores
- Identifies knowledge gaps

```python
# Example: Creating a task automatically finds relevant docs
task = {
    'name': 'Implement JWT authentication',
    'description': 'Create JWT token generation and validation',
    'required_knowledge_tags': ['jwt', 'security', 'authentication']
}

# System automatically:
# 1. Searches for JWT documentation chunks
# 2. Links top 10 most relevant chunks
# 3. Sets relevance scores
# 4. Flags if coverage is low (<40%)
```

### 2. Knowledge-Aware Task Execution

When an agent executes a task:
- Retrieves all linked knowledge chunks
- Injects them into the agent's context
- Agent uses RAG to access relevant information
- New insights are stored back to the knowledge base

```python
# Agent receives task with auto-injected knowledge
async def execute_task_with_knowledge(task_id: str):
    task = await get_task(task_id)
    knowledge = await get_task_knowledge(task_id)

    # Knowledge injected into agent context
    result = await executor_agent.run(
        task_description=task['description'],
        knowledge_context=knowledge  # Automatically available
    )
```

### 3. Task Dependencies and Scheduling

Define complex workflows:

```python
# Task 1: Research FastAPI
research_task = create_task('Research FastAPI authentication')

# Task 2: Implement (depends on research)
impl_task = create_task('Implement auth endpoints')
add_dependency(
    task_id=impl_task.id,
    depends_on=research_task.id,
    type='finish_to_start'
)

# System ensures research completes before implementation starts
```

### 4. Knowledge Graph Building

Build relationships between concepts:

```python
# Link related knowledge chunks
create_relationship(
    from_chunk='FastAPI dependency injection intro',
    to_chunk='Pydantic BaseModel usage',
    type='prerequisite_for',
    confidence=0.85
)

# Visualize in UI to see how concepts connect
```

### 5. Learning from Task Completion

The system learns as you work:

```python
# After task completion, extract insights
async def extract_learnings(task_id, result):
    # LLM analyzes what was learned
    insights = await analyze_task_result(task, result)

    # Store as new knowledge chunks
    for insight in insights:
        store_knowledge(
            content=insight,
            tags=task.tags + ['learned_insight'],
            source_task_id=task_id
        )
```

## Advanced RPC Functions

### `match_knowledge_advanced`

Enhanced knowledge search with multiple filters:

```sql
SELECT * FROM match_knowledge_advanced(
    query_embedding := get_embedding('FastAPI authentication'),
    match_count := 10,
    match_threshold := 0.7,
    required_tags := ARRAY['fastapi', 'authentication'],
    required_frameworks := ARRAY['fastapi'],
    knowledge_types := ARRAY['documentation', 'tutorial'],
    language_filter := 'python'
);
```

### `get_task_knowledge`

Retrieve all knowledge for a task:

```sql
SELECT * FROM get_task_knowledge('task-uuid-here');
-- Returns: title, summary, content, relevance_score, link_type
```

### `get_task_dependencies_tree`

Get full dependency tree:

```sql
SELECT * FROM get_task_dependencies_tree('task-uuid-here');
-- Returns: all dependencies with task details and status
```

### `check_knowledge_coverage`

Check if we have enough knowledge:

```sql
SELECT * FROM check_knowledge_coverage(
    ARRAY['fastapi', 'oauth2', 'jwt'],
    ARRAY['fastapi']
);
-- Returns: total_chunks, coverage_score, missing_tags, available_frameworks
```

## Usage Workflows

### Workflow 1: Knowledge-Driven Development

```
1. User: "Build a real-time chat app with WebSockets"

2. System checks knowledge coverage
   - Coverage: 30% (low!)
   - Missing: WebSocket implementation details

3. Scraper Agent triggered automatically
   - Crawls FastAPI WebSocket docs
   - Crawls Socket.IO documentation
   - Stores with tags: ['websockets', 'realtime', 'fastapi']

4. Project Decomposer creates tasks:
   - Task 1: Setup WebSocket connection
     → Attached: 5 WebSocket doc chunks
   - Task 2: Implement message broadcasting
     → Attached: 3 broadcasting pattern chunks
   - Task 3: Add authentication to WebSocket
     → Attached: 4 auth + 2 WebSocket chunks

5. Each task executed with full knowledge context

6. Learnings stored for future projects
```

### Workflow 2: Multi-Framework Project

```
1. User: "Build a full-stack app: React frontend + FastAPI backend"

2. System identifies two frameworks
   - Frontend: React + TypeScript
   - Backend: FastAPI + Python

3. Tasks tagged appropriately:
   - "Design React components" → tags: ['react', 'typescript', 'ui']
   - "Build API endpoints" → tags: ['fastapi', 'python', 'api']

4. Knowledge automatically filtered:
   - React tasks see only React docs
   - FastAPI tasks see only FastAPI docs
   - Integration tasks see both

5. Dependencies ensure proper order:
   - Backend API designed first
   - Frontend components depend on API spec
```

### Workflow 3: Continuous Learning

```
1. Complete a task: "Implement rate limiting"

2. System extracts learnings:
   - "FastAPI dependency injection works well for rate limiters"
   - "Use Redis for distributed rate limiting"
   - "Consider token bucket vs sliding window"

3. Learnings stored as knowledge chunks
   - Tagged: ['rate-limiting', 'fastapi', 'learned_insight']
   - Linked to original task

4. Future similar tasks automatically benefit:
   - Next rate limiting task finds these insights
   - Coverage score higher
   - Less research needed
```

## Archon-Generated Agents

The following agents will be generated by Archon itself to power the knowledge management system:

### 1. Universal Scraper Agent
- Crawls any documentation
- Auto-tags content
- Handles multiple formats (HTML, PDF, Markdown)
- Respects rate limits and robots.txt

### 2. Knowledge Linker Agent
- Analyzes task requirements
- Searches for relevant knowledge
- Calculates relevance scores
- Suggests additional resources

### 3. Project Decomposer Agent
- Breaks down complex projects
- Identifies knowledge requirements
- Creates task hierarchy
- Sets up dependencies

### 4. Context-Aware Executor Agent
- Executes tasks with injected knowledge
- Uses RAG for deep context
- Stores learnings
- Reports progress

### 5. Project Manager Agent
- Orchestrates entire workflow
- Manages agent assignments
- Handles blocking and re-planning
- Provides status updates

## Migration Guide

If you have existing data in `site_pages`:

1. The schema enhancement is **non-destructive**
2. New columns are added with sensible defaults
3. Existing data remains intact
4. You can gradually tag existing knowledge:

```python
# Batch update existing chunks with tags
from utils.utils import get_clients

_, supabase = get_clients()

# Update Pydantic AI docs with framework tag
supabase.table('site_pages')\
    .update({
        'framework': 'pydantic_ai',
        'tags': ['pydantic', 'ai', 'agents'],
        'knowledge_type': 'documentation'
    })\
    .like('url', '%ai.pydantic.dev%')\
    .execute()
```

## Future Enhancements

Planned features:

- **V7**: LangGraph documentation support
- **V8**: Knowledge expiry and auto-refresh
- **V9**: Visual knowledge graph browser
- **V10**: Multi-agent collaborative projects
- **V11**: Automatic test generation based on knowledge
- **V12**: Integration with Motion API for external PM tools

## Troubleshooting

### Schema Won't Install

**Issue**: SQL errors during schema creation

**Solution**:
1. Check Supabase SQL editor for specific error messages
2. Ensure you have admin permissions
3. Run sections one at a time if needed
4. Check logs: `workbench/logs.txt`

### Knowledge Not Linking to Tasks

**Issue**: Tasks created but no knowledge attached

**Solution**:
1. Check if tags are populated: `SELECT tags FROM tasks WHERE id = 'task-id';`
2. Verify knowledge exists with those tags: `SELECT COUNT(*) FROM site_pages WHERE tags && ARRAY['your-tag'];`
3. Run knowledge linker manually (once agent is built)

### Low Coverage Scores

**Issue**: `knowledge_coverage_score` always low

**Solution**:
1. Trigger scraper for needed framework
2. Check tag spelling (exact match required)
3. Lower match threshold: `match_threshold := 0.5`

## Support

- **GitHub Issues**: https://github.com/coleam00/archon/issues
- **Community Forum**: https://thinktank.ottomator.ai/c/archon/30
- **Documentation**: Check `/docs` folder

---

**Built with Archon** - The world's first Agenteer 🤖
