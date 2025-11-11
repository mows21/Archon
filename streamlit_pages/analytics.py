"""
Analytics Dashboard for Archon

This module provides comprehensive analytics and visualizations for projects,
tasks, knowledge chunks, and agent activities with interactive charts and metrics.
"""

import streamlit as st
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import get_clients

# Initialize clients
embedding_client, supabase = get_clients()


# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================

def get_analytics_data(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    project_id: Optional[str] = None,
    status_filter: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch all analytics data from database

    Args:
        start_date: Optional start date filter
        end_date: Optional end date filter
        project_id: Optional project filter
        status_filter: Optional status filter

    Returns:
        Dictionary containing all analytics data
    """
    try:
        # Fetch projects
        projects_query = supabase.table('projects').select('*')
        if start_date:
            projects_query = projects_query.gte('created_at', start_date.isoformat())
        if end_date:
            projects_query = projects_query.lte('created_at', end_date.isoformat())
        if status_filter and status_filter != 'All':
            projects_query = projects_query.eq('status', status_filter)

        projects = projects_query.execute().data or []

        # Fetch tasks
        tasks_query = supabase.table('tasks').select('*')
        if project_id:
            tasks_query = tasks_query.eq('project_id', project_id)
        if start_date:
            tasks_query = tasks_query.gte('created_at', start_date.isoformat())
        if end_date:
            tasks_query = tasks_query.lte('created_at', end_date.isoformat())
        if status_filter and status_filter != 'All':
            tasks_query = tasks_query.eq('status', status_filter)

        tasks = tasks_query.execute().data or []

        # Fetch knowledge chunks
        knowledge_query = supabase.table('knowledge').select('*')
        if start_date:
            knowledge_query = knowledge_query.gte('created_at', start_date.isoformat())
        if end_date:
            knowledge_query = knowledge_query.lte('created_at', end_date.isoformat())

        knowledge = knowledge_query.execute().data or []

        # Fetch task-knowledge links
        links_query = supabase.table('task_knowledge_links').select('*')
        if start_date:
            links_query = links_query.gte('created_at', start_date.isoformat())
        if end_date:
            links_query = links_query.lte('created_at', end_date.isoformat())

        links = links_query.execute().data or []

        return {
            'projects': projects,
            'tasks': tasks,
            'knowledge': knowledge,
            'links': links
        }
    except Exception as e:
        st.error(f"Error fetching analytics data: {e}")
        return {
            'projects': [],
            'tasks': [],
            'knowledge': [],
            'links': []
        }


def get_projects_list() -> List[Dict[str, Any]]:
    """Get list of all projects for filter dropdown"""
    try:
        response = supabase.table('projects').select('id, name').order('name').execute()
        return response.data or []
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return []


# ============================================================================
# METRICS CALCULATION
# ============================================================================

def calculate_overview_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate overview metrics from analytics data"""
    projects = data['projects']
    tasks = data['tasks']
    knowledge = data['knowledge']
    links = data['links']

    # Project status breakdown
    project_status_counts = {}
    for project in projects:
        status = project.get('status', 'unknown')
        project_status_counts[status] = project_status_counts.get(status, 0) + 1

    # Task status breakdown
    task_status_counts = {}
    for task in tasks:
        status = task.get('status', 'unknown')
        task_status_counts[status] = task_status_counts.get(status, 0) + 1

    # Calculate average coverage scores
    project_coverage_scores = [p.get('knowledge_coverage_score', 0) for p in projects if p.get('knowledge_coverage_score') is not None]
    task_coverage_scores = [t.get('knowledge_coverage_score', 0) for t in tasks if t.get('knowledge_coverage_score') is not None]

    avg_project_coverage = sum(project_coverage_scores) / len(project_coverage_scores) if project_coverage_scores else 0
    avg_task_coverage = sum(task_coverage_scores) / len(task_coverage_scores) if task_coverage_scores else 0

    # Active agents (unique agent types assigned to tasks)
    active_agents = set(task.get('assigned_agent_type') for task in tasks if task.get('assigned_agent_type'))

    return {
        'total_projects': len(projects),
        'total_tasks': len(tasks),
        'total_knowledge_chunks': len(knowledge),
        'total_links': len(links),
        'project_status_counts': project_status_counts,
        'task_status_counts': task_status_counts,
        'avg_project_coverage': avg_project_coverage,
        'avg_task_coverage': avg_task_coverage,
        'active_agents': len(active_agents),
        'agent_types': list(active_agents)
    }


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_project_status_pie_chart(metrics: Dict[str, Any]) -> go.Figure:
    """Create pie chart for project status distribution"""
    status_counts = metrics['project_status_counts']

    if not status_counts:
        return None

    labels = list(status_counts.keys())
    values = list(status_counts.values())

    colors = {
        'planning': '#808080',
        'ready': '#4B9EFF',
        'in_progress': '#FFA500',
        'blocked': '#FF4B4B',
        'completed': '#00CC99',
        'cancelled': '#666666',
        'on_hold': '#FFD700'
    }

    color_sequence = [colors.get(label, '#808080') for label in labels]

    fig = go.Figure(data=[go.Pie(
        labels=[label.replace('_', ' ').title() for label in labels],
        values=values,
        marker=dict(colors=color_sequence),
        hole=0.4,
        textinfo='label+percent',
        textposition='auto'
    )])

    fig.update_layout(
        title='Project Status Distribution',
        height=400,
        showlegend=True,
        template='plotly_dark'
    )

    return fig


def create_task_status_bar_chart(metrics: Dict[str, Any]) -> go.Figure:
    """Create bar chart for task status distribution"""
    status_counts = metrics['task_status_counts']

    if not status_counts:
        return None

    labels = list(status_counts.keys())
    values = list(status_counts.values())

    colors = {
        'pending': '#808080',
        'ready': '#4B9EFF',
        'in_progress': '#FFA500',
        'blocked': '#FF4B4B',
        'completed': '#00CC99',
        'cancelled': '#666666',
        'failed': '#CC0000'
    }

    color_sequence = [colors.get(label, '#808080') for label in labels]

    fig = go.Figure(data=[go.Bar(
        x=[label.replace('_', ' ').title() for label in labels],
        y=values,
        marker=dict(color=color_sequence),
        text=values,
        textposition='auto'
    )])

    fig.update_layout(
        title='Task Status Distribution',
        xaxis_title='Status',
        yaxis_title='Count',
        height=400,
        template='plotly_dark',
        showlegend=False
    )

    return fig


def create_coverage_histogram(data: Dict[str, Any]) -> go.Figure:
    """Create histogram for coverage score distribution"""
    tasks = data['tasks']

    coverage_scores = [t.get('knowledge_coverage_score', 0) for t in tasks if t.get('knowledge_coverage_score') is not None]

    if not coverage_scores:
        return None

    fig = go.Figure(data=[go.Histogram(
        x=coverage_scores,
        nbinsx=20,
        marker=dict(
            color=coverage_scores,
            colorscale='RdYlGn',
            showscale=True,
            colorbar=dict(title='Coverage Score')
        ),
        hovertemplate='Coverage: %{x:.2f}<br>Count: %{y}<extra></extra>'
    )])

    fig.update_layout(
        title='Task Coverage Score Distribution',
        xaxis_title='Coverage Score',
        yaxis_title='Number of Tasks',
        height=400,
        template='plotly_dark',
        showlegend=False
    )

    return fig


def create_priority_bar_chart(data: Dict[str, Any]) -> go.Figure:
    """Create bar chart for tasks by priority"""
    tasks = data['tasks']

    priority_counts = {}
    for task in tasks:
        priority = task.get('priority', 3)
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

    if not priority_counts:
        return None

    priorities = sorted(priority_counts.keys())
    values = [priority_counts[p] for p in priorities]

    colors = {
        1: '#FF4B4B',
        2: '#FFA500',
        3: '#FFD700',
        4: '#90EE90',
        5: '#00CC99'
    }

    color_sequence = [colors.get(p, '#808080') for p in priorities]

    fig = go.Figure(data=[go.Bar(
        x=[f'Priority {p}' for p in priorities],
        y=values,
        marker=dict(color=color_sequence),
        text=values,
        textposition='auto'
    )])

    fig.update_layout(
        title='Tasks by Priority Level',
        xaxis_title='Priority',
        yaxis_title='Count',
        height=400,
        template='plotly_dark',
        showlegend=False
    )

    return fig


def create_agent_type_pie_chart(data: Dict[str, Any]) -> go.Figure:
    """Create pie chart for tasks by agent type"""
    tasks = data['tasks']

    agent_counts = {}
    for task in tasks:
        agent_type = task.get('assigned_agent_type', 'unassigned')
        agent_counts[agent_type] = agent_counts.get(agent_type, 0) + 1

    if not agent_counts:
        return None

    labels = list(agent_counts.keys())
    values = list(agent_counts.values())

    colors = ['#4B9EFF', '#00CC99', '#FFA500', '#FF4B4B', '#FFD700', '#9370DB']

    fig = go.Figure(data=[go.Pie(
        labels=[label.replace('_', ' ').title() for label in labels],
        values=values,
        marker=dict(colors=colors[:len(labels)]),
        hole=0.3,
        textinfo='label+percent',
        textposition='auto'
    )])

    fig.update_layout(
        title='Tasks by Agent Type',
        height=400,
        showlegend=True,
        template='plotly_dark'
    )

    return fig


def create_timeline_chart(data: Dict[str, Any]) -> go.Figure:
    """Create timeline chart showing projects/tasks created over time"""
    projects = data['projects']
    tasks = data['tasks']

    # Parse dates and count by day
    project_dates = {}
    task_dates = {}

    for project in projects:
        date_str = project.get('created_at', '')[:10]
        if date_str:
            project_dates[date_str] = project_dates.get(date_str, 0) + 1

    for task in tasks:
        date_str = task.get('created_at', '')[:10]
        if date_str:
            task_dates[date_str] = task_dates.get(date_str, 0) + 1

    if not project_dates and not task_dates:
        return None

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add project trace
    if project_dates:
        dates = sorted(project_dates.keys())
        values = [project_dates[d] for d in dates]
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=values,
                name='Projects',
                mode='lines+markers',
                line=dict(color='#4B9EFF', width=3),
                marker=dict(size=8)
            ),
            secondary_y=False
        )

    # Add task trace
    if task_dates:
        dates = sorted(task_dates.keys())
        values = [task_dates[d] for d in dates]
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=values,
                name='Tasks',
                mode='lines+markers',
                line=dict(color='#00CC99', width=3),
                marker=dict(size=8)
            ),
            secondary_y=True
        )

    fig.update_xaxes(title_text='Date')
    fig.update_yaxes(title_text='Projects Created', secondary_y=False)
    fig.update_yaxes(title_text='Tasks Created', secondary_y=True)

    fig.update_layout(
        title='Projects & Tasks Created Over Time',
        height=400,
        template='plotly_dark',
        hovermode='x unified'
    )

    return fig


