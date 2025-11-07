"""
Project Management Dashboard for Archon

This module provides a beautiful UI for managing knowledge-aware projects,
including project creation, detailed views, coverage analysis, and task decomposition.
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

    def check_coverage(self, required_tags: List[str], required_frameworks: List[str] = None) -> Dict[str, Any]:
        """Check knowledge coverage for tags and frameworks"""
        try:
            if required_frameworks is None:
                required_frameworks = []

            result = self.supabase.rpc('check_knowledge_coverage', {
                'required_tags_param': required_tags,
                'required_frameworks_param': required_frameworks
            }).execute()

            if result.data and len(result.data) > 0:
                return result.data[0]
            return {
                'total_chunks': 0,
                'coverage_score': 0.0,
                'missing_tags': required_tags,
                'available_frameworks': []
            }
        except Exception as e:
            st.error(f"Error checking coverage: {e}")
            return {
                'total_chunks': 0,
                'coverage_score': 0.0,
                'missing_tags': required_tags,
                'available_frameworks': []
            }

    def search_knowledge(self, query_embedding: List[float], tags: List[str] = None,
                         frameworks: List[str] = None, match_count: int = 10) -> List[Dict]:
        """Search for relevant knowledge"""
        try:
            if tags is None:
                tags = []
            if frameworks is None:
                frameworks = []

            result = self.supabase.rpc('match_knowledge_advanced', {
                'query_embedding': query_embedding,
                'match_count': match_count,
                'required_tags': tags,
                'required_frameworks': frameworks
            }).execute()

            return result.data if result.data else []
        except Exception as e:
            st.error(f"Error searching knowledge: {e}")
            return []


# Initialize Knowledge Manager
km = KnowledgeManager(supabase, embedding_client) if supabase and embedding_client else None


# ============================================================================
# DATABASE HELPER FUNCTIONS
# ============================================================================

def get_all_projects() -> List[Dict[str, Any]]:
    """Fetch all projects from database"""
    try:
        response = supabase.table('projects').select('*').order('created_at', desc=True).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching projects: {e}")
        return []


def get_project_by_id(project_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single project by ID"""
    try:
        response = supabase.table('projects').select('*').eq('id', project_id).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error fetching project: {e}")
        return None


