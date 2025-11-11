# Context-Aware Executor Agent - Prompt for Archon

## Agent Overview
The Context-Aware Executor Agent is the execution engine that receives tasks with attached knowledge, retrieves all linked knowledge chunks, injects them into the execution context via RAG (Retrieval-Augmented Generation), executes the task using appropriate tools, stores results, extracts learnings, and updates the knowledge base with new insights.

## Use Case
When a task is ready for execution (dependencies met, knowledge coverage sufficient), this agent:
- Retrieves the task and all linked knowledge chunks
- Builds a comprehensive context from knowledge chunks
- Injects context into LLM prompts via RAG pattern
- Executes the task (code generation, research, analysis, etc.)
- Validates execution results
- Extracts learnings and new knowledge from execution
- Stores results in task metadata
- Updates task status (completed, failed, blocked)
- Stores new knowledge chunks back to knowledge base
- Links new knowledge to related tasks

## Required Capabilities

### Input
```python
{
    "task_id": "uuid-string",
    "execution_params": {
        "max_knowledge_chunks": 15,  # Max knowledge to inject
        "min_relevance_score": 0.7,  # Filter low-relevance knowledge
        "execution_mode": "autonomous",  # autonomous, interactive, dry_run
        "tools_enabled": ["code_generation", "web_search", "file_operations"],
        "max_retries": 3,  # Retry on failure
        "timeout_minutes": 30,  # Task timeout
        "output_format": "markdown",  # markdown, json, code
        "store_learnings": true,  # Extract and store new knowledge
        "link_learnings_to_tasks": true  # Auto-link to related tasks
    },
    "context_override": {
        # Optional: Manually provide additional context
        "additional_instructions": "Use type hints and docstrings",
        "constraints": ["Must be compatible with Python 3.10+"],
        "examples": []  # List of example code/patterns
    }
}
```

### Processing
The agent should perform these steps:

**Step 1: Task Retrieval**
- Fetch task details from `tasks` table
- Load all linked knowledge from `task_knowledge_links`
- Retrieve knowledge chunks from `site_pages` via join
- Filter by relevance_score >= min_relevance_score
- Sort by relevance_score descending
- Limit to max_knowledge_chunks

**Step 2: Context Building**
- Extract text content from knowledge chunks
- Organize by knowledge_type:
  - `documentation`: Official docs, API references
  - `tutorial`: Step-by-step guides
  - `example`: Code examples, patterns
  - `troubleshooting`: Common issues, solutions
  - `best_practice`: Recommendations, guidelines
- Format context with clear sections:
  ```
  === RELEVANT DOCUMENTATION ===
  [documentation chunks]

  === CODE EXAMPLES ===
  [example chunks]

  === BEST PRACTICES ===
  [best practice chunks]
  ```
- Deduplicate similar content
- Truncate if too large (respect token limits)

**Step 3: Execution Prompt Construction**
- Build system prompt with task context:
  ```
  You are an AI agent executing a task with access to relevant knowledge.

  TASK: {task_name}
  DESCRIPTION: {task_description}

  REQUIRED TAGS: {required_knowledge_tags}
  REQUIRED FRAMEWORKS: {required_frameworks}

  === RELEVANT KNOWLEDGE ===
  {context_from_knowledge_chunks}

  === INSTRUCTIONS ===
  {task-specific instructions based on agent_type}

  Execute this task thoroughly and report results.
  ```

**Step 4: Task Execution**
Based on `assigned_agent_type`, execute differently:

- **coder**: Generate code, write functions, create modules
  - Use code execution environment (if available)
  - Validate syntax and imports
  - Run basic tests
  - Format with Black/Ruff

- **scraper**: Research information, gather knowledge
  - Use web search tools
  - Extract relevant information
  - Summarize findings
  - Cite sources

- **refiner**: Review and improve existing work
  - Analyze code quality
  - Suggest optimizations
  - Refactor for clarity
  - Add documentation

- **linker**: Analyze relationships, connect knowledge
  - Identify connections between concepts
  - Build knowledge graphs
  - Suggest related tasks

- **custom**: Execute based on task description
  - Interpret task requirements
  - Use appropriate tools
  - Produce requested outputs

