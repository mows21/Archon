"""
Task Scheduling Calendar for Archon

This module provides calendar views, Gantt charts, dependency visualization,
and intelligent auto-scheduling based on dependencies and knowledge coverage.
"""

import streamlit as st
import sys
import os
from datetime import datetime, timedelta, date
from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from collections import defaultdict
import calendar

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import get_clients

# Initialize clients
embedding_client, supabase = get_clients()


# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================

def get_all_tasks(project_id: Optional[str] = None, agent_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch all tasks with optional filters"""
    try:
        query = supabase.table('tasks').select('*')

        if project_id:
            query = query.eq('project_id', project_id)

        if agent_type and agent_type != 'All':
            query = query.eq('assigned_agent_type', agent_type)

        response = query.order('created_at').execute()
        return response.data or []
    except Exception as e:
        st.error(f"Error fetching tasks: {e}")
        return []


def get_task_dependencies() -> List[Dict[str, Any]]:
    """Fetch all task dependencies"""
    try:
        response = supabase.table('task_dependencies').select('*').execute()
        return response.data or []
    except Exception as e:
        st.error(f"Error fetching dependencies: {e}")
        return []


def get_projects_list() -> List[Dict[str, Any]]:
    """Get list of all projects"""
    try:
        response = supabase.table('projects').select('id, name').order('name').execute()
        return response.data or []
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return []


def update_task_schedule(task_id: str, scheduled_start: Optional[datetime], scheduled_end: Optional[datetime]) -> bool:
    """Update task schedule dates"""
    try:
        updates = {}
        if scheduled_start:
            updates['scheduled_start'] = scheduled_start.isoformat()
        if scheduled_end:
            updates['scheduled_end'] = scheduled_end.isoformat()

        if updates:
            supabase.table('tasks').update(updates).eq('id', task_id).execute()
            return True
        return False
    except Exception as e:
        st.error(f"Error updating task schedule: {e}")
        return False


# ============================================================================
# SCHEDULING ALGORITHMS
# ============================================================================

def build_dependency_graph(tasks: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Build dependency graph

    Returns:
        Dictionary mapping task_id to list of dependency task_ids
    """
    dep_graph = defaultdict(list)

    for dep in dependencies:
        task_id = dep.get('task_id')
        depends_on = dep.get('depends_on_task_id')

        if task_id and depends_on:
            dep_graph[task_id].append(depends_on)

    return dep_graph


def topological_sort_tasks(tasks: List[Dict[str, Any]], dep_graph: Dict[str, List[str]]) -> List[str]:
    """
    Topologically sort tasks based on dependencies

    Returns:
        List of task IDs in execution order
    """
    # Create task ID set
    task_ids = {task['id'] for task in tasks}

    # Calculate in-degrees
    in_degree = {task_id: 0 for task_id in task_ids}

    for task_id, deps in dep_graph.items():
        if task_id in task_ids:
            for dep in deps:
                if dep in task_ids:
                    in_degree[task_id] += 1

    # Queue of tasks with no dependencies
    queue = [task_id for task_id, degree in in_degree.items() if degree == 0]
    sorted_tasks = []

    while queue:
        # Process task with no remaining dependencies
        current = queue.pop(0)
        sorted_tasks.append(current)

        # Reduce in-degree for dependent tasks
        for task_id, deps in dep_graph.items():
            if current in deps and task_id in task_ids:
                in_degree[task_id] -= 1
                if in_degree[task_id] == 0:
                    queue.append(task_id)

    # If we haven't sorted all tasks, there's a cycle or missing dependencies
    if len(sorted_tasks) < len(task_ids):
        # Add remaining tasks
        remaining = task_ids - set(sorted_tasks)
        sorted_tasks.extend(list(remaining))

    return sorted_tasks


def auto_schedule_tasks(
    tasks: List[Dict[str, Any]],
    dependencies: List[Dict[str, Any]],
    start_date: datetime,
    hours_per_day: int = 8
) -> Dict[str, Tuple[datetime, datetime]]:
    """
    Automatically schedule tasks based on dependencies and estimates

    Args:
        tasks: List of task dictionaries
        dependencies: List of dependency dictionaries
        start_date: Project start date
        hours_per_day: Working hours per day

    Returns:
        Dictionary mapping task_id to (start_datetime, end_datetime)
    """
    # Build dependency graph
    dep_graph = build_dependency_graph(tasks, dependencies)

    # Topologically sort tasks
    sorted_task_ids = topological_sort_tasks(tasks, dep_graph)

    # Create task lookup
    task_lookup = {task['id']: task for task in tasks}

    # Schedule each task
    schedule = {}
    task_end_times = {}  # Track when each task ends

    current_time = start_date

    for task_id in sorted_task_ids:
        task = task_lookup.get(task_id)
        if not task:
            continue

        # Determine earliest start time based on dependencies
        earliest_start = current_time

        # Check dependency completion times
        deps = dep_graph.get(task_id, [])
        for dep_id in deps:
            if dep_id in task_end_times:
                dep_end = task_end_times[dep_id]
                if dep_end > earliest_start:
                    earliest_start = dep_end

        # Calculate task duration
        duration_minutes = task.get('estimated_duration_minutes', 60)
        duration_hours = duration_minutes / 60

        # Calculate end time
        end_time = earliest_start + timedelta(hours=duration_hours)

        # Store schedule
        schedule[task_id] = (earliest_start, end_time)
        task_end_times[task_id] = end_time

        # Update current time (for tasks without dependencies)
        if not deps:
            current_time = end_time

    return schedule


def calculate_critical_path(
    tasks: List[Dict[str, Any]],
    dependencies: List[Dict[str, Any]],
    schedule: Dict[str, Tuple[datetime, datetime]]
) -> List[str]:
    """
    Calculate critical path (longest path through the dependency graph)

    Returns:
        List of task IDs on the critical path
    """
    # Build dependency graph
    dep_graph = build_dependency_graph(tasks, dependencies)

    # Create task lookup
    task_lookup = {task['id']: task for task in tasks}

    # Calculate earliest finish times
    earliest_finish = {}

    def get_earliest_finish(task_id: str) -> float:
        if task_id in earliest_finish:
            return earliest_finish[task_id]

        task = task_lookup.get(task_id)
        if not task:
            return 0

        duration = task.get('estimated_duration_minutes', 60) / 60

        deps = dep_graph.get(task_id, [])
        if not deps:
            earliest_finish[task_id] = duration
            return duration

        max_dep_finish = max(get_earliest_finish(dep_id) for dep_id in deps)
        earliest_finish[task_id] = max_dep_finish + duration
        return earliest_finish[task_id]

    # Calculate for all tasks
    for task in tasks:
        get_earliest_finish(task['id'])

    # Find task with maximum finish time
    if not earliest_finish:
        return []

    max_task_id = max(earliest_finish, key=earliest_finish.get)

    # Backtrack to find critical path
    critical_path = [max_task_id]

    def backtrack(task_id: str):
        deps = dep_graph.get(task_id, [])
        if not deps:
            return

        # Find dependency with maximum finish time
        max_dep = max(deps, key=lambda d: earliest_finish.get(d, 0))
        critical_path.insert(0, max_dep)
        backtrack(max_dep)

    backtrack(max_task_id)

    return critical_path


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_calendar_view(
    tasks: List[Dict[str, Any]],
    year: int,
    month: int,
    view_mode: str = 'monthly'
) -> go.Figure:
    """
    Create calendar view with tasks

    Args:
        tasks: List of tasks with schedule
        year: Year to display
        month: Month to display
        view_mode: 'monthly' or 'weekly'

    Returns:
        Plotly Figure
    """
    # Filter tasks with scheduled dates in the given month
    scheduled_tasks = []
    for task in tasks:
        scheduled_start = task.get('scheduled_start')
        if scheduled_start:
            try:
                start_date = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00'))
                if start_date.year == year and start_date.month == month:
                    scheduled_tasks.append(task)
            except:
                pass

    if view_mode == 'monthly':
        return create_monthly_calendar(scheduled_tasks, year, month)
    else:
        return create_weekly_calendar(scheduled_tasks, year, month)


def create_monthly_calendar(tasks: List[Dict[str, Any]], year: int, month: int) -> go.Figure:
    """Create monthly calendar view"""
    # Get calendar for the month
    cal = calendar.monthcalendar(year, month)

    # Create figure
    fig = go.Figure()

    # Define priority colors
    priority_colors = {
        1: '#FF4B4B',
        2: '#FFA500',
        3: '#FFD700',
        4: '#90EE90',
        5: '#00CC99'
    }

    # Group tasks by date
    tasks_by_date = defaultdict(list)
    for task in tasks:
        scheduled_start = task.get('scheduled_start')
        if scheduled_start:
            try:
                start_date = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00'))
                date_key = start_date.date()
                tasks_by_date[date_key].append(task)
            except:
                pass

    # Add calendar grid
    for week_idx, week in enumerate(cal):
        for day_idx, day in enumerate(week):
            if day == 0:
                continue

            # Create date
            current_date = date(year, month, day)

            # Get tasks for this date
            day_tasks = tasks_by_date.get(current_date, [])

            # Cell color based on number of tasks
            cell_color = 'rgba(255,255,255,0.05)'
            if day_tasks:
                cell_color = 'rgba(75, 158, 255, 0.3)'

            # Add rectangle for day
            fig.add_shape(
                type="rect",
                x0=day_idx,
                y0=6 - week_idx,
                x1=day_idx + 1,
                y1=6 - week_idx + 1,
                line=dict(color="white", width=1),
                fillcolor=cell_color
            )

            # Add day number
            fig.add_annotation(
                x=day_idx + 0.1,
                y=6 - week_idx + 0.9,
                text=str(day),
                showarrow=False,
                font=dict(size=12, color="white"),
                xanchor='left',
                yanchor='top'
            )

            # Add task indicators
            for i, task in enumerate(day_tasks[:3]):  # Max 3 tasks visible
                priority = task.get('priority', 3)
                color = priority_colors.get(priority, '#808080')

                # Add small colored circle
                fig.add_shape(
                    type="circle",
                    x0=day_idx + 0.2 + (i * 0.25),
                    y0=6 - week_idx + 0.1,
                    x1=day_idx + 0.4 + (i * 0.25),
                    y1=6 - week_idx + 0.3,
                    fillcolor=color,
                    line=dict(color=color)
                )

            if len(day_tasks) > 3:
                fig.add_annotation(
                    x=day_idx + 0.9,
                    y=6 - week_idx + 0.2,
                    text=f"+{len(day_tasks) - 3}",
                    showarrow=False,
                    font=dict(size=8, color="white"),
                    xanchor='right'
                )

    # Add day labels
    days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    for i, day in enumerate(days):
        fig.add_annotation(
            x=i + 0.5,
            y=7.2,
            text=day,
            showarrow=False,
            font=dict(size=14, color="white", weight="bold")
        )

    # Update layout
    month_name = calendar.month_name[month]
    fig.update_layout(
        title=f"{month_name} {year} - Task Calendar",
        xaxis=dict(range=[0, 7], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[0, 7.5], showgrid=False, zeroline=False, showticklabels=False),
        template='plotly_dark',
        height=500,
        showlegend=False
    )

    return fig


def create_weekly_calendar(tasks: List[Dict[str, Any]], year: int, month: int) -> go.Figure:
    """Create weekly calendar view (simplified)"""
    # For simplicity, use monthly view
    return create_monthly_calendar(tasks, year, month)


def create_gantt_chart(
    tasks: List[Dict[str, Any]],
    critical_path: Optional[List[str]] = None,
    show_dependencies: bool = True
) -> go.Figure:
    """
    Create Gantt chart showing tasks and dependencies

    Args:
        tasks: List of tasks with schedule
        critical_path: List of task IDs on critical path
        show_dependencies: Whether to show dependency lines

    Returns:
        Plotly Figure
    """
    # Filter tasks with schedules
    scheduled_tasks = []
    for task in tasks:
        if task.get('scheduled_start') and task.get('scheduled_end'):
            scheduled_tasks.append(task)

    if not scheduled_tasks:
        # Return empty figure
        fig = go.Figure()
        fig.add_annotation(
            text="No scheduled tasks. Use Auto-Schedule to create a schedule.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(template='plotly_dark', height=400)
        return fig

    # Prepare data for Gantt
    df_data = []

    for task in scheduled_tasks:
        try:
            start = datetime.fromisoformat(task['scheduled_start'].replace('Z', '+00:00'))
            end = datetime.fromisoformat(task['scheduled_end'].replace('Z', '+00:00'))

            # Determine color
            if critical_path and task['id'] in critical_path:
                color = '#FF4B4B'  # Red for critical path
            else:
                priority = task.get('priority', 3)
                color = {
                    1: '#FF4B4B',
                    2: '#FFA500',
                    3: '#FFD700',
                    4: '#90EE90',
                    5: '#00CC99'
                }.get(priority, '#808080')

            df_data.append({
                'Task': task.get('name', 'Untitled')[:30],
                'Start': start,
                'Finish': end,
                'Priority': task.get('priority', 3),
                'Color': color,
                'Task_ID': task['id']
            })
        except:
            pass

    if not df_data:
        fig = go.Figure()
        fig.add_annotation(
            text="Error parsing task schedules",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False
        )
        fig.update_layout(template='plotly_dark', height=400)
        return fig

    df = pd.DataFrame(df_data)

    # Create Gantt chart
    fig = go.Figure()

    for i, row in df.iterrows():
        fig.add_trace(go.Bar(
            x=[row['Finish'] - row['Start']],
            y=[row['Task']],
            base=row['Start'],
            orientation='h',
            marker=dict(color=row['Color']),
            name=row['Task'],
            showlegend=False,
            hovertemplate=f"<b>{row['Task']}</b><br>Start: {row['Start']}<br>End: {row['Finish']}<extra></extra>"
        ))

    # Update layout
    fig.update_layout(
        title='Task Gantt Chart',
        xaxis_title='Timeline',
        yaxis_title='Tasks',
        template='plotly_dark',
        height=max(400, len(df) * 30),
        barmode='overlay',
        showlegend=False,
        xaxis=dict(type='date')
    )

    return fig


def create_agent_capacity_chart(tasks: List[Dict[str, Any]]) -> go.Figure:
    """Create agent capacity/workload visualization"""
    # Group tasks by agent type and count
    agent_workload = defaultdict(lambda: {'total': 0, 'pending': 0, 'in_progress': 0, 'completed': 0})

    for task in tasks:
        agent_type = task.get('assigned_agent_type', 'unassigned')
        status = task.get('status', 'pending')

        agent_workload[agent_type]['total'] += 1
        if status == 'pending':
            agent_workload[agent_type]['pending'] += 1
        elif status == 'in_progress':
            agent_workload[agent_type]['in_progress'] += 1
        elif status == 'completed':
            agent_workload[agent_type]['completed'] += 1

    if not agent_workload:
        return None

    # Create stacked bar chart
    agents = list(agent_workload.keys())
    pending = [agent_workload[agent]['pending'] for agent in agents]
    in_progress = [agent_workload[agent]['in_progress'] for agent in agents]
    completed = [agent_workload[agent]['completed'] for agent in agents]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='Pending',
        x=agents,
        y=pending,
        marker_color='#808080'
    ))

    fig.add_trace(go.Bar(
        name='In Progress',
        x=agents,
        y=in_progress,
        marker_color='#FFA500'
    ))

    fig.add_trace(go.Bar(
        name='Completed',
        x=agents,
        y=completed,
        marker_color='#00CC99'
    ))

    fig.update_layout(
        title='Agent Capacity & Workload',
        xaxis_title='Agent Type',
        yaxis_title='Number of Tasks',
        barmode='stack',
        template='plotly_dark',
        height=400,
        showlegend=True
    )

    return fig