def create_project(project_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new project"""
    try:
        response = supabase.table('projects').insert(project_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        st.error(f"Error creating project: {e}")
        return None


def update_project(project_id: str, updates: Dict[str, Any]) -> bool:
    """Update a project"""
    try:
        supabase.table('projects').update(updates).eq('id', project_id).execute()
        return True
    except Exception as e:
        st.error(f"Error updating project: {e}")
        return False


def get_project_tasks(project_id: str) -> List[Dict[str, Any]]:
    """Get all tasks for a project"""
    try:
        response = supabase.table('tasks').select('*').eq('project_id', project_id).order('created_at', desc=False).execute()
        return response.data if response.data else []
    except Exception as e:
        st.error(f"Error fetching tasks: {e}")
        return []


# ============================================================================
# UI HELPER FUNCTIONS
# ============================================================================

def get_priority_color(priority: int) -> str:
    """Get color for priority level (1=highest/red, 5=lowest/green)"""
    colors = {
        1: "#FF4B4B",  # Red
        2: "#FFA500",  # Orange
        3: "#FFD700",  # Yellow
        4: "#90EE90",  # Light Green
        5: "#00CC99"   # Green
    }
    return colors.get(priority, "#808080")


def get_status_badge_color(status: str) -> str:
    """Get color for status badge"""
    status_colors = {
        'planning': '#808080',
        'ready': '#4B9EFF',
        'in_progress': '#FFA500',
        'blocked': '#FF4B4B',
        'completed': '#00CC99',
        'cancelled': '#666666',
        'on_hold': '#FFD700'
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


def render_priority_indicator(priority: int):
    """Render a priority indicator"""
    color = get_priority_color(priority)
    stars = "★" * priority
    st.markdown(
        f'<span style="color: {color}; font-size: 1.2em;">{stars}</span>',
        unsafe_allow_html=True
    )


def render_coverage_bar(coverage_score: float, label: str = "Coverage"):
    """Render a coverage progress bar"""
    percentage = int(coverage_score * 100)

    # Color based on coverage
    if coverage_score >= 0.8:
        color = "#00CC99"
    elif coverage_score >= 0.5:
        color = "#FFA500"
    else:
        color = "#FF4B4B"

    st.markdown(f"**{label}:** {percentage}%")
    st.progress(coverage_score)


# ============================================================================
# MAIN UI FUNCTIONS
# ============================================================================

def show_project_list() -> None:
    """Display all projects in cards"""
    st.subheader("Projects")

    projects = get_all_projects()

    if not projects:
        st.info("No projects found. Create your first project below!")
        return

    # Filter options
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "planning", "ready", "in_progress", "blocked", "completed", "cancelled", "on_hold"],
            key="status_filter"
        )
    with col2:
        priority_filter = st.selectbox(
            "Filter by Priority",
            ["All", "1", "2", "3", "4", "5"],
            key="priority_filter"
        )
    with col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Created Date", "Priority", "Deadline", "Status"],
            key="sort_by"
        )

    # Apply filters
    filtered_projects = projects
    if status_filter != "All":
        filtered_projects = [p for p in filtered_projects if p.get('status') == status_filter]
    if priority_filter != "All":
        filtered_projects = [p for p in filtered_projects if p.get('priority') == int(priority_filter)]

    # Display projects in a grid
    cols_per_row = 2
    for i in range(0, len(filtered_projects), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            if i + j < len(filtered_projects):
                project = filtered_projects[i + j]
                with col:
                    render_project_card(project)


def render_project_card(project: Dict[str, Any]):
    """Render a single project card"""
    with st.container():
        # Border color based on priority
        border_color = get_priority_color(project.get('priority', 3))

        st.markdown(f"""
            <div style="border-left: 4px solid {border_color}; padding: 12px; margin: 8px 0;
                        background-color: rgba(255,255,255,0.05); border-radius: 4px;">
        """, unsafe_allow_html=True)

        # Title and status
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {project.get('name', 'Untitled')}")
        with col2:
            render_status_badge(project.get('status', 'planning'))

        # Description
        description = project.get('description', 'No description')
        if len(description) > 100:
            description = description[:100] + "..."
        st.markdown(f"*{description}*")

        # Metadata row
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Priority:**")
            render_priority_indicator(project.get('priority', 3))
        with col2:
            deadline = project.get('deadline')
            if deadline:
                st.markdown(f"**Deadline:** {deadline[:10]}")
            else:
                st.markdown("**Deadline:** Not set")
        with col3:
            coverage = project.get('knowledge_coverage_score', 0)
            if coverage:
                st.markdown(f"**Coverage:** {int(coverage * 100)}%")

        # View button
        if st.button(f"View Details", key=f"view_{project['id']}", use_container_width=True):
            st.session_state.selected_project_id = project['id']
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)


def show_create_project_form() -> None:
    """Form to create new project"""
    st.subheader("Create New Project")

    with st.form("create_project_form", clear_on_submit=True):
        name = st.text_input("Project Name*", placeholder="e.g., Build FastAPI Authentication System")
        description = st.text_area("Description*", placeholder="Detailed description of the project...")

        col1, col2 = st.columns(2)
        with col1:
            priority = st.slider("Priority (1=Highest, 5=Lowest)", 1, 5, 3)
            status = st.selectbox("Status", ["planning", "ready", "in_progress", "blocked", "completed", "cancelled", "on_hold"])
        with col2:
            deadline = st.date_input("Deadline (Optional)", value=None)
            estimated_duration = st.number_input("Estimated Duration (minutes)", min_value=0, value=0)

        # Knowledge tags
        tags_input = st.text_input("Required Knowledge Tags (comma-separated)",
                                   placeholder="e.g., fastapi, authentication, jwt, security")
        frameworks_input = st.text_input("Required Frameworks (comma-separated)",
                                        placeholder="e.g., fastapi, pydantic")

        # Auto knowledge discovery
        auto_discover = st.checkbox("Auto-discover knowledge after creation", value=True,
                                   help="Automatically search for relevant knowledge and calculate coverage")

        submitted = st.form_submit_button("Create Project", use_container_width=True)

        if submitted:
            if not name or not description:
                st.error("Name and description are required!")
                return

            # Parse tags and frameworks
            tags = [t.strip() for t in tags_input.split(',') if t.strip()]
            frameworks = [f.strip() for f in frameworks_input.split(',') if f.strip()]

            # Prepare project data
            project_data = {
                'name': name,
                'description': description,
                'priority': priority,
                'status': status,
                'required_knowledge_tags': tags,
                'required_frameworks': frameworks,
            }

            if deadline:
                project_data['deadline'] = deadline.isoformat()
            if estimated_duration > 0:
                project_data['estimated_duration_minutes'] = estimated_duration

            # Generate embedding for project context if possible
            if km and embedding_client:
                with st.spinner("Generating project context embedding..."):
                    embedding = asyncio.run(km.get_embedding(f"{name}\n{description}"))
                    if embedding:
                        project_data['knowledge_context_embedding'] = embedding

            # Create the project
            with st.spinner("Creating project..."):
                new_project = create_project(project_data)

                if new_project:
                    st.success(f"✅ Project '{name}' created successfully!")

                    # Auto-discover knowledge
                    if auto_discover and km and tags:
                        with st.spinner("Analyzing knowledge coverage..."):
                            coverage_info = km.check_coverage(tags, frameworks)

                            # Update coverage score
                            if coverage_info:
                                update_project(new_project['id'], {
                                    'knowledge_coverage_score': coverage_info['coverage_score']
                                })

                                st.info(f"""
                                **Knowledge Coverage Analysis:**
                                - Total relevant chunks found: {coverage_info['total_chunks']}
                                - Coverage score: {int(coverage_info['coverage_score'] * 100)}%
                                - Missing tags: {', '.join(coverage_info['missing_tags']) if coverage_info['missing_tags'] else 'None'}
                                """)

                                if coverage_info['coverage_score'] < 0.5:
                                    st.warning("⚠️ Low knowledge coverage detected. Consider running the scraper to acquire missing knowledge.")

                    # Set the new project as selected
                    st.session_state.selected_project_id = new_project['id']
                    st.rerun()


def show_project_details(project_id: str) -> None:
    """Detailed view of one project"""
    project = get_project_by_id(project_id)

    if not project:
        st.error("Project not found!")
        if st.button("← Back to Projects"):
            st.session_state.selected_project_id = None
            st.rerun()
        return

    # Header with back button
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("← Back"):
            st.session_state.selected_project_id = None
            st.rerun()
    with col2:
        st.title(project.get('name', 'Untitled Project'))

    # Status and priority row
    col1, col2, col3 = st.columns([2, 2, 3])
    with col1:
        st.markdown("**Status:**")
        render_status_badge(project.get('status', 'planning'))
    with col2:
        st.markdown("**Priority:**")
        render_priority_indicator(project.get('priority', 3))
    with col3:
        deadline = project.get('deadline')
        if deadline:
            st.markdown(f"**Deadline:** {deadline[:10]}")

    st.divider()

    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Knowledge Coverage", "Tasks", "Settings"])

    with tab1:
        show_project_overview(project)

    with tab2:
        show_coverage_analysis(project)

    with tab3:
        show_project_tasks(project)

    with tab4:
        show_project_settings(project)


def show_project_overview(project: Dict[str, Any]):
    """Show project overview"""
    st.markdown("### Description")
    st.markdown(project.get('description', 'No description provided.'))

    st.markdown("### Project Information")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Created:** " + (project.get('created_at', '')[:10] if project.get('created_at') else 'Unknown'))
        st.markdown("**Updated:** " + (project.get('updated_at', '')[:10] if project.get('updated_at') else 'Unknown'))

        if project.get('estimated_duration_minutes'):
            hours = project['estimated_duration_minutes'] // 60
            minutes = project['estimated_duration_minutes'] % 60
            st.markdown(f"**Estimated Duration:** {hours}h {minutes}m")

    with col2:
        if project.get('started_at'):
            st.markdown("**Started:** " + project['started_at'][:10])
        if project.get('completed_at'):
            st.markdown("**Completed:** " + project['completed_at'][:10])

    # Tags and frameworks
    st.markdown("### Required Knowledge")

    tags = project.get('required_knowledge_tags', [])
    frameworks = project.get('required_frameworks', [])

    if tags:
        st.markdown("**Tags:**")
        tag_html = " ".join([
            f'<span style="background-color: #4B9EFF; color: white; padding: 4px 8px; '
            f'border-radius: 8px; margin: 2px; display: inline-block; font-size: 0.85em;">{tag}</span>'
            for tag in tags
        ])
        st.markdown(tag_html, unsafe_allow_html=True)

    if frameworks:
        st.markdown("**Frameworks:**")
        framework_html = " ".join([
            f'<span style="background-color: #00CC99; color: white; padding: 4px 8px; '
            f'border-radius: 8px; margin: 2px; display: inline-block; font-size: 0.85em;">{fw}</span>'
            for fw in frameworks
        ])
        st.markdown(framework_html, unsafe_allow_html=True)


def show_coverage_analysis(project: Dict[str, Any]):
    """Visual coverage analysis"""
    st.markdown("### Knowledge Coverage Analysis")

    tags = project.get('required_knowledge_tags', [])
    frameworks = project.get('required_frameworks', [])

    if not tags and not frameworks:
        st.info("No required knowledge tags or frameworks specified for this project.")
        return

    if km:
        # Check current coverage
        with st.spinner("Analyzing knowledge coverage..."):
            coverage_info = km.check_coverage(tags, frameworks)

        # Display coverage score
        coverage_score = coverage_info.get('coverage_score', 0)
        render_coverage_bar(coverage_score, "Overall Coverage")

        st.markdown(f"**Total Knowledge Chunks Found:** {coverage_info.get('total_chunks', 0)}")

        # Missing tags
        missing_tags = coverage_info.get('missing_tags', [])
        if missing_tags:
            st.warning(f"**Missing or Low Coverage Tags:** {', '.join(missing_tags)}")
        else:
            st.success("✅ All required tags have sufficient knowledge!")

        # Available frameworks
        available_frameworks = coverage_info.get('available_frameworks', [])
        if available_frameworks:
            st.info(f"**Available Frameworks:** {', '.join(available_frameworks)}")

        # Update coverage score if different
        current_score = project.get('knowledge_coverage_score')
        if current_score != coverage_score:
            if st.button("Update Project Coverage Score"):
                with st.spinner("Updating..."):
                    if update_project(project['id'], {'knowledge_coverage_score': coverage_score}):
                        st.success("Coverage score updated!")
                        st.rerun()

        # Action buttons
        st.divider()
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🔍 Search & Attach Knowledge", use_container_width=True):
                st.session_state.show_knowledge_search = True

        with col2:
            if coverage_score < 0.5:
                if st.button("🌐 Trigger Web Scraper", use_container_width=True):
                    st.info("🚧 Web scraper integration coming soon!")
                    st.info("This will automatically crawl documentation for missing knowledge.")

        # Knowledge search interface
        if st.session_state.get('show_knowledge_search'):
            st.markdown("### Search Knowledge")
            search_query = st.text_input("Search for relevant knowledge",
                                        placeholder="Enter search query...")

            if search_query and st.button("Search"):
                with st.spinner("Searching..."):
                    # Generate embedding for search
                    query_embedding = asyncio.run(km.get_embedding(search_query))
                    if query_embedding:
                        results = km.search_knowledge(query_embedding, tags, frameworks, match_count=10)

                        if results:
                            st.success(f"Found {len(results)} relevant knowledge chunks:")
                            for result in results:
                                with st.expander(f"{result.get('title', 'Untitled')} (Similarity: {result.get('similarity', 0):.2%})"):
                                    st.markdown(f"**URL:** {result.get('url', 'N/A')}")
                                    st.markdown(f"**Summary:** {result.get('summary', 'N/A')}")
                                    st.markdown(f"**Tags:** {', '.join(result.get('tags', []))}")
                        else:
                            st.warning("No relevant knowledge found.")
    else:
        st.error("Knowledge Manager not available. Please configure Supabase and Embedding client.")


def show_project_tasks(project: Dict[str, Any]):
    """Show task list for project"""
    st.markdown("### Project Tasks")

    tasks = get_project_tasks(project['id'])

    if not tasks:
        st.info("No tasks yet for this project.")
    else:
        st.markdown(f"**Total Tasks:** {len(tasks)}")

        # Task statistics
        task_stats = {
            'pending': 0,
            'in_progress': 0,
            'completed': 0,
            'blocked': 0
        }

        for task in tasks:
            status = task.get('status', 'pending')
            if status in task_stats:
                task_stats[status] += 1

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Pending", task_stats['pending'])
        with col2:
            st.metric("In Progress", task_stats['in_progress'])
        with col3:
            st.metric("Completed", task_stats['completed'])
        with col4:
            st.metric("Blocked", task_stats['blocked'])

        st.divider()

        # Display tasks
        for task in tasks:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{task.get('name', 'Untitled Task')}**")
            with col2:
                render_status_badge(task.get('status', 'pending'))
            with col3:
                if st.button("View", key=f"view_task_{task['id']}"):
                    # Navigate to tasks page with this task selected
                    st.session_state.selected_task_id = task['id']
                    st.session_state.page = 'tasks'
                    st.rerun()

    # Decompose button
    st.divider()
    if st.button("🤖 Decompose Project into Tasks", use_container_width=True):
        decompose_project_into_tasks(project['id'])


def decompose_project_into_tasks(project_id: str) -> None:
    """Use LLM to break down project into tasks"""
    project = get_project_by_id(project_id)

    if not project:
        st.error("Project not found!")
        return

    st.markdown("### AI Task Decomposition")
    st.info("🤖 Using AI to analyze your project and suggest tasks...")

    # Initialize LLM client
    base_url = get_env_var('BASE_URL') or 'https://api.openai.com/v1'
    api_key = get_env_var('LLM_API_KEY') or 'no-api-key-provided'
    llm_model = get_env_var('LLM_MODEL') or 'gpt-4'

    try:
        llm_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    except Exception as e:
        st.error(f"Failed to initialize LLM client: {e}")
        return

    # Prepare prompt
    prompt = f"""
Analyze this project and break it down into specific, actionable tasks:

Project Name: {project.get('name')}
Description: {project.get('description')}
Required Knowledge Tags: {', '.join(project.get('required_knowledge_tags', []))}
Required Frameworks: {', '.join(project.get('required_frameworks', []))}

Please provide 5-10 specific tasks to complete this project. For each task, provide:
1. Task name (concise)
2. Description (detailed)
3. Estimated duration in minutes
4. Priority (1-5, where 1 is highest)
5. Assigned agent type (choose from: coder, scraper, refiner)
6. Required knowledge tags (list)

Format your response as a JSON array of task objects with these fields:
[{{"name": "...", "description": "...", "estimated_duration_minutes": 60, "priority": 2, "assigned_agent_type": "coder", "required_knowledge_tags": ["tag1", "tag2"]}}]
"""

    with st.spinner("AI is analyzing the project and generating tasks..."):
        try:
            async def generate_tasks():
                response = await llm_client.chat.completions.create(
                    model=llm_model,
                    messages=[
                        {"role": "system", "content": "You are a project management assistant that breaks down projects into specific, actionable tasks."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                return response.choices[0].message.content

            result = asyncio.run(generate_tasks())

            # Try to parse JSON from result
            import json
            import re

            # Extract JSON array from result
            json_match = re.search(r'\[.*\]', result, re.DOTALL)
            if json_match:
                tasks_json = json.loads(json_match.group())

                st.success(f"✅ AI generated {len(tasks_json)} tasks!")

                # Preview tasks
                st.markdown("### Preview Generated Tasks")
                for i, task_data in enumerate(tasks_json):
                    with st.expander(f"{i+1}. {task_data.get('name', 'Untitled')}"):
                        st.markdown(f"**Description:** {task_data.get('description', 'N/A')}")
                        st.markdown(f"**Duration:** {task_data.get('estimated_duration_minutes', 0)} minutes")
                        st.markdown(f"**Priority:** {task_data.get('priority', 3)}")
                        st.markdown(f"**Agent Type:** {task_data.get('assigned_agent_type', 'coder')}")
                        st.markdown(f"**Tags:** {', '.join(task_data.get('required_knowledge_tags', []))}")

                # Create tasks button
                if st.button("Create All Tasks", use_container_width=True):
                    with st.spinner("Creating tasks..."):
                        created_count = 0
                        for task_data in tasks_json:
                            task_data['project_id'] = project_id
                            task_data['status'] = 'pending'

                            try:
                                supabase.table('tasks').insert(task_data).execute()
                                created_count += 1
                            except Exception as e:
                                st.error(f"Error creating task: {e}")

                        st.success(f"✅ Created {created_count} tasks!")
                        st.rerun()
            else:
                st.warning("Could not parse AI response as JSON. Here's the raw response:")
                st.text(result)

        except Exception as e:
            st.error(f"Error generating tasks: {e}")


def show_project_settings(project: Dict[str, Any]):
    """Show project settings and edit form"""
    st.markdown("### Project Settings")

    with st.form("edit_project_form"):
        name = st.text_input("Project Name", value=project.get('name', ''))
        description = st.text_area("Description", value=project.get('description', ''))

        col1, col2 = st.columns(2)
        with col1:
            priority = st.slider("Priority", 1, 5, project.get('priority', 3))
            status = st.selectbox("Status",
                                 ["planning", "ready", "in_progress", "blocked", "completed", "cancelled", "on_hold"],
                                 index=["planning", "ready", "in_progress", "blocked", "completed", "cancelled", "on_hold"].index(project.get('status', 'planning')))
        with col2:
            current_deadline = None
            if project.get('deadline'):
                try:
                    from datetime import date
                    deadline_str = project['deadline'][:10]
                    year, month, day = map(int, deadline_str.split('-'))
                    current_deadline = date(year, month, day)
                except:
                    pass

            deadline = st.date_input("Deadline", value=current_deadline)
            estimated_duration = st.number_input("Estimated Duration (minutes)",
                                               min_value=0,
                                               value=project.get('estimated_duration_minutes', 0))

        submitted = st.form_submit_button("Save Changes", use_container_width=True)

        if submitted:
            updates = {
                'name': name,
                'description': description,
                'priority': priority,
                'status': status,
                'estimated_duration_minutes': estimated_duration if estimated_duration > 0 else None
            }

            if deadline:
                updates['deadline'] = deadline.isoformat()

            with st.spinner("Saving changes..."):
                if update_project(project['id'], updates):
                    st.success("✅ Project updated successfully!")
                    st.rerun()

    st.divider()

    # Danger zone
    st.markdown("### Danger Zone")
    if st.button("🗑️ Delete Project", type="secondary"):
        st.session_state.confirm_delete = True

    if st.session_state.get('confirm_delete'):
        st.warning("⚠️ Are you sure? This will delete the project and all its tasks!")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", use_container_width=True):
                try:
                    supabase.table('projects').delete().eq('id', project['id']).execute()
                    st.success("Project deleted!")
                    st.session_state.selected_project_id = None
                    st.session_state.confirm_delete = False
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting project: {e}")
        with col2:
            if st.button("Cancel", use_container_width=True):
                st.session_state.confirm_delete = False
                st.rerun()


# ============================================================================
# MAIN PAGE
# ============================================================================

def projects_page():
    """Main projects page"""
    st.title("📊 Projects Dashboard")

    # Check if database is configured
    if not supabase:
        st.error("⚠️ Supabase is not configured. Please set up your database in the Database tab.")
        return

    # Initialize session state
    if 'selected_project_id' not in st.session_state:
        st.session_state.selected_project_id = None
    if 'show_knowledge_search' not in st.session_state:
        st.session_state.show_knowledge_search = False
    if 'confirm_delete' not in st.session_state:
        st.session_state.confirm_delete = False

    # Show selected project or list
    if st.session_state.selected_project_id:
        show_project_details(st.session_state.selected_project_id)
    else:
        # Main view with projects list and create form
        tab1, tab2 = st.tabs(["All Projects", "Create New Project"])

        with tab1:
            show_project_list()

        with tab2:
            show_create_project_form()


# Entry point
if __name__ == "__main__":
    projects_page()
