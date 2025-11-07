# Knowledge Manager Orchestrator - Usage Guide

## Overview

The Knowledge Manager Orchestrator (`archon/knowledge_manager.py`) is the central coordination layer for Archon's knowledge-aware project and task management system. It orchestrates all knowledge management operations and integrates with the universal_crawler and knowledge_linker (to be built in Phase 2-3).

## Architecture

```
User creates project → Extract requirements → Check coverage
    ↓ (if low coverage)
Trigger scraper → Wait for crawl → Auto-link knowledge
    ↓ (if good coverage)
Auto-link knowledge → Create tasks → Return to user
```

## Quick Start

### Initialize the Manager

```python
from archon.knowledge_manager import KnowledgeManager
import asyncio

async def main():
    # Auto-initializes with Supabase and OpenAI clients from env
    km = KnowledgeManager()

    # Or provide your own clients
    km = KnowledgeManager(
        supabase=my_supabase_client,
        embedding_client=my_embedding_client,
        llm_client=my_llm_client
    )
```

### Create a Project with Auto-Discovery

```python
# Create a project - automatically discovers knowledge needs
project = await km.create_project(
    name="FastAPI Authentication System",
    description="Build a complete authentication system with JWT tokens, OAuth2, and password reset using FastAPI and PostgreSQL",
    priority=1,  # 1=highest, 5=lowest
    deadline=datetime(2025, 12, 31),
    auto_discover=True,  # Automatically check knowledge coverage
    min_coverage=0.4  # Trigger scraper if coverage < 40%
)

# Returns:
# {
#     "project": {...},  # Project metadata
#     "coverage": {
#         "total_chunks": 150,
#         "coverage_score": 0.75,
#         "missing_tags": [],
#         "available_frameworks": ["fastapi", "pydantic"],
#         "needs_scraping": False
#     },
#     "scraper_triggered": False
# }
```

### Create Tasks with Auto-Linking

```python
# Create a task - automatically links relevant knowledge
task = await km.create_task(
    project_id=project['project']['id'],
    name="Implement JWT token generation",
    description="Create JWT token generation and validation using PyJWT with RS256 algorithm",
    priority=1,
    deadline=datetime(2025, 11, 15),
    auto_link=True,  # Automatically link relevant docs
    assigned_agent_type="coder"
)

# Returns:
# {
#     "task": {...},  # Task metadata
#     "linked_knowledge": [
#         {
#             "id": 123,
#             "title": "JWT Authentication in FastAPI",
#             "content": "...",
#             "similarity": 0.89
#         },
#         ...
#     ],
#     "coverage_score": 0.82,
#     "links_created": 8
# }
```

### Get Task with All Knowledge

```python
# Get a task with all its linked knowledge chunks
task_with_knowledge = await km.get_task_with_knowledge(task_id)

# Returns:
# {
#     "task": {...},
#     "linked_knowledge": [
#         {
#             "id": 123,
#             "url": "https://...",
#             "title": "JWT Authentication",
#             "content": "...",
#             "tags": ["jwt", "authentication"],
#             "framework": "fastapi",
#             "relevance_score": 0.89,
#             "link_type": "suggested"
#         },
#         ...
#     ]
# }
```

### Decompose Project into Tasks

```python
# Break a project into tasks using LLM
tasks = await km.decompose_project(
    project_id=project['project']['id'],
    decomposition_strategy="auto",  # "auto", "sequential", "parallel"
    auto_link_knowledge=True
)

# Returns list of created tasks with dependencies
# [
#     {"task": {...}, "linked_knowledge": [...], "coverage_score": 0.75},
#     {"task": {...}, "linked_knowledge": [...], "coverage_score": 0.68},
#     ...
# ]
```

### Check Knowledge Coverage

```python
# Check if we have enough knowledge for specific requirements
coverage = await km.check_and_acquire_knowledge(
    tags=["authentication", "jwt", "oauth2"],
    frameworks=["fastapi", "pydantic"],
    min_coverage=0.4
)

# Returns:
# KnowledgeCoverage(
#     total_chunks=45,
#     coverage_score=0.35,
#     missing_tags=["oauth2"],
#     available_frameworks=["fastapi", "pydantic"],
#     needs_scraping=True  # True if coverage < min_coverage
# )
```

