"""
Interactive Knowledge Graph Visualization for Archon

This module provides an interactive graph visualization of knowledge chunks and their
relationships, with node details, filtering, and search capabilities.
"""

import streamlit as st
import sys
import os
from typing import Optional, Dict, Any, List, Set, Tuple
import pandas as pd
import plotly.graph_objects as go
import networkx as nx
from collections import defaultdict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import get_clients

# Initialize clients
embedding_client, supabase = get_clients()


# ============================================================================
# DATA FETCHING FUNCTIONS
# ============================================================================

def get_knowledge_chunks(
    framework_filter: Optional[str] = None,
    knowledge_type_filter: Optional[str] = None,
    tag_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Fetch knowledge chunks with optional filters"""
    try:
        query = supabase.table('knowledge').select('*')

        if framework_filter and framework_filter != 'All':
            query = query.eq('framework', framework_filter)

        if knowledge_type_filter and knowledge_type_filter != 'All':
            query = query.eq('knowledge_type', knowledge_type_filter)

        if tag_filter:
            # Use contains for array column
            query = query.contains('tags', [tag_filter])

        response = query.limit(500).execute()  # Limit for performance
        return response.data or []
    except Exception as e:
        st.error(f"Error fetching knowledge chunks: {e}")
        return []


def get_knowledge_relationships() -> List[Dict[str, Any]]:
    """Fetch knowledge relationships (if table exists)"""
    try:
        # Check if knowledge_relationships table exists
        response = supabase.table('knowledge_relationships').select('*').limit(1000).execute()
        return response.data or []
    except Exception as e:
        # Table might not exist, return empty
        return []


def get_task_knowledge_links() -> List[Dict[str, Any]]:
    """Get all task-knowledge links for relationship visualization"""
    try:
        response = supabase.table('task_knowledge_links').select('*').limit(1000).execute()
        return response.data or []
    except Exception as e:
        st.error(f"Error fetching task-knowledge links: {e}")
        return []


def get_tasks_by_ids(task_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Get task details for multiple task IDs"""
    try:
        if not task_ids:
            return {}

        response = supabase.table('tasks').select('*').in_('id', task_ids).execute()
        tasks = response.data or []

        return {task['id']: task for task in tasks}
    except Exception as e:
        st.error(f"Error fetching tasks: {e}")
        return {}


def get_unique_frameworks() -> List[str]:
    """Get list of unique frameworks"""
    try:
        response = supabase.table('knowledge').select('framework').execute()
        frameworks = set(k.get('framework', 'unknown') for k in response.data or [] if k.get('framework'))
        return sorted(list(frameworks))
    except Exception as e:
        return []


def get_unique_knowledge_types() -> List[str]:
    """Get list of unique knowledge types"""
    try:
        response = supabase.table('knowledge').select('knowledge_type').execute()
        types = set(k.get('knowledge_type', 'unknown') for k in response.data or [] if k.get('knowledge_type'))
        return sorted(list(types))
    except Exception as e:
        return []


def get_unique_tags() -> List[str]:
    """Get list of unique tags across all knowledge chunks"""
    try:
        response = supabase.table('knowledge').select('tags').execute()
        all_tags = set()
        for k in response.data or []:
            tags = k.get('tags', [])
            if tags:
                all_tags.update(tags)
        return sorted(list(all_tags))
    except Exception as e:
        return []


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def build_knowledge_graph(
    knowledge_chunks: List[Dict[str, Any]],
    relationships: List[Dict[str, Any]],
    task_links: List[Dict[str, Any]],
    show_task_links: bool = False
) -> Tuple[nx.Graph, Dict[int, Dict[str, Any]]]:
    """
    Build NetworkX graph from knowledge chunks and relationships

    Args:
        knowledge_chunks: List of knowledge chunk dictionaries
        relationships: List of knowledge relationship dictionaries
        task_links: List of task-knowledge link dictionaries
        show_task_links: Whether to include task-knowledge links as edges

    Returns:
        Tuple of (NetworkX graph, node metadata dict)
    """
    G = nx.Graph()
    node_metadata = {}

    # Add knowledge chunk nodes
    for chunk in knowledge_chunks:
        chunk_id = chunk.get('id')
        if chunk_id:
            G.add_node(chunk_id, type='knowledge')
            node_metadata[chunk_id] = chunk

    # Add relationship edges
    for rel in relationships:
        source_id = rel.get('source_knowledge_id')
        target_id = rel.get('target_knowledge_id')

        if source_id in G.nodes and target_id in G.nodes:
            G.add_edge(
                source_id,
                target_id,
                relationship_type=rel.get('relationship_type', 'related'),
                confidence=rel.get('confidence_score', 0.5)
            )

    # Optionally add task-knowledge links
    if show_task_links:
        # Group links by task to create task nodes
        task_chunks = defaultdict(list)
        for link in task_links:
            task_id = link.get('task_id')
            knowledge_id = link.get('knowledge_id')

            if knowledge_id in G.nodes:
                task_chunks[task_id].append(knowledge_id)

        # Add edges from task to knowledge (virtual connections)
        for task_id, knowledge_ids in task_chunks.items():
            # Create connections between knowledge chunks linked to same task
            for i, kid1 in enumerate(knowledge_ids):
                for kid2 in knowledge_ids[i + 1:]:
                    if kid1 in G.nodes and kid2 in G.nodes:
                        # Add edge if not exists
                        if not G.has_edge(kid1, kid2):
                            G.add_edge(kid1, kid2, relationship_type='shared_task', confidence=0.3)

    return G, node_metadata


def calculate_layout(G: nx.Graph, layout_type: str = 'spring') -> Dict[int, Tuple[float, float]]:
    """
    Calculate node positions using NetworkX layout algorithm

    Args:
        G: NetworkX graph
        layout_type: Type of layout ('spring', 'circular', 'kamada_kawai')

    Returns:
        Dictionary mapping node IDs to (x, y) positions
    """
    if len(G.nodes) == 0:
        return {}

    if layout_type == 'spring':
        return nx.spring_layout(G, k=1, iterations=50)
    elif layout_type == 'circular':
        return nx.circular_layout(G)
    elif layout_type == 'kamada_kawai':
        if len(G.nodes) < 100:  # Only use for smaller graphs
            return nx.kamada_kawai_layout(G)
        else:
            return nx.spring_layout(G, k=1, iterations=30)
    else:
        return nx.spring_layout(G, k=1, iterations=50)


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def create_knowledge_graph_plot(
    G: nx.Graph,
    node_metadata: Dict[int, Dict[str, Any]],
    layout_type: str = 'spring',
    selected_node_id: Optional[int] = None,
    highlight_nodes: Optional[Set[int]] = None
) -> go.Figure:
    """
    Create interactive Plotly graph visualization

    Args:
        G: NetworkX graph
        node_metadata: Dictionary of node metadata
        layout_type: Layout algorithm to use
        selected_node_id: ID of selected node to highlight
        highlight_nodes: Set of node IDs to highlight

    Returns:
        Plotly Figure object
    """
    if len(G.nodes) == 0:
        # Create empty figure with message
        fig = go.Figure()
        fig.add_annotation(
            text="No knowledge chunks match the current filters",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20)
        )
        fig.update_layout(
            template='plotly_dark',
            height=600,
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig

    # Calculate layout
    pos = calculate_layout(G, layout_type)

    # Define colors for frameworks
    framework_colors = {
        'fastapi': '#00CC99',
        'react': '#61DAFB',
        'pydantic_ai': '#E92063',
        'streamlit': '#FF4B4B',
        'supabase': '#3ECF8E',
        'nextjs': '#000000',
        'django': '#092E20',
        'flask': '#000000',
        'default': '#4B9EFF'
    }

    # Create edge trace
    edge_traces = []

    # Group edges by relationship type
    edge_types = defaultdict(list)
    for edge in G.edges(data=True):
        source, target, data = edge
        rel_type = data.get('relationship_type', 'related')
        edge_types[rel_type].append((source, target, data))

    # Color map for relationship types
    rel_colors = {
        'prerequisite': '#FF4B4B',
        'related': '#4B9EFF',
        'example_of': '#00CC99',
        'extension_of': '#FFA500',
        'shared_task': '#9370DB',
        'default': '#808080'
    }

    for rel_type, edges in edge_types.items():
        edge_x = []
        edge_y = []

        for source, target, data in edges:
            x0, y0 = pos[source]
            x1, y1 = pos[target]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        color = rel_colors.get(rel_type, rel_colors['default'])
        edge_trace = go.Scatter(
            x=edge_x,
            y=edge_y,
            mode='lines',
            line=dict(width=0.5, color=color),
            hoverinfo='none',
            name=rel_type.replace('_', ' ').title(),
            showlegend=True
        )
        edge_traces.append(edge_trace)

    # Create node trace
    node_x = []
    node_y = []
    node_colors = []
    node_text = []
    node_sizes = []
    node_ids = []

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)
        node_ids.append(node)

        # Get metadata
        metadata = node_metadata.get(node, {})
        framework = metadata.get('framework', 'unknown')
        title = metadata.get('title', 'Untitled')
        tags = metadata.get('tags', [])

        # Determine color
        if selected_node_id == node:
            color = '#FFD700'  # Gold for selected
        elif highlight_nodes and node in highlight_nodes:
            color = '#FF69B4'  # Pink for highlighted
        else:
            color = framework_colors.get(framework, framework_colors['default'])

        node_colors.append(color)

        # Node size based on degree (connections)
        degree = G.degree(node)
        size = min(10 + degree * 2, 40)
        node_sizes.append(size)

        # Hover text
        hover_text = f"<b>{title}</b><br>"
        hover_text += f"Framework: {framework}<br>"
        hover_text += f"Connections: {degree}<br>"
        if tags:
            hover_text += f"Tags: {', '.join(tags[:3])}<br>"

        node_text.append(hover_text)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode='markers',
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=2, color='white')
        ),
        text=node_text,
        hoverinfo='text',
        name='Knowledge Chunks',
        showlegend=False,
        customdata=node_ids
    )

    # Create figure
    fig = go.Figure(data=edge_traces + [node_trace])

    fig.update_layout(
        title='Knowledge Graph Visualization',
        template='plotly_dark',
        showlegend=True,
        hovermode='closest',
        height=600,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig


# ============================================================================
# NODE DETAILS
# ============================================================================

def show_node_details(node_id: int, node_metadata: Dict[int, Dict[str, Any]], G: nx.Graph):
    """Display detailed information about selected node"""
    if node_id not in node_metadata:
        st.warning("Node not found")
        return

    metadata = node_metadata[node_id]

    st.markdown(f"### {metadata.get('title', 'Untitled')}")

    # Basic info
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Framework:** {metadata.get('framework', 'N/A')}")
        st.markdown(f"**Type:** {metadata.get('knowledge_type', 'N/A')}")
        st.markdown(f"**Language:** {metadata.get('language', 'N/A')}")

    with col2:
        degree = G.degree(node_id)
        st.markdown(f"**Connections:** {degree}")
        st.markdown(f"**Created:** {metadata.get('created_at', '')[:10]}")

    # URL
    url = metadata.get('url', '')
    if url:
        st.markdown(f"**URL:** [{url}]({url})")

    # Summary
    st.markdown("#### Summary")
    st.markdown(metadata.get('summary', 'No summary available'))

    # Tags
    tags = metadata.get('tags', [])
    if tags:
        st.markdown("#### Tags")
        tag_html = " ".join([
            f'<span style="background-color: #4B9EFF; color: white; padding: 4px 8px; '
            f'border-radius: 8px; margin: 2px; display: inline-block; font-size: 0.85em;">{tag}</span>'
            for tag in tags
        ])
        st.markdown(tag_html, unsafe_allow_html=True)

    # Related chunks (neighbors)
    st.markdown("#### Related Chunks")
    neighbors = list(G.neighbors(node_id))

    if neighbors:
        for neighbor_id in neighbors[:5]:  # Show top 5
            neighbor_metadata = node_metadata.get(neighbor_id, {})
            neighbor_title = neighbor_metadata.get('title', 'Untitled')

            # Get edge data
            edge_data = G.get_edge_data(node_id, neighbor_id, {})
            rel_type = edge_data.get('relationship_type', 'related')
            confidence = edge_data.get('confidence', 0.5)

            st.markdown(
                f"- **{neighbor_title}** ({rel_type.replace('_', ' ')}, "
                f"confidence: {confidence:.2f})"
            )

        if len(neighbors) > 5:
            st.markdown(f"*...and {len(neighbors) - 5} more*")
    else:
        st.info("No direct relationships found")

    # Tasks using this knowledge
    st.markdown("#### Tasks Using This Knowledge")

    try:
        links = supabase.table('task_knowledge_links').select('*').eq('knowledge_id', node_id).execute()
        task_links = links.data or []

        if task_links:
            task_ids = [link['task_id'] for link in task_links]
            tasks = get_tasks_by_ids(task_ids)

            for link in task_links[:5]:  # Show top 5
                task = tasks.get(link['task_id'], {})
                task_name = task.get('name', 'Unknown Task')
                relevance = link.get('relevance_score', 0)

                st.markdown(f"- **{task_name}** (relevance: {relevance:.2%})")

            if len(task_links) > 5:
                st.markdown(f"*...and {len(task_links) - 5} more tasks*")
        else:
            st.info("Not linked to any tasks yet")
    except Exception as e:
        st.error(f"Error fetching task links: {e}")


# ============================================================================
# SEARCH AND FILTER
# ============================================================================

def search_knowledge_chunks(
    knowledge_chunks: List[Dict[str, Any]],
    search_query: str
) -> Set[int]:
    """
    Search knowledge chunks by title or tags

    Returns:
        Set of matching knowledge chunk IDs
    """
    if not search_query:
        return set()

    search_lower = search_query.lower()
    matches = set()

    for chunk in knowledge_chunks:
        chunk_id = chunk.get('id')
        title = chunk.get('title', '').lower()
        tags = [tag.lower() for tag in chunk.get('tags', [])]

        if search_lower in title or any(search_lower in tag for tag in tags):
            matches.add(chunk_id)

    return matches


def find_path_between_nodes(G: nx.Graph, source_id: int, target_id: int) -> Optional[List[int]]:
    """Find shortest path between two nodes"""
    try:
        if source_id in G.nodes and target_id in G.nodes:
            return nx.shortest_path(G, source_id, target_id)
        return None
    except nx.NetworkXNoPath:
        return None


# ============================================================================
# STATISTICS
# ============================================================================

def calculate_graph_statistics(G: nx.Graph, node_metadata: Dict[int, Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate graph statistics"""
    if len(G.nodes) == 0:
        return {
            'total_nodes': 0,
            'total_edges': 0,
            'avg_connections': 0,
            'most_connected': [],
            'relationship_types': {}
        }

    # Basic stats
    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()
    avg_connections = 2 * total_edges / total_nodes if total_nodes > 0 else 0

    # Most connected nodes
    degrees = dict(G.degree())
    sorted_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:5]

    most_connected = []
    for node_id, degree in sorted_nodes:
        metadata = node_metadata.get(node_id, {})
        most_connected.append({
            'title': metadata.get('title', 'Untitled'),
            'degree': degree
        })

    # Relationship type distribution
    rel_types = defaultdict(int)
    for _, _, data in G.edges(data=True):
        rel_type = data.get('relationship_type', 'unknown')
        rel_types[rel_type] += 1

    return {
        'total_nodes': total_nodes,
        'total_edges': total_edges,
        'avg_connections': avg_connections,
        'most_connected': most_connected,
        'relationship_types': dict(rel_types)
    }


# ============================================================================
# MAIN PAGE
# ============================================================================

def knowledge_graph_page():
    """Main knowledge graph visualization page"""
    st.title("🕸️ Knowledge Graph")

    # Check if database is configured
    if not supabase:
        st.error("⚠️ Supabase is not configured. Please set up your database in the Database tab.")
        return

    # Initialize session state
    if 'selected_node_id' not in st.session_state:
        st.session_state.selected_node_id = None
    if 'highlight_nodes' not in st.session_state:
        st.session_state.highlight_nodes = set()

    # Sidebar filters
    with st.sidebar:
        st.markdown("### Filters")

        # Framework filter
        frameworks = ['All'] + get_unique_frameworks()
        framework_filter = st.selectbox("Framework", frameworks)

        # Knowledge type filter
        knowledge_types = ['All'] + get_unique_knowledge_types()
        knowledge_type_filter = st.selectbox("Knowledge Type", knowledge_types)

        # Tag filter
        tags = get_unique_tags()
        tag_filter = st.selectbox("Tag", ['All'] + tags) if tags else None

        # Layout selection
        layout_type = st.selectbox(
            "Layout Algorithm",
            ['spring', 'circular', 'kamada_kawai'],
            help="Choose graph layout algorithm"
        )

        # Show task links
        show_task_links = st.checkbox(
            "Show Task Relationships",
            value=False,
            help="Connect knowledge chunks that share tasks"
        )

        # Refresh button
        if st.button("🔄 Refresh Graph", use_container_width=True):
            st.session_state.selected_node_id = None
            st.session_state.highlight_nodes = set()
            st.rerun()

    # Fetch data
    with st.spinner("Loading knowledge graph..."):
        knowledge_chunks = get_knowledge_chunks(
            framework_filter if framework_filter != 'All' else None,
            knowledge_type_filter if knowledge_type_filter != 'All' else None,
            tag_filter if tag_filter and tag_filter != 'All' else None
        )

        relationships = get_knowledge_relationships()
        task_links = get_task_knowledge_links() if show_task_links else []

        # Build graph
        G, node_metadata = build_knowledge_graph(
            knowledge_chunks,
            relationships,
            task_links,
            show_task_links
        )

    # Main content area
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### Graph Visualization")

        # Search bar
        search_query = st.text_input(
            "Search by title or tag",
            placeholder="Enter search term...",
            key="graph_search"
        )

        if search_query:
            highlight_nodes = search_knowledge_chunks(knowledge_chunks, search_query)
            st.session_state.highlight_nodes = highlight_nodes

            if highlight_nodes:
                st.success(f"Found {len(highlight_nodes)} matching nodes (highlighted in pink)")
            else:
                st.warning("No matches found")
        else:
            st.session_state.highlight_nodes = set()

        # Create and display graph
        fig = create_knowledge_graph_plot(
            G,
            node_metadata,
            layout_type,
            st.session_state.selected_node_id,
            st.session_state.highlight_nodes
        )

        # Handle click events (using plotly click data)
        selected_points = st.plotly_chart(fig, use_container_width=True, on_select="rerun", key="graph_plot")

        # Note: Plotly click events in Streamlit are limited
        # We'll use a selectbox as a workaround for node selection

    with col2:
        st.markdown("### Statistics")

        stats = calculate_graph_statistics(G, node_metadata)

        st.metric("Total Nodes", stats['total_nodes'])
        st.metric("Total Edges", stats['total_edges'])
        st.metric("Avg Connections", f"{stats['avg_connections']:.2f}")

        if stats['most_connected']:
            st.markdown("#### Most Connected")
            for item in stats['most_connected']:
                st.markdown(f"- {item['title']} ({item['degree']} connections)")

        if stats['relationship_types']:
            st.markdown("#### Relationship Types")
            for rel_type, count in stats['relationship_types'].items():
                st.markdown(f"- {rel_type.replace('_', ' ').title()}: {count}")

    # Node details section
    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### Node Details")

        # Node selector (workaround for click limitation)
        if len(knowledge_chunks) > 0:
            chunk_options = {f"{chunk.get('title', 'Untitled')} (ID: {chunk.get('id')})": chunk.get('id') for chunk in knowledge_chunks}
            chunk_names = list(chunk_options.keys())

            if chunk_names:
                selected_chunk_name = st.selectbox(
                    "Select a node to view details",
                    ['None'] + chunk_names,
                    key="node_selector"
                )

                if selected_chunk_name != 'None':
                    selected_node_id = chunk_options[selected_chunk_name]
                    st.session_state.selected_node_id = selected_node_id

        if st.session_state.selected_node_id:
            show_node_details(st.session_state.selected_node_id, node_metadata, G)
        else:
            st.info("Select a node to view details")

    with col2:
        st.markdown("### Path Finder")

        if len(knowledge_chunks) > 0:
            chunk_options = {f"{chunk.get('title', 'Untitled')}": chunk.get('id') for chunk in knowledge_chunks}
            chunk_names = list(chunk_options.keys())

            source_name = st.selectbox("From", chunk_names, key="path_source")
            target_name = st.selectbox("To", chunk_names, key="path_target")

            if st.button("Find Path"):
                source_id = chunk_options[source_name]
                target_id = chunk_options[target_name]

                path = find_path_between_nodes(G, source_id, target_id)

                if path:
                    st.success(f"Path found with {len(path)} nodes")

                    for i, node_id in enumerate(path):
                        metadata = node_metadata.get(node_id, {})
                        title = metadata.get('title', 'Untitled')

                        if i < len(path) - 1:
                            st.markdown(f"{i + 1}. {title} →")
                        else:
                            st.markdown(f"{i + 1}. {title}")

                    # Highlight path
                    st.session_state.highlight_nodes = set(path)
                    st.rerun()
                else:
                    st.warning("No path found between these nodes")


# Entry point
if __name__ == "__main__":
    knowledge_graph_page()
