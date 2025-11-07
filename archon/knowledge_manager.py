"""
Archon Knowledge Manager Orchestrator

This module orchestrates knowledge management operations for Archon's knowledge-aware
project and task management system. It coordinates universal_crawler and knowledge_linker
with Archon's existing workflow.

Architecture:
    User creates project → Extract requirements → Check coverage
        ↓ (if low coverage)
    Trigger scraper → Wait for crawl → Auto-link knowledge
        ↓ (if good coverage)
    Auto-link knowledge → Create tasks → Return to user

Key Features:
    - Project/Task CRUD operations
    - Automatic knowledge discovery and linking
    - Coverage-based scraper triggering
    - Parallel processing with asyncio
    - Agent registry tracking
"""

from __future__ import annotations

import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from openai import AsyncOpenAI
from supabase import Client
import logging

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import get_env_var, get_clients, write_to_log

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND DATA CLASSES
# ============================================================================

class ProjectStatus(str, Enum):
    """Project status options"""
    PLANNING = "planning"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ON_HOLD = "on_hold"


class TaskStatus(str, Enum):
    """Task status options"""
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class LinkType(str, Enum):
    """Knowledge link type options"""
    REQUIRED = "required"
    SUGGESTED = "suggested"
    LEARNED = "learned"
    REFERENCE = "reference"


class AgentType(str, Enum):
    """Agent type options"""
    CODER = "coder"
    SCRAPER = "scraper"
    REFINER = "refiner"
    LINKER = "linker"
    DECOMPOSER = "decomposer"
    CUSTOM = "custom"


@dataclass
class KnowledgeCoverage:
    """Knowledge coverage information"""
    total_chunks: int
    coverage_score: float
    missing_tags: List[str]
    available_frameworks: List[str]
    needs_scraping: bool


@dataclass
class ProjectMetadata:
    """Project metadata"""
    id: str
    name: str
    description: str
    status: str
    priority: int
    deadline: Optional[datetime]
    required_knowledge_tags: List[str]
    required_frameworks: List[str]
    knowledge_coverage_score: Optional[float]
    created_at: datetime
    updated_at: datetime


@dataclass
class TaskMetadata:
    """Task metadata"""
    id: str
    project_id: str
    name: str
    description: str
    status: str
    priority: int
    required_knowledge_tags: List[str]
    required_frameworks: List[str]
    knowledge_coverage_score: Optional[float]
    assigned_agent_type: Optional[str]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# KNOWLEDGE MANAGER ORCHESTRATOR
# ============================================================================

