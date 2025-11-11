# Advanced Streamlit UI Features for Archon Knowledge Management

## Overview

Three new advanced Streamlit pages have been created for Archon's knowledge management system, providing powerful analytics, visualizations, and scheduling capabilities.

---

## 1. Analytics Dashboard (`streamlit_pages/analytics.py`)

### Features

#### Overview Metrics
- **Total Projects**: Count of all projects in the system
- **Total Tasks**: Count of all tasks across projects
- **Knowledge Chunks**: Total knowledge chunks stored
- **Average Coverage**: Average knowledge coverage score
- **Active Agents**: Number of unique agent types assigned

#### Interactive Charts (Plotly)

1. **Project Status Pie Chart**
   - Donut chart showing project distribution by status
   - Color-coded by status (planning, in_progress, completed, etc.)
   - Interactive hover details

2. **Task Status Bar Chart**
   - Horizontal bar chart of task status distribution
   - Shows counts for pending, in_progress, completed, blocked, etc.
   - Color-coded bars

3. **Coverage Score Histogram**
   - Distribution of task coverage scores
   - Color gradient from red (low) to green (high)
   - Helps identify knowledge gaps

4. **Tasks by Priority**
   - Bar chart showing task counts by priority level (1-5)
   - Priority 1 (highest) in red, Priority 5 (lowest) in green

5. **Tasks by Agent Type**
   - Pie chart showing task distribution across agent types
   - Helps visualize workload distribution

6. **Timeline Chart**
   - Dual-axis line chart showing projects and tasks created over time
   - Tracks growth and activity patterns

#### Data Tables

1. **Top 5 Projects by Task Count**
   - Shows most complex projects
   - Includes status, task count, coverage, and priority

2. **Top 5 Tasks by Knowledge Links**
   - Tasks with most knowledge attached
   - Shows how well-documented tasks are

3. **Bottom 5 Tasks by Coverage (Need Attention)**
   - Identifies tasks lacking knowledge
   - Helps prioritize knowledge acquisition

4. **Recent Activity Log**
   - Latest 10 project and task creations
   - Shows system activity timeline

#### Filters

- **Date Range**: Filter by creation date range
- **Project**: Filter by specific project
- **Status**: Filter by status (planning, in_progress, etc.)
- **Refresh**: Reload all data

#### Export Options

- Export Projects to CSV
- Export Tasks to CSV
- Export Knowledge to CSV

### Usage

```python
# Navigate to Analytics from sidebar
# Click "Analytics" button
```

---

## 2. Knowledge Graph Visualization (`streamlit_pages/knowledge_graph.py`)

### Features

#### Interactive Graph Display

- **Nodes**: Knowledge chunks (circles)
  - Sized by number of connections
  - Colored by framework (FastAPI, React, etc.)
  - Selected node highlighted in gold
  - Search results highlighted in pink

- **Edges**: Relationships between chunks
  - Color-coded by relationship type:
    - Red: Prerequisites
    - Blue: Related content
    - Green: Examples
    - Orange: Extensions
    - Purple: Shared tasks

#### Layout Algorithms

- **Spring Layout**: Force-directed (default)
- **Circular Layout**: Nodes in a circle
- **Kamada-Kawai**: Optimized for smaller graphs (<100 nodes)

#### Node Details Sidebar

When a node is selected:
- Title and summary
- Framework, type, and language
- Number of connections
- Clickable URL
- Tags (visual badges)
- Related chunks (neighbors)
- Tasks using this knowledge

#### Filters

- **Framework**: Filter by framework (FastAPI, React, etc.)
- **Knowledge Type**: Filter by type (documentation, tutorial, API reference)
- **Tag**: Filter by specific tag
- **Show Task Relationships**: Toggle task-knowledge connections

#### Search Functionality

- Search by title or tag
- Highlights matching nodes in pink
- Shows match count

#### Path Finder

- Find shortest path between two nodes
- Highlights path on graph
- Shows step-by-step connections

#### Statistics

- Total nodes and edges
- Average connections per node
- Most connected chunks (top 5)
- Relationship type distribution

### Usage

```python
# Navigate to Knowledge Graph from sidebar
# Click "Knowledge Graph" button

# To explore:
# 1. Use filters to narrow down nodes
# 2. Search for specific topics
# 3. Select nodes to see details
# 4. Find paths between related knowledge
```

---

## 3. Task Scheduler (`streamlit_pages/scheduler.py`)

### Features

#### Calendar View

- **Monthly Calendar**
  - Color-coded cells by task count
  - Task indicators (colored dots) by priority
  - Shows up to 3 tasks per day with overflow indicator
  - Month and year selectors

