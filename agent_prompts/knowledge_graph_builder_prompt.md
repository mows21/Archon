# Knowledge Graph Builder Agent - Prompt for Archon

## Agent Overview
The Knowledge Graph Builder Agent analyzes knowledge chunks to discover and create relationships between them, building a traversable knowledge graph. It identifies semantic relationships (depends_on, related_to, example_of, prerequisite_for), calculates confidence scores, creates knowledge_relationships entries, and enables graph-based knowledge discovery and visualization.

## Use Case
As the knowledge base grows, this agent:
- Analyzes pairs of knowledge chunks for relationships
- Identifies relationship types using LLM-based analysis
- Calculates confidence scores for each relationship
- Creates entries in `knowledge_relationships` table
- Builds a traversable graph structure for:
  - Learning path recommendations (prerequisites)
  - Related knowledge discovery
  - Knowledge gap identification
  - Visual knowledge map generation
- Suggests related knowledge when linking to tasks
- Enables graph-based queries (find all knowledge about X and its dependencies)

## Required Capabilities

### Input
```python
{
    "operation": "build_full_graph",  # build_full_graph, update_incremental, analyze_chunk
    "params": {
        "knowledge_ids": [],  # Empty = all knowledge, or specific IDs
        "relationship_types": [
            "depends_on",      # A depends on understanding B first
            "related_to",      # A and B are related concepts
            "example_of",      # A is an example/implementation of B
            "prerequisite_for" # A is prerequisite for understanding B
        ],
        "min_confidence_score": 0.7,  # Only create relationships with >= 70% confidence
        "max_relationships_per_chunk": 10,  # Limit connections
        "use_embeddings": true,  # Use vector similarity as first filter
        "embedding_threshold": 0.75,  # Min cosine similarity
        "batch_size": 50,  # Process N chunks at a time
        "analyze_bidirectional": true,  # Check A→B and B→A
        "incremental_mode": false  # Only analyze new knowledge
    },
    "filters": {
        "tags": ["fastapi", "authentication"],  # Limit to specific tags
        "frameworks": ["fastapi"],
        "knowledge_types": ["documentation", "example"],
        "min_chunk_length": 100  # Skip tiny chunks
    }
}
```

### Processing
The agent should perform these steps:

**Step 1: Knowledge Retrieval**
- Fetch knowledge chunks from `site_pages` based on filters
- If incremental_mode: Only get chunks added/updated since last run
- Load existing relationships from `knowledge_relationships`
- Build in-memory graph of existing relationships

**Step 2: Candidate Pair Generation**
- **Similarity-Based Filtering** (if use_embeddings = true):
  - For each chunk A, find chunks with cosine similarity >= embedding_threshold
  - This reduces comparisons from O(n²) to O(n × k) where k ≈ 20-50
- **Tag-Based Filtering**:
  - Only compare chunks with overlapping tags (at least 1 common tag)
- **Framework-Based Filtering**:
  - Prioritize chunks with same framework
- Generate candidate pairs for relationship analysis

**Step 3: Relationship Detection**
For each candidate pair (A, B), use LLM to detect relationships:

```python
DETECTION_PROMPT = """
Analyze the relationship between these two knowledge chunks:

CHUNK A:
Title: {chunk_a_title}
Tags: {chunk_a_tags}
Framework: {chunk_a_framework}
Content: {chunk_a_content}

CHUNK B:
Title: {chunk_b_title}
Tags: {chunk_b_tags}
Framework: {chunk_b_framework}
Content: {chunk_b_content}

Determine if there is a relationship. Return JSON:
{
    "has_relationship": true/false,
    "relationship_type": "depends_on" | "related_to" | "example_of" | "prerequisite_for",
    "confidence_score": 0.0-1.0,
    "explanation": "Brief explanation of the relationship",
    "bidirectional": true/false  # If relationship goes both ways
}

RELATIONSHIP TYPES:
- depends_on: Chunk A depends on understanding Chunk B first (A cannot be understood without B)
- related_to: A and B cover related concepts (symmetric relationship)
- example_of: A is a concrete example/implementation of concept B
- prerequisite_for: A is a prerequisite for understanding B (inverse of depends_on)
```

**Step 4: Confidence Scoring**
Calculate final confidence score combining:
- LLM confidence score (0-1)
- Embedding similarity score (0-1)
- Tag overlap score: overlap_count / total_unique_tags
- Framework match bonus: +0.1 if same framework