# ============================================================================
# TABLE FUNCTIONS
# ============================================================================

def create_top_projects_table(data: Dict[str, Any]) -> pd.DataFrame:
    """Create table of top 5 projects by task count"""
    projects = data['projects']
    tasks = data['tasks']

    # Count tasks per project
    project_task_counts = {}
    for task in tasks:
        project_id = task.get('project_id')
        if project_id:
            project_task_counts[project_id] = project_task_counts.get(project_id, 0) + 1

    # Build table data
    table_data = []
    for project in projects:
        project_id = project.get('id')
        task_count = project_task_counts.get(project_id, 0)

        table_data.append({
            'Project': project.get('name', 'Untitled'),
            'Status': project.get('status', 'unknown').replace('_', ' ').title(),
            'Tasks': task_count,
            'Coverage': f"{int(project.get('knowledge_coverage_score', 0) * 100)}%" if project.get('knowledge_coverage_score') is not None else 'N/A',
            'Priority': project.get('priority', 3)
        })

    # Sort by task count and take top 5
    df = pd.DataFrame(table_data)
    if not df.empty:
        df = df.sort_values('Tasks', ascending=False).head(5)

    return df


def create_top_tasks_by_knowledge_table(data: Dict[str, Any]) -> pd.DataFrame:
    """Create table of top 5 tasks by knowledge link count"""
    tasks = data['tasks']
    links = data['links']

    # Count links per task
    task_link_counts = {}
    for link in links:
        task_id = link.get('task_id')
        if task_id:
            task_link_counts[task_id] = task_link_counts.get(task_id, 0) + 1

    # Build table data
    table_data = []
    for task in tasks:
        task_id = task.get('id')
        link_count = task_link_counts.get(task_id, 0)

        if link_count > 0:  # Only include tasks with knowledge
            table_data.append({
                'Task': task.get('name', 'Untitled'),
                'Status': task.get('status', 'unknown').replace('_', ' ').title(),
                'Knowledge Links': link_count,
                'Coverage': f"{int(task.get('knowledge_coverage_score', 0) * 100)}%" if task.get('knowledge_coverage_score') is not None else 'N/A',
                'Agent': task.get('assigned_agent_type', 'N/A')
            })

    # Sort by link count and take top 5
    df = pd.DataFrame(table_data)
    if not df.empty:
        df = df.sort_values('Knowledge Links', ascending=False).head(5)

    return df