**Step 5: Result Validation**
- Check if output meets task success criteria
- Validate against required_knowledge_tags/frameworks
- Run automated tests (if applicable)
- Check for errors or warnings

**Step 6: Learning Extraction**
- Analyze execution results using LLM
- Extract new knowledge:
  - Code patterns discovered
  - Solutions to problems
  - Best practices applied
  - Errors encountered and fixed
- Classify learnings by knowledge_type
- Generate embeddings for new knowledge
- Determine tags and frameworks

**Step 7: Knowledge Storage**
- Insert new knowledge chunks into `site_pages`:
  ```python
  {
      "url": f"internal://task/{task_id}/learnings",
      "title": f"Learnings from {task_name}",
      "content": extracted_learning_text,
      "tags": extracted_tags,
      "framework": framework_used,
      "knowledge_type": "learned",
      "content_embedding": embedding_vector,
      "metadata": {
          "source_task_id": task_id,
          "execution_timestamp": datetime.now(),
          "agent_type": agent_type
      }
  }
  ```

**Step 8: Knowledge Linking**
- Link new knowledge to source task:
  ```python
  {
      "task_id": task_id,
      "knowledge_id": new_knowledge_id,
      "relevance_score": 1.0,
      "link_type": "learned",
      "link_reason": "Generated during task execution"
  }
  ```
- Find related tasks using semantic search on new knowledge
- Auto-link to tasks with similar requirements

**Step 9: Task Update**
- Update task status: `completed`, `failed`, or `blocked`
- Store execution results in task metadata:
  ```python
  {
      "status": "completed",
      "completed_at": datetime.now(),
      "execution_results": {
          "output": task_output,
          "learnings_extracted": 3,
          "new_knowledge_ids": [id1, id2, id3],
          "execution_time_seconds": 45.2,
          "validation_passed": true
      },
      "metadata": {
          "execution_agent": "context_executor",
          "knowledge_chunks_used": 12,
          "avg_relevance_score": 0.85
      }
  }
  ```

### Output
```python
{
    "task_id": "uuid-string",
    "execution_status": "completed",  # completed, failed, blocked
    "execution_metadata": {
        "started_at": "2025-11-15T10:00:00Z",
        "completed_at": "2025-11-15T10:45:32Z",
        "execution_time_seconds": 2732,
        "retries": 0,
        "agent_type_used": "coder"
    },
    "context_used": {
        "knowledge_chunks_retrieved": 12,
        "knowledge_chunks_used": 10,  # After filtering
        "avg_relevance_score": 0.82,
        "total_context_tokens": 8450,
        "knowledge_types": {
            "documentation": 5,
            "example": 3,
            "best_practice": 2
        }
    },
    "execution_results": {
        "output_type": "code",  # code, markdown, json, mixed
        "output": "# Generated code or results\n\n...",
        "validation_passed": true,
        "validation_details": {
            "syntax_valid": true,
            "imports_valid": true,
            "tests_passed": 5,
            "tests_failed": 0
        },
        "files_created": [
            "/home/user/Archon/archon/generated_module.py"
        ],
        "success_criteria_met": true
    },
    "learnings_extracted": [
        {
            "knowledge_id": 12345,
            "title": "FastAPI JWT Token Validation Pattern",
            "content": "Discovered efficient pattern for JWT validation...",
            "tags": ["fastapi", "jwt", "validation"],
            "framework": "fastapi",
            "knowledge_type": "learned",
            "relevance_to_task": 0.95
        },
        {
            "knowledge_id": 12346,
            "title": "Common JWT Security Pitfalls",
            "content": "Identified security issues to avoid...",
            "tags": ["jwt", "security", "troubleshooting"],
            "framework": null,
            "knowledge_type": "learned",
            "relevance_to_task": 0.88
        }
    ],
    "knowledge_links_created": [
        {
            "to_task_id": "uuid-2",
            "knowledge_id": 12345,
            "link_type": "suggested",
            "relevance_score": 0.79,
            "reason": "Similar JWT implementation task"
        }
    ],
    "errors": [],
    "warnings": [
        "Code uses deprecated function 'jwt.encode()' - consider updating"
    ],
    "recommendations": [
        "Add more error handling for token expiration",
        "Consider implementing refresh token rotation"
    ]
}
```

