# Project Decomposer Agent - Prompt for Archon

## Agent Overview
The Project Decomposer Agent intelligently analyzes project descriptions and breaks them down into 5-15 actionable, well-structured tasks. It identifies dependencies, estimates durations, assigns priorities, extracts knowledge requirements, creates task hierarchies, and assigns appropriate agent types for execution.

## Use Case
When a user creates a new project in Archon's knowledge management system, this agent:
- Analyzes the project description and constraints
- Breaks it into concrete, executable tasks
- Identifies task dependencies and critical paths
- Estimates durations and sets priorities
- Maps knowledge requirements (tags, frameworks) to each task
- Assigns appropriate agent types (coder, scraper, refiner, etc.)
- Creates parent/child task relationships
- Ensures tasks are not too granular (no micro-tasks) or too broad

## Required Capabilities

### Input
```python
{
    "project_id": "uuid-string",
    "project_name": "FastAPI Authentication System",
    "project_description": "Build a complete authentication system with JWT tokens...",
    "required_knowledge_tags": ["authentication", "jwt", "security"],
    "required_frameworks": ["fastapi", "pydantic"],
    "constraints": {
        "deadline": "2025-12-31T00:00:00Z",  # Optional
        "max_tasks": 15,  # Default: 15
        "min_tasks": 5,   # Default: 5
        "complexity_target": "medium",  # low, medium, high
        "decomposition_strategy": "auto"  # auto, sequential, parallel, hybrid
    },
    "metadata": {
        "priority": 2,
        "estimated_total_hours": 40  # Optional hint
    }
}
```

### Processing
The agent should perform these steps:

**Step 1: Analysis**
- Parse project description using LLM
- Extract key requirements, deliverables, and constraints
- Identify technical domains (backend, frontend, database, etc.)
- Determine optimal number of tasks (5-15 range)
- Assess overall project complexity

**Step 2: Task Generation**
- Generate 5-15 concrete, actionable tasks
- Each task should be:
  - Completable by a single agent
  - Estimated at 15 minutes to 8 hours
  - Have clear success criteria
  - Not require human intervention mid-task
- Avoid micro-tasks (e.g., "write one function")
- Avoid mega-tasks (e.g., "build entire backend")

**Step 3: Dependency Analysis**
- Identify dependencies between tasks
- Classify dependency types:
  - `finish_to_start`: Task B starts after Task A completes (most common)
  - `start_to_start`: Task B can start when Task A starts
  - `finish_to_finish`: Task B finishes when Task A finishes
- Calculate lag times (optional delay between dependent tasks)
- Identify the critical path

**Step 4: Task Enrichment**
- Extract knowledge requirements for each task:
  - `required_knowledge_tags`: Specific concepts needed
  - `required_frameworks`: Libraries/tools needed
  - `programming_language`: Primary language for the task
- Estimate duration in minutes
- Assign priority (1=highest, 5=lowest)
- Assign appropriate agent type:
  - `coder`: Write code, implement features
  - `scraper`: Research, gather information
  - `refiner`: Review, optimize, refactor
  - `linker`: Connect knowledge, analyze relationships
  - `custom`: Special-purpose tasks

**Step 5: Hierarchy Creation**
- Group related tasks under parent tasks
- Create parent/child relationships where appropriate
- Example: "Build Authentication" (parent) → "Implement JWT", "Create Endpoints" (children)

**Step 6: Validation**
- Ensure task count is within bounds (5-15)
- Verify no circular dependencies
- Check that all tasks have at least one path to completion
- Validate that knowledge requirements are specific