class KnowledgeManager:
    """
    Orchestrates knowledge management operations for Archon.

    This class coordinates:
    - Project and task CRUD operations
    - Automatic knowledge discovery
    - Coverage checking and scraper triggering
    - Knowledge linking to tasks
    - Agent registry tracking
    """

    def __init__(
        self,
        supabase: Optional[Client] = None,
        embedding_client: Optional[AsyncOpenAI] = None,
        llm_client: Optional[AsyncOpenAI] = None
    ):
        """
        Initialize the Knowledge Manager.

        Args:
            supabase: Supabase client (auto-initialized if None)
            embedding_client: OpenAI client for embeddings (auto-initialized if None)
            llm_client: OpenAI client for LLM operations (auto-initialized if None)
        """
        # Initialize clients
        if supabase is None or embedding_client is None:
            self.embedding_client, self.supabase = get_clients()
        else:
            self.supabase = supabase
            self.embedding_client = embedding_client

        # Setup LLM client
        if llm_client is None:
            base_url = get_env_var('BASE_URL') or 'https://api.openai.com/v1'
            api_key = get_env_var('LLM_API_KEY') or 'no-api-key-provided'
            provider = get_env_var('LLM_PROVIDER') or 'OpenAI'

            if provider == "Ollama":
                if api_key == "NOT_REQUIRED":
                    api_key = "ollama"
                self.llm_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
            else:
                self.llm_client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        else:
            self.llm_client = llm_client

        # Get configuration
        self.embedding_model = get_env_var('EMBEDDING_MODEL') or 'text-embedding-3-small'
        self.primary_model = get_env_var('PRIMARY_MODEL') or 'gpt-4o-mini'

        # Knowledge coverage threshold
        self.min_coverage_threshold = 0.4

        logger.info("KnowledgeManager initialized successfully")
        write_to_log("KnowledgeManager initialized successfully")

    # ========================================================================
    # PROJECT OPERATIONS
    # ========================================================================

    async def create_project(
        self,
        name: str,
        description: str,
        priority: int = 3,
        deadline: Optional[datetime] = None,
        auto_discover: bool = True,
        min_coverage: float = 0.4
    ) -> Dict[str, Any]:
        """
        Create a new project with automatic knowledge discovery.

        Workflow:
            1. Insert project into database
            2. Generate embedding for description
            3. Extract tags/frameworks with LLM
            4. Check knowledge coverage
            5. Trigger scraper if coverage < threshold
            6. Auto-link knowledge to project
            7. Return project with coverage info

        Args:
            name: Project name
            description: Project description
            priority: Priority (1=highest, 5=lowest)
            deadline: Optional deadline
            auto_discover: Whether to auto-discover knowledge needs
            min_coverage: Minimum coverage threshold (default 0.4)

        Returns:
            Dictionary containing:
                - project: Project metadata
                - coverage: Knowledge coverage info
                - scraper_triggered: Whether scraper was triggered
        """
        try:
            logger.info(f"Creating project: {name}")
            write_to_log(f"Creating project: {name}")

            # Step 1: Extract tags and frameworks from description
            tags, frameworks = await self._extract_tags_and_frameworks(description)
            logger.info(f"Extracted tags: {tags}, frameworks: {frameworks}")

            # Step 2: Generate embedding for project description
            embedding = await self._get_embedding(description)

            # Step 3: Insert project into database
            project_data = {
                "name": name,
                "description": description,
                "status": ProjectStatus.PLANNING.value,
                "priority": priority,
                "deadline": deadline.isoformat() if deadline else None,
                "required_knowledge_tags": tags,
                "required_frameworks": frameworks,
                "knowledge_context_embedding": embedding,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = self.supabase.table("projects").insert(project_data).execute()
            project = result.data[0]
            project_id = project['id']

            logger.info(f"Project created with ID: {project_id}")
            write_to_log(f"Project created with ID: {project_id}")

            # Step 4: Check knowledge coverage and auto-discover if enabled
            coverage = None
            scraper_triggered = False

            if auto_discover:
                coverage = await self.check_and_acquire_knowledge(
                    tags=tags,
                    frameworks=frameworks,
                    min_coverage=min_coverage
                )

                # Update project with coverage score
                await self._update_project_coverage(project_id, coverage.coverage_score)

                scraper_triggered = coverage.needs_scraping

            return {
                "project": project,
                "coverage": asdict(coverage) if coverage else None,
                "scraper_triggered": scraper_triggered
            }

        except Exception as e:
            logger.error(f"Error creating project: {e}")
            write_to_log(f"Error creating project: {e}")
            raise

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """
        Get a project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project data dictionary
        """
        try:
            result = self.supabase.table("projects").select("*").eq("id", project_id).execute()

            if not result.data:
                raise ValueError(f"Project not found: {project_id}")

            return result.data[0]

        except Exception as e:
            logger.error(f"Error getting project: {e}")
            raise

    async def update_project_status(
        self,
        project_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update project status and optional metadata.

        Args:
            project_id: Project UUID
            status: New status (must be valid ProjectStatus)
            metadata: Optional metadata to update

        Returns:
            Updated project data
        """
        try:
            # Validate status
            ProjectStatus(status)

            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            # Add completion timestamp if status is completed
            if status == ProjectStatus.COMPLETED.value:
                update_data["completed_at"] = datetime.now(timezone.utc).isoformat()

            # Add start timestamp if status is in_progress
            if status == ProjectStatus.IN_PROGRESS.value:
                project = await self.get_project(project_id)
                if not project.get("started_at"):
                    update_data["started_at"] = datetime.now(timezone.utc).isoformat()

            # Update metadata if provided
            if metadata:
                update_data["metadata"] = metadata

            result = self.supabase.table("projects").update(update_data).eq("id", project_id).execute()

            logger.info(f"Updated project {project_id} status to {status}")
            write_to_log(f"Updated project {project_id} status to {status}")

            return result.data[0]

        except Exception as e:
            logger.error(f"Error updating project status: {e}")
            raise

    async def delete_project(self, project_id: str) -> bool:
        """
        Delete a project and all associated tasks.

        Args:
            project_id: Project UUID

        Returns:
            True if successful
        """
        try:
            # Tasks will be cascade deleted due to foreign key constraint
            self.supabase.table("projects").delete().eq("id", project_id).execute()

            logger.info(f"Deleted project: {project_id}")
            write_to_log(f"Deleted project: {project_id}")

            return True

        except Exception as e:
            logger.error(f"Error deleting project: {e}")
            raise

    # ========================================================================
    # TASK OPERATIONS
    # ========================================================================

    async def create_task(
        self,
        project_id: str,
        name: str,
        description: str,
        priority: int = 3,
        deadline: Optional[datetime] = None,
        parent_task_id: Optional[str] = None,
        auto_link: bool = True,
        assigned_agent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a task with optional automatic knowledge linking.

        Workflow:
            1. Insert task into database
            2. Generate embedding for description
            3. Extract requirements (tags/frameworks)
            4. Auto-link knowledge if requested
            5. Calculate coverage score
            6. Return task with linked knowledge

        Args:
            project_id: Parent project UUID
            name: Task name
            description: Task description
            priority: Priority (1=highest, 5=lowest)
            deadline: Optional deadline
            parent_task_id: Optional parent task for subtasks
            auto_link: Whether to auto-link knowledge
            assigned_agent_type: Optional agent type to assign

        Returns:
            Dictionary containing:
                - task: Task metadata
                - linked_knowledge: List of linked knowledge chunks
                - coverage_score: Knowledge coverage score
        """
        try:
            logger.info(f"Creating task: {name} for project {project_id}")
            write_to_log(f"Creating task: {name} for project {project_id}")

            # Step 1: Extract tags and frameworks
            tags, frameworks = await self._extract_tags_and_frameworks(description)

            # Step 2: Generate embedding
            embedding = await self._get_embedding(description)

            # Step 3: Insert task
            task_data = {
                "project_id": project_id,
                "parent_task_id": parent_task_id,
                "name": name,
                "description": description,
                "status": TaskStatus.PENDING.value,
                "priority": priority,
                "deadline": deadline.isoformat() if deadline else None,
                "required_knowledge_tags": tags,
                "required_frameworks": frameworks,
                "task_context_embedding": embedding,
                "assigned_agent_type": assigned_agent_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            result = self.supabase.table("tasks").insert(task_data).execute()
            task = result.data[0]
            task_id = task['id']

            logger.info(f"Task created with ID: {task_id}")

            # Step 4: Auto-link knowledge if requested
            linked_knowledge = []
            coverage_score = 0.0

            if auto_link:
                link_result = await self.link_task_knowledge(task_id)
                linked_knowledge = link_result['linked_knowledge']
                coverage_score = link_result['coverage_score']

            return {
                "task": task,
                "linked_knowledge": linked_knowledge,
                "coverage_score": coverage_score
            }

        except Exception as e:
            logger.error(f"Error creating task: {e}")
            write_to_log(f"Error creating task: {e}")
            raise

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """
        Get a task by ID.

        Args:
            task_id: Task UUID

        Returns:
            Task data dictionary
        """
        try:
            result = self.supabase.table("tasks").select("*").eq("id", task_id).execute()

            if not result.data:
                raise ValueError(f"Task not found: {task_id}")

            return result.data[0]

        except Exception as e:
            logger.error(f"Error getting task: {e}")
            raise

    async def get_task_with_knowledge(self, task_id: str) -> Dict[str, Any]:
        """
        Get task with all linked knowledge chunks.

        Args:
            task_id: Task UUID

        Returns:
            Dictionary containing:
                - task: Task metadata
                - linked_knowledge: List of knowledge chunks with relevance scores
        """
        try:
            # Get task
            task = await self.get_task(task_id)

            # Get linked knowledge using RPC function
            result = self.supabase.rpc(
                "get_task_knowledge",
                {"task_id_param": task_id}
            ).execute()

            linked_knowledge = result.data if result.data else []

            return {
                "task": task,
                "linked_knowledge": linked_knowledge
            }

        except Exception as e:
            logger.error(f"Error getting task with knowledge: {e}")
            raise

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update task status and optional metadata.

        Args:
            task_id: Task UUID
            status: New status (must be valid TaskStatus)
            metadata: Optional metadata to update

        Returns:
            Updated task data
        """
        try:
            # Validate status
            TaskStatus(status)

            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }

            # Add timestamps based on status
            if status == TaskStatus.COMPLETED.value:
                update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
            elif status == TaskStatus.IN_PROGRESS.value:
                task = await self.get_task(task_id)
                if not task.get("started_at"):
                    update_data["started_at"] = datetime.now(timezone.utc).isoformat()

            # Update metadata if provided
            if metadata:
                update_data["metadata"] = metadata

            result = self.supabase.table("tasks").update(update_data).eq("id", task_id).execute()

            logger.info(f"Updated task {task_id} status to {status}")
            write_to_log(f"Updated task {task_id} status to {status}")

            return result.data[0]

        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            raise

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task and all associated links.

        Args:
            task_id: Task UUID

        Returns:
            True if successful
        """
        try:
            # Links will be cascade deleted due to foreign key constraint
            self.supabase.table("tasks").delete().eq("id", task_id).execute()

            logger.info(f"Deleted task: {task_id}")
            write_to_log(f"Deleted task: {task_id}")

            return True

        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            raise

    # ========================================================================
    # KNOWLEDGE OPERATIONS
    # ========================================================================

    async def check_and_acquire_knowledge(
        self,
        tags: List[str],
        frameworks: List[str],
        min_coverage: float = 0.4
    ) -> KnowledgeCoverage:
        """
        Check knowledge coverage and trigger scraper if needed.

        Workflow:
            1. Use check_knowledge_coverage RPC
            2. If coverage < min_coverage, build scraper config
            3. Trigger universal_crawler (to be implemented)
            4. Return coverage info

        Args:
            tags: Required tags
            frameworks: Required frameworks
            min_coverage: Minimum acceptable coverage (0-1)

        Returns:
            KnowledgeCoverage object with coverage details
        """
        try:
            logger.info(f"Checking knowledge coverage for tags={tags}, frameworks={frameworks}")

            # Call RPC function to check coverage
            result = self.supabase.rpc(
                "check_knowledge_coverage",
                {
                    "required_tags_param": tags,
                    "required_frameworks_param": frameworks
                }
            ).execute()

            if not result.data or len(result.data) == 0:
                # No data returned, assume zero coverage
                coverage_data = {
                    "total_chunks": 0,
                    "coverage_score": 0.0,
                    "missing_tags": tags,
                    "available_frameworks": []
                }
            else:
                coverage_data = result.data[0]

            # Create coverage object
            coverage = KnowledgeCoverage(
                total_chunks=coverage_data['total_chunks'],
                coverage_score=coverage_data['coverage_score'],
                missing_tags=coverage_data.get('missing_tags', []) or [],
                available_frameworks=coverage_data.get('available_frameworks', []) or [],
                needs_scraping=coverage_data['coverage_score'] < min_coverage
            )

            logger.info(f"Coverage score: {coverage.coverage_score}, needs_scraping: {coverage.needs_scraping}")

            # If coverage is low, trigger scraper (placeholder - actual implementation in Phase 2)
            if coverage.needs_scraping:
                logger.warning(f"Low coverage ({coverage.coverage_score:.2f}), scraper trigger needed")
                write_to_log(f"Low coverage for tags={tags}, frameworks={frameworks}. Scraper needed.")
                # TODO: Trigger universal_crawler here in Phase 2
                # await self._trigger_scraper(tags, frameworks, coverage.missing_tags)

            return coverage

        except Exception as e:
            logger.error(f"Error checking knowledge coverage: {e}")
            write_to_log(f"Error checking knowledge coverage: {e}")
            raise

    async def link_task_knowledge(
        self,
        task_id: str,
        refresh: bool = False,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Link knowledge to a task using semantic search.

        Workflow:
            1. Get task details and embedding
            2. Use match_knowledge_advanced RPC with task's tags/frameworks
            3. Create task_knowledge_links for top matches
            4. Calculate and update coverage score
            5. Return linked knowledge

        Args:
            task_id: Task UUID
            refresh: Whether to delete existing links and re-link
            top_k: Number of top knowledge chunks to link

        Returns:
            Dictionary containing:
                - linked_knowledge: List of linked knowledge chunks
                - coverage_score: Updated coverage score
        """
        try:
            logger.info(f"Linking knowledge to task: {task_id}")
            write_to_log(f"Linking knowledge to task: {task_id}")

            # Get task details
            task = await self.get_task(task_id)

            # Delete existing links if refresh requested
            if refresh:
                self.supabase.table("task_knowledge_links").delete().eq("task_id", task_id).execute()
                logger.info(f"Cleared existing knowledge links for task {task_id}")

            # Get task embedding
            task_embedding = task.get('task_context_embedding')
            if not task_embedding:
                # Generate embedding if not exists
                task_embedding = await self._get_embedding(task['description'])
                # Update task with embedding
                self.supabase.table("tasks").update({
                    "task_context_embedding": task_embedding
                }).eq("id", task_id).execute()

            # Search for relevant knowledge using RPC
            result = self.supabase.rpc(
                "match_knowledge_advanced",
                {
                    "query_embedding": task_embedding,
                    "match_count": top_k,
                    "match_threshold": 0.5,
                    "required_tags": task.get('required_knowledge_tags', []),
                    "required_frameworks": task.get('required_frameworks', [])
                }
            ).execute()

            matched_knowledge = result.data if result.data else []

            # Create knowledge links
            links_created = 0
            for knowledge in matched_knowledge:
                try:
                    link_data = {
                        "task_id": task_id,
                        "knowledge_id": knowledge['id'],
                        "relevance_score": knowledge['similarity'],
                        "link_type": LinkType.SUGGESTED.value,
                        "linked_by": "auto",
                        "link_reason": "Semantic similarity match",
                        "created_at": datetime.now(timezone.utc).isoformat()
                    }

                    # Use upsert to avoid duplicates
                    self.supabase.table("task_knowledge_links").upsert(link_data).execute()
                    links_created += 1

                except Exception as link_error:
                    # Link might already exist, skip
                    logger.debug(f"Could not create link for knowledge {knowledge['id']}: {link_error}")

            logger.info(f"Created {links_created} knowledge links for task {task_id}")

            # Calculate coverage score
            coverage_score = min(1.0, links_created / max(1, len(task.get('required_knowledge_tags', [])) * 3))

            # Update task with coverage score
            self.supabase.table("tasks").update({
                "knowledge_coverage_score": coverage_score,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", task_id).execute()

            return {
                "linked_knowledge": matched_knowledge,
                "coverage_score": coverage_score,
                "links_created": links_created
            }

        except Exception as e:
            logger.error(f"Error linking task knowledge: {e}")
            write_to_log(f"Error linking task knowledge: {e}")
            raise

    # ========================================================================
    # PROJECT DECOMPOSITION
    # ========================================================================

    async def decompose_project(
        self,
        project_id: str,
        decomposition_strategy: str = "auto",
        auto_link_knowledge: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Break a project into tasks using LLM.

        This is a placeholder implementation using LLM directly.
        In Phase 3, this will use an Archon-generated Project Decomposer Agent.

        Args:
            project_id: Project UUID
            decomposition_strategy: Strategy for decomposition ("auto", "sequential", "parallel")
            auto_link_knowledge: Whether to auto-link knowledge to created tasks

        Returns:
            List of created tasks
        """
        try:
            logger.info(f"Decomposing project: {project_id}")
            write_to_log(f"Decomposing project: {project_id}")

            # Get project details
            project = await self.get_project(project_id)

            # Use LLM to break down project into tasks
            system_prompt = """You are an AI project manager that breaks down projects into actionable tasks.

Given a project description, create a list of tasks needed to complete the project.
For each task, provide:
- name: Clear, actionable task name
- description: Detailed description of what needs to be done
- priority: 1 (highest) to 5 (lowest)
- estimated_duration_minutes: Estimate in minutes
- dependencies: List of task names this depends on (empty if none)

Return a JSON array of tasks."""

            user_prompt = f"""Project: {project['name']}

Description: {project['description']}

Required Tags: {project.get('required_knowledge_tags', [])}
Required Frameworks: {project.get('required_frameworks', [])}

Strategy: {decomposition_strategy}

Break this project into concrete, actionable tasks."""

            # Call LLM
            response = await self.llm_client.chat.completions.create(
                model=self.primary_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )

            # Parse response
            result = json.loads(response.choices[0].message.content)
            task_definitions = result.get('tasks', [])

            # Create tasks
            created_tasks = []
            task_id_map = {}  # Map task names to IDs for dependencies

            for task_def in task_definitions:
                task = await self.create_task(
                    project_id=project_id,
                    name=task_def['name'],
                    description=task_def['description'],
                    priority=task_def.get('priority', 3),
                    auto_link=auto_link_knowledge
                )

                created_tasks.append(task)
                task_id_map[task_def['name']] = task['task']['id']

            # Create dependencies (in a second pass)
            for i, task_def in enumerate(task_definitions):
                dependencies = task_def.get('dependencies', [])
                for dep_name in dependencies:
                    if dep_name in task_id_map:
                        await self._create_task_dependency(
                            task_id=task_id_map[task_def['name']],
                            depends_on_task_id=task_id_map[dep_name],
                            dependency_type='finish_to_start'
                        )

            logger.info(f"Created {len(created_tasks)} tasks for project {project_id}")
            write_to_log(f"Decomposed project {project_id} into {len(created_tasks)} tasks")

            return created_tasks

        except Exception as e:
            logger.error(f"Error decomposing project: {e}")
            write_to_log(f"Error decomposing project: {e}")
            raise

    # ========================================================================
    # AGENT REGISTRY
    # ========================================================================

    async def register_agent(
        self,
        agent_name: str,
        agent_type: str,
        capabilities: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Register an agent in the system.

        Note: This is a placeholder. In the full implementation, we would have
        a separate agents table. For now, we'll store in metadata.

        Args:
            agent_name: Unique agent name
            agent_type: Agent type (from AgentType enum)
            capabilities: Dictionary describing agent capabilities
            metadata: Optional additional metadata

        Returns:
            Agent registration data
        """
        try:
            # Validate agent type
            AgentType(agent_type)

            agent_data = {
                "agent_name": agent_name,
                "agent_type": agent_type,
                "capabilities": capabilities,
                "metadata": metadata or {},
                "registered_at": datetime.now(timezone.utc).isoformat()
            }

            logger.info(f"Registered agent: {agent_name} (type: {agent_type})")
            write_to_log(f"Registered agent: {agent_name} (type: {agent_type})")

            # TODO: Store in agents table when it's created
            return agent_data

        except Exception as e:
            logger.error(f"Error registering agent: {e}")
            raise

    # ========================================================================
    # PARALLEL OPERATIONS
    # ========================================================================

    async def batch_create_tasks(
        self,
        project_id: str,
        task_definitions: List[Dict[str, Any]],
        auto_link: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Create multiple tasks in parallel.

        Args:
            project_id: Parent project UUID
            task_definitions: List of task definition dicts
            auto_link: Whether to auto-link knowledge

        Returns:
            List of created tasks
        """
        try:
            logger.info(f"Batch creating {len(task_definitions)} tasks for project {project_id}")

            # Create tasks in parallel
            tasks = await asyncio.gather(*[
                self.create_task(
                    project_id=project_id,
                    name=task_def['name'],
                    description=task_def['description'],
                    priority=task_def.get('priority', 3),
                    deadline=task_def.get('deadline'),
                    auto_link=auto_link,
                    assigned_agent_type=task_def.get('assigned_agent_type')
                )
                for task_def in task_definitions
            ])

            logger.info(f"Batch created {len(tasks)} tasks")
            return tasks

        except Exception as e:
            logger.error(f"Error batch creating tasks: {e}")
            raise

    async def batch_link_knowledge(
        self,
        task_ids: List[str],
        refresh: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Link knowledge to multiple tasks in parallel.

        Args:
            task_ids: List of task UUIDs
            refresh: Whether to refresh existing links

        Returns:
            List of link results
        """
        try:
            logger.info(f"Batch linking knowledge to {len(task_ids)} tasks")

            # Link knowledge in parallel
            results = await asyncio.gather(*[
                self.link_task_knowledge(task_id, refresh=refresh)
                for task_id in task_ids
            ])

            logger.info(f"Batch linked knowledge to {len(task_ids)} tasks")
            return results

        except Exception as e:
            logger.error(f"Error batch linking knowledge: {e}")
            raise

    async def batch_check_coverage(
        self,
        tag_framework_pairs: List[Tuple[List[str], List[str]]],
        min_coverage: float = 0.4
    ) -> List[KnowledgeCoverage]:
        """
        Check coverage for multiple tag/framework combinations in parallel.

        Args:
            tag_framework_pairs: List of (tags, frameworks) tuples
            min_coverage: Minimum coverage threshold

        Returns:
            List of KnowledgeCoverage objects
        """
        try:
            logger.info(f"Batch checking coverage for {len(tag_framework_pairs)} combinations")

            # Check coverage in parallel
            coverages = await asyncio.gather(*[
                self.check_and_acquire_knowledge(tags, frameworks, min_coverage)
                for tags, frameworks in tag_framework_pairs
            ])

            logger.info(f"Batch checked {len(coverages)} coverages")
            return coverages

        except Exception as e:
            logger.error(f"Error batch checking coverage: {e}")
            raise

    # ========================================================================
    # HELPER METHODS (PRIVATE)
    # ========================================================================

    async def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        try:
            response = await self.embedding_client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            # Return zero vector on error
            return [0.0] * 1536

    async def _extract_tags_and_frameworks(
        self,
        description: str
    ) -> Tuple[List[str], List[str]]:
        """
        Extract tags and frameworks from a description using LLM.

        Args:
            description: Text description

        Returns:
            Tuple of (tags, frameworks)
        """
        try:
            system_prompt = """You are an AI that extracts technical tags and frameworks from project/task descriptions.

Extract relevant:
- tags: Technical concepts, technologies, patterns (e.g., "authentication", "rest-api", "websockets")
- frameworks: Specific frameworks/libraries (e.g., "fastapi", "react", "pydantic_ai")

Return JSON with "tags" and "frameworks" arrays. Be specific but concise."""

            response = await self.llm_client.chat.completions.create(
                model=self.primary_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Description: {description}"}
                ],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            tags = result.get('tags', [])
            frameworks = result.get('frameworks', [])

            # Convert to lowercase for consistency
            tags = [tag.lower() for tag in tags]
            frameworks = [fw.lower() for fw in frameworks]

            return tags, frameworks

        except Exception as e:
            logger.error(f"Error extracting tags and frameworks: {e}")
            # Return empty lists on error
            return [], []

    async def _update_project_coverage(
        self,
        project_id: str,
        coverage_score: float
    ) -> None:
        """
        Update project's knowledge coverage score.

        Args:
            project_id: Project UUID
            coverage_score: Coverage score (0-1)
        """
        try:
            self.supabase.table("projects").update({
                "knowledge_coverage_score": coverage_score,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", project_id).execute()
        except Exception as e:
            logger.error(f"Error updating project coverage: {e}")

    async def _create_task_dependency(
        self,
        task_id: str,
        depends_on_task_id: str,
        dependency_type: str = 'finish_to_start',
        lag_minutes: int = 0
    ) -> Dict[str, Any]:
        """
        Create a task dependency.

        Args:
            task_id: Task UUID
            depends_on_task_id: Task UUID this depends on
            dependency_type: Type of dependency
            lag_minutes: Lag time in minutes

        Returns:
            Dependency data
        """
        try:
            dependency_data = {
                "task_id": task_id,
                "depends_on_task_id": depends_on_task_id,
                "dependency_type": dependency_type,
                "lag_minutes": lag_minutes,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            result = self.supabase.table("task_dependencies").insert(dependency_data).execute()
            return result.data[0]

        except Exception as e:
            logger.error(f"Error creating task dependency: {e}")
            raise

    # ========================================================================
    # FUTURE INTEGRATIONS (Placeholders for Phase 2-3)
    # ========================================================================

    async def _trigger_scraper(
        self,
        tags: List[str],
        frameworks: List[str],
        missing_tags: List[str]
    ) -> Dict[str, Any]:
        """
        Trigger universal_crawler for missing knowledge.

        This is a placeholder for Phase 2 implementation.

        Args:
            tags: All required tags
            frameworks: Required frameworks
            missing_tags: Tags with insufficient coverage

        Returns:
            Scraper trigger result
        """
        # TODO: Implement in Phase 2
        # This will:
        # 1. Build scraper configuration
        # 2. Trigger universal_crawler agent
        # 3. Wait for completion or run async
        # 4. Return scraper status

        logger.warning("Scraper trigger not yet implemented (Phase 2)")
        write_to_log(f"Scraper trigger needed for tags={missing_tags}, frameworks={frameworks}")

        return {
            "status": "not_implemented",
            "message": "Universal scraper integration coming in Phase 2"
        }


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def get_knowledge_manager(
    supabase: Optional[Client] = None,
    embedding_client: Optional[AsyncOpenAI] = None,
    llm_client: Optional[AsyncOpenAI] = None
) -> KnowledgeManager:
    """
    Factory function to create a KnowledgeManager instance.

    Args:
        supabase: Optional Supabase client
        embedding_client: Optional embedding client
        llm_client: Optional LLM client

    Returns:
        Initialized KnowledgeManager
    """
    return KnowledgeManager(
        supabase=supabase,
        embedding_client=embedding_client,
        llm_client=llm_client
    )


# ============================================================================
# MAIN (for testing)
# ============================================================================

async def main():
    """Main function for testing the Knowledge Manager."""
    # Initialize manager
    km = KnowledgeManager()

    # Example: Create a project
    project = await km.create_project(
        name="FastAPI Authentication System",
        description="Build a complete authentication system with JWT tokens, OAuth2, and password reset functionality using FastAPI and PostgreSQL",
        priority=1,
        auto_discover=True
    )

    print(f"Created project: {project['project']['id']}")
    print(f"Coverage score: {project['coverage']['coverage_score']}")
    print(f"Scraper triggered: {project['scraper_triggered']}")

    # Example: Decompose project into tasks
    if not project['scraper_triggered']:
        tasks = await km.decompose_project(
            project_id=project['project']['id'],
            auto_link_knowledge=True
        )
        print(f"Created {len(tasks)} tasks")


if __name__ == "__main__":
    asyncio.run(main())