- **Weekly Calendar** (uses monthly view for now)

#### Gantt Chart

- **Visual Timeline**
  - Horizontal bars for each task
  - Start and end dates
  - Color-coded by priority
  - Critical path highlighted in red

- **Critical Path Analysis**
  - Automatically calculates longest path through dependencies
  - Identifies bottleneck tasks
  - Highlights in red on Gantt chart

- **Dependency Visualization** (optional toggle)
  - Shows task dependencies as connections

#### Auto-Scheduler

**Intelligent Task Scheduling Algorithm**:

1. **Dependency Analysis**
   - Builds dependency graph
   - Performs topological sort

2. **Schedule Calculation**
   - Respects task dependencies
   - Uses estimated durations
   - Calculates optimal start/end times
   - Prevents dependency conflicts

3. **Configuration**:
   - Project start date
   - Working hours per day (1-24)

4. **Execution**:
   - Click "Auto-Schedule All Tasks"
   - Updates all task schedules in database
   - Shows preview before saving

#### Agent Capacity View

- **Stacked Bar Chart**
  - Shows workload per agent type
  - Breakdown by status (pending, in_progress, completed)

- **Load Balancing Suggestions**
  - Detects imbalances (>2x difference)
  - Suggests task reassignment

#### Filters

- **Project**: Filter tasks by project
- **Agent Type**: Filter by agent type
- **Date Range**: (future enhancement placeholder)

#### Quick Stats

- Total tasks count
- Scheduled tasks count
- Dependencies count
- Completion rate percentage

### Usage

```python
# Navigate to Scheduler from sidebar
# Click "Scheduler" button

# To auto-schedule:
# 1. Set project start date
# 2. Set working hours per day
# 3. Click "Auto-Schedule All Tasks"
# 4. Review schedule in Gantt chart
```

---

## Integration with Archon

### Navigation

All three pages are now accessible from the main Streamlit sidebar:

1. Click **"Analytics"** for metrics and charts
2. Click **"Knowledge Graph"** for graph visualization
3. Click **"Scheduler"** for task scheduling

### Data Flow

All pages integrate with:
- **Supabase**: Database queries
- **KnowledgeManager**: Knowledge operations
- **Projects & Tasks**: Existing data

### Database Requirements

The pages use these Supabase tables:
- `projects`: Project information
- `tasks`: Task information
- `knowledge`: Knowledge chunks
- `task_knowledge_links`: Task-knowledge relationships
- `task_dependencies`: Task dependencies
- `knowledge_relationships`: Knowledge relationships (optional)

---

## Technical Stack

### Dependencies

```python
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx  # For graph algorithms
from datetime import datetime, timedelta
```

### Key Technologies

- **Streamlit**: UI framework
- **Plotly**: Interactive charts and graphs
- **NetworkX**: Graph algorithms (topological sort, shortest path)
- **Pandas**: Data manipulation
- **Supabase**: Database backend

---

## File Structure

```
/home/user/Archon/
├── streamlit_pages/
│   ├── analytics.py          # Analytics dashboard (26KB)
│   ├── knowledge_graph.py    # Graph visualization (26KB)
│   ├── scheduler.py          # Task scheduler (27KB)
│   ├── projects.py           # Existing projects page
│   ├── tasks.py              # Existing tasks page
│   └── ...
└── streamlit_ui.py           # Updated main UI with navigation
```

---

## Features Summary

### Analytics Dashboard
- ✅ 5 overview metrics
- ✅ 6 interactive Plotly charts
- ✅ 4 data tables
- ✅ Date range, project, and status filters
- ✅ CSV export for projects, tasks, and knowledge

### Knowledge Graph
- ✅ Interactive graph visualization with NetworkX
- ✅ Node details sidebar
- ✅ Framework, type, and tag filters
- ✅ Search by title/tag
- ✅ Path finder between nodes
- ✅ Graph statistics
- ✅ 3 layout algorithms
- ✅ Relationship type color coding

### Scheduler
- ✅ Monthly calendar view
- ✅ Gantt chart with critical path
- ✅ Auto-scheduling algorithm
- ✅ Dependency-aware scheduling
- ✅ Agent capacity visualization
- ✅ Load balancing suggestions
- ✅ Project and agent filters
- ✅ Quick stats dashboard

---

## Usage Examples

### Example 1: Identify Knowledge Gaps

1. Go to **Analytics**
2. Check "Bottom 5 Tasks by Coverage" table
3. Note tasks with low coverage
4. Go to **Knowledge Graph**
5. Search for related topics
6. Attach knowledge to tasks