### Output
```python
{
    "project_id": "uuid-string",
    "decomposition_metadata": {
        "total_tasks": 12,
        "total_estimated_minutes": 2400,
        "critical_path_duration_minutes": 1800,
        "parallelization_potential": 0.67,  # 0-1, how much can run in parallel
        "complexity_score": 7.5,  # 1-10
        "decomposition_strategy_used": "hybrid"
    },
    "tasks": [
        {
            "name": "Research FastAPI authentication patterns",
            "description": "Study FastAPI documentation, OAuth2 implementations, and JWT best practices. Create summary of patterns and recommendations.",
            "priority": 1,
            "estimated_duration_minutes": 120,
            "required_knowledge_tags": ["fastapi", "authentication", "oauth2", "jwt"],
            "required_frameworks": ["fastapi"],
            "programming_language": "python",
            "assigned_agent_type": "scraper",
            "parent_task_name": null,  # Top-level task
            "dependencies": [],  # No dependencies
            "success_criteria": "Documentation summary created with at least 5 implementation patterns",
            "blocking_risk": "low",  # low, medium, high
            "knowledge_coverage_required": 0.6  # 0-1, minimum coverage needed to start
        },
        {
            "name": "Implement JWT token generation",
            "description": "Create Python module with functions to generate, sign, and validate JWT tokens. Include refresh token logic.",
            "priority": 2,
            "estimated_duration_minutes": 180,
            "required_knowledge_tags": ["jwt", "security", "cryptography", "python"],
            "required_frameworks": ["pyjwt", "python-jose"],
            "programming_language": "python",
            "assigned_agent_type": "coder",
            "parent_task_name": "Build core authentication logic",
            "dependencies": [
                {
                    "depends_on_task_name": "Research FastAPI authentication patterns",
                    "dependency_type": "finish_to_start",
                    "lag_minutes": 0
                }
            ],
            "success_criteria": "JWT module with 100% test coverage, handles expiration and refresh",
            "blocking_risk": "medium",
            "knowledge_coverage_required": 0.7
        }
        // ... more tasks
    ],
    "task_groups": [
        {
            "group_name": "Build core authentication logic",
            "child_tasks": ["Implement JWT token generation", "Create password hashing utilities"],
            "estimated_duration_minutes": 360
        }
    ],
    "critical_path": [
        "Research FastAPI authentication patterns",
        "Implement JWT token generation",
        "Create authentication endpoints",
        "Write integration tests"
    ],
    "warnings": [
        "Task 'Implement JWT token generation' has medium blocking risk - ensure sufficient knowledge coverage",
        "No database tasks identified - may need manual verification"
    ]
}
```

## Tools Required

### 1. Supabase Client
- **Purpose**: Read project data, insert tasks, create dependencies
- **Tables Used**:
  - `projects` (SELECT)
  - `tasks` (INSERT)
  - `task_dependencies` (INSERT)

### 2. OpenAI LLM Client
- **Purpose**: Analyze project descriptions, generate tasks
- **Models**: `gpt-4o-mini` or `gpt-4o` for complex projects
- **Use Cases**:
  - Parse project description
  - Generate task list
  - Extract knowledge requirements
  - Estimate durations

### 3. Knowledge Coverage Checker
- **Purpose**: Check if knowledge exists for generated tasks
- **RPC Function**: `check_knowledge_coverage(required_tags, required_frameworks)`
- **Use**: Validate that tasks are achievable with available knowledge

### 4. Dependency Graph Analyzer
- **Purpose**: Detect circular dependencies, calculate critical path
- **Algorithm**: Topological sort, longest path in DAG
- **Libraries**: NetworkX or custom implementation

## Integration Points

### Input Integration
- Called by `KnowledgeManager.decompose_project(project_id, strategy)`
- Receives project data from `projects` table
- Can be triggered from Streamlit UI Projects page

### Output Integration
- Creates tasks in `tasks` table via Supabase
- Creates dependencies in `task_dependencies` table
- Returns task list to KnowledgeManager
- Triggers `TaskScheduler` agent after completion (optional)

### Knowledge Integration
- Uses existing knowledge base to validate task requirements
- Checks coverage scores before finalizing tasks
- May trigger `UniversalCrawler` if coverage < 40%

### Workflow Integration
- Integrates with LangGraph workflow as a node
- Can be called as part of project creation workflow
- Outputs feed into task scheduling and execution

## Example Usage

```python
from archon.project_decomposer import ProjectDecomposer

# Initialize
decomposer = ProjectDecomposer()

# Decompose project
result = await decomposer.decompose_project(
    project_id="550e8400-e29b-41d4-a716-446655440000",
    strategy="auto",  # auto, sequential, parallel, hybrid
    auto_insert=True,  # Insert tasks into database
    check_coverage=True  # Verify knowledge coverage
)

# Access results
print(f"Created {result['total_tasks']} tasks")
print(f"Critical path: {result['critical_path_duration_minutes']} minutes")
print(f"Parallelization: {result['parallelization_potential']:.0%}")

# Get tasks
for task in result['tasks']:
    print(f"- {task['name']} ({task['estimated_duration_minutes']}m)")
```

## Test Cases

### Test Case 1: Simple Sequential Project
**Input:**
```python
{
    "project_name": "Build a REST API",
    "project_description": "Create a simple REST API with 3 endpoints using FastAPI",
    "constraints": {"complexity_target": "low"}
}
```
**Expected Output:**
- 5-7 tasks
- Mostly sequential dependencies
- All tasks assigned to `coder` agent
- Total duration: 4-8 hours