# ============================================================================
# MAIN UI COMPONENTS
# ============================================================================

def show_calendar_section(tasks: List[Dict[str, Any]]):
    """Display calendar view"""
    st.subheader("Calendar View")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Month selector
        current_date = datetime.now()
        selected_month = st.selectbox(
            "Month",
            range(1, 13),
            index=current_date.month - 1,
            format_func=lambda x: calendar.month_name[x]
        )

    with col2:
        # Year selector
        selected_year = st.selectbox(
            "Year",
            range(2024, 2030),
            index=0 if current_date.year == 2024 else current_date.year - 2024
        )

    with col3:
        # View mode (future enhancement)
        view_mode = st.selectbox("View", ["Monthly", "Weekly"])

    # Create and display calendar
    fig = create_calendar_view(tasks, selected_year, selected_month, view_mode.lower())
    st.plotly_chart(fig, use_container_width=True)


def show_gantt_section(tasks: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]):
    """Display Gantt chart"""
    st.subheader("Gantt Chart")

    # Calculate critical path if tasks are scheduled
    critical_path = None
    scheduled_tasks = [t for t in tasks if t.get('scheduled_start')]

    if scheduled_tasks:
        schedule = {
            t['id']: (
                datetime.fromisoformat(t['scheduled_start'].replace('Z', '+00:00')),
                datetime.fromisoformat(t['scheduled_end'].replace('Z', '+00:00'))
            )
            for t in scheduled_tasks
        }
        critical_path = calculate_critical_path(scheduled_tasks, dependencies, schedule)

    # Display critical path info
    if critical_path:
        st.info(f"Critical Path: {len(critical_path)} tasks highlighted in red")

    # Create Gantt chart
    show_deps = st.checkbox("Show Dependencies", value=False)
    fig = create_gantt_chart(tasks, critical_path, show_deps)
    st.plotly_chart(fig, use_container_width=True)