### Manually Link/Re-link Knowledge

```python
# Link or refresh knowledge links for a task
result = await km.link_task_knowledge(
    task_id=task_id,
    refresh=True,  # Delete existing links and re-link
    top_k=15  # Number of top knowledge chunks to link
)

# Returns:
# {
#     "linked_knowledge": [...],
#     "coverage_score": 0.82,
#     "links_created": 12
# }
```

### Update Project/Task Status

```python
# Update project status
await km.update_project_status(
    project_id=project_id,
    status="in_progress",  # planning, ready, in_progress, blocked, completed, cancelled, on_hold
    metadata={"started_by": "agent_123"}
)

# Update task status
await km.update_task_status(
    task_id=task_id,
    status="completed",  # pending, ready, in_progress, blocked, completed, cancelled, failed
    metadata={"completed_by": "coder_agent"}
)
```

## Parallel Operations

### Batch Create Tasks

```python
# Create multiple tasks in parallel
task_definitions = [
    {
        "name": "Setup database models",
        "description": "Create SQLAlchemy models for users and sessions",
        "priority": 1
    },
    {
        "name": "Implement password hashing",
        "description": "Use bcrypt for secure password hashing",
        "priority": 2
    },
    {
        "name": "Create JWT utilities",
        "description": "Token generation and validation functions",
        "priority": 2
    }
]

tasks = await km.batch_create_tasks(
    project_id=project_id,
    task_definitions=task_definitions,
    auto_link=True
)
```

### Batch Link Knowledge

```python
# Link knowledge to multiple tasks in parallel
task_ids = ["uuid-1", "uuid-2", "uuid-3"]
results = await km.batch_link_knowledge(
    task_ids=task_ids,
    refresh=False
)
```

### Batch Check Coverage

```python
# Check coverage for multiple combinations in parallel
combinations = [
    (["authentication", "jwt"], ["fastapi"]),
    (["database", "orm"], ["sqlalchemy"]),
    (["websockets", "realtime"], ["fastapi"])
]

coverages = await km.batch_check_coverage(
    tag_framework_pairs=combinations,
    min_coverage=0.4
)
```

## Agent Registry (Coming in Phase 2)

```python
# Register an agent
agent = await km.register_agent(
    agent_name="jwt_coder_v1",
    agent_type="coder",
    capabilities={
        "languages": ["python"],
        "frameworks": ["fastapi"],
        "specializations": ["authentication", "jwt"]
    },
    metadata={
        "created_by": "archon",
        "version": "1.0"
    }
)
```

## Complete Example Workflow

```python
import asyncio
from datetime import datetime, timedelta
from archon.knowledge_manager import KnowledgeManager

async def build_auth_system():
    # Initialize
    km = KnowledgeManager()

    # 1. Create project with auto-discovery
    print("Creating project...")
    project = await km.create_project(
        name="FastAPI Authentication System",
        description="Build a complete authentication system with JWT tokens, OAuth2, and password reset functionality using FastAPI and PostgreSQL",
        priority=1,
        deadline=datetime.now() + timedelta(days=30),
        auto_discover=True,
        min_coverage=0.4
    )

    project_id = project['project']['id']
    print(f"✓ Project created: {project_id}")
    print(f"  Coverage: {project['coverage']['coverage_score']:.2f}")
    print(f"  Scraper needed: {project['scraper_triggered']}")

    # 2. If coverage is good, decompose into tasks
    if not project['scraper_triggered']:
        print("\nDecomposing project into tasks...")
        tasks = await km.decompose_project(
            project_id=project_id,
            decomposition_strategy="auto",
            auto_link_knowledge=True
        )

        print(f"✓ Created {len(tasks)} tasks")
        for task in tasks:
            print(f"  - {task['task']['name']}: {task['coverage_score']:.2f} coverage")

        # 3. Update project status
        await km.update_project_status(
            project_id=project_id,
            status="ready"
        )

        print("\n✓ Project is ready for execution!")

    else:
        print("\n⚠ Waiting for scraper to acquire missing knowledge...")
        print(f"  Missing tags: {project['coverage']['missing_tags']}")

    return project

# Run it
if __name__ == "__main__":
    asyncio.run(build_auth_system())
```