```python
final_confidence = (
    llm_confidence * 0.6 +
    embedding_similarity * 0.2 +
    tag_overlap_score * 0.15 +
    framework_bonus * 0.05
)
```

**Step 5: Relationship Creation**
- Filter relationships by min_confidence_score
- Limit to max_relationships_per_chunk per chunk
- Insert into `knowledge_relationships` table:
  ```python
  {
      "source_knowledge_id": chunk_a_id,
      "target_knowledge_id": chunk_b_id,
      "relationship_type": "depends_on",
      "confidence_score": 0.85,
      "created_by": "graph_builder",
      "metadata": {
          "embedding_similarity": 0.82,
          "tag_overlap": 0.67,
          "llm_explanation": "FastAPI auth depends on understanding JWT",
          "detected_at": "2025-11-15T10:00:00Z"
      }
  }
  ```

**Step 6: Bidirectional Relationship Handling**
- For "related_to" relationships, create symmetric links:
  - If A related_to B, also create B related_to A
- For "depends_on" / "prerequisite_for":
  - These are inverse relationships
  - If A depends_on B, also create B prerequisite_for A

**Step 7: Graph Validation**
- Check for cycles in "depends_on" relationships (should be DAG)
- Warn if detected: "Circular dependency in knowledge graph"
- Calculate graph metrics:
  - Number of nodes (knowledge chunks)
  - Number of edges (relationships)
  - Average degree (connections per chunk)
  - Connected components
  - Longest dependency chain

**Step 8: Graph Enrichment**
- Identify central/hub knowledge:
  - High in-degree: Many chunks depend on this
  - High out-degree: This depends on many concepts
- Identify knowledge clusters (related groups)
- Calculate PageRank scores for knowledge importance

**Step 9: Learning Path Generation**
- For a given target knowledge chunk:
  - Use graph traversal to find all prerequisites
  - Order by dependency depth (BFS/topological sort)
  - Generate recommended learning sequence

### Output
```python
{
    "operation_type": "build_full_graph",
    "processing_metadata": {
        "chunks_analyzed": 250,
        "pairs_evaluated": 1850,
        "relationships_detected": 420,
        "relationships_created": 380,  # After filtering
        "execution_time_seconds": 145.3,
        "llm_calls_made": 1850,
        "batches_processed": 5
    },
    "graph_statistics": {
        "total_nodes": 250,
        "total_edges": 380,
        "average_degree": 3.04,
        "density": 0.012,  # edges / possible_edges
        "connected_components": 12,
        "largest_component_size": 180,
        "longest_dependency_chain": 5,
        "cycles_detected": 0
    },
    "relationships_by_type": {
        "depends_on": 120,
        "related_to": 180,
        "example_of": 50,
        "prerequisite_for": 30
    },
    "top_hub_knowledge": [
        {
            "knowledge_id": 42,
            "title": "FastAPI Fundamentals",
            "in_degree": 15,  # 15 chunks depend on this
            "out_degree": 2,
            "pagerank_score": 0.045,
            "cluster": "fastapi-core"
        },
        {
            "knowledge_id": 78,
            "title": "JWT Token Structure",
            "in_degree": 12,
            "out_degree": 3,
            "pagerank_score": 0.038,
            "cluster": "authentication"
        }
    ],
    "knowledge_clusters": [
        {
            "cluster_id": "fastapi-core",
            "size": 25,
            "central_knowledge_ids": [42, 51, 63],
            "primary_tags": ["fastapi", "api", "web-framework"],
            "description": "Core FastAPI concepts and patterns"
        },
        {
            "cluster_id": "authentication",
            "size": 18,
            "central_knowledge_ids": [78, 85, 92],
            "primary_tags": ["authentication", "jwt", "security"],
            "description": "Authentication and security implementation"
        }
    ],
    "sample_learning_paths": [
        {
            "target_knowledge_id": 150,
            "target_title": "Advanced FastAPI Authentication",
            "path": [
                {"step": 1, "knowledge_id": 10, "title": "Python Basics"},
                {"step": 2, "knowledge_id": 42, "title": "FastAPI Fundamentals"},
                {"step": 3, "knowledge_id": 78, "title": "JWT Token Structure"},
                {"step": 4, "knowledge_id": 120, "title": "OAuth2 Flow"},
                {"step": 5, "knowledge_id": 150, "title": "Advanced FastAPI Authentication"}
            ],
            "total_steps": 5,
            "estimated_reading_time_minutes": 45
        }
    ],
    "warnings": [
        "Knowledge chunk 234 has no relationships (orphan node)",
        "High confidence relationship density might indicate over-connection"
    ],
    "recommendations": [
        "Add more 'example_of' relationships for FastAPI concepts",
        "Create beginner documentation for orphaned knowledge chunks",
        "Review cluster 'authentication' for missing prerequisite links"
    ]
}
```