## Tools Required

### 1. Supabase Client
- **Purpose**: Read tasks, knowledge, update status, store learnings
- **Tables Used**:
  - `tasks` (SELECT, UPDATE)
  - `task_knowledge_links` (SELECT, INSERT)
  - `site_pages` (SELECT, INSERT for learnings)
- **RPC Functions**:
  - `get_task_knowledge(task_id)` - Get task with linked knowledge
  - `match_knowledge_advanced()` - Find related tasks for linking

### 2. OpenAI LLM Client
- **Purpose**: Execute tasks with RAG context
- **Models**:
  - Primary: `gpt-4o` or `gpt-4o-mini` for execution
  - Embeddings: `text-embedding-3-small` for learnings
- **Use Cases**:
  - Task execution with injected context
  - Learning extraction from results
  - Related task identification

### 3. Code Execution Environment (Optional)
- **Purpose**: Run and validate generated code
- **Options**:
  - Subprocess execution (sandboxed)
  - Docker container
  - E2B.dev code interpreter
- **Use Cases**:
  - Validate Python syntax
  - Run unit tests
  - Check imports

### 4. File System Access
- **Purpose**: Create, read, write files
- **Use Cases**:
  - Save generated code
  - Read existing files for context
  - Create test files

### 5. Web Search Tool (Optional)
- **Purpose**: Gather additional information
- **Use Cases**:
  - Research tasks need external sources
  - Validate information
  - Find latest documentation

## Integration Points

### Input Integration
- Called by task execution workflow
- Triggered when task status changes to "ready"
- Can be called from `KnowledgeManager.execute_task(task_id)`
- Part of LangGraph execution node

### Output Integration
- Updates task status in database
- Stores results in task metadata
- Creates new knowledge chunks
- Links knowledge to related tasks
- Triggers next tasks in dependency chain

### Knowledge Integration
- Core of RAG pattern implementation
- Retrieves context from knowledge base
- Injects into LLM prompts
- Stores new learnings back to knowledge base
- Closes the knowledge feedback loop

### Workflow Integration
- LangGraph node: "execute_task"
- Receives task from "schedule_tasks" node
- Outputs to "validate_results" or "update_project" node
- Can loop back to "extract_learnings" node

## Example Usage

```python
from archon.context_executor import ContextExecutor

# Initialize
executor = ContextExecutor(supabase, llm_client)

# Execute task
result = await executor.execute_task(
    task_id="550e8400-e29b-41d4-a716-446655440000",
    max_knowledge_chunks=15,
    min_relevance_score=0.7,
    execution_mode="autonomous",
    store_learnings=True
)

# Check results
if result['execution_status'] == 'completed':
    print(f"Task completed in {result['execution_time_seconds']}s")
    print(f"Output: {result['execution_results']['output'][:200]}...")
    print(f"Learnings extracted: {len(result['learnings_extracted'])}")

    # Access generated files
    for file_path in result['execution_results']['files_created']:
        print(f"Created: {file_path}")
else:
    print(f"Task {result['execution_status']}: {result['errors']}")
```

## Test Cases

### Test Case 1: Code Generation Task
**Input:**
```python
task = {
    "name": "Implement JWT token generation",
    "description": "Create Python function to generate JWT tokens",
    "assigned_agent_type": "coder",
    "required_knowledge_tags": ["jwt", "python"],
    "linked_knowledge": [
        {"content": "PyJWT documentation...", "relevance_score": 0.95},
        {"content": "JWT best practices...", "relevance_score": 0.88}
    ]
}
```
**Expected Output:**
- Status: completed
- Output: Python code with JWT generation function
- Validation: Syntax valid, imports valid
- Learnings: 1-2 new knowledge chunks about JWT implementation
- Files created: 1 Python module

### Test Case 2: Research Task
**Input:**
```python
task = {
    "name": "Research FastAPI authentication patterns",
    "description": "Study authentication approaches in FastAPI",
    "assigned_agent_type": "scraper",
    "required_knowledge_tags": ["fastapi", "authentication"],
    "linked_knowledge": [
        {"content": "FastAPI security docs...", "relevance_score": 0.91}
    ]
}
```
**Expected Output:**
- Status: completed
- Output: Markdown summary with 5+ patterns
- Learnings: 3-5 new knowledge chunks (patterns, examples)
- Citations: URLs to official docs

