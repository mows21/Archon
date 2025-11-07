"""
ARCHON KNOWLEDGE LINKER AGENT

This module provides intelligent knowledge linking capabilities for Archon's task management system.
It automatically analyzes tasks and attaches relevant knowledge chunks from the knowledge base.

Key Features:
- Task analysis to extract tags, frameworks, and complexity
- Smart knowledge search with vector similarity and filtering
- Relevance scoring for knowledge chunks
- Automatic link creation and management
- Coverage analysis to identify knowledge gaps
- Support for continuous updates and refresh

Author: Archon Team
"""

from __future__ import annotations as _annotations

import os
import sys
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from openai import AsyncOpenAI
from supabase import Client
from dotenv import load_dotenv

# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import get_env_var, get_clients, write_to_log

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

embedding_model = get_env_var('EMBEDDING_MODEL') or 'text-embedding-3-small'
llm_model = get_env_var('PRIMARY_MODEL') or 'gpt-4o-mini'
base_url = get_env_var('BASE_URL') or 'https://api.openai.com/v1'
api_key = get_env_var('LLM_API_KEY') or 'no-api-key-provided'

# Initialize clients
embedding_client, supabase = get_clients()

# Setup LLM client
llm_client = AsyncOpenAI(base_url=base_url, api_key=api_key)


# ============================================================================
# DATA MODELS
# ============================================================================

class LinkType(str, Enum):
    """Types of knowledge links"""
    REQUIRED = "required"      # Critical knowledge needed for the task
    SUGGESTED = "suggested"    # Helpful knowledge for the task
    REFERENCE = "reference"    # Related but not essential
    LEARNED = "learned"        # Knowledge created during task execution


@dataclass
class TaskRequirements:
    """Extracted requirements from task analysis"""
    tags: List[str]
    frameworks: List[str]
    language: Optional[str]
    complexity: str  # 'simple', 'medium', 'complex'
    suggested_knowledge_types: List[str]
    confidence: float  # 0-1, confidence in the extraction


@dataclass
class KnowledgeChunk:
    """Represents a knowledge chunk with metadata"""
    id: int
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str
    tags: List[str]
    knowledge_type: str
    framework: Optional[str]
    language: Optional[str]
    similarity: float
    metadata: Dict[str, Any]