## Tools Required

### 1. Supabase Client
- **Purpose**: Read knowledge, create relationships
- **Tables Used**:
  - `site_pages` (SELECT for knowledge chunks)
  - `knowledge_relationships` (SELECT, INSERT, UPDATE)
- **Operations**:
  - Batch fetch knowledge chunks
  - Check existing relationships
  - Bulk insert relationships

### 2. OpenAI LLM Client
- **Purpose**: Analyze chunk pairs for relationships
- **Models**: `gpt-4o-mini` (fast, cost-effective)
- **Use Cases**:
  - Relationship detection
  - Confidence scoring
  - Explanation generation
- **Optimization**: Batch multiple pair analyses in single call

### 3. Vector Operations
- **Purpose**: Calculate cosine similarity between embeddings
- **Library**: NumPy, scikit-learn
- **Use Cases**:
  - Filter candidate pairs by similarity
  - Calculate embedding-based confidence

### 4. Graph Analysis Library
- **Purpose**: Graph algorithms and metrics
- **Options**:
  - NetworkX (recommended): Full-featured
  - graph-tool: High performance
  - Custom implementation: Lighter
- **Algorithms Needed**:
  - Cycle detection (detect circular dependencies)
  - Topological sort (learning path ordering)
  - PageRank (knowledge importance)
  - Connected components
  - Shortest path (for learning paths)

### 5. Clustering Algorithm
- **Purpose**: Identify knowledge clusters
- **Algorithms**:
  - Community detection (Louvain algorithm)
  - K-means on embeddings
  - Hierarchical clustering

## Integration Points

### Input Integration
- Called after knowledge acquisition (universal_crawler completes)
- Can be triggered manually from UI
- Scheduled job: Run nightly for incremental updates
- Called from `KnowledgeManager.build_knowledge_graph()`

### Output Integration
- Populates `knowledge_relationships` table
- Used by knowledge linker to suggest better matches
- Powers UI knowledge graph visualization
- Enables learning path recommendations

### Knowledge Integration
- Enhances knowledge discovery
- Improves task-knowledge linking quality
- Identifies knowledge gaps (orphaned nodes)
- Supports prerequisite checking before task execution

### Workflow Integration
- LangGraph node: "build_knowledge_graph"
- Can run as background job (async)
- Triggered after crawler ingests new knowledge
- Feeds into visualization and recommendation systems

## Example Usage

```python
from archon.knowledge_graph_builder import KnowledgeGraphBuilder

# Initialize
graph_builder = KnowledgeGraphBuilder(supabase, llm_client)

# Build full graph
result = await graph_builder.build_graph(
    operation="build_full_graph",
    min_confidence_score=0.7,
    use_embeddings=True,
    embedding_threshold=0.75
)

# View statistics
print(f"Analyzed {result['chunks_analyzed']} chunks")
print(f"Created {result['relationships_created']} relationships")
print(f"Graph density: {result['graph_statistics']['density']:.3f}")

# Get learning path
path = await graph_builder.get_learning_path(
    target_knowledge_id=150,
    max_depth=10
)
print(f"Learning path: {[step['title'] for step in path['path']]}")

# Find related knowledge
related = await graph_builder.find_related_knowledge(
    knowledge_id=42,
    relationship_types=["related_to", "example_of"],
    max_depth=2
)
print(f"Found {len(related)} related chunks")

# Get knowledge clusters
clusters = result['knowledge_clusters']
for cluster in clusters:
    print(f"Cluster '{cluster['cluster_id']}': {cluster['size']} chunks")
```

## Test Cases

### Test Case 1: Build Graph from Scratch
**Input:**
- 100 knowledge chunks
- Mix of documentation, examples, tutorials
- Tags: fastapi, authentication, jwt, python

**Expected Output:**
- 80-120 relationships created
- All relationship types represented
- No cycles in "depends_on" relationships
- Graph density: 0.01-0.05
- Execution time: < 3 minutes