def create_low_coverage_tasks_table(data: Dict[str, Any]) -> pd.DataFrame:
    """Create table of bottom 5 tasks by coverage (need attention)"""
    tasks = data['tasks']

    # Filter tasks with coverage scores and incomplete status
    table_data = []
    for task in tasks:
        if task.get('status') not in ['completed', 'cancelled'] and task.get('knowledge_coverage_score') is not None:
            table_data.append({
                'Task': task.get('name', 'Untitled'),
                'Status': task.get('status', 'unknown').replace('_', ' ').title(),
                'Coverage': task.get('knowledge_coverage_score', 0),
                'Coverage %': f"{int(task.get('knowledge_coverage_score', 0) * 100)}%",
                'Priority': task.get('priority', 3)
            })

    # Sort by coverage and take bottom 5
    df = pd.DataFrame(table_data)
    if not df.empty:
        df = df.sort_values('Coverage').head(5)
        df = df.drop('Coverage', axis=1)  # Remove numeric column, keep percentage

    return df


def create_recent_activity_table(data: Dict[str, Any]) -> pd.DataFrame:
    """Create table of recent activity"""
    projects = data['projects']
    tasks = data['tasks']

    # Combine recent projects and tasks
    activity = []

    for project in projects:
        activity.append({
            'Type': 'Project',
            'Name': project.get('name', 'Untitled'),
            'Action': 'Created',
            'Status': project.get('status', 'unknown').replace('_', ' ').title(),
            'Date': project.get('created_at', '')[:10]
        })

    for task in tasks:
        activity.append({
            'Type': 'Task',
            'Name': task.get('name', 'Untitled'),
            'Action': 'Created',
            'Status': task.get('status', 'unknown').replace('_', ' ').title(),
            'Date': task.get('created_at', '')[:10]
        })

    # Sort by date and take recent 10
    df = pd.DataFrame(activity)
    if not df.empty:
        df = df.sort_values('Date', ascending=False).head(10)

    return df