@dataclass
class LinkResult:
    """Result of linking knowledge to a task"""
    task_id: str
    total_chunks_found: int
    links_created: int
    links_updated: int
    coverage_score: float
    missing_knowledge: List[str]
    suggested_crawl_sources: List[str]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def get_embedding(text: str) -> List[float]:
    """
    Get embedding vector from OpenAI/Ollama.

    Args:
        text: The text to embed

    Returns:
        List of floats representing the embedding vector
    """
    try:
        response = await embedding_client.embeddings.create(
            model=embedding_model,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        write_to_log(f"Error getting embedding: {e}")
        return [0] * 1536  # Return zero vector on error


async def call_llm(system_prompt: str, user_prompt: str, response_format: str = "json_object") -> Dict[str, Any]:
    """
    Call the LLM with structured output.

    Args:
        system_prompt: System instruction for the LLM
        user_prompt: User query/input
        response_format: Format for response ("json_object" or "text")

    Returns:
        Parsed JSON response or text response
    """
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        if response_format == "json_object":
            response = await llm_client.chat.completions.create(
                model=llm_model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.3  # Lower temperature for more consistent extraction
            )
            return json.loads(response.choices[0].message.content)
        else:
            response = await llm_client.chat.completions.create(
                model=llm_model,
                messages=messages,
                temperature=0.5
            )
            return {"response": response.choices[0].message.content}

    except Exception as e:
        write_to_log(f"Error calling LLM: {e}")
        return {}


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

async def analyze_task_requirements(task_description: str, task_name: str = "") -> TaskRequirements:
    """
    Analyze task description to extract knowledge requirements using LLM.

    This function uses an LLM to intelligently parse the task description and identify:
    - Required tags (technologies, concepts, patterns)
    - Frameworks mentioned or implied
    - Programming language
    - Task complexity
    - Types of knowledge that would be helpful

    Args:
        task_description: The full description of the task
        task_name: Optional task name for additional context

    Returns:
        TaskRequirements object with extracted information
    """
    system_prompt = """You are an expert at analyzing software development tasks and identifying knowledge requirements.

Your job is to analyze a task description and extract:
1. **tags**: List of specific technologies, concepts, patterns, or topics mentioned (e.g., ["fastapi", "authentication", "jwt", "async"])
2. **frameworks**: List of frameworks mentioned (e.g., ["fastapi", "django", "react"])
3. **language**: Primary programming language (e.g., "python", "javascript", "typescript")
4. **complexity**: Estimate complexity as "simple", "medium", or "complex"
5. **suggested_knowledge_types**: Types of documentation that would help (e.g., ["documentation", "tutorial", "example"])
6. **confidence**: Your confidence in this analysis (0.0 to 1.0)

Return a JSON object with these exact keys. Be specific with tags but don't over-extract.
For tags, focus on: frameworks, libraries, patterns, technologies, concepts, and methodologies.
"""

    user_prompt = f"""Task Name: {task_name}

Task Description:
{task_description}

Analyze this task and extract the knowledge requirements in JSON format."""

    try:
        result = await call_llm(system_prompt, user_prompt, response_format="json_object")

        return TaskRequirements(
            tags=result.get("tags", []),
            frameworks=result.get("frameworks", []),
            language=result.get("language"),
            complexity=result.get("complexity", "medium"),
            suggested_knowledge_types=result.get("suggested_knowledge_types", ["documentation"]),
            confidence=result.get("confidence", 0.7)
        )
    except Exception as e:
        write_to_log(f"Error analyzing task requirements: {e}")
        # Return default requirements on error
        return TaskRequirements(
            tags=[],
            frameworks=[],
            language=None,
            complexity="medium",
            suggested_knowledge_types=["documentation"],
            confidence=0.0
        )


async def search_relevant_knowledge(
    task_embedding: List[float],
    requirements: TaskRequirements,
    match_count: int = 15,
    match_threshold: float = 0.7
) -> List[KnowledgeChunk]:
    """
    Search for relevant knowledge using vector similarity and filters.

    Uses the match_knowledge_advanced RPC function to combine:
    - Vector similarity (semantic matching)
    - Tag filtering (explicit matching)
    - Framework filtering (structured matching)
    - Knowledge type preferences
    - Language filtering

    Args:
        task_embedding: Vector embedding of the task description
        requirements: TaskRequirements with extracted tags, frameworks, etc.
        match_count: Maximum number of chunks to return
        match_threshold: Minimum similarity score (0-1)

    Returns:
        List of KnowledgeChunk objects sorted by relevance
    """
    try:
        # Call the match_knowledge_advanced RPC function
        result = supabase.rpc(
            'match_knowledge_advanced',
            {
                'query_embedding': task_embedding,
                'match_count': match_count,
                'match_threshold': match_threshold,
                'required_tags': requirements.tags,
                'required_frameworks': requirements.frameworks,
                'knowledge_types': requirements.suggested_knowledge_types,
                'language_filter': requirements.language
            }
        ).execute()

        if not result.data:
            write_to_log("No relevant knowledge found in search")
            return []

        # Convert to KnowledgeChunk objects
        chunks = []
        for item in result.data:
            chunk = KnowledgeChunk(
                id=item['id'],
                url=item['url'],
                chunk_number=item['chunk_number'],
                title=item['title'],
                summary=item['summary'],
                content=item['content'],
                tags=item.get('tags', []),
                knowledge_type=item.get('knowledge_type', 'documentation'),
                framework=item.get('framework'),
                language=item.get('language'),
                similarity=item['similarity'],
                metadata=item.get('metadata', {})
            )
            chunks.append(chunk)

        write_to_log(f"Found {len(chunks)} relevant knowledge chunks")
        return chunks

    except Exception as e:
        write_to_log(f"Error searching knowledge: {e}")
        return []


async def calculate_relevance_score(
    task_description: str,
    task_requirements: TaskRequirements,
    chunk: KnowledgeChunk
) -> float:
    """
    Calculate a detailed relevance score for a knowledge chunk.

    Combines multiple factors:
    - Vector similarity (base score)
    - Tag overlap
    - Framework match
    - Knowledge type appropriateness
    - Content quality indicators

    Args:
        task_description: Full task description
        task_requirements: Extracted requirements
        chunk: Knowledge chunk to score

    Returns:
        Relevance score between 0 and 1
    """
    try:
        # Start with vector similarity as base
        score = chunk.similarity

        # Boost for tag overlap
        if task_requirements.tags and chunk.tags:
            task_tags_set = set(tag.lower() for tag in task_requirements.tags)
            chunk_tags_set = set(tag.lower() for tag in chunk.tags)
            overlap = len(task_tags_set & chunk_tags_set)
            if overlap > 0:
                # Add up to 0.15 for tag overlap
                score += min(0.15, overlap * 0.05)

        # Boost for framework match
        if task_requirements.frameworks and chunk.framework:
            frameworks_lower = [f.lower() for f in task_requirements.frameworks]
            if chunk.framework.lower() in frameworks_lower:
                score += 0.1

        # Boost for language match
        if task_requirements.language and chunk.language:
            if task_requirements.language.lower() == chunk.language.lower():
                score += 0.05

        # Boost for preferred knowledge types
        if chunk.knowledge_type in task_requirements.suggested_knowledge_types:
            score += 0.05

        # Cap at 1.0
        return min(1.0, score)

    except Exception as e:
        write_to_log(f"Error calculating relevance score: {e}")
        return chunk.similarity  # Fall back to just similarity


def deduplicate_chunks(chunks: List[KnowledgeChunk], max_chunks: int = 15) -> List[KnowledgeChunk]:
    """
    Deduplicate similar chunks to avoid linking redundant information.

    If multiple chunks are from the same URL/section, keep only the most relevant one.
    Also limits the total number of chunks to avoid overwhelming the task.

    Args:
        chunks: List of knowledge chunks sorted by relevance
        max_chunks: Maximum number of chunks to keep

    Returns:
        Deduplicated list of chunks
    """
    seen_urls = {}
    deduplicated = []

    for chunk in chunks:
        # Create a key for this URL (base URL without chunk number)
        url_key = chunk.url

        # If we haven't seen this URL yet, or this chunk is more relevant
        if url_key not in seen_urls:
            seen_urls[url_key] = chunk
            deduplicated.append(chunk)
        else:
            # Keep the more relevant chunk
            existing = seen_urls[url_key]
            if chunk.similarity > existing.similarity:
                # Replace with more relevant chunk
                deduplicated.remove(existing)
                deduplicated.append(chunk)
                seen_urls[url_key] = chunk

        # Stop if we've reached max chunks
        if len(deduplicated) >= max_chunks:
            break

    return deduplicated


def determine_link_type(relevance_score: float, has_tag_match: bool) -> LinkType:
    """
    Determine the type of link based on relevance and matches.

    Logic:
    - required: High relevance (>0.8) AND has matching tags
    - suggested: Medium-high relevance (0.7-0.8) OR high relevance without tag match
    - reference: Lower relevance but still above threshold

    Args:
        relevance_score: Calculated relevance score (0-1)
        has_tag_match: Whether any tags match between task and chunk

    Returns:
        LinkType enum value
    """
    if relevance_score > 0.8 and has_tag_match:
        return LinkType.REQUIRED
    elif relevance_score >= 0.7:
        return LinkType.SUGGESTED
    else:
        return LinkType.REFERENCE


async def link_knowledge_to_task(
    task_id: str,
    knowledge_id: int,
    relevance_score: float,
    link_type: LinkType,
    link_reason: str = ""
) -> bool:
    """
    Create or update a link between a task and a knowledge chunk.

    Uses an upsert pattern to avoid duplicate links.

    Args:
        task_id: UUID of the task
        knowledge_id: ID of the knowledge chunk (site_pages.id)
        relevance_score: Calculated relevance (0-1)
        link_type: Type of link (required, suggested, reference)
        link_reason: Optional explanation for why this was linked

    Returns:
        True if successful, False otherwise
    """
    try:
        link_data = {
            "task_id": task_id,
            "knowledge_id": knowledge_id,
            "relevance_score": relevance_score,
            "link_type": link_type.value,
            "linked_by": "auto",
            "link_reason": link_reason or "Automatically linked by Knowledge Linker Agent"
        }

        # Use upsert to avoid duplicates
        result = supabase.table("task_knowledge_links").upsert(
            link_data,
            on_conflict="task_id,knowledge_id"
        ).execute()

        return True

    except Exception as e:
        write_to_log(f"Error linking knowledge {knowledge_id} to task {task_id}: {e}")
        return False


async def calculate_coverage_score(
    required_tags: List[str],
    required_frameworks: List[str],
    found_chunks: List[KnowledgeChunk]
) -> Tuple[float, List[str]]:
    """
    Calculate how well the found knowledge covers the task requirements.

    Coverage is based on:
    - What percentage of required tags have at least 2 supporting chunks
    - Whether all required frameworks are covered
    - Overall quality of matches

    Args:
        required_tags: List of tags extracted from task
        required_frameworks: List of frameworks extracted from task
        found_chunks: List of knowledge chunks that were found

    Returns:
        Tuple of (coverage_score, missing_knowledge)
        - coverage_score: Float between 0 and 1
        - missing_knowledge: List of tags/frameworks that lack coverage
    """
    if not required_tags and not required_frameworks:
        # No specific requirements, so any knowledge is bonus
        return 1.0 if found_chunks else 0.0, []

    # Count chunks per tag
    tag_coverage = {}
    for tag in required_tags:
        tag_lower = tag.lower()
        tag_coverage[tag] = 0
        for chunk in found_chunks:
            chunk_tags_lower = [t.lower() for t in chunk.tags]
            if tag_lower in chunk_tags_lower or tag_lower in chunk.content.lower()[:500]:
                tag_coverage[tag] += 1

    # Count chunks per framework
    framework_coverage = {}
    for framework in required_frameworks:
        framework_lower = framework.lower()
        framework_coverage[framework] = 0
        for chunk in found_chunks:
            if chunk.framework and chunk.framework.lower() == framework_lower:
                framework_coverage[framework] += 1

    # Calculate coverage
    total_requirements = len(required_tags) + len(required_frameworks)
    covered_requirements = 0
    missing = []

    # Check tag coverage (need at least 2 chunks per tag for good coverage)
    for tag, count in tag_coverage.items():
        if count >= 2:
            covered_requirements += 1
        elif count == 1:
            covered_requirements += 0.5  # Partial credit
        else:
            missing.append(tag)

    # Check framework coverage
    for framework, count in framework_coverage.items():
        if count >= 1:
            covered_requirements += 1
        else:
            missing.append(framework)

    # Calculate score
    if total_requirements == 0:
        coverage = 1.0 if found_chunks else 0.0
    else:
        coverage = covered_requirements / total_requirements

    return coverage, missing


async def suggest_crawl_sources(missing_knowledge: List[str], task_requirements: TaskRequirements) -> List[str]:
    """
    Suggest documentation sources to crawl based on missing knowledge.

    Uses LLM to suggest relevant documentation URLs that could fill knowledge gaps.

    Args:
        missing_knowledge: List of tags/frameworks that lack coverage
        task_requirements: Full task requirements

    Returns:
        List of suggested URLs to crawl
    """
    if not missing_knowledge:
        return []

    system_prompt = """You are an expert at finding documentation sources for software development.
Given a list of missing knowledge topics, suggest official documentation URLs that should be crawled.

Return a JSON object with a "sources" key containing a list of objects with:
- "url": The documentation URL
- "reason": Why this source would be helpful
- "priority": "high", "medium", or "low"

Focus on official documentation, popular tutorials, and authoritative sources.
Limit to 5 most important sources."""

    user_prompt = f"""Missing knowledge topics: {', '.join(missing_knowledge)}

Task context:
- Language: {task_requirements.language}
- Frameworks: {', '.join(task_requirements.frameworks)}
- Complexity: {task_requirements.complexity}

Suggest documentation sources to crawl."""

    try:
        result = await call_llm(system_prompt, user_prompt, response_format="json_object")
        sources = result.get("sources", [])

        # Format as URLs with priority
        suggestions = []
        for source in sources:
            url = source.get("url", "")
            priority = source.get("priority", "medium")
            reason = source.get("reason", "")
            suggestions.append(f"[{priority.upper()}] {url} - {reason}")

        return suggestions

    except Exception as e:
        write_to_log(f"Error suggesting crawl sources: {e}")
        return []


async def update_task_metadata(
    task_id: str,
    attached_knowledge_ids: List[int],
    coverage_score: float,
    requirements: TaskRequirements
) -> bool:
    """
    Update the task's knowledge-related metadata.

    Updates:
    - attached_knowledge_ids: Array of linked knowledge chunk IDs
    - knowledge_coverage_score: Overall coverage score
    - required_knowledge_tags: Extracted tags
    - required_frameworks: Extracted frameworks

    Args:
        task_id: UUID of the task
        attached_knowledge_ids: List of knowledge chunk IDs
        coverage_score: Coverage score (0-1)
        requirements: Extracted task requirements

    Returns:
        True if successful, False otherwise
    """
    try:
        update_data = {
            "attached_knowledge_ids": attached_knowledge_ids,
            "knowledge_coverage_score": coverage_score,
            "required_knowledge_tags": requirements.tags,
            "required_frameworks": requirements.frameworks,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        result = supabase.table("tasks").update(update_data).eq("id", task_id).execute()

        return True

    except Exception as e:
        write_to_log(f"Error updating task metadata: {e}")
        return False


# ============================================================================
# MAIN ORCHESTRATION FUNCTION
# ============================================================================

async def auto_link_task_knowledge(
    task_id: str,
    task_name: str = "",
    task_description: str = "",
    force_refresh: bool = False
) -> LinkResult:
    """
    Main orchestration function to automatically link knowledge to a task.

    This function coordinates the entire knowledge linking process:
    1. Fetches task details from database if not provided
    2. Analyzes task to extract requirements
    3. Searches for relevant knowledge
    4. Calculates relevance scores
    5. Deduplicates and prioritizes chunks
    6. Creates/updates knowledge links
    7. Calculates coverage score
    8. Identifies missing knowledge
    9. Suggests crawl sources if needed
    10. Updates task metadata

    Args:
        task_id: UUID of the task to link knowledge to
        task_name: Optional task name (fetched from DB if not provided)
        task_description: Optional task description (fetched from DB if not provided)
        force_refresh: If True, re-link even if already linked

    Returns:
        LinkResult with details about the linking process
    """
    write_to_log(f"Starting knowledge linking for task {task_id}")

    try:
        # Step 1: Fetch task details if not provided
        if not task_description:
            result = supabase.table("tasks").select("name, description").eq("id", task_id).execute()
            if not result.data:
                write_to_log(f"Task {task_id} not found in database")
                return LinkResult(
                    task_id=task_id,
                    total_chunks_found=0,
                    links_created=0,
                    links_updated=0,
                    coverage_score=0.0,
                    missing_knowledge=[],
                    suggested_crawl_sources=[]
                )

            task_data = result.data[0]
            task_name = task_data.get("name", "")
            task_description = task_data.get("description", "")

        if not task_description:
            write_to_log(f"Task {task_id} has no description to analyze")
            return LinkResult(
                task_id=task_id,
                total_chunks_found=0,
                links_created=0,
                links_updated=0,
                coverage_score=0.0,
                missing_knowledge=["No task description provided"],
                suggested_crawl_sources=[]
            )

        # Step 2: Analyze task requirements
        write_to_log(f"Analyzing requirements for task: {task_name}")
        requirements = await analyze_task_requirements(task_description, task_name)
        write_to_log(f"Extracted requirements: tags={requirements.tags}, frameworks={requirements.frameworks}, "
                    f"language={requirements.language}, complexity={requirements.complexity}")

        # Step 3: Create task embedding
        write_to_log("Creating task embedding...")
        task_embedding = await get_embedding(f"{task_name}\n\n{task_description}")

        # Step 4: Search for relevant knowledge
        write_to_log("Searching for relevant knowledge...")
        chunks = await search_relevant_knowledge(
            task_embedding=task_embedding,
            requirements=requirements,
            match_count=20,  # Get more initially, will deduplicate
            match_threshold=0.6  # Lower threshold, we'll refine with relevance scoring
        )

        if not chunks:
            write_to_log("No relevant knowledge found")
            # Still calculate coverage to identify missing knowledge
            coverage, missing = await calculate_coverage_score(
                requirements.tags,
                requirements.frameworks,
                []
            )

            suggested_sources = await suggest_crawl_sources(missing, requirements) if coverage < 0.4 else []

            return LinkResult(
                task_id=task_id,
                total_chunks_found=0,
                links_created=0,
                links_updated=0,
                coverage_score=coverage,
                missing_knowledge=missing,
                suggested_crawl_sources=suggested_sources
            )

        # Step 5: Calculate relevance scores
        write_to_log("Calculating relevance scores...")
        chunks_with_scores = []
        for chunk in chunks:
            relevance = await calculate_relevance_score(task_description, requirements, chunk)
            # Store relevance in the chunk for sorting
            chunk.similarity = relevance  # Override similarity with relevance
            chunks_with_scores.append(chunk)

        # Sort by relevance
        chunks_with_scores.sort(key=lambda c: c.similarity, reverse=True)

        # Step 6: Deduplicate
        write_to_log("Deduplicating chunks...")
        final_chunks = deduplicate_chunks(chunks_with_scores, max_chunks=15)
        write_to_log(f"Selected {len(final_chunks)} unique chunks after deduplication")

        # Step 7: Create/update links
        write_to_log("Creating knowledge links...")
        links_created = 0
        links_updated = 0

        for chunk in final_chunks:
            # Determine link type based on relevance and tag match
            has_tag_match = bool(
                set(tag.lower() for tag in requirements.tags) &
                set(tag.lower() for tag in chunk.tags)
            )
            link_type = determine_link_type(chunk.similarity, has_tag_match)

            # Create link
            success = await link_knowledge_to_task(
                task_id=task_id,
                knowledge_id=chunk.id,
                relevance_score=chunk.similarity,
                link_type=link_type,
                link_reason=f"Matched on {', '.join(chunk.tags[:3])} with {chunk.similarity:.2f} relevance"
            )

            if success:
                links_created += 1

        # Step 8: Calculate coverage
        write_to_log("Calculating knowledge coverage...")
        coverage, missing = await calculate_coverage_score(
            requirements.tags,
            requirements.frameworks,
            final_chunks
        )
        write_to_log(f"Coverage score: {coverage:.2f}, Missing: {missing}")

        # Step 9: Suggest crawl sources if coverage is low
        suggested_sources = []
        if coverage < 0.4 and missing:
            write_to_log("Coverage is low, suggesting crawl sources...")
            suggested_sources = await suggest_crawl_sources(missing, requirements)

        # Step 10: Update task metadata
        write_to_log("Updating task metadata...")
        knowledge_ids = [chunk.id for chunk in final_chunks]
        await update_task_metadata(task_id, knowledge_ids, coverage, requirements)

        # Create result
        result = LinkResult(
            task_id=task_id,
            total_chunks_found=len(chunks),
            links_created=links_created,
            links_updated=links_updated,
            coverage_score=coverage,
            missing_knowledge=missing,
            suggested_crawl_sources=suggested_sources
        )

        write_to_log(f"Knowledge linking complete for task {task_id}: "
                    f"{links_created} links created, coverage={coverage:.2f}")

        return result

    except Exception as e:
        write_to_log(f"Error in auto_link_task_knowledge: {e}")
        import traceback
        write_to_log(traceback.format_exc())

        return LinkResult(
            task_id=task_id,
            total_chunks_found=0,
            links_created=0,
            links_updated=0,
            coverage_score=0.0,
            missing_knowledge=[f"Error: {str(e)}"],
            suggested_crawl_sources=[]
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def refresh_task_knowledge(task_id: str) -> LinkResult:
    """
    Refresh knowledge links for a task.

    This removes old links and re-links with current knowledge base.
    Use this when:
    - Task description has changed significantly
    - New knowledge has been added to the database
    - User explicitly requests a refresh

    Args:
        task_id: UUID of the task

    Returns:
        LinkResult with details about the refresh
    """
    try:
        # Remove existing links
        write_to_log(f"Refreshing knowledge for task {task_id}")
        supabase.table("task_knowledge_links").delete().eq("task_id", task_id).execute()

        # Re-link
        return await auto_link_task_knowledge(task_id, force_refresh=True)

    except Exception as e:
        write_to_log(f"Error refreshing task knowledge: {e}")
        return LinkResult(
            task_id=task_id,
            total_chunks_found=0,
            links_created=0,
            links_updated=0,
            coverage_score=0.0,
            missing_knowledge=[f"Error: {str(e)}"],
            suggested_crawl_sources=[]
        )


async def batch_link_tasks(task_ids: List[str]) -> Dict[str, LinkResult]:
    """
    Link knowledge for multiple tasks in parallel.

    Args:
        task_ids: List of task UUIDs

    Returns:
        Dictionary mapping task_id to LinkResult
    """
    write_to_log(f"Batch linking knowledge for {len(task_ids)} tasks")

    # Process tasks in parallel
    tasks = [auto_link_task_knowledge(task_id) for task_id in task_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Build result dictionary
    result_dict = {}
    for task_id, result in zip(task_ids, results):
        if isinstance(result, Exception):
            write_to_log(f"Error linking task {task_id}: {result}")
            result_dict[task_id] = LinkResult(
                task_id=task_id,
                total_chunks_found=0,
                links_created=0,
                links_updated=0,
                coverage_score=0.0,
                missing_knowledge=[f"Error: {str(result)}"],
                suggested_crawl_sources=[]
            )
        else:
            result_dict[task_id] = result

    return result_dict


async def get_task_linked_knowledge(task_id: str) -> List[KnowledgeChunk]:
    """
    Retrieve all knowledge currently linked to a task.

    Args:
        task_id: UUID of the task

    Returns:
        List of KnowledgeChunk objects
    """
    try:
        # Use the get_task_knowledge RPC function
        result = supabase.rpc('get_task_knowledge', {'task_id_param': task_id}).execute()

        if not result.data:
            return []

        # Convert to KnowledgeChunk objects
        chunks = []
        for item in result.data:
            chunk = KnowledgeChunk(
                id=item['id'],
                url=item['url'],
                chunk_number=0,  # Not returned by this function
                title=item['title'],
                summary=item['summary'],
                content=item['content'],
                tags=item.get('tags', []),
                knowledge_type=item.get('knowledge_type', 'documentation'),
                framework=item.get('framework'),
                language=None,
                similarity=item.get('relevance_score', 0.0),
                metadata={'link_type': item.get('link_type', 'suggested')}
            )
            chunks.append(chunk)

        return chunks

    except Exception as e:
        write_to_log(f"Error getting linked knowledge: {e}")
        return []


# ============================================================================
# MAIN ENTRY POINT (for testing)
# ============================================================================

async def main():
    """Main function for testing the knowledge linker."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python knowledge_linker.py <task_id>")
        print("Or: python knowledge_linker.py test")
        return

    if sys.argv[1] == "test":
        # Create a test task for demonstration
        print("Creating test task...")
        test_task = {
            "name": "Build FastAPI authentication system",
            "description": """Create a complete authentication system using FastAPI with the following features:
- JWT token-based authentication
- User registration and login endpoints
- Password hashing with bcrypt
- Protected routes using dependencies
- Refresh token mechanism
- Email verification

The system should be async and follow FastAPI best practices.""",
            "status": "pending",
            "priority": 2
        }

        result = supabase.table("tasks").insert(test_task).execute()
        if result.data:
            task_id = result.data[0]['id']
            print(f"Created test task with ID: {task_id}")
        else:
            print("Failed to create test task")
            return
    else:
        task_id = sys.argv[1]

    # Link knowledge
    print(f"\nLinking knowledge for task {task_id}...")
    result = await auto_link_task_knowledge(task_id)

    # Print results
    print("\n" + "="*80)
    print("KNOWLEDGE LINKING RESULTS")
    print("="*80)
    print(f"Task ID: {result.task_id}")
    print(f"Total chunks found: {result.total_chunks_found}")
    print(f"Links created: {result.links_created}")
    print(f"Coverage score: {result.coverage_score:.2%}")

    if result.missing_knowledge:
        print(f"\nMissing knowledge:")
        for item in result.missing_knowledge:
            print(f"  - {item}")

    if result.suggested_crawl_sources:
        print(f"\nSuggested documentation sources to crawl:")
        for source in result.suggested_crawl_sources:
            print(f"  - {source}")

    print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())