### Test Case 2: Incremental Update
**Input:**
- Existing graph with 200 chunks, 300 relationships
- Add 10 new chunks
- Run incremental update

**Expected Output:**
- Only 10 chunks analyzed
- 15-25 new relationships created
- Existing relationships unchanged
- Execution time: < 30 seconds

### Test Case 3: Cycle Detection
**Input:**
- Manually create: A depends_on B, B depends_on C, C depends_on A
- Run graph validation

**Expected Output:**
- Cycle detected: [A, B, C, A]
- Warning raised
- Suggestions to break cycle

### Test Case 4: Learning Path Generation
**Input:**
- Target: "Advanced FastAPI Authentication" (chunk 150)
- Graph with clear prerequisite chain

**Expected Output:**
- Path with 4-6 steps
- Ordered by dependency (beginner → advanced)
- Total estimated time calculated
- All steps connected via "prerequisite_for" or "depends_on"

### Test Case 5: Orphan Node Detection
**Input:**
- 50 chunks, 10 have no relationships

**Expected Output:**
- Warnings for 10 orphaned chunks
- Recommendations to add relationships or remove
- List of orphan IDs and titles

## Error Handling

### Error: No Knowledge Chunks Found
```python
{
    "error": "NoKnowledgeFoundError",
    "message": "No knowledge chunks found matching filters",
    "filters_applied": {"tags": ["nonexistent"]},
    "suggestion": "Check filters or add knowledge to database"
}
```

### Error: Circular Dependency Detected
```python
{
    "error": "CircularDependencyWarning",
    "warning_type": "warning",  # Non-fatal
    "message": "Circular dependency detected in knowledge graph",
    "cycles": [
        ["Chunk A", "Chunk B", "Chunk C", "Chunk A"]
    ],
    "suggestion": "Review and remove dependency from Chunk C to Chunk A"
}
```

### Error: LLM Rate Limit
```python
{
    "error": "RateLimitError",
    "message": "LLM API rate limit exceeded",
    "pairs_analyzed": 500,
    "pairs_remaining": 1000,
    "retry_after_seconds": 60,
    "suggestion": "Reduce batch_size or wait before retrying"
}
```

### Error: Graph Too Large
```python
{
    "error": "GraphSizeWarning",
    "warning_type": "warning",
    "message": "Knowledge graph very large - operations may be slow",
    "total_nodes": 5000,
    "total_edges": 25000,
    "suggestion": "Consider filtering by tags/framework or using incremental mode"
}
```

## Performance Requirements

### Response Time
- **Small graphs** (<100 chunks): < 2 minutes
- **Medium graphs** (100-500 chunks): < 10 minutes
- **Large graphs** (500-1000 chunks): < 30 minutes
- **Incremental updates**: < 1 minute per 10 new chunks

### Scalability
- Handle up to 5000 knowledge chunks
- Graph algorithms: O(V + E) or better
- Use embedding similarity to reduce pair comparisons
- Batch LLM calls (analyze multiple pairs per call)
- Support parallel processing

### Accuracy
- Relationship detection precision: >85%
- Confidence score accuracy: ±10%
- Cycle detection: 100% (must catch all cycles)
- Learning path correctness: >90%

### Resource Usage
- Memory: < 1GB for 1000 chunks
- Database queries: Batch operations (< 50 queries total)
- LLM calls: ~O(n × k) where k = avg similar chunks per node
- Optimize with caching and similarity filtering

---

## Full Prompt for Archon

**Copy the text below and paste into Archon's chat:**

```
Build me a Knowledge Graph Builder Agent for Archon's knowledge management system.

OVERVIEW:
Create a production-ready agent that analyzes knowledge chunks, detects relationships between them, builds a traversable knowledge graph, and enables graph-based knowledge discovery and learning path generation.

TECHNICAL REQUIREMENTS:

1. FILE LOCATION: /home/user/Archon/archon/knowledge_graph_builder.py

2. CORE FUNCTIONALITY:
   - Fetch knowledge chunks from site_pages table
   - Generate candidate pairs using embedding similarity and tag overlap
   - Analyze pairs using LLM to detect relationships:
     - depends_on: A requires understanding B first
     - related_to: A and B are related concepts
     - example_of: A is example/implementation of B
     - prerequisite_for: A is prerequisite for B
   - Calculate confidence scores (LLM + embeddings + tag overlap)
   - Create entries in knowledge_relationships table
   - Handle bidirectional relationships (related_to is symmetric)
   - Detect cycles in dependency graph (must be DAG)
   - Calculate graph metrics (density, degree, components)
   - Identify hub knowledge (high connectivity)
   - Cluster related knowledge
   - Generate learning paths (prerequisite ordering)
   - Support incremental updates (only analyze new chunks)

3. CLASS STRUCTURE:
```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set
import networkx as nx
import numpy as np

