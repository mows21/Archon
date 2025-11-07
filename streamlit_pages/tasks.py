"""
Task Management Board for Archon

This module provides a Kanban-style UI for managing tasks with knowledge attachment,
agent assignment, dependencies, and intelligent task scheduling.
"""

import streamlit as st
import sys
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import asyncio
from openai import AsyncOpenAI

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import get_clients, get_env_var

# Initialize clients
embedding_client, supabase = get_clients()


# ============================================================================
# KNOWLEDGE MANAGER HELPER CLASS
# ============================================================================

class KnowledgeManager:
    """Helper class for managing knowledge operations"""

    def __init__(self, supabase_client, embedding_client):
        self.supabase = supabase_client
        self.embedding_client = embedding_client
        self.embedding_model = get_env_var('EMBEDDING_MODEL') or 'text-embedding-3-small'

    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        try:
            response = await self.embedding_client.embeddings.create(
                input=text,
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            st.error(f"Error generating embedding: {e}")
            return None

    def search_knowledge(self, query_embedding: List[float], tags: List[str] = None,
                         frameworks: List[str] = None, match_count: int = 10,
                         match_threshold: float = 0.0) -> List[Dict]:
        """Search for relevant knowledge"""
        try:
            if tags is None:
                tags = []
            if frameworks is None:
                frameworks = []

            result = self.supabase.rpc('match_knowledge_advanced', {
                'query_embedding': query_embedding,
                'match_count': match_count,
                'match_threshold': match_threshold,
                'required_tags': tags,
                'required_frameworks': frameworks
            }).execute()

            return result.data if result.data else []
        except Exception as e:
            st.error(f"Error searching knowledge: {e}")
            return []

    def get_task_knowledge(self, task_id: str) -> List[Dict]:
        """Get all knowledge chunks attached to a task"""
        try:
            result = self.supabase.rpc('get_task_knowledge', {
                'task_id_param': task_id
            }).execute()

            return result.data if result.data else []
        except Exception as e:
            st.error(f"Error fetching task knowledge: {e}")
            return []

    def attach_knowledge_to_task(self, task_id: str, knowledge_id: int,
                                 relevance_score: float = 0.0,
                                 link_type: str = 'suggested',
                                 linked_by: str = 'user') -> bool:
        """Attach knowledge to a task"""
        try:
            link_data = {
                'task_id': task_id,
                'knowledge_id': knowledge_id,
                'relevance_score': relevance_score,
                'link_type': link_type,
                'linked_by': linked_by
            }

            self.supabase.table('task_knowledge_links').insert(link_data).execute()
            return True
        except Exception as e:
            st.error(f"Error attaching knowledge: {e}")
            return False

    def detach_knowledge_from_task(self, task_id: str, knowledge_id: int) -> bool:
        """Remove knowledge from a task"""
        try:
            self.supabase.table('task_knowledge_links').delete().eq('task_id', task_id).eq('knowledge_id', knowledge_id).execute()
            return True
        except Exception as e:
            st.error(f"Error detaching knowledge: {e}")
            return False


# Initialize Knowledge Manager
km = KnowledgeManager(supabase, embedding_client) if supabase and embedding_client else None


# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

def get_all_tasks(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch all tasks, optionally filtered by project"""
    try:
        query = supabase.table('tasks').select('*')
        if project_id:
            query = query.eq('project_id', project_id)
        response = query.order('created_at', desc=False).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching tasks: {e}")
        return []


def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single task by ID"""
    try:
        response = supabase.table('tasks').select('*').eq('id', task_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error fetching task: {e}")
        return None


def create_task(task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new task"""
    try:
        response = supabase.table('tasks').insert(task_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error creating task: {e}")
        return None


def update_task(task_id: str, updates: Dict[str, Any]) -> bool:
    """Update a task"""
    try:
        supabase.table('tasks').update(updates).eq('id', task_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating task: {e}")
        return False


def get_all_projects() -> List[Dict[str, Any]]:
    """Fetch all projects for dropdown"""
    try:
        response = supabase.table('projects').select('id, name').order('name', desc=False).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return []


def get_task_dependencies(task_id: str) -> List[Dict[str, Any]]:
    """Get dependencies for a task"""
    try:
        result = supabase.rpc('get_task_dependencies_tree', {
            'task_id_param': task_id
        }).execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Error fetching dependencies: {e}")
        return []


# ============================================================================
# UI HELPER FUNCTIONS
# ============================================================================

def get_priority_color(priority: int) -> str:
    """Get color for priority level"""
    colors = {
        1: "#FF4B4B",
        2: "#FFA500",
        3: "#FFD700",
        4: "#90EE90",
        5: "#00CC99"
    }
    return colors.get(priority, "#808080")


def get_status_badge_color(status: str) -> str:
    """Get color for status badge"""
    status_colors = {
        'pending': '#808080',
        'ready': '#4B9EFF',
        'in_progress': '#FFA500',
        'blocked': '#FF4B4B',
        'completed': '#00CC99',
        'cancelled': '#666666',
        'failed': '#CC0000'
    }
    return status_colors.get(status, '#808080')


def render_status_badge(status: str):
    """Render a colored status badge"""
    color = get_status_badge_color(status)
    st.markdown(
        f'<span style="background-color: {color}; color: white; padding: 4px 12px; '
        f'border-radius: 12px; font-size: 0.85em; font-weight: bold;">{status.replace("_", " ").upper()}</span>',
        unsafe_allow_html=True
    )


def render_tag_badge(tag: str, color: str = "#4B9EFF"):
    """Render a tag badge"""
    st.markdown(
        f'<span style="background-color: {color}; color: white; padding: 3px 8px; '
        f'border-radius: 8px; margin: 2px; display: inline-block; font-size: 0.8em;">{tag}</span>',
        unsafe_allow_html=True
    )


# ============================================================================
# KANBAN BOARD FUNCTIONS
# ============================================================================

def show_kanban_board(project_id: Optional[str] = None) -> None:
    """Kanban view of tasks"""
    st.subheader("Task Board")

    # Filter selector
    col1, col2 = st.columns([2, 1])
    with col1:
        projects = get_all_projects()
        project_options = [{"id": None, "name": "All Projects"}] + projects
        project_names = [p["name"] for p in project_options]
        project_ids = [p["id"] for p in project_options]

        selected_idx = st.selectbox(
            "Filter by Project",
            range(len(project_names)),
            format_func=lambda i: project_names[i],
            key="kanban_project_filter"
        )
        selected_project_id = project_ids[selected_idx]
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # Fetch tasks
    tasks = get_all_tasks(selected_project_id)

    # Group tasks by status
    task_columns = {
        'pending': [],
        'in_progress': [],
        'blocked': [],
        'completed': []
    }

    for task in tasks:
        status = task.get('status', 'pending')
        if status in task_columns:
            task_columns[status].append(task)
        elif status == 'ready':
            task_columns['pending'].append(task)

    # Display Kanban columns
    cols = st.columns(4)

    column_configs = [
        ('pending', 'Pending', '#808080'),
        ('in_progress', 'In Progress', '#FFA500'),
        ('blocked', 'Blocked', '#FF4B4B'),
        ('completed', 'Completed', '#00CC99')
    ]

    for col, (status_key, title, color) in zip(cols, column_configs):
        with col:
            st.markdown(f"### {title} ({len(task_columns[status_key])})")
            st.markdown(f"<div style='border-top: 4px solid {color}; margin-bottom: 10px;'></div>",
                       unsafe_allow_html=True)

            # Display tasks in this column
            for task in task_columns[status_key]:
                render_kanban_card(task)


def render_kanban_card(task: Dict[str, Any]):
    """Render a task card in the Kanban board"""
    priority_color = get_priority_color(task.get('priority', 3))

    with st.container():
        st.markdown(f"""
            <div style="border-left: 4px solid {priority_color}; padding: 8px; margin: 8px 0;
                        background-color: rgba(255,255,255,0.05); border-radius: 4px; cursor: pointer;">
        """, unsafe_allow_html=True)

        # Task name
        st.markdown(f"**{task.get('name', 'Untitled Task')}**")

        # Metadata
        if task.get('assigned_agent_type'):
            agent_emoji = {
                'coder': '👨‍💻',
                'scraper': '🕷️',
                'refiner': '✨',
                'custom': '🤖'
            }.get(task.get('assigned_agent_type'), '🤖')
            st.markdown(f"{agent_emoji} {task.get('assigned_agent_type')}")

        # Coverage indicator
        coverage = task.get('knowledge_coverage_score')
        if coverage is not None:
            coverage_pct = int(coverage * 100)
            coverage_color = '#00CC99' if coverage >= 0.7 else '#FFA500' if coverage >= 0.4 else '#FF4B4B'
            st.markdown(
                f'<div style="font-size: 0.85em;">📚 Coverage: '
                f'<span style="color: {coverage_color}; font-weight: bold;">{coverage_pct}%</span></div>',
                unsafe_allow_html=True
            )

        # View button
        if st.button("View", key=f"kanban_view_{task['id']}", use_container_width=True):
            st.session_state.selected_task_id = task['id']
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


# ============================================================================
# TASK CREATION FORM
# ============================================================================

def show_create_task_form() -> None:
    """Form to create new task"""
    st.subheader("Create New Task")

    projects = get_all_projects()

    with st.form("create_task_form", clear_on_submit=True):
        # Project selector
        if projects:
            project_names = ["No Project"] + [p['name'] for p in projects]
            project_ids = [None] + [p['id'] for p in projects]
            project_idx = st.selectbox("Project", range(len(project_names)),
                                      format_func=lambda i: project_names[i])
            selected_project_id = project_ids[project_idx]
        else:
            st.info("No projects available. Create a project first.")
            selected_project_id = None

        name = st.text_input("Task Name*", placeholder="e.g., Implement JWT token generation")
        description = st.text_area("Description", placeholder="Detailed description of the task...")

        col1, col2 = st.columns(2)
        with col1:
            priority = st.slider("Priority (1=Highest, 5=Lowest)", 1, 5, 3)
            status = st.selectbox("Status", ["pending", "ready", "in_progress", "blocked", "completed", "cancelled", "failed"])
        with col2:
            estimated_duration = st.number_input("Estimated Duration (minutes)", min_value=0, value=60)
            deadline = st.date_input("Deadline (Optional)", value=None)

        # Agent assignment
        assigned_agent_type = st.selectbox("Assigned Agent Type",
                                          ["coder", "scraper", "refiner", "custom"],
                                          help="Select the type of agent best suited for this task")

        # Knowledge tags
        tags_input = st.text_input("Required Knowledge Tags (comma-separated)",
                                   placeholder="e.g., jwt, authentication, python")
        frameworks_input = st.text_input("Required Frameworks (comma-separated)",
                                        placeholder="e.g., fastapi, pydantic")

        # Auto-link knowledge
        auto_link = st.checkbox("Automatically search and suggest relevant knowledge", value=True)

        submitted = st.form_submit_button("Create Task", use_container_width=True)

        if submitted:
            if not name:
                st.error("Task name is required!")
                return

            # Parse tags and frameworks
            tags = [t.strip() for t in tags_input.split(',') if t.strip()]
            frameworks = [f.strip() for f in frameworks_input.split(',') if f.strip()]

            # Prepare task data
            task_data = {
                'name': name,
                'description': description,
                'priority': priority,
                'status': status,
                'estimated_duration_minutes': estimated_duration,
                'required_knowledge_tags': tags,
                'required_frameworks': frameworks,
                'assigned_agent_type': assigned_agent_type,
            }

            if selected_project_id:
                task_data['project_id'] = selected_project_id

            if deadline:
                task_data['deadline'] = deadline.isoformat()

            # Generate embedding for task context
            if km and embedding_client and description:
                with st.spinner("Generating task context embedding..."):
                    embedding = asyncio.run(km.get_embedding(f"{name}\n{description}"))
                    if embedding:
                        task_data['task_context_embedding'] = embedding

            # Create the task
            with st.spinner("Creating task..."):
                new_task = create_task(task_data)

                if new_task:
                    st.success(f"✅ Task '{name}' created successfully!")

                    # Auto-link knowledge
                    if auto_link and km and (tags or description):
                        with st.spinner("Searching for relevant knowledge..."):
                            # Use embedding to search
                            if 'task_context_embedding' in task_data:
                                knowledge_results = km.search_knowledge(
                                    task_data['task_context_embedding'],
                                    tags,
                                    frameworks,
                                    match_count=5,
                                    match_threshold=0.3
                                )

                                if knowledge_results:
                                    st.info(f"Found {len(knowledge_results)} relevant knowledge chunks. Attaching...")

                                    attached_count = 0
                                    for result in knowledge_results:
                                        if km.attach_knowledge_to_task(
                                            new_task['id'],
                                            result['id'],
                                            relevance_score=result.get('similarity', 0),
                                            link_type='suggested',
                                            linked_by='auto'
                                        ):
                                            attached_count += 1

                                    st.success(f"✅ Attached {attached_count} knowledge chunks to the task!")

                    # Navigate to the new task
                    st.session_state.selected_task_id = new_task['id']
                    st.rerun()


# ============================================================================
# TASK DETAIL VIEW
# ============================================================================

def show_task_details(task_id: str) -> None:
    """Detailed task view with knowledge panel"""
    task = get_task_by_id(task_id)

    if not task:
        st.error("Task not found!")
        if st.button("← Back to Board"):
            st.session_state.selected_task_id = None
            st.rerun()
        return

    # Header with back button
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("← Back"):
            st.session_state.selected_task_id = None
            st.rerun()
    with col2:
        st.title(task.get('name', 'Untitled Task'))

    # Status and priority row
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        st.markdown("**Status:**")
        render_status_badge(task.get('status', 'pending'))
    with col2:
        priority = task.get('priority', 3)
        st.markdown(f"**Priority:** {'★' * priority}")
    with col3:
        agent_type = task.get('assigned_agent_type')
        if agent_type:
            st.markdown(f"**Agent:** {agent_type}")

    st.divider()

    # Main content area with tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Knowledge", "Dependencies", "Settings"])

    with tab1:
        show_task_overview(task)

    with tab2:
        show_knowledge_panel(task_id)

    with tab3:
        show_dependencies(task_id)

    with tab4:
        show_task_settings(task)


def show_task_overview(task: Dict[str, Any]):
    """Show task overview"""
    st.markdown("### Description")
    description = task.get('description', 'No description provided.')
    st.markdown(description if description else "No description provided.")

    st.markdown("### Task Information")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Created:** " + (task.get('created_at', '')[:10] if task.get('created_at') else 'Unknown'))
        st.markdown("**Updated:** " + (task.get('updated_at', '')[:10] if task.get('updated_at') else 'Unknown'))

        if task.get('estimated_duration_minutes'):
            hours = task['estimated_duration_minutes'] // 60
            minutes = task['estimated_duration_minutes'] % 60
            st.markdown(f"**Estimated Duration:** {hours}h {minutes}m")

        if task.get('deadline'):
            st.markdown(f"**Deadline:** {task['deadline'][:10]}")

    with col2:
        if task.get('started_at'):
            st.markdown("**Started:** " + task['started_at'][:10])
        if task.get('completed_at'):
            st.markdown("**Completed:** " + task['completed_at'][:10])

        if task.get('project_id'):
            # Fetch project name
            try:
                project = supabase.table('projects').select('name').eq('id', task['project_id']).execute()
                if project.data:
                    st.markdown(f"**Project:** {project.data[0]['name']}")
            except:
                pass

    # Tags and frameworks
    st.markdown("### Required Knowledge")

    tags = task.get('required_knowledge_tags', [])
    frameworks = task.get('required_frameworks', [])

    if tags:
        st.markdown("**Tags:**")
        for tag in tags:
            render_tag_badge(tag, "#4B9EFF")

    if frameworks:
        st.markdown("**Frameworks:**")
        for fw in frameworks:
            render_tag_badge(fw, "#00CC99")

    # Coverage score
    coverage = task.get('knowledge_coverage_score')
    if coverage is not None:
        st.markdown("### Knowledge Coverage")
        percentage = int(coverage * 100)
        st.progress(coverage)
        st.markdown(f"**{percentage}%** of required knowledge is available")


def show_knowledge_panel(task_id: str) -> None:
    """List attached knowledge + search/attach more"""
    st.markdown("### Attached Knowledge")

    if not km:
        st.error("Knowledge Manager not available. Please configure Supabase and Embedding client.")
        return

    # Fetch attached knowledge
    attached_knowledge = km.get_task_knowledge(task_id)

    if attached_knowledge:
        st.markdown(f"**{len(attached_knowledge)} knowledge chunks attached:**")

        for knowledge in attached_knowledge:
            with st.expander(f"📄 {knowledge.get('title', 'Untitled')} (Relevance: {knowledge.get('relevance_score', 0):.2%})"):
                st.markdown(f"**URL:** [{knowledge.get('url', 'N/A')}]({knowledge.get('url', '#')})")
                st.markdown(f"**Summary:** {knowledge.get('summary', 'N/A')}")

                # Tags
                tags = knowledge.get('tags', [])
                if tags:
                    st.markdown("**Tags:**")
                    for tag in tags:
                        render_tag_badge(tag, "#4B9EFF")

                st.markdown(f"**Type:** {knowledge.get('link_type', 'N/A')}")
                st.markdown(f"**Framework:** {knowledge.get('framework', 'N/A')}")

                # Remove button
                if st.button("Remove", key=f"remove_{task_id}_{knowledge['id']}"):
                    with st.spinner("Removing..."):
                        if km.detach_knowledge_from_task(task_id, knowledge['id']):
                            st.success("Knowledge removed!")
                            st.rerun()
    else:
        st.info("No knowledge attached to this task yet.")

    st.divider()

    # Search and attach more knowledge
    st.markdown("### Search & Attach Knowledge")

    search_query = st.text_input("Search for relevant knowledge",
                                 placeholder="Enter search query...",
                                 key=f"search_knowledge_{task_id}")

    col1, col2 = st.columns([3, 1])
    with col1:
        match_threshold = st.slider("Minimum Relevance", 0.0, 1.0, 0.3, 0.05,
                                   help="Minimum similarity score for results")
    with col2:
        match_count = st.number_input("Max Results", 1, 20, 10)

    if st.button("🔍 Search", use_container_width=True):
        if search_query:
            with st.spinner("Searching knowledge base..."):
                # Get task info for filtering
                task = get_task_by_id(task_id)
                tags = task.get('required_knowledge_tags', [])
                frameworks = task.get('required_frameworks', [])

                # Generate embedding
                query_embedding = asyncio.run(km.get_embedding(search_query))

                if query_embedding:
                    results = km.search_knowledge(
                        query_embedding,
                        tags,
                        frameworks,
                        match_count=match_count,
                        match_threshold=match_threshold
                    )

                    if results:
                        st.success(f"Found {len(results)} relevant knowledge chunks:")

                        for result in results:
                            with st.expander(f"📄 {result.get('title', 'Untitled')} (Similarity: {result.get('similarity', 0):.2%})"):
                                st.markdown(f"**URL:** [{result.get('url', 'N/A')}]({result.get('url', '#')})")
                                st.markdown(f"**Summary:** {result.get('summary', 'N/A')}")

                                # Tags
                                result_tags = result.get('tags', [])
                                if result_tags:
                                    st.markdown("**Tags:**")
                                    for tag in result_tags:
                                        render_tag_badge(tag, "#4B9EFF")

                                # Check if already attached
                                already_attached = any(k['id'] == result['id'] for k in attached_knowledge)

                                if already_attached:
                                    st.info("✓ Already attached")
                                else:
                                    if st.button("Attach", key=f"attach_{task_id}_{result['id']}"):
                                        with st.spinner("Attaching..."):
                                            if km.attach_knowledge_to_task(
                                                task_id,
                                                result['id'],
                                                relevance_score=result.get('similarity', 0),
                                                link_type='reference',
                                                linked_by='user'
                                            ):
                                                st.success("Knowledge attached!")
                                                st.rerun()
                    else:
                        st.warning("No relevant knowledge found. Try adjusting your search query or lowering the threshold.")
        else:
            st.warning("Please enter a search query.")


def show_dependencies(task_id: str) -> None:
    """Show task dependencies"""
    st.markdown("### Task Dependencies")

    dependencies = get_task_dependencies(task_id)

    if dependencies:
        st.markdown(f"**This task depends on {len(dependencies)} other task(s):**")

        for dep in dependencies:
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                st.markdown(f"**{dep.get('depends_on_task_name', 'Unknown')}**")
            with col2:
                render_status_badge(dep.get('depends_on_task_status', 'pending'))
            with col3:
                st.markdown(f"*{dep.get('dependency_type', 'N/A')}*")

            # Show if dependency is blocking
            if dep.get('depends_on_task_status') not in ['completed', 'cancelled']:
                st.warning(f"⚠️ Blocked by: {dep.get('depends_on_task_name')}")
    else:
        st.info("This task has no dependencies.")

    st.divider()

    # Add dependency
    st.markdown("### Add Dependency")

    all_tasks = get_all_tasks()
    # Filter out current task
    available_tasks = [t for t in all_tasks if t['id'] != task_id]

    if available_tasks:
        task_names = [t['name'] for t in available_tasks]
        task_ids = [t['id'] for t in available_tasks]

        selected_idx = st.selectbox("Select task this depends on:", range(len(task_names)),
                                   format_func=lambda i: task_names[i])

        dependency_type = st.selectbox("Dependency Type",
                                      ["finish_to_start", "start_to_start", "finish_to_finish", "start_to_finish"])

        if st.button("Add Dependency", use_container_width=True):
            try:
                dep_data = {
                    'task_id': task_id,
                    'depends_on_task_id': task_ids[selected_idx],
                    'dependency_type': dependency_type
                }

                supabase.table('task_dependencies').insert(dep_data).execute()
                st.success("Dependency added!")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding dependency: {e}")
    else:
        st.info("No other tasks available to create dependencies.")


def show_task_settings(task: Dict[str, Any]):
    """Show task settings and edit form"""
    st.markdown("### Task Settings")

    with st.form("edit_task_form"):
        name = st.text_input("Task Name", value=task.get('name', ''))
        description = st.text_area("Description", value=task.get('description', ''))

        col1, col2 = st.columns(2)
        with col1:
            priority = st.slider("Priority", 1, 5, task.get('priority', 3))
            status = st.selectbox("Status",
                                 ["pending", "ready", "in_progress", "blocked", "completed", "cancelled", "failed"],
                                 index=["pending", "ready", "in_progress", "blocked", "completed", "cancelled", "failed"].index(task.get('status', 'pending')))
        with col2:
            estimated_duration = st.number_input("Estimated Duration (minutes)",
                                               min_value=0,
                                               value=task.get('estimated_duration_minutes', 0))
            assigned_agent_type = st.selectbox("Agent Type",
                                             ["coder", "scraper", "refiner", "custom"],
                                             index=["coder", "scraper", "refiner", "custom"].index(task.get('assigned_agent_type', 'coder')) if task.get('assigned_agent_type') else 0)

        submitted = st.form_submit_button("Save Changes", use_container_width=True)

        if submitted:
            updates = {
                'name': name,
                'description': description,
                'priority': priority,
                'status': status,
                'estimated_duration_minutes': estimated_duration if estimated_duration > 0 else None,
                'assigned_agent_type': assigned_agent_type
            }

            with st.spinner("Saving changes..."):
                if update_task(task['id'], updates):
                    st.success("✅ Task updated successfully!")
                    st.rerun()

    st.divider()

    # Danger zone
    st.markdown("### Danger Zone")
    if st.button("🗑️ Delete Task", type="secondary"):
        st.session_state.confirm_delete_task = True

    if st.session_state.get('confirm_delete_task'):
        st.warning("⚠️ Are you sure? This will delete the task permanently!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", use_container_width=True):
                try:
                    supabase.table('tasks').delete().eq('id', task['id']).execute()
                    st.success("Task deleted!")
                    st.session_state.selected_task_id = None
                    st.session_state.confirm_delete_task = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting task: {e}")
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_delete_task = False
                st.rerun()


# ============================================================================
# MAIN PAGE
# ============================================================================

def tasks_page():
    """Main tasks page"""
    st.title("📋 Task Management")

    # Check if database is configured
    if not supabase:
        st.error("⚠️ Supabase is not configured. Please set up your database in the Database tab.")
        return

    # Initialize session state
    if 'selected_task_id' not in st.session_state:
        st.session_state.selected_task_id = None
    if 'confirm_delete_task' not in st.session_state:
        st.session_state.confirm_delete_task = False

    # Show selected task or board
    if st.session_state.selected_task_id:
        show_task_details(st.session_state.selected_task_id)
    else:
        # Main view with Kanban board and create form
        tab1, tab2 = st.tabs(["Task Board", "Create New Task"])

        with tab1:
            show_kanban_board()

        with tab2:
            show_create_task_form()


# Entry point
if __name__ == "__main__":
    tasks_page()