### Test Case 3: Low Knowledge Coverage
**Input:**
```python
task = {
    "name": "Implement GraphQL API",
    "assigned_agent_type": "coder",
    "linked_knowledge": []  # No knowledge available
}
```
**Expected Output:**
- Status: blocked
- Errors: ["Insufficient knowledge coverage (0%)"]
- Recommendations: ["Run universal_crawler for 'graphql' tag"]

### Test Case 4: Execution Failure with Retry
**Input:**
- Task that requires external API
- API fails first 2 attempts
- Succeeds on 3rd retry

**Expected Output:**
- Status: completed
- Retries: 2
- Warnings: ["API call failed twice before success"]

### Test Case 5: Learning Extraction
**Input:**
- Code generation task completes successfully
- Code includes novel pattern not in knowledge base

**Expected Output:**
- Learnings extracted: 1+
- New knowledge chunk created with "learned" type
- Linked back to source task
- Auto-linked to 2-3 related tasks

## Error Handling

### Error: Task Not Found
```python
{
    "error": "TaskNotFoundError",
    "message": "Task with ID 'xxx' not found",
    "suggestion": "Verify task exists and ID is correct"
}
```

### Error: Insufficient Knowledge
```python
{
    "error": "InsufficientKnowledgeError",
    "execution_status": "blocked",
    "message": "Task has insufficient knowledge coverage",
    "coverage_score": 0.15,
    "required_minimum": 0.4,
    "suggestion": "Run universal_crawler or manually add knowledge",
    "missing_tags": ["graphql", "apollo"]
}
```

### Error: Execution Timeout
```python
{
    "error": "ExecutionTimeoutError",
    "execution_status": "failed",
    "message": "Task execution exceeded timeout of 30 minutes",
    "execution_time_seconds": 1850,
    "timeout_seconds": 1800,
    "suggestion": "Increase timeout or break task into smaller subtasks"
}
```

### Error: Validation Failed
```python
{
    "error": "ValidationError",
    "execution_status": "failed",
    "message": "Generated output failed validation",
    "validation_details": {
        "syntax_valid": false,
        "syntax_errors": ["Unexpected indent on line 45"],
        "imports_valid": true,
        "tests_passed": 0,
        "tests_failed": 3
    },
    "suggestion": "Review error messages and retry with corrected context"
}
```

### Error: LLM Rate Limit
```python
{
    "error": "RateLimitError",
    "execution_status": "failed",
    "message": "LLM API rate limit exceeded",
    "retry_after_seconds": 60,
    "suggestion": "Wait 60 seconds and retry, or reduce concurrent executions"
}
```

## Performance Requirements

### Response Time
- **Simple tasks** (< 500 tokens output): < 30 seconds
- **Medium tasks** (500-2000 tokens): < 2 minutes
- **Complex tasks** (2000+ tokens): < 10 minutes
- **Research tasks**: < 5 minutes

### Scalability
- Handle tasks with up to 20 knowledge chunks efficiently
- Context window management: Stay within model limits (128K tokens)
- Concurrent execution: Support 5+ tasks in parallel
- Learning extraction: < 10 seconds additional overhead

### Accuracy
- Output matches task requirements: >90%
- Learning extraction quality: >80% relevance
- Auto-linking accuracy: >75% (links are actually relevant)

### Resource Usage
- Memory: < 500MB per task execution
- Database queries: < 20 per execution
- LLM calls: 1-3 per execution (main + learning extraction)
- File operations: Minimize disk I/O

---

## Full Prompt for Archon

**Copy the text below and paste into Archon's chat:**