@dataclass
class GraphBuildParams:
    min_confidence_score: float = 0.7
    max_relationships_per_chunk: int = 10
    use_embeddings: bool = True
    embedding_threshold: float = 0.75
    batch_size: int = 50
    relationship_types: List[str] = None

@dataclass
class Relationship:
    source_id: int
    target_id: int
    relationship_type: str
    confidence_score: float
    explanation: str

class KnowledgeGraphBuilder:
    def __init__(self, supabase: Client, llm_client: AsyncOpenAI):
        self.supabase = supabase
        self.llm_client = llm_client
        self.graph = nx.DiGraph()

    async def build_graph(
        self,
        operation: str = "build_full_graph",
        params: Optional[GraphBuildParams] = None,
        filters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        # Main method to build/update graph

    async def _fetch_knowledge_chunks(
        self,
        filters: Optional[Dict] = None,
        incremental: bool = False
    ) -> List[Dict]:
        # Fetch from site_pages with optional filters

    async def _load_existing_relationships(self) -> List[Dict]:
        # Load from knowledge_relationships table

    def _generate_candidate_pairs(
        self,
        chunks: List[Dict],
        params: GraphBuildParams
    ) -> List[Tuple[Dict, Dict]]:
        # Use embedding similarity and tag overlap to filter pairs
        # Reduces O(n²) to O(n × k)

    def _calculate_embedding_similarity(
        self,
        emb1: List[float],
        emb2: List[float]
    ) -> float:
        # Cosine similarity

    def _calculate_tag_overlap(
        self,
        tags1: List[str],
        tags2: List[str]
    ) -> float:
        # Jaccard similarity or overlap percentage

    async def _detect_relationship(
        self,
        chunk_a: Dict,
        chunk_b: Dict
    ) -> Optional[Relationship]:
        # Use LLM to analyze relationship
        # Return None if no relationship

    async def _batch_detect_relationships(
        self,
        pairs: List[Tuple[Dict, Dict]],
        batch_size: int = 10
    ) -> List[Relationship]:
        # Analyze multiple pairs in parallel or single LLM call

    def _calculate_confidence_score(
        self,
        llm_confidence: float,
        embedding_similarity: float,
        tag_overlap: float,
        framework_match: bool
    ) -> float:
        # Weighted combination

    async def _create_relationships(
        self,
        relationships: List[Relationship]
    ) -> int:
        # Batch insert into knowledge_relationships table
        # Handle bidirectional relationships
        # Return count created

    def _build_networkx_graph(
        self,
        relationships: List[Dict]
    ) -> nx.DiGraph:
        # Create NetworkX graph from relationships

    def _detect_cycles(self, graph: nx.DiGraph) -> List[List[int]]:
        # Find all cycles in directed graph
        # Should be empty for "depends_on" relationships

    def _calculate_graph_metrics(
        self,
        graph: nx.DiGraph
    ) -> Dict[str, Any]:
        # Density, degree distribution, components, etc.

    def _identify_hub_knowledge(
        self,
        graph: nx.DiGraph,
        top_k: int = 10
    ) -> List[Dict]:
        # High in-degree and out-degree nodes
        # Calculate PageRank

    def _cluster_knowledge(
        self,
        graph: nx.DiGraph,
        chunks: List[Dict]
    ) -> List[Dict]:
        # Use community detection or embedding clustering

    async def get_learning_path(
        self,
        target_knowledge_id: int,
        max_depth: int = 10
    ) -> Dict[str, Any]:
        # Traverse graph to find all prerequisites
        # Order by topological sort
        # Return ordered path

    async def find_related_knowledge(
        self,
        knowledge_id: int,
        relationship_types: List[str],
        max_depth: int = 2
    ) -> List[Dict]:
        # BFS/DFS traversal from starting node
        # Follow specified relationship types

    async def update_incremental(
        self,
        new_chunk_ids: List[int],
        params: Optional[GraphBuildParams] = None
    ) -> Dict[str, Any]:
        # Only analyze new chunks against existing graph
```

4. LLM RELATIONSHIP DETECTION:

   Prompt Template:
   ```
   Analyze these two knowledge chunks for relationships:

   CHUNK A:
   Title: {title_a}
   Tags: {tags_a}
   Framework: {framework_a}
   Content: {content_a[:500]}...

   CHUNK B:
   Title: {title_b}
   Tags: {tags_b}
   Framework: {framework_b}
   Content: {content_b[:500]}...

   Determine if there is a relationship. Return JSON:
   {
       "has_relationship": boolean,
       "relationship_type": "depends_on" | "related_to" | "example_of" | "prerequisite_for",
       "confidence_score": 0.0-1.0,
       "explanation": "Brief explanation"
   }

   TYPES:
   - depends_on: A requires B to be understood first
   - related_to: A and B are related (symmetric)
   - example_of: A is concrete example of concept B
   - prerequisite_for: A is prerequisite for B
   ```

5. CONFIDENCE SCORING:
   ```python
   final_confidence = (
       llm_confidence * 0.6 +
       embedding_similarity * 0.2 +
       tag_overlap_score * 0.15 +
       (0.05 if framework_match else 0)
   )
   ```

6. DATABASE SCHEMA:
   - knowledge_relationships table:
     - source_knowledge_id (FK to site_pages)
     - target_knowledge_id (FK to site_pages)
     - relationship_type (enum)
     - confidence_score (float 0-1)
     - created_by (text)
     - metadata (jsonb)
     - created_at (timestamp)

7. GRAPH ALGORITHMS:
   - Cycle detection: NetworkX simple_cycles() or DFS
   - Topological sort: For learning path ordering
   - PageRank: For knowledge importance
   - Connected components: Identify isolated clusters
   - Shortest path: For learning path optimization

8. OPTIMIZATION STRATEGIES:
   - Use embedding similarity to pre-filter pairs (only compare similar chunks)
   - Batch LLM calls (analyze multiple pairs per call)
   - Cache relationship detection results
   - Parallel processing for independent pairs
   - Incremental updates (only new chunks)

9. INTEGRATION:
   - Import from: from utils.utils import get_clients
   - Creates data in knowledge_relationships table
   - Used by knowledge linker for better suggestions
   - Powers UI graph visualization
   - Enables learning path features

10. ERROR HANDLING:
    - Handle missing embeddings gracefully
    - Detect and warn on cycles
    - Handle LLM failures (retry or skip pair)
    - Validate relationship types
    - Handle orphaned nodes (no relationships)

11. TESTING:
    Include test scenarios:
    - Build full graph from 100 chunks
    - Incremental update with 10 new chunks
    - Cycle detection
    - Learning path generation
    - Orphan node detection

12. PERFORMANCE:
    - Complete 100 chunks in < 2 minutes
    - Use O(V+E) algorithms
    - Batch database operations
    - Minimize LLM calls with smart filtering
    - Support up to 5000 chunks

13. OUTPUT:
    Return comprehensive results:
    - Processing metadata (chunks analyzed, relationships created)
    - Graph statistics (nodes, edges, density, components)
    - Top hub knowledge (high connectivity)
    - Knowledge clusters
    - Sample learning paths
    - Warnings and recommendations

EXAMPLE USAGE:
```python
from archon.knowledge_graph_builder import KnowledgeGraphBuilder, GraphBuildParams

builder = KnowledgeGraphBuilder(supabase, llm_client)

result = await builder.build_graph(
    operation="build_full_graph",
    params=GraphBuildParams(
        min_confidence_score=0.7,
        use_embeddings=True,
        embedding_threshold=0.75
    )
)

print(f"Created {result['relationships_created']} relationships")
print(f"Graph density: {result['graph_statistics']['density']}")

# Get learning path
path = await builder.get_learning_path(target_knowledge_id=150)
for step in path['path']:
    print(f"{step['step']}. {step['title']}")
```

Please create a complete, production-ready implementation with:
- Full docstrings and type hints
- LLM-based relationship detection
- Confidence scoring algorithm
- Graph algorithms (NetworkX recommended)
- Cycle detection and validation
- Hub identification and clustering
- Learning path generation
- Incremental update support
- Performance optimizations
- Clean, maintainable code

Focus on intelligence and graph quality - relationships should be meaningful and accurate, enabling powerful knowledge discovery and learning path recommendations.
```