## Integration with Streamlit

```python
# In your Streamlit app
import streamlit as st
from archon.knowledge_manager import KnowledgeManager
import asyncio

# Initialize (cached)
@st.cache_resource
def get_manager():
    return KnowledgeManager()

km = get_manager()

# Create project form
with st.form("create_project"):
    name = st.text_input("Project Name")
    description = st.text_area("Description")
    priority = st.slider("Priority", 1, 5, 3)

    if st.form_submit_button("Create Project"):
        with st.spinner("Creating project..."):
            project = asyncio.run(km.create_project(
                name=name,
                description=description,
                priority=priority,
                auto_discover=True
            ))

            st.success(f"Project created! Coverage: {project['coverage']['coverage_score']:.2f}")

            if project['scraper_triggered']:
                st.warning("Low knowledge coverage. Triggering scraper...")
```

## Integration with LangGraph

```python
# In your LangGraph workflow
from archon.knowledge_manager import KnowledgeManager
from langgraph.graph import StateGraph

km = KnowledgeManager()

async def create_project_node(state):
    """Node to create a project with knowledge discovery"""
    project = await km.create_project(
        name=state['project_name'],
        description=state['project_description'],
        auto_discover=True
    )

    return {
        "project_id": project['project']['id'],
        "coverage": project['coverage']['coverage_score'],
        "needs_scraping": project['scraper_triggered']
    }

async def decompose_project_node(state):
    """Node to decompose project into tasks"""
    tasks = await km.decompose_project(
        project_id=state['project_id'],
        auto_link_knowledge=True
    )

    return {"tasks": tasks}

# Add to your graph
graph = StateGraph(YourState)
graph.add_node("create_project", create_project_node)
graph.add_node("decompose_project", decompose_project_node)
# ... etc
```

## Configuration

The Knowledge Manager uses environment variables from `workbench/env_vars.json`:

- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_SERVICE_KEY`: Your Supabase service key
- `EMBEDDING_MODEL`: Embedding model (default: text-embedding-3-small)
- `EMBEDDING_PROVIDER`: Provider (OpenAI, Ollama, etc.)
- `EMBEDDING_API_KEY`: API key for embeddings
- `PRIMARY_MODEL`: LLM model for extraction (default: gpt-4o-mini)
- `LLM_PROVIDER`: LLM provider
- `LLM_API_KEY`: API key for LLM

## Error Handling

All methods include comprehensive error handling and logging:

```python
try:
    project = await km.create_project(...)
except ValueError as e:
    print(f"Validation error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
    # Check logs in workbench/logs.txt
```

## Logging

All operations are logged to:
- Console (via Python logging)
- `workbench/logs.txt` (via write_to_log)

```python
import logging
logging.basicConfig(level=logging.INFO)

# Now you'll see detailed logs
km = KnowledgeManager()
```

## Next Steps (Phase 2-3)

The following integrations are placeholders and will be implemented in future phases:

1. **Universal Scraper Integration** (Phase 2)
   - `_trigger_scraper()` will actually trigger the scraper agent
   - Scraper will crawl missing documentation
   - Results will be automatically indexed

2. **Knowledge Linker Agent** (Phase 2)
   - Dedicated agent for intelligent knowledge linking
   - Advanced relevance scoring
   - Multi-hop knowledge graph traversal

3. **Project Decomposer Agent** (Phase 3)
   - Replace LLM decomposition with specialized agent
   - Better task breakdown strategies
   - Automatic dependency detection

4. **Context-Aware Executor** (Phase 3)
   - Agent that executes tasks with injected knowledge
   - Learning from execution results
   - Storing new insights

## API Reference

See inline docstrings in `knowledge_manager.py` for complete API documentation. All methods include:
- Type hints
- Comprehensive docstrings
- Parameter descriptions
- Return value descriptions
- Example usage in docstrings

## Testing

```python
# Run the built-in test
python archon/knowledge_manager.py
```

This will create a sample project and demonstrate the workflow.