# ============================================================================
# MAIN UI COMPONENTS
# ============================================================================

def show_overview_metrics(metrics: Dict[str, Any]):
    """Display overview metrics cards"""
    st.subheader("Overview Metrics")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Total Projects",
            metrics['total_projects'],
            help="Total number of projects in the system"
        )

    with col2:
        st.metric(
            "Total Tasks",
            metrics['total_tasks'],
            help="Total number of tasks across all projects"
        )

    with col3:
        st.metric(
            "Knowledge Chunks",
            metrics['total_knowledge_chunks'],
            help="Total knowledge chunks in the database"
        )

    with col4:
        avg_cov = metrics['avg_task_coverage']
        st.metric(
            "Avg Coverage",
            f"{int(avg_cov * 100)}%",
            help="Average knowledge coverage score across all tasks"
        )

    with col5:
        st.metric(
            "Active Agents",
            metrics['active_agents'],
            help="Number of unique agent types assigned to tasks"
        )


def show_charts_section(data: Dict[str, Any], metrics: Dict[str, Any]):
    """Display all charts"""
    st.subheader("Analytics Charts")

    # Row 1: Status distributions
    col1, col2 = st.columns(2)

    with col1:
        fig = create_project_status_pie_chart(metrics)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No project data available for chart")

    with col2:
        fig = create_task_status_bar_chart(metrics)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No task data available for chart")

    # Row 2: Coverage and Priority
    col1, col2 = st.columns(2)

    with col1:
        fig = create_coverage_histogram(data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No coverage data available for chart")

    with col2:
        fig = create_priority_bar_chart(data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No priority data available for chart")

    # Row 3: Agent types and Timeline
    col1, col2 = st.columns(2)

    with col1:
        fig = create_agent_type_pie_chart(data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No agent assignment data available for chart")

    with col2:
        fig = create_timeline_chart(data)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No timeline data available for chart")


def show_tables_section(data: Dict[str, Any]):
    """Display all tables"""
    st.subheader("Data Tables")

    # Top projects
    st.markdown("#### Top 5 Projects by Task Count")
    df = create_top_projects_table(data)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No project data available")

    st.divider()

    # Top tasks by knowledge
    st.markdown("#### Top 5 Tasks by Knowledge Links")
    df = create_top_tasks_by_knowledge_table(data)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No tasks with knowledge links")

    st.divider()

    # Low coverage tasks
    st.markdown("#### Bottom 5 Tasks by Coverage (Need Attention)")
    df = create_low_coverage_tasks_table(data)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No tasks with low coverage")

    st.divider()

    # Recent activity
    st.markdown("#### Recent Activity Log")
    df = create_recent_activity_table(data)
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No recent activity")


# ============================================================================
# MAIN PAGE
# ============================================================================

def analytics_page():
    """Main analytics dashboard page"""
    st.title("📊 Analytics Dashboard")

    # Check if database is configured
    if not supabase:
        st.error("⚠️ Supabase is not configured. Please set up your database in the Database tab.")
        return

    # Filters section
    st.markdown("### Filters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Date range selector
        date_range = st.date_input(
            "Date Range",
            value=(datetime.now() - timedelta(days=30), datetime.now()),
            help="Filter data by date range"
        )

        start_date = date_range[0] if isinstance(date_range, tuple) and len(date_range) == 2 else None
        end_date = date_range[1] if isinstance(date_range, tuple) and len(date_range) == 2 else None

    with col2:
        # Project selector
        projects = get_projects_list()
        project_options = [{'id': None, 'name': 'All Projects'}] + projects
        project_names = [p['name'] for p in project_options]
        project_ids = [p['id'] for p in project_options]

        project_idx = st.selectbox(
            "Project",
            range(len(project_names)),
            format_func=lambda i: project_names[i],
            help="Filter by specific project"
        )
        selected_project_id = project_ids[project_idx]

    with col3:
        # Status filter
        status_filter = st.selectbox(
            "Status",
            ['All', 'planning', 'ready', 'in_progress', 'blocked', 'completed', 'cancelled'],
            help="Filter by status"
        )

    with col4:
        # Refresh button
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    st.divider()

    # Fetch data with filters
    with st.spinner("Loading analytics data..."):
        data = get_analytics_data(
            start_date=start_date,
            end_date=end_date,
            project_id=selected_project_id,
            status_filter=status_filter
        )

        metrics = calculate_overview_metrics(data)

    # Display sections
    show_overview_metrics(metrics)

    st.divider()

    show_charts_section(data, metrics)

    st.divider()

    show_tables_section(data)

    # Export data option
    st.divider()
    st.markdown("### Export Data")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📥 Export Projects CSV", use_container_width=True):
            if data['projects']:
                df = pd.DataFrame(data['projects'])
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download Projects CSV",
                    csv,
                    "projects.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No projects to export")

    with col2:
        if st.button("📥 Export Tasks CSV", use_container_width=True):
            if data['tasks']:
                df = pd.DataFrame(data['tasks'])
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download Tasks CSV",
                    csv,
                    "tasks.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No tasks to export")

    with col3:
        if st.button("📥 Export Knowledge CSV", use_container_width=True):
            if data['knowledge']:
                df = pd.DataFrame(data['knowledge'])
                csv = df.to_csv(index=False)
                st.download_button(
                    "Download Knowledge CSV",
                    csv,
                    "knowledge.csv",
                    "text/csv",
                    use_container_width=True
                )
            else:
                st.warning("No knowledge to export")


# Entry point
if __name__ == "__main__":
    analytics_page()