def show_auto_schedule_section(tasks: List[Dict[str, Any]], dependencies: List[Dict[str, Any]]):
    """Display auto-schedule controls"""
    st.subheader("Auto-Schedule Tasks")

    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input(
            "Project Start Date",
            value=datetime.now().date(),
            help="When should the project start?"
        )

    with col2:
        hours_per_day = st.slider(
            "Working Hours Per Day",
            min_value=1,
            max_value=24,
            value=8,
            help="How many hours of work per day?"
        )

    if st.button("🤖 Auto-Schedule All Tasks", use_container_width=True):
        with st.spinner("Calculating optimal schedule..."):
            # Convert to datetime
            start_datetime = datetime.combine(start_date, datetime.min.time())

            # Run auto-scheduler
            schedule = auto_schedule_tasks(tasks, dependencies, start_datetime, hours_per_day)

            if schedule:
                st.success(f"✅ Scheduled {len(schedule)} tasks!")

                # Update database
                updated_count = 0
                for task_id, (start, end) in schedule.items():
                    if update_task_schedule(task_id, start, end):
                        updated_count += 1

                st.success(f"Updated {updated_count} tasks in database")

                # Show preview
                with st.expander("View Schedule Preview"):
                    for task in tasks:
                        task_id = task['id']
                        if task_id in schedule:
                            start, end = schedule[task_id]
                            st.markdown(
                                f"**{task.get('name', 'Untitled')}:** "
                                f"{start.strftime('%Y-%m-%d %H:%M')} → {end.strftime('%Y-%m-%d %H:%M')}"
                            )

                st.rerun()
            else:
                st.warning("No tasks to schedule")