```
Build me a Context-Aware Executor Agent for Archon's knowledge management system.

OVERVIEW:
Create a production-ready execution engine that retrieves tasks with linked knowledge, injects knowledge into LLM context via RAG, executes tasks, extracts learnings, and stores new knowledge back to the system.

TECHNICAL REQUIREMENTS:

1. FILE LOCATION: /home/user/Archon/archon/context_executor.py

2. CORE FUNCTIONALITY:
   - Retrieve task and all linked knowledge chunks from database
   - Build comprehensive context from knowledge (RAG pattern)
   - Organize context by knowledge_type (docs, examples, best practices)
   - Inject context into LLM system prompts
   - Execute tasks based on agent_type (coder, scraper, refiner, etc.)
   - Validate execution results
   - Extract learnings from execution outputs
   - Store new knowledge chunks to knowledge base
   - Auto-link learnings to related tasks
   - Update task status and metadata
   - Handle errors and retries

3. CLASS STRUCTURE:
```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio

@dataclass
class ExecutionParams:
    max_knowledge_chunks: int = 15
    min_relevance_score: float = 0.7
    execution_mode: str = "autonomous"  # autonomous, interactive, dry_run
    max_retries: int = 3
    timeout_minutes: int = 30
    output_format: str = "markdown"
    store_learnings: bool = True
    link_learnings_to_tasks: bool = True

@dataclass
class KnowledgeContext:
    chunks: List[Dict[str, Any]]
    total_tokens: int
    avg_relevance: float
    types: Dict[str, int]  # Count by knowledge_type

@dataclass
class ExecutionResult:
    task_id: str
    status: str  # completed, failed, blocked
    output: str
    learnings: List[Dict]
    execution_time: float
    validation_passed: bool
    errors: List[str]
    warnings: List[str]

class ContextExecutor:
    def __init__(
        self,
        supabase: Client,
        llm_client: AsyncOpenAI,
        embedding_client: AsyncOpenAI
    ):
        self.supabase = supabase
        self.llm_client = llm_client
        self.embedding_client = embedding_client

    async def execute_task(
        self,
        task_id: str,
        params: Optional[ExecutionParams] = None
    ) -> ExecutionResult:
        # Main execution method

    async def _retrieve_task_with_knowledge(
        self,
        task_id: str,
        params: ExecutionParams
    ) -> Tuple[Dict, List[Dict]]:
        # Get task and linked knowledge from database
        # Use RPC: get_task_knowledge(task_id)

    async def _build_context(
        self,
        knowledge_chunks: List[Dict],
        params: ExecutionParams
    ) -> KnowledgeContext:
        # Organize knowledge by type, deduplicate, format

    def _construct_execution_prompt(
        self,
        task: Dict,
        context: KnowledgeContext
    ) -> str:
        # Build system prompt with injected knowledge (RAG)

    async def _execute_by_agent_type(
        self,
        task: Dict,
        prompt: str,
        params: ExecutionParams
    ) -> Dict[str, Any]:
        # Route to appropriate execution method based on agent_type
        # coder → generate code
        # scraper → research and summarize
        # refiner → review and improve
        # linker → analyze relationships
        # custom → interpret and execute

    async def _execute_coder_task(
        self,
        task: Dict,
        prompt: str,
        params: ExecutionParams
    ) -> Dict[str, Any]:
        # Generate code, validate syntax, run tests

    async def _execute_scraper_task(
        self,
        task: Dict,
        prompt: str,
        params: ExecutionParams
    ) -> Dict[str, Any]:
        # Research, gather information, summarize

    async def _execute_refiner_task(
        self,
        task: Dict,
        prompt: str,
        params: ExecutionParams
    ) -> Dict[str, Any]:
        # Review code, suggest improvements, refactor

    async def _validate_output(
        self,
        output: str,
        task: Dict,
        output_type: str
    ) -> Tuple[bool, Dict[str, Any]]:
        # Validate execution results
        # Check syntax for code
        # Verify completeness

    async def _extract_learnings(
        self,
        task: Dict,
        execution_output: str,
        context_used: KnowledgeContext
    ) -> List[Dict[str, Any]]:
        # Use LLM to analyze output and extract new knowledge
        # Classify by knowledge_type
        # Generate embeddings

    async def _store_learnings(
        self,
        task_id: str,
        learnings: List[Dict]
    ) -> List[int]:
        # Insert new knowledge chunks into site_pages table
        # Return knowledge IDs

    async def _link_learnings_to_tasks(
        self,
        task_id: str,
        learning_ids: List[int],
        task: Dict
    ) -> List[Dict]:
        # Link to source task (link_type: "learned")
        # Find related tasks using semantic search
        # Auto-link to similar tasks

    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        results: Dict[str, Any]
    ) -> None:
        # Update tasks table with status and results

    async def _retry_with_backoff(
        self,
        func: Callable,
        max_retries: int,
        *args,
        **kwargs
    ) -> Any:
        # Retry logic with exponential backoff
