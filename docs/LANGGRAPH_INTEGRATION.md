# LangGraph Knowledge Management Integration

Complete guide for integrating knowledge management into Archon's LangGraph workflows.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Components](#components)
- [Usage Examples](#usage-examples)
- [Integration Patterns](#integration-patterns)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Overview

This integration adds knowledge-aware project and task management capabilities to Archon's existing agent creation workflow. It enables:

- ✅ Automatic knowledge coverage checking
- ✅ Intelligent documentation crawling when knowledge gaps exist
- ✅ Semantic knowledge linking to tasks
- ✅ LLM-powered project decomposition
- ✅ Dependency-aware task scheduling
- ✅ Knowledge-injected task execution

### Key Benefits

1. **Automated Knowledge Discovery**: System automatically identifies and acquires missing knowledge
2. **Context-Aware Execution**: Tasks execute with relevant documentation injected into agent context
3. **Intelligent Planning**: Projects decomposed into tasks with automatic dependency resolution
4. **Flexible Integration**: Multiple patterns for integrating with existing workflows

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Archon LangGraph System                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────┐         ┌─────────────────────────┐  │
│  │  Agent Creation  │◄────────┤  Integrated Workflows   │  │
│  │    Workflow      │         │  (Sequential/Parallel/  │  │
│  │  (archon_graph)  │         │   Conditional)          │  │
│  └──────────────────┘         └─────────────────────────┘  │
│           │                              │                  │
│           │                              ▼                  │
│           │                   ┌─────────────────────────┐  │
│           └──────────────────►│  Knowledge Workflow     │  │
│                                │  (knowledge_workflow)   │  │
│                                └─────────────────────────┘  │
│                                           │                  │
│                      ┌────────────────────┼─────────────┐   │
│                      ▼                    ▼             ▼   │
│           ┌────────────────┐   ┌──────────────┐  ┌────────┐│
│           │ Check Coverage │   │ Acquire      │  │ Link   ││
│           │                │   │ Knowledge    │  │ Tasks  ││
│           └────────────────┘   └──────────────┘  └────────┘│
│                                           │                  │
│                      ┌────────────────────┼─────────────┐   │
│                      ▼                    ▼             ▼   │
│           ┌────────────────┐   ┌──────────────┐  ┌────────┐│
│           │ Decompose      │   │ Schedule     │  │ Execute││
│           │ Project        │   │ Tasks        │  │ Tasks  ││
│           └────────────────┘   └──────────────┘  └────────┘│
│                                                              │
└─────────────────────────────────────────────────────────────┘
           │                    │                    │
           ▼                    ▼                    ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐
│ Knowledge        │  │ Universal        │  │ Supabase     │
│ Manager          │  │ Crawler          │  │ Database     │
│ (Orchestrator)   │  │ (Acquisition)    │  │ (Storage)    │
└──────────────────┘  └──────────────────┘  └──────────────┘
```

### Workflow States

The system uses two main state schemas:

1. **KnowledgeState**: For knowledge-focused workflows
2. **CombinedState**: For integrated agent+knowledge workflows

---

## Components

### 1. Knowledge Workflow Nodes (`knowledge_workflow.py`)

Individual LangGraph nodes for knowledge operations:

#### `check_knowledge_node`
Checks if required knowledge exists in the database.

```python
async def check_knowledge_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Returns:
        - coverage_score: 0-1 score
        - needs_scraping: bool
        - required_tags: List[str]
        - required_frameworks: List[str]
    """
```

#### `acquire_knowledge_node`
Triggers universal_crawler to fetch missing documentation.

```python
async def acquire_knowledge_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Returns:
        - crawl_status: "completed" | "failed"
        - crawled_urls: List[str]
        - crawl_progress: Dict
    """
```

#### `link_knowledge_node`
Links relevant knowledge chunks to tasks using semantic search.

```python
async def link_knowledge_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Returns:
        - linked_knowledge: List[Dict]
        - coverage_score: float
    """
```

#### `decompose_project_node`
Breaks projects into actionable tasks using LLM.

```python
async def decompose_project_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Returns:
        - task_ids: List[str]
        - schedule: List[Dict]
    """
```

#### `schedule_tasks_node`
Creates task schedule based on dependencies and priorities.

```python
async def schedule_tasks_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Returns:
        - schedule: List[Dict] with scheduled_start/end times
    """
```

#### `execute_with_knowledge_node`
Executes task with relevant knowledge injected into context.

```python
async def execute_with_knowledge_node(state: KnowledgeState) -> Dict[str, Any]:
    """
    Returns:
        - execution_result: Dict
        - agent_output: str
    """
```

### 2. Enhanced Workflows (`archon_graph_enhanced.py`)

Pre-built workflow compositions:

#### Full Knowledge Workflow
Complete workflow with all nodes:
```
Check → Acquire (if needed) → Link → Decompose → Schedule → End
```

#### Simple Knowledge Workflow
Quick linking without acquisition:
```
Check → Link → End
```

#### Task Execution Workflow
Focus on single task execution:
```
Check → Acquire (if needed) → Link → Execute → End
```

#### Project Planning Workflow
Planning without execution:
```
Check → Acquire (if needed) → Decompose → Link → Schedule → End
```

### 3. Integrated Workflows (`integrated_workflow.py`)

Three patterns for combining agent creation with knowledge management:

#### Pattern 1: Sequential
Agent creation followed by project management:
```
Agent Workflow → Ask User → Project Workflow → End
```

#### Pattern 2: Parallel
Both workflows run simultaneously:
```
        ┌─► Agent Branch ─┐
Parse ──┤                 ├─► Merge → End
        └─► Project Branch┘
```

#### Pattern 3: Conditional
Route based on detected intent:
```
Detect Intent ──┬─► Agent Workflow → End
                ├─► Project Workflow → End
                └─► Combined Workflow → End
```

---

## Usage Examples

### Example 1: Run Complete Knowledge Workflow

```python
from archon.archon_graph_enhanced import run_knowledge_workflow

# Run full workflow for a project
result = await run_knowledge_workflow(
    project_description="Build a FastAPI authentication system with JWT and OAuth2",
    project_name="FastAPI Auth System",
    min_coverage=0.4,
    thread_id="my-project-123"
)

print(f"Coverage: {result['coverage_score']}")
print(f"Tasks created: {len(result['task_ids'])}")
print(f"Scraper triggered: {result['crawl_status']}")
```

### Example 2: Link Knowledge to Existing Task

```python
from archon.archon_graph_enhanced import run_simple_knowledge_workflow

# Link knowledge to an existing task
result = await run_simple_knowledge_workflow(
    task_id="task-uuid-here",
    thread_id="task-123"
)

print(f"Linked {len(result['linked_knowledge'])} knowledge chunks")
print(f"Coverage: {result['coverage_score']}")
```

### Example 3: Execute Task with Knowledge Context

```python
from archon.archon_graph_enhanced import run_task_execution_workflow

# Execute a task with knowledge injection
result = await run_task_execution_workflow(
    task_id="task-uuid-here",
    min_coverage=0.5,
    thread_id="execution-123"
)

print(f"Execution result: {result['execution_result']}")
print(f"Agent output: {result['agent_output']}")
```

### Example 4: Plan Project with Tasks

```python
from archon.archon_graph_enhanced import run_project_planning_workflow
from archon.knowledge_manager import KnowledgeManager

# Create project first
km = KnowledgeManager()
project = await km.create_project(
    name="E-commerce API",
    description="Build a complete e-commerce REST API with FastAPI",
    priority=1
)

# Plan the project
result = await run_project_planning_workflow(
    project_id=project['project']['id'],
    min_coverage=0.4,
    thread_id="planning-123"
)

print(f"Tasks: {len(result['task_ids'])}")
for task in result['schedule']:
    print(f"  - {task['task_name']} (Priority: {task['priority']})")
```

### Example 5: Integrated Workflow with Intent Detection

```python
from archon.integrated_workflow import run_integrated_workflow

# System automatically detects intent and routes appropriately
result = await run_integrated_workflow(
    user_message="Create an agent for web scraping and plan a project to scrape documentation",
    workflow_type="conditional",
    thread_id="integrated-123"
)

print(f"Agent created: {result['agent_created']}")
print(f"Project created: {result['project_created']}")
```

### Example 6: Using Individual Nodes

```python
from archon.knowledge_workflow import (
    initialize_knowledge_state,
    check_knowledge_node,
    acquire_knowledge_node
)

# Initialize state
state = initialize_knowledge_state(
    project_description="Build a React dashboard with charts",
    min_coverage_threshold=0.4
)

# Check coverage
coverage_result = await check_knowledge_node(state)
state.update(coverage_result)

# Acquire knowledge if needed
if state['needs_scraping']:
    acquire_result = await acquire_knowledge_node(state)
    state.update(acquire_result)
    print(f"Crawled {len(state['crawled_urls'])} pages")
```

### Example 7: Custom Workflow Composition

```python
from langgraph.graph import StateGraph, END
from archon.knowledge_workflow import (
    KnowledgeState,
    check_knowledge_node,
    link_knowledge_node,
    execute_with_knowledge_node
)

# Build custom workflow
graph = StateGraph(KnowledgeState)

# Add only the nodes you need
graph.add_node("check", check_knowledge_node)
graph.add_node("link", link_knowledge_node)
graph.add_node("execute", execute_with_knowledge_node)

# Custom routing
graph.set_entry_point("check")
graph.add_edge("check", "link")
graph.add_edge("link", "execute")
graph.add_edge("execute", END)

# Compile and run
custom_workflow = graph.compile()
result = await custom_workflow.ainvoke(initial_state)
```

---

## Integration Patterns

### Pattern 1: Sequential Integration

**Use Case**: User creates an agent, then wants to create a project using that agent

**Implementation**:
```python
from archon.integrated_workflow import sequential_workflow

# Run sequential workflow
result = await sequential_workflow.ainvoke(
    {
        "latest_user_message": "Create a web scraping agent",
        "create_project_after_agent": True,  # Enable project creation
        # ... other state fields
    },
    config={"configurable": {"thread_id": "seq-123"}}
)
```

**Flow**:
1. User requests agent
2. Agent creation workflow runs
3. System asks if user wants to create project
4. If yes, knowledge workflow runs
5. Generated agent linked to project

### Pattern 2: Parallel Integration

**Use Case**: User wants both agent and project created simultaneously

**Implementation**:
```python
from archon.integrated_workflow import parallel_workflow

# Run parallel workflow
result = await parallel_workflow.ainvoke(
    {
        "latest_user_message": "Create authentication agent and plan auth project",
        "workflow_mode": "combined",
        # ... other state fields
    },
    config={"configurable": {"thread_id": "par-123"}}
)
```

**Flow**:
1. Parse user intent
2. Launch agent creation branch
3. Launch project creation branch (parallel)
4. Merge results when both complete

### Pattern 3: Conditional Integration

**Use Case**: Flexible workflow that adapts to user intent

**Implementation**:
```python
from archon.integrated_workflow import conditional_workflow

# System automatically detects and routes
result = await conditional_workflow.ainvoke(
    {
        "latest_user_message": user_input,
        # workflow_mode will be auto-detected
    },
    config={"configurable": {"thread_id": "cond-123"}}
)
```

**Flow**:
1. LLM detects intent (agent/project/both)
2. Routes to appropriate workflow
3. Returns results

---

## API Reference

### REST API Endpoints (graph_service.py)

#### `POST /knowledge/invoke`
Run knowledge workflow

```json
{
  "project_description": "Build FastAPI app",
  "min_coverage": 0.4,
  "workflow_type": "full",
  "thread_id": "proj-123"
}
```

Response:
```json
{
  "coverage_score": 0.65,
  "task_ids": ["task-1", "task-2"],
  "crawl_status": "completed",
  "workflow_stage": "tasks_scheduled"
}
```

#### `POST /knowledge/check-coverage`
Check knowledge coverage

```json
{
  "tags": ["authentication", "jwt"],
  "frameworks": ["fastapi"],
  "min_coverage": 0.4
}
```

Response:
```json
{
  "coverage_score": 0.7,
  "needs_scraping": false,
  "total_chunks": 25
}
```

#### `POST /knowledge/link-task`
Link knowledge to task

```json
{
  "task_id": "task-uuid",
  "refresh": false
}
```

Response:
```json
{
  "linked_knowledge": [...],
  "coverage_score": 0.8,
  "links_created": 5
}
```

### Streamlit UI Integration

Add to your Streamlit pages:

```python
import streamlit as st
from archon.archon_graph_enhanced import run_knowledge_workflow

st.title("Knowledge-Aware Project Planning")

project_desc = st.text_area("Project Description")
min_coverage = st.slider("Min Coverage", 0.0, 1.0, 0.4)

if st.button("Run Knowledge Workflow"):
    with st.spinner("Running workflow..."):
        result = await run_knowledge_workflow(
            project_description=project_desc,
            min_coverage=min_coverage
        )

    st.success(f"Coverage: {result['coverage_score']:.2f}")
    st.write(f"Created {len(result['task_ids'])} tasks")

    # Display schedule
    for task in result['schedule']:
        st.write(f"- {task['task_name']}")
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/test_langgraph_integration.py -v

# Run specific test categories
pytest tests/test_langgraph_integration.py -m unit
pytest tests/test_langgraph_integration.py -m integration
pytest tests/test_langgraph_integration.py -m slow

# Run with coverage
pytest tests/test_langgraph_integration.py --cov=archon --cov-report=html
```

### Test Structure

```
tests/test_langgraph_integration.py
├── Node Tests (test individual nodes)
├── Routing Tests (test routing logic)
├── Workflow Tests (test complete workflows)
├── State Management Tests (test state handling)
├── Error Handling Tests (test error scenarios)
├── Integration Tests (test workflow integration)
└── Performance Tests (test with multiple tasks)
```

### Mock Testing

The test suite includes comprehensive mocks:

```python
from tests.conftest import mock_knowledge_manager, mock_universal_crawler

@pytest.mark.asyncio
async def test_my_workflow(mock_knowledge_manager, mock_universal_crawler):
    # Your test code here
    result = await check_knowledge_node(state)
    assert result['coverage_score'] > 0
```

---

## Troubleshooting

### Common Issues

#### Issue 1: Low Coverage Score

**Problem**: Coverage score is always low, triggering unnecessary scraping

**Solution**:
- Check if knowledge base is populated: `SELECT COUNT(*) FROM knowledge`
- Verify tags are being extracted correctly
- Lower `min_coverage_threshold` temporarily
- Ensure embedding model is working

```python
# Debug coverage
from archon.knowledge_manager import KnowledgeManager

km = KnowledgeManager()
coverage = await km.check_and_acquire_knowledge(
    tags=["fastapi"],
    frameworks=["fastapi"],
    min_coverage=0.4
)
print(f"Total chunks: {coverage.total_chunks}")
print(f"Coverage: {coverage.coverage_score}")
```

#### Issue 2: Crawler Not Triggering

**Problem**: `needs_scraping` is True but crawler doesn't run

**Solution**:
- Check `acquire_knowledge_node` logs
- Verify framework documentation URLs are configured
- Ensure network access to documentation sites
- Check crawler configuration

```python
# Test crawler directly
from archon.universal_crawler import UniversalCrawler, SourceConfig

crawler = await get_universal_crawler()
result = await crawler.crawl_source(
    SourceConfig(
        source_url="https://fastapi.tiangolo.com",
        framework="fastapi",
        crawl_profile="quick"
    )
)
print(f"Crawled: {len(result['crawled_urls'])} pages")
```

#### Issue 3: Task Scheduling Errors

**Problem**: `schedule_tasks_node` fails or produces incorrect schedule

**Solution**:
- Check for circular dependencies in tasks
- Verify task dependencies exist in database
- Review task priority values
- Check for missing task data

```python
# Debug task dependencies
from archon.knowledge_manager import KnowledgeManager

km = KnowledgeManager()
for task_id in task_ids:
    deps = km.supabase.table("task_dependencies").select("*").eq("task_id", task_id).execute()
    print(f"Task {task_id}: {len(deps.data)} dependencies")
```

#### Issue 4: Knowledge Not Linking to Tasks

**Problem**: `link_knowledge_node` creates no links

**Solution**:
- Verify task has embedding: Check `task_context_embedding` column
- Check knowledge chunks exist for required tags
- Lower similarity threshold in `match_knowledge_advanced`
- Review task tags and frameworks

```python
# Debug knowledge linking
result = km.supabase.rpc(
    "match_knowledge_advanced",
    {
        "query_embedding": task_embedding,
        "match_count": 10,
        "match_threshold": 0.3,  # Lower threshold
        "required_tags": [],  # Remove tag requirement
        "required_frameworks": []
    }
).execute()
print(f"Found {len(result.data)} matches")
```

#### Issue 5: State Not Persisting

**Problem**: State lost between workflow steps

**Solution**:
- Ensure workflow compiled with `checkpointer=memory`
- Use consistent `thread_id` across invocations
- Verify `thread_id` in config

```python
# Correct persistence setup
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
workflow = graph.compile(checkpointer=memory)

# Use consistent thread_id
config = {"configurable": {"thread_id": "my-thread"}}
result1 = await workflow.ainvoke(state1, config)
result2 = await workflow.ainvoke(state2, config)  # Same thread_id
```

### Debug Mode

Enable verbose logging:

```python
import logging

# Enable debug logging for all modules
logging.basicConfig(level=logging.DEBUG)

# Or specific modules
logging.getLogger('archon.knowledge_workflow').setLevel(logging.DEBUG)
logging.getLogger('archon.knowledge_manager').setLevel(logging.DEBUG)
```

### Performance Tips

1. **Batch Operations**: Use `batch_link_knowledge` for multiple tasks
2. **Cache Coverage**: Store coverage results to avoid repeated checks
3. **Limit Crawl Depth**: Use "quick" profile for faster crawling
4. **Parallel Execution**: Use parallel workflow for independent operations
5. **Selective Linking**: Only link top-k most relevant knowledge chunks

---

## Best Practices

### 1. Coverage Thresholds

Choose appropriate thresholds based on use case:

- **0.3-0.4**: Acceptable for general projects
- **0.5-0.7**: Recommended for critical systems
- **0.7+**: High confidence, may trigger frequent crawling

### 2. Crawl Profiles

Select profile based on needs:

- **quick**: Fast scan, summaries only (50 pages, depth 1)
- **default**: Balanced approach (100 pages, depth 2)
- **deep**: Comprehensive crawl (500 pages, depth 5)
- **api-only**: Focus on API docs (200 pages, API filter)

### 3. State Management

- Use descriptive thread IDs: `f"project-{project_id}"`
- Clean up old threads periodically
- Persist important state to database

### 4. Error Handling

Always check workflow stage:

```python
if result['workflow_stage'] == 'error':
    print(f"Error: {result['error_message']}")
    # Handle error
else:
    # Process result
```

### 5. Integration Strategy

Choose pattern based on requirements:

| Pattern | Use When | Pros | Cons |
|---------|----------|------|------|
| Sequential | User flow is linear | Clear progression | Longer total time |
| Parallel | Operations independent | Faster execution | Complex coordination |
| Conditional | Dynamic routing needed | Flexible | Requires intent detection |

---

## Examples Repository

See `/home/user/Archon/examples/` for complete working examples:

- `knowledge_workflow_basic.py`: Basic workflow usage
- `knowledge_workflow_advanced.py`: Advanced patterns
- `integrated_workflow_examples.py`: Integration patterns
- `custom_workflow_composition.py`: Building custom workflows

---

## Support

For issues, questions, or contributions:

- GitHub Issues: [Archon Issues](https://github.com/your-org/archon/issues)
- Documentation: [Full Docs](https://docs.archon.dev)
- Discord: [Community Server](https://discord.gg/archon)

---

## License

This integration is part of Archon and follows the same license.

## Changelog

### v1.0.0 (2025-01-11)
- Initial release
- Complete knowledge workflow integration
- Three integration patterns
- Comprehensive test suite
- Full documentation

---

**Built with ❤️ by the Archon Team**