def show_agent_capacity_section(tasks: List[Dict[str, Any]]):
    """Display agent capacity view"""
    st.subheader("Agent Capacity & Load Balancing")

    fig = create_agent_capacity_chart(tasks)

    if fig:
        st.plotly_chart(fig, use_container_width=True)

        # Suggestions
        agent_counts = defaultdict(int)
        for task in tasks:
            if task.get('status') not in ['completed', 'cancelled']:
                agent_type = task.get('assigned_agent_type', 'unassigned')
                agent_counts[agent_type] += 1

        if agent_counts:
            max_agent = max(agent_counts, key=agent_counts.get)
            min_agent = min(agent_counts, key=agent_counts.get)

            if agent_counts[max_agent] > agent_counts[min_agent] * 2:
                st.warning(
                    f"⚠️ Load imbalance detected: {max_agent} has {agent_counts[max_agent]} tasks "
                    f"while {min_agent} has only {agent_counts[min_agent]}. "
                    f"Consider reassigning some tasks for better load balancing."
                )
    else:
        st.info("No agent assignments found")


# ============================================================================
# MAIN PAGE
# ============================================================================

def scheduler_page():
    """Main scheduler page"""
    st.title("📅 Task Scheduler")

    # Check if database is configured
    if not supabase:
        st.error("⚠️ Supabase is not configured. Please set up your database in the Database tab.")
        return

    # Filters section
    st.markdown("### Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Project selector
        projects = get_projects_list()
        project_options = [{'id': None, 'name': 'All Projects'}] + projects
        project_names = [p['name'] for p in project_options]
        project_ids = [p['id'] for p in project_options]

        project_idx = st.selectbox(
            "Project",
            range(len(project_names)),
            format_func=lambda i: project_names[i]
        )
        selected_project_id = project_ids[project_idx]

    with col2:
        # Agent type filter
        agent_type_filter = st.selectbox(
            "Agent Type",
            ['All', 'coder', 'scraper', 'refiner', 'linker', 'custom']
        )

    with col3:
        # Date range (future enhancement)
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    st.divider()

    # Fetch data
    with st.spinner("Loading tasks and dependencies..."):
        tasks = get_all_tasks(selected_project_id, agent_type_filter)
        dependencies = get_task_dependencies()

    # Display sections in tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "Calendar View",
        "Gantt Chart",
        "Auto-Schedule",
        "Agent Capacity"
    ])

    with tab1:
        show_calendar_section(tasks)

    with tab2:
        show_gantt_section(tasks, dependencies)

    with tab3:
        show_auto_schedule_section(tasks, dependencies)

    with tab4:
        show_agent_capacity_section(tasks)

    # Quick stats
    st.divider()
    st.markdown("### Quick Stats")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Tasks", len(tasks))

    with col2:
        scheduled = sum(1 for t in tasks if t.get('scheduled_start'))
        st.metric("Scheduled", scheduled)

    with col3:
        st.metric("Dependencies", len(dependencies))

    with col4:
        completed = sum(1 for t in tasks if t.get('status') == 'completed')
        completion_rate = (completed / len(tasks) * 100) if tasks else 0
        st.metric("Completion Rate", f"{completion_rate:.0f}%")


# Entry point
if __name__ == "__main__":
    scheduler_page()
