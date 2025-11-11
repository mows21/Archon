# Task Scheduler Agent - Prompt for Archon

## Agent Overview
The Task Scheduler Agent is a sophisticated scheduling engine that analyzes task dependencies, calculates critical paths, and schedules tasks based on dependencies, priorities, agent availability, knowledge coverage, and deadlines. It generates timeline data compatible with Gantt charts and handles dynamic re-planning when tasks are blocked or delayed.

## Use Case
After a project has been decomposed into tasks, this agent:
- Analyzes the dependency graph
- Calculates the critical path (longest sequence of dependent tasks)
- Schedules tasks with realistic start and end times
- Respects dependencies (can't start Task B until Task A finishes)
- Considers knowledge coverage (don't schedule if coverage < 40%)
- Balances agent workload across available agents
- Handles blocking scenarios and triggers re-planning
- Generates Gantt-compatible data for visualization
- Provides early warning for deadline risks

## Required Capabilities

### Input
```python
{
    "project_id": "uuid-string",
    "scheduling_params": {
        "start_date": "2025-11-15T09:00:00Z",  # When to start scheduling
        "deadline": "2025-12-31T23:59:59Z",  # Optional project deadline
        "work_hours_per_day": 8,  # Productive hours per day
        "work_days": [1, 2, 3, 4, 5],  # Monday-Friday (1=Monday)
        "min_knowledge_coverage": 0.4,  # Don't schedule tasks with < 40% coverage
        "agent_capacity": {
            "coder": 2,  # 2 coder agents available
            "scraper": 1,
            "refiner": 1,
            "linker": 1,
            "custom": 1
        },
        "buffer_percentage": 0.2,  # Add 20% buffer to estimates
        "allow_parallel": true,  # Allow tasks without dependencies to run in parallel
        "scheduling_algorithm": "critical_path"  # critical_path, earliest_start, resource_leveling
    },
    "constraints": [
        {
            "type": "task_fixed_start",
            "task_id": "uuid",
            "fixed_start": "2025-11-20T10:00:00Z"
        },
        {
            "type": "agent_unavailable",
            "agent_type": "coder",
            "unavailable_from": "2025-12-01T00:00:00Z",
            "unavailable_to": "2025-12-07T23:59:59Z"
        }
    ]
}
```

### Processing
The agent should perform these steps:

**Step 1: Load Task Data**
- Fetch all tasks for the project from `tasks` table
- Load dependencies from `task_dependencies` table
- Check knowledge coverage for each task
- Identify tasks that are blocked due to low coverage

**Step 2: Build Dependency Graph**
- Create directed acyclic graph (DAG) from tasks and dependencies
- Validate no circular dependencies exist
- Calculate in-degree and out-degree for each task
- Identify source tasks (no dependencies) and sink tasks (no dependents)

**Step 3: Calculate Critical Path**
- Use longest path algorithm to find critical path
- Calculate Early Start (ES) and Early Finish (EF) for each task
- Calculate Late Start (LS) and Late Finish (LF) for each task
- Calculate slack/float time: Slack = LS - ES
- Tasks with zero slack are on the critical path

**Step 4: Resource Allocation**
- Count available agents by type
- Track agent utilization over time
- Ensure no agent is over-allocated
- Balance workload across agents

**Step 5: Schedule Generation**
- Start with source tasks (no dependencies)
- For each task:
  - Check if dependencies are complete
  - Check if knowledge coverage >= minimum threshold
  - Check if required agent type is available
  - Calculate scheduled_start based on:
    - Dependency finish times + lag
    - Agent availability
    - Work hours/days constraints
  - Calculate scheduled_end = scheduled_start + (duration × buffer)
  - Mark task as scheduled
- Repeat until all tasks scheduled or blocked

**Step 6: Deadline Analysis**
- Compare project finish date to deadline
- Calculate schedule variance (actual vs. deadline)
- Identify tasks that could be crashed (reduced duration)
- Suggest optimizations if deadline at risk

**Step 7: Generate Timeline Data**
- Create Gantt-compatible data structure
- Include critical path highlighting
- Calculate milestones
- Generate resource utilization charts

### Output
```python
{
    "project_id": "uuid-string",
    "schedule_metadata": {
        "scheduled_start": "2025-11-15T09:00:00Z",
        "scheduled_end": "2025-12-20T17:00:00Z",
        "deadline": "2025-12-31T23:59:59Z",
        "total_duration_days": 35,
        "working_duration_days": 25,
        "buffer_included_percentage": 0.2,
        "on_schedule": true,
        "schedule_variance_days": -11,  # Negative = ahead of schedule
        "critical_path_length_days": 18,
        "parallelization_achieved": 0.72,  # 0-1
        "algorithm_used": "critical_path"
    },
    "scheduled_tasks": [
        {
            "task_id": "uuid-1",
            "task_name": "Research FastAPI authentication patterns",
            "scheduled_start": "2025-11-15T09:00:00Z",
            "scheduled_end": "2025-11-15T11:00:00Z",
            "duration_minutes": 120,
            "buffered_duration_minutes": 144,  # +20%
            "early_start": "2025-11-15T09:00:00Z",
            "early_finish": "2025-11-15T11:24:00Z",
            "late_start": "2025-11-15T09:00:00Z",
            "late_finish": "2025-11-15T11:24:00Z",
            "slack_minutes": 0,  # On critical path
            "is_critical": true,
            "assigned_agent_type": "scraper",
            "assigned_agent_id": "scraper-1",  # Optional
            "dependencies_met": true,
            "knowledge_coverage": 0.85,
            "status": "scheduled",  # scheduled, blocked, completed
            "blocking_reason": null
        },
        {
            "task_id": "uuid-2",
            "task_name": "Implement JWT token generation",
            "scheduled_start": "2025-11-15T11:24:00Z",  # After dependency
            "scheduled_end": "2025-11-15T14:48:00Z",
            "duration_minutes": 180,
            "buffered_duration_minutes": 216,
            "early_start": "2025-11-15T11:24:00Z",
            "early_finish": "2025-11-15T14:48:00Z",
            "late_start": "2025-11-15T11:24:00Z",
            "late_finish": "2025-11-15T14:48:00Z",
            "slack_minutes": 0,
            "is_critical": true,
            "assigned_agent_type": "coder",
            "assigned_agent_id": "coder-1",
            "dependencies_met": true,
            "knowledge_coverage": 0.72,
            "status": "scheduled",
            "blocking_reason": null
        },
        {
            "task_id": "uuid-3",
            "task_name": "Design database schema",
            "scheduled_start": "2025-11-15T09:00:00Z",  # Parallel with research
            "scheduled_end": "2025-11-15T10:30:00Z",
            "duration_minutes": 90,
            "buffered_duration_minutes": 108,
            "early_start": "2025-11-15T09:00:00Z",
            "early_finish": "2025-11-15T10:48:00Z",
            "late_start": "2025-11-16T09:00:00Z",  # Can start later
            "late_finish": "2025-11-16T10:48:00Z",
            "slack_minutes": 480,  # 8 hours of slack
            "is_critical": false,
            "assigned_agent_type": "coder",
            "assigned_agent_id": "coder-2",
            "dependencies_met": true,
            "knowledge_coverage": 0.91,
            "status": "scheduled",
            "blocking_reason": null
        },
        {
            "task_id": "uuid-4",
            "task_name": "Implement advanced ML features",
            "scheduled_start": null,
            "scheduled_end": null,
            "status": "blocked",
            "blocking_reason": "knowledge_coverage_too_low",
            "knowledge_coverage": 0.15,  # < 40%
            "required_action": "Run universal_crawler for tags: ['machine-learning', 'tensorflow']"
        }
    ],
    "critical_path": [
        "uuid-1",  # Research
        "uuid-2",  # JWT implementation
        "uuid-5",  # Create endpoints
        "uuid-7"   # Integration tests
    ],
    "resource_utilization": [
        {
            "agent_type": "coder",
            "total_capacity_hours": 400,  # 2 agents × 25 days × 8 hours
            "allocated_hours": 320,
            "utilization_percentage": 0.80,
            "peak_concurrent_tasks": 2,
            "idle_time_hours": 80
        },
        {
            "agent_type": "scraper",
            "total_capacity_hours": 200,
            "allocated_hours": 120,
            "utilization_percentage": 0.60,
            "peak_concurrent_tasks": 1,
            "idle_time_hours": 80
        }
    ],
    "gantt_data": {
        "tasks": [
            {
                "id": "uuid-1",
                "name": "Research FastAPI authentication patterns",
                "start": "2025-11-15",
                "end": "2025-11-15",
                "duration": 1,
                "progress": 0,
                "type": "task",
                "is_critical": true,
                "dependencies": []
            }
            // ... more tasks
        ],
        "milestones": [
            {
                "name": "Research Phase Complete",
                "date": "2025-11-18",
                "tasks_completed": ["uuid-1", "uuid-3"]
            },
            {
                "name": "Core Implementation Done",
                "date": "2025-12-01",
                "tasks_completed": ["uuid-2", "uuid-5", "uuid-6"]
            }
        ]
    },
    "warnings": [
        "Task 'Implement advanced ML features' blocked due to low knowledge coverage (15%)",
        "Agent type 'coder' has 80% utilization - consider adding capacity if scope increases"
    ],
    "recommendations": [
        "Run universal_crawler for 'machine-learning' and 'tensorflow' to unblock uuid-4",
        "Task 'Design database schema' has 8 hours of slack - can be delayed if needed",
        "Project finishes 11 days ahead of deadline - buffer can absorb 11 days of delays"
    ]
}
```

## Tools Required

### 1. Supabase Client
- **Purpose**: Read tasks, dependencies, update scheduled dates
- **Tables Used**:
  - `tasks` (SELECT, UPDATE for scheduled_start/scheduled_end)
  - `task_dependencies` (SELECT)
  - `projects` (SELECT for deadline)
- **RPC Functions**:
  - `check_knowledge_coverage()` - Verify coverage before scheduling

### 2. Graph Algorithm Library
- **Purpose**: Calculate critical path, topological sort
- **Options**:
  - NetworkX (recommended): Full-featured graph library
  - Custom implementation: Lighter weight
- **Algorithms Needed**:
  - Topological sort (dependency ordering)
  - Longest path in DAG (critical path)
  - All paths enumeration (alternative paths)

### 3. Date/Time Library
- **Purpose**: Handle scheduling calculations
- **Libraries**: datetime, dateutil
- **Use Cases**:
  - Add business days (skip weekends)
  - Calculate duration between dates
  - Handle time zones
  - Respect work hours (9am-5pm)

### 4. OpenAI LLM Client (Optional)
- **Purpose**: Intelligent re-planning suggestions
- **Use Cases**:
  - Suggest which tasks to crash (reduce duration)
  - Recommend parallelization opportunities
  - Analyze schedule risks

## Integration Points

### Input Integration
- Called after `ProjectDecomposer` completes
- Can be called from `KnowledgeManager.schedule_project(project_id)`
- Triggered from Streamlit UI Scheduler page
- Part of LangGraph project workflow

### Output Integration
- Updates `tasks` table with scheduled_start and scheduled_end
- Creates entries in `agent_schedules` table (if exists)
- Feeds data to Gantt chart visualization in UI
- Triggers alerts if deadline at risk

### Knowledge Integration
- Checks task knowledge coverage before scheduling
- Blocks tasks with coverage < minimum threshold
- Suggests crawler runs for blocked tasks
- Re-schedules after knowledge acquisition completes

### Workflow Integration
- LangGraph node: "schedule_tasks"
- Receives task list from "decompose_project" node
- Outputs to "execute_tasks" node
- Can trigger "replan_schedule" on blocking events

## Example Usage

```python
from archon.task_scheduler import TaskScheduler
from datetime import datetime, timezone

# Initialize
scheduler = TaskScheduler(supabase_client)

# Schedule project
result = await scheduler.schedule_project(
    project_id="550e8400-e29b-41d4-a716-446655440000",
    start_date=datetime.now(timezone.utc),
    deadline=datetime(2025, 12, 31, tzinfo=timezone.utc),
    agent_capacity={"coder": 2, "scraper": 1},
    min_knowledge_coverage=0.4,
    auto_update_db=True
)

# Check results
print(f"Project scheduled from {result['scheduled_start']} to {result['scheduled_end']}")
print(f"On schedule: {result['on_schedule']}")
print(f"Critical path: {len(result['critical_path'])} tasks")

# Get blocked tasks
blocked = [t for t in result['scheduled_tasks'] if t['status'] == 'blocked']
for task in blocked:
    print(f"Blocked: {task['task_name']} - {task['blocking_reason']}")

# Export to Gantt
gantt_data = result['gantt_data']
# ... render with visualization library
```

## Test Cases

### Test Case 1: Simple Linear Schedule
**Input:**
- 5 tasks in sequence (A → B → C → D → E)
- No resource constraints
- 8-hour workday, Mon-Fri

**Expected Output:**
- All tasks on critical path (zero slack)
- Tasks scheduled sequentially
- Respects work hours (no scheduling outside 9-5)
- Skips weekends

### Test Case 2: Parallel Tasks with Resource Limits
**Input:**
- 10 tasks, 5 pairs can run in parallel
- Only 2 coder agents available
- All tasks require "coder" agent type

**Expected Output:**
- Maximum 2 tasks scheduled concurrently
- Some tasks wait for agent availability
- Resource utilization ~90%
- Finish time > critical path (due to resource limits)

### Test Case 3: Knowledge Coverage Blocking
**Input:**
- 8 tasks total
- 2 tasks have < 40% knowledge coverage

**Expected Output:**
- 6 tasks scheduled normally
- 2 tasks marked as "blocked" with status "knowledge_coverage_too_low"
- Warnings include "Run universal_crawler for [tags]"
- Recommendations suggest knowledge acquisition

### Test Case 4: Deadline at Risk
**Input:**
- 15 tasks, total estimated duration = 30 days
- Deadline = 25 days from start
- 20% buffer already applied

**Expected Output:**
- scheduled_end > deadline (exceeds by ~6 days)
- on_schedule = false
- schedule_variance_days = +6
- Recommendations include:
  - "Reduce task scope"
  - "Increase agent capacity"
  - "Crash critical path tasks"

### Test Case 5: Re-planning After Task Delay
**Input:**
- Schedule already exists
- Task #3 (on critical path) takes 2x longer than estimated
- Re-run scheduler with updated completion time

**Expected Output:**
- All dependent tasks re-scheduled later
- New schedule_variance calculated
- Warnings if deadline now at risk
- Preserves completed task schedules

## Error Handling

### Error: Circular Dependency Detected
```python
{
    "error": "CircularDependencyError",
    "message": "Cannot schedule project with circular dependencies",
    "cycle": ["Task A", "Task B", "Task C", "Task A"],
    "suggestion": "Fix dependencies using ProjectDecomposer before scheduling"
}
```

### Error: No Source Tasks
```python
{
    "error": "InvalidDependencyGraphError",
    "message": "No source tasks found (all tasks have dependencies)",
    "suggestion": "At least one task must have no dependencies to start"
}
```

### Error: Insufficient Agent Capacity
```python
{
    "error": "InsufficientCapacityWarning",
    "warning_type": "warning",  # Non-fatal
    "message": "Agent capacity too low to meet deadline",
    "required_capacity": {"coder": 4},
    "available_capacity": {"coder": 2},
    "suggestion": "Increase agent capacity or extend deadline"
}
```

### Error: All Tasks Blocked
```python
{
    "error": "AllTasksBlockedError",
    "message": "No tasks can be scheduled - all blocked by low knowledge coverage",
    "blocked_tasks": 15,
    "average_coverage": 0.12,
    "suggestion": "Run universal_crawler for all project requirements before scheduling"
}
```

## Performance Requirements

### Response Time
- **Simple projects** (<10 tasks): < 2 seconds
- **Medium projects** (10-20 tasks): < 5 seconds
- **Complex projects** (20+ tasks): < 10 seconds

### Scalability
- Handle up to 50 tasks efficiently
- Graph algorithms must be O(V + E) or better
- Support for 10+ concurrent agent types
- Schedule calculations in a single database transaction

### Accuracy
- Critical path calculation: 100% accurate
- Schedule dates: Exact (accounting for work hours/days)
- Resource allocation: Zero over-allocation
- Deadline prediction: ±1 day accuracy

### Resource Usage
- Memory: < 50MB for typical project
- Database queries: < 10 per scheduling operation
- No LLM calls required (unless using optional intelligent re-planning)

---

## Full Prompt for Archon

**Copy the text below and paste into Archon's chat:**

```
Build me a Task Scheduler Agent for Archon's knowledge management system.

OVERVIEW:
Create a production-ready scheduling engine that analyzes task dependencies, calculates critical paths, and generates realistic schedules with Gantt chart compatibility.

TECHNICAL REQUIREMENTS:

1. FILE LOCATION: /home/user/Archon/archon/task_scheduler.py

2. CORE FUNCTIONALITY:
   - Load tasks and dependencies from Supabase
   - Build dependency graph (directed acyclic graph)
   - Calculate critical path using longest path algorithm
   - Compute Early Start/Finish and Late Start/Finish for each task
   - Calculate slack/float time (tasks with zero slack are critical)
   - Schedule tasks respecting:
     - Dependencies (finish-to-start, start-to-start, finish-to-finish)
     - Knowledge coverage minimums (don't schedule if < 40%)
     - Agent availability and capacity
     - Work hours/days (e.g., Mon-Fri, 9am-5pm)
     - Fixed constraints (fixed start dates, agent unavailability)
   - Track resource utilization by agent type
   - Generate Gantt-compatible data structure
   - Detect deadline risks and suggest optimizations
   - Support re-planning when tasks are blocked or delayed

3. CLASS STRUCTURE:
```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import networkx as nx  # Or custom graph implementation

@dataclass
class SchedulingParams:
    start_date: datetime
    deadline: Optional[datetime]
    work_hours_per_day: int = 8
    work_days: List[int] = None  # [1,2,3,4,5] = Mon-Fri
    min_knowledge_coverage: float = 0.4
    agent_capacity: Dict[str, int] = None
    buffer_percentage: float = 0.2
    allow_parallel: bool = True
    scheduling_algorithm: str = "critical_path"

class TaskScheduler:
    def __init__(self, supabase: Client):
        # Initialize with Supabase client
        self.supabase = supabase
        self.graph = None

    async def schedule_project(
        self,
        project_id: str,
        start_date: datetime,
        deadline: Optional[datetime] = None,
        params: Optional[SchedulingParams] = None,
        auto_update_db: bool = True
    ) -> Dict[str, Any]:
        # Main scheduling method

    async def _load_tasks_and_dependencies(
        self,
        project_id: str
    ) -> Tuple[List[Dict], List[Dict]]:
        # Fetch from database

    def _build_dependency_graph(
        self,
        tasks: List[Dict],
        dependencies: List[Dict]
    ) -> nx.DiGraph:
        # Create NetworkX directed graph or custom graph

    def _validate_graph(self, graph: nx.DiGraph) -> Tuple[bool, List[str]]:
        # Check for cycles, validate structure

    def _calculate_critical_path(self, graph: nx.DiGraph) -> List[str]:
        # Use longest path algorithm

    def _calculate_early_times(
        self,
        graph: nx.DiGraph,
        start_date: datetime,
        params: SchedulingParams
    ) -> Dict[str, Tuple[datetime, datetime]]:
        # Forward pass: Early Start and Early Finish

    def _calculate_late_times(
        self,
        graph: nx.DiGraph,
        project_end: datetime,
        params: SchedulingParams
    ) -> Dict[str, Tuple[datetime, datetime]]:
        # Backward pass: Late Start and Late Finish

    def _calculate_slack(
        self,
        early_times: Dict,
        late_times: Dict
    ) -> Dict[str, int]:
        # Slack = LS - ES (in minutes)

    async def _schedule_tasks(
        self,
        graph: nx.DiGraph,
        tasks: List[Dict],
        params: SchedulingParams
    ) -> List[Dict]:
        # Generate scheduled_start and scheduled_end for each task
        # Respect all constraints

    def _check_resource_availability(
        self,
        agent_type: str,
        start_time: datetime,
        end_time: datetime,
        params: SchedulingParams
    ) -> bool:
        # Check if agent type has capacity

    def _add_business_time(
        self,
        start: datetime,
        duration_minutes: int,
        params: SchedulingParams
    ) -> datetime:
        # Add duration respecting work hours/days

    def _analyze_deadline_risk(
        self,
        scheduled_end: datetime,
        deadline: Optional[datetime]
    ) -> Dict[str, Any]:
        # Compare schedule to deadline

    def _generate_gantt_data(
        self,
        scheduled_tasks: List[Dict],
        critical_path: List[str]
    ) -> Dict[str, Any]:
        # Create Gantt-compatible structure

    async def _update_task_schedules(
        self,
        scheduled_tasks: List[Dict]
    ) -> None:
        # Batch update tasks table with scheduled times

    async def replan_schedule(
        self,
        project_id: str,
        completed_tasks: List[str],
        delayed_tasks: List[Tuple[str, int]]  # (task_id, delay_minutes)
    ) -> Dict[str, Any]:
        # Re-schedule based on actual progress
```

4. ALGORITHM DETAILS:

   a) Critical Path Method (CPM):
   - Forward pass: Calculate ES and EF for each task
     - ES(task) = max(EF of all predecessors)
     - EF(task) = ES(task) + duration
   - Backward pass: Calculate LS and LF for each task
     - LF(task) = min(LS of all successors)
     - LS(task) = LF(task) - duration
   - Slack = LS - ES
   - Critical path = all tasks with slack = 0

   b) Resource Leveling:
   - Track agent utilization over time
   - Don't over-allocate (max concurrent = capacity)
   - Delay non-critical tasks to smooth resource usage

   c) Business Time Calculation:
   - Skip non-work days (weekends)
   - Respect work hours (e.g., 9am-5pm)
   - Example: Add 10 hours to Friday 4pm = Tuesday 10am

5. DATABASE SCHEMA:
   - tasks table columns needed:
     - id, project_id, name, description
     - estimated_duration_minutes
     - assigned_agent_type
     - required_knowledge_tags, required_frameworks
     - knowledge_coverage_score
     - scheduled_start, scheduled_end (UPDATE these)
     - status
   - task_dependencies table:
     - task_id, depends_on_task_id
     - dependency_type (finish_to_start, start_to_start, finish_to_finish)
     - lag_minutes

6. INTEGRATION:
   - Import from: from utils.utils import get_clients
   - Use existing RPC: check_knowledge_coverage()
   - Return format compatible with Gantt chart libraries
   - Can be called from KnowledgeManager or directly
   - Works with LangGraph workflows

7. ERROR HANDLING:
   - Detect circular dependencies
   - Handle missing/invalid data gracefully
   - Warn on deadline risks
   - Block scheduling if all tasks have low coverage
   - Provide actionable recommendations

8. TESTING:
   Include test scenarios:
   - Linear sequence of tasks
   - Parallel tasks with resource constraints
   - Knowledge coverage blocking
   - Deadline at risk
   - Re-planning after delay

9. PERFORMANCE:
   - Use efficient graph algorithms (NetworkX recommended)
   - Batch database operations
   - Complete in < 10 seconds for 50 tasks
   - Memory efficient

10. OUTPUT:
    Return comprehensive schedule including:
    - scheduled_start and scheduled_end for all tasks
    - critical_path (list of task IDs)
    - resource_utilization by agent type
    - gantt_data (visualization-ready)
    - warnings and recommendations
    - deadline analysis

EXAMPLE USAGE:
```python
from archon.task_scheduler import TaskScheduler
from datetime import datetime, timezone

scheduler = TaskScheduler(supabase)

result = await scheduler.schedule_project(
    project_id="uuid",
    start_date=datetime.now(timezone.utc),
    deadline=datetime(2025, 12, 31, tzinfo=timezone.utc),
    agent_capacity={"coder": 2, "scraper": 1},
    min_knowledge_coverage=0.4,
    auto_update_db=True
)

print(f"Scheduled: {result['scheduled_start']} to {result['scheduled_end']}")
print(f"Critical path: {result['critical_path']}")
```

Please create a complete, production-ready implementation with:
- Full docstrings and type hints
- Robust error handling
- Efficient algorithms (O(V+E) or better)
- Business time calculations
- Resource tracking
- Gantt data generation
- Clean, maintainable code

Focus on accuracy and efficiency - schedules must be realistic and respect all constraints.
```