### Test Case 2: Complex Parallel Project
**Input:**
```python
{
    "project_name": "Full-Stack E-commerce Platform",
    "project_description": "Build complete e-commerce with frontend, backend, database, payments",
    "constraints": {"complexity_target": "high", "max_tasks": 15}
}
```
**Expected Output:**
- 12-15 tasks
- Multiple parallel branches (frontend, backend, database)
- Mix of agent types (coder, scraper, refiner)
- Total duration: 40-80 hours
- Parallelization potential > 0.6

### Test Case 3: Research-Heavy Project
**Input:**
```python
{
    "project_name": "Implement Advanced ML Pipeline",
    "project_description": "Research and implement a machine learning pipeline with experiment tracking",
    "constraints": {"complexity_target": "high"}
}
```
**Expected Output:**
- 8-12 tasks
- Multiple `scraper` tasks at the beginning
- Clear research → implementation → testing flow
- High knowledge requirements

### Test Case 4: Edge Case - Vague Description
**Input:**
```python
{
    "project_name": "Make something cool",
    "project_description": "Build a thing",
    "constraints": {}
}
```
**Expected Output:**
- Agent asks for clarification (error or clarification request)
- OR generates generic template tasks
- Warns about vague requirements

### Test Case 5: Circular Dependency Detection
**Scenario:** Manually inject circular dependency
**Expected Output:**
- Error raised: "Circular dependency detected: Task A → Task B → Task A"
- No tasks inserted into database
- Provides suggestion to fix

## Error Handling

### Error: Project Not Found
```python
{
    "error": "ProjectNotFoundError",
    "message": "Project with ID 'xxx' not found",
    "suggestion": "Verify project exists and ID is correct"
}
```

### Error: Insufficient Information
```python
{
    "error": "InsufficientInformationError",
    "message": "Project description too vague to decompose",
    "suggestion": "Provide more details about features, technologies, and goals",
    "minimum_required": ["feature list", "tech stack", "target platform"]
}
```

### Error: Circular Dependencies
```python
{
    "error": "CircularDependencyError",
    "message": "Circular dependency detected in task graph",
    "cycle": ["Task A", "Task B", "Task C", "Task A"],
    "suggestion": "Remove dependency from 'Task C' to 'Task A'"
}
```

### Error: Knowledge Coverage Too Low
```python
{
    "error": "LowKnowledgeCoverageWarning",
    "warning_type": "warning",  # Non-fatal
    "message": "Several tasks have < 40% knowledge coverage",
    "low_coverage_tasks": [
        {"task": "Implement GraphQL API", "coverage": 0.15}
    ],
    "suggestion": "Run universal_crawler before proceeding or reduce scope"
}
```

### Error: Task Count Out of Bounds
```python
{
    "error": "TaskCountError",
    "message": "Generated 23 tasks, exceeds max_tasks=15",
    "suggestion": "Increase max_tasks or reduce project scope",
    "auto_fix": "Merge similar tasks to fit within bounds"
}
```

## Performance Requirements

### Response Time
- **Simple projects** (complexity: low): < 10 seconds
- **Medium projects** (complexity: medium): < 30 seconds
- **Complex projects** (complexity: high): < 60 seconds

### Scalability
- Handle projects up to 15 tasks efficiently
- Dependency graph operations must be O(n log n) or better
- Parallel LLM calls for independent analysis where possible

### Accuracy
- Task estimates within ±30% of actual (measured over time)
- Dependency detection: >90% accuracy
- Knowledge requirement extraction: >85% precision

### Resource Usage
- Maximum 5 LLM calls per decomposition
- Database transactions batched (insert all tasks in one transaction)
- Memory usage: < 100MB for typical project

---

## Full Prompt for Archon

**Copy the text below and paste into Archon's chat:**