### Example 2: Schedule a New Project

1. Create project in **Projects** page
2. Create tasks in **Tasks** page
3. Add dependencies in task settings
4. Go to **Scheduler**
5. Click "Auto-Schedule All Tasks"
6. Review Gantt chart
7. Check critical path

### Example 3: Analyze Project Health

1. Go to **Analytics**
2. Set date range to project timeline
3. Select specific project
4. Check coverage score
5. Review task status distribution
6. Export data for reporting

### Example 4: Explore Knowledge Relationships

1. Go to **Knowledge Graph**
2. Filter by framework (e.g., "fastapi")
3. Select a node
4. View related chunks
5. Find path to another topic
6. Identify knowledge clusters

---

## Design Language

All pages follow Archon's design language:

- **Dark theme** (Plotly dark template)
- **Color scheme**:
  - Blue (#4B9EFF): Primary
  - Green (#00CC99): Success/Completed
  - Orange (#FFA500): In Progress
  - Red (#FF4B4B): Blocked/High Priority
  - Gold (#FFD700): Warning/Selected

- **Consistent UI elements**:
  - Status badges
  - Priority indicators
  - Coverage progress bars
  - Tag badges

---

## Performance Considerations

- **Data Limits**:
  - Knowledge graph: 500 nodes max
  - Analytics: All data loaded
  - Scheduler: All tasks loaded

- **Optimizations**:
  - Efficient database queries
  - Client-side filtering where possible
  - Lazy loading for large datasets

---

## Future Enhancements

Potential improvements:

1. **Analytics**:
   - Real-time updates
   - Custom date presets (last 7 days, last month, etc.)
   - Agent performance metrics
   - Knowledge acquisition trends

2. **Knowledge Graph**:
   - Click-to-select nodes directly on graph
   - Force-directed layout animation
   - Community detection (clusters)
   - Export graph as image

3. **Scheduler**:
   - Drag-and-drop task rescheduling
   - Resource allocation optimization
   - Slack time visualization
   - Calendar export (iCal)

---

## Troubleshooting

### No Data Showing

- Check Supabase connection in Database tab
- Verify tables exist and have data
- Check browser console for errors

### Graph Not Rendering

- Ensure knowledge chunks have valid IDs
- Check that relationships reference existing chunks
- Try different layout algorithm

### Auto-Schedule Fails

- Verify tasks have estimated durations
- Check for circular dependencies
- Ensure tasks have valid statuses

---

## API Reference

### Analytics Functions

```python
# Get analytics data with filters
get_analytics_data(start_date, end_date, project_id, status_filter)

# Calculate metrics
calculate_overview_metrics(data)

# Create charts
create_project_status_pie_chart(metrics)
create_task_status_bar_chart(metrics)
create_coverage_histogram(data)
create_priority_bar_chart(data)
create_agent_type_pie_chart(data)
create_timeline_chart(data)

# Create tables
create_top_projects_table(data)
create_top_tasks_by_knowledge_table(data)
create_low_coverage_tasks_table(data)
create_recent_activity_table(data)
```

### Knowledge Graph Functions

```python
# Build graph
build_knowledge_graph(chunks, relationships, task_links, show_task_links)

# Calculate layout
calculate_layout(G, layout_type)

# Create visualization
create_knowledge_graph_plot(G, node_metadata, layout_type, selected_node_id, highlight_nodes)

# Search and analyze
search_knowledge_chunks(chunks, search_query)
find_path_between_nodes(G, source_id, target_id)
calculate_graph_statistics(G, node_metadata)
```

### Scheduler Functions

```python
# Scheduling algorithms
build_dependency_graph(tasks, dependencies)
topological_sort_tasks(tasks, dep_graph)
auto_schedule_tasks(tasks, dependencies, start_date, hours_per_day)
calculate_critical_path(tasks, dependencies, schedule)

# Visualizations
create_calendar_view(tasks, year, month, view_mode)
create_gantt_chart(tasks, critical_path, show_dependencies)
create_agent_capacity_chart(tasks)

# Database operations
update_task_schedule(task_id, scheduled_start, scheduled_end)
```

---

## Conclusion

These three advanced UI pages provide comprehensive analytics, visualization, and scheduling capabilities for Archon's knowledge management system. They integrate seamlessly with existing projects and tasks, offering powerful insights and automation features.

**Total New Code**: ~79KB (26KB + 26KB + 27KB)
**Total Features**: 30+ interactive features
**Integration**: Fully integrated with Archon's existing system

Enjoy your new advanced Archon UI features!