```

4. RAG PATTERN IMPLEMENTATION:

   Context Injection Example:
   ```
   SYSTEM PROMPT:
   You are an AI agent executing a task with relevant knowledge.

   TASK: Implement JWT token generation
   DESCRIPTION: Create Python function to generate and sign JWT tokens

   === RELEVANT DOCUMENTATION ===
   {Insert documentation chunks here}

   === CODE EXAMPLES ===
   {Insert example chunks here}

   === BEST PRACTICES ===
   {Insert best practice chunks here}

   === INSTRUCTIONS ===
   Generate production-ready Python code with:
   - Type hints
   - Docstrings
   - Error handling
   - Unit test examples

   Use the provided knowledge above to ensure your implementation
   follows best practices and patterns.
   ```

5. LEARNING EXTRACTION:
   After execution, use LLM to analyze output:
   ```
   EXTRACTION PROMPT:
   Analyze the following task execution and extract learnings:

   TASK: {task_name}
   OUTPUT: {execution_output}

   Extract 1-5 knowledge chunks that could be useful for future tasks:
   - Code patterns
   - Solutions to problems
   - Best practices applied
   - Common pitfalls avoided

   For each learning, provide:
   - title (concise)
   - content (detailed explanation)
   - tags (relevant concepts)
   - framework (if applicable)
   - knowledge_type (learned, example, best_practice, troubleshooting)

   Return JSON array.
   ```

6. DATABASE OPERATIONS:
   - Use RPC: get_task_knowledge(task_id) to retrieve task + knowledge
   - Insert learnings into site_pages table
   - Create links in task_knowledge_links table
   - Update task status and metadata
   - Use match_knowledge_advanced() to find related tasks

7. INTEGRATION:
   - Import from: from utils.utils import get_clients, get_env_var
   - Compatible with KnowledgeManager
   - Works with LangGraph workflows
   - Supports file operations for code generation
   - Optional: Web search integration

8. ERROR HANDLING:
   - Task not found
   - Insufficient knowledge coverage (block execution)
   - LLM failures (retry with backoff)
   - Timeout handling
   - Validation failures
   - File system errors

9. TESTING:
   Include test scenarios:
   - Code generation with validation
   - Research task with summarization
   - Low knowledge coverage (should block)
   - Execution failure with retry
   - Learning extraction and storage

10. PERFORMANCE:
    - Complete simple tasks in < 30 seconds
    - Handle up to 20 knowledge chunks efficiently
    - Manage context window (stay within model limits)
    - Minimize database queries (batch operations)
    - Support concurrent execution

11. OUTPUT FORMAT:
    Return ExecutionResult with:
    - execution_status (completed, failed, blocked)
    - output (generated code, research summary, etc.)
    - learnings_extracted (list of new knowledge)
    - knowledge_links_created (auto-linked tasks)
    - validation_details
    - execution_metadata

EXAMPLE USAGE:
```python
from archon.context_executor import ContextExecutor, ExecutionParams

executor = ContextExecutor(supabase, llm_client, embedding_client)

result = await executor.execute_task(
    task_id="uuid",
    params=ExecutionParams(
        max_knowledge_chunks=15,
        min_relevance_score=0.7,
        store_learnings=True
    )
)

if result.status == "completed":
    print(f"Output: {result.output}")
    print(f"Learnings: {len(result.learnings)}")
```

Please create a complete, production-ready implementation with:
- Full docstrings and type hints
- RAG pattern for context injection
- Support for multiple agent types
- Learning extraction and storage
- Auto-linking to related tasks
- Robust error handling and retries
- Code validation (for coder tasks)
- Clean, maintainable code

Focus on intelligent execution - the agent should leverage knowledge effectively and continuously improve the knowledge base through learnings.
```