```
Build me a Project Decomposer Agent for Archon's knowledge management system.

OVERVIEW:
Create a production-ready agent that analyzes project descriptions and intelligently breaks them into 5-15 actionable tasks with dependencies, estimates, and knowledge requirements.

TECHNICAL REQUIREMENTS:

1. FILE LOCATION: /home/user/Archon/archon/project_decomposer.py

2. CORE FUNCTIONALITY:
   - Analyze project descriptions using LLM (gpt-4o-mini)
   - Generate 5-15 concrete, executable tasks
   - Identify task dependencies (finish-to-start, start-to-start, finish-to-finish)
   - Estimate duration for each task (15 minutes to 8 hours)
   - Extract knowledge requirements (tags, frameworks, language)
   - Assign agent types (coder, scraper, refiner, linker, custom)
   - Create parent/child task hierarchies
   - Detect circular dependencies
   - Calculate critical path
   - Validate knowledge coverage

3. CLASS STRUCTURE:
```python
class ProjectDecomposer:
    def __init__(self, supabase: Client, llm_client: AsyncOpenAI):
        # Initialize with Supabase and LLM clients

    async def decompose_project(
        self,
        project_id: str,
        strategy: str = "auto",  # auto, sequential, parallel, hybrid
        auto_insert: bool = True,
        check_coverage: bool = True
    ) -> Dict[str, Any]:
        # Main method - returns task list with metadata

    async def _analyze_project(self, project_data: Dict) -> Dict:
        # Use LLM to understand project scope

    async def _generate_tasks(self, analysis: Dict) -> List[Dict]:
        # Generate 5-15 tasks using LLM

    async def _extract_dependencies(self, tasks: List[Dict]) -> List[Dict]:
        # Identify and classify dependencies

    async def _calculate_critical_path(self, tasks: List[Dict], deps: List[Dict]) -> List[str]:
        # Use graph algorithm to find critical path

    async def _enrich_tasks(self, tasks: List[Dict]) -> List[Dict]:
        # Add knowledge requirements, estimates, priorities

    async def _validate_task_graph(self, tasks: List[Dict], deps: List[Dict]) -> Tuple[bool, List[str]]:
        # Check for circular dependencies, validate structure

    async def _insert_tasks_to_db(self, project_id: str, tasks: List[Dict], deps: List[Dict]) -> List[str]:
        # Batch insert tasks and dependencies
```

4. LLM PROMPT TEMPLATES:
   Create these system prompts:

   a) Project Analysis Prompt:
   "You are an AI project manager analyzing project descriptions. Extract:
   - Key deliverables
   - Technical domains (frontend, backend, database, etc.)
   - Complexity level (1-10)
   - Recommended task count (5-15)
   - Decomposition strategy (sequential, parallel, hybrid)

   Return JSON format."

   b) Task Generation Prompt:
   "You are an AI project manager breaking down projects into tasks. Generate 5-15 tasks that are:
   - Actionable and concrete
   - Completable by a single agent
   - 15 minutes to 8 hours each
   - Have clear success criteria

   For each task provide:
   - name (clear, action-oriented)
   - description (detailed, specific)
   - estimated_duration_minutes
   - priority (1-5)
   - required_knowledge_tags (list)
   - required_frameworks (list)
   - programming_language
   - assigned_agent_type (coder, scraper, refiner, linker, custom)
   - dependencies (list of task names)
   - parent_task_name (optional)

   Return JSON array."

5. INTEGRATION POINTS:
   - Import from: from utils.utils import get_clients, get_env_var
   - Database tables: projects, tasks, task_dependencies
   - Call check_knowledge_coverage RPC for validation
   - Use NetworkX for graph algorithms (or custom implementation)
   - Return format compatible with KnowledgeManager

6. ERROR HANDLING:
   - Handle missing projects gracefully
   - Detect and report circular dependencies
   - Warn on low knowledge coverage (< 40%)
   - Validate task count bounds (5-15)
   - Provide helpful error messages

7. TESTING:
   Include these test scenarios in docstrings:
   - Simple sequential project (5-7 tasks)
   - Complex parallel project (12-15 tasks)
   - Research-heavy project (multiple scraper tasks)
   - Edge case: vague description
   - Edge case: circular dependency detection

8. PERFORMANCE:
   - Batch database operations
   - Minimize LLM calls (max 5 per decomposition)
   - Use async/await throughout
   - Complete in < 60 seconds for complex projects

9. OUTPUT FORMAT:
   Return dictionary with:
   - project_id
   - decomposition_metadata (counts, durations, scores)
   - tasks (list of task dicts)
   - task_groups (parent/child groupings)
   - critical_path (ordered list of task names)
   - warnings (list of issues/suggestions)

EXAMPLE USAGE:
```python
from archon.project_decomposer import ProjectDecomposer

decomposer = ProjectDecomposer(supabase, llm_client)

result = await decomposer.decompose_project(
    project_id="uuid",
    strategy="auto",
    auto_insert=True,
    check_coverage=True
)

print(f"Created {result['total_tasks']} tasks")
print(f"Critical path: {result['critical_path']}")
```

Please create a complete, production-ready implementation with:
- Full docstrings
- Type hints
- Error handling
- Logging
- Async operations
- Clean, maintainable code

Focus on intelligence and accuracy - this agent should produce high-quality task decompositions that enable successful project execution.
```
