import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.utils import get_env_var
from utils.knowledge_db_setup import KnowledgeDBSetup

@st.cache_data
def load_sql_template():
    """Load the SQL template file and cache it"""
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utils", "site_pages.sql"), "r") as f:
        return f.read()

@st.cache_data
def load_knowledge_sql_template():
    """Load the knowledge management SQL template file and cache it"""
    with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "utils", "knowledge_schema.sql"), "r") as f:
        return f.read()

def get_supabase_sql_editor_url(supabase_url):
    """Get the URL for the Supabase SQL Editor"""
    try:
        # Extract the project reference from the URL
        # Format is typically: https://<project-ref>.supabase.co
        if '//' in supabase_url and 'supabase' in supabase_url:
            parts = supabase_url.split('//')
            if len(parts) > 1:
                domain_parts = parts[1].split('.')
                if len(domain_parts) > 0:
                    project_ref = domain_parts[0]
                    return f"https://supabase.com/dashboard/project/{project_ref}/sql/new"
        
        # Fallback to a generic URL
        return "https://supabase.com/dashboard"
    except Exception:
        return "https://supabase.com/dashboard"

def show_manual_sql_instructions(sql, vector_dim, recreate=False):
    """Show instructions for manually executing SQL in Supabase"""
    st.info("### Manual SQL Execution Instructions")
    
    # Provide a link to the Supabase SQL Editor
    supabase_url = get_env_var("SUPABASE_URL")
    if supabase_url:
        dashboard_url = get_supabase_sql_editor_url(supabase_url)
        st.markdown(f"**Step 1:** [Open Your Supabase SQL Editor with this URL]({dashboard_url})")
    else:
        st.markdown("**Step 1:** Open your Supabase Dashboard and navigate to the SQL Editor")
    
    st.markdown("**Step 2:** Create a new SQL query")
    
    if recreate:
        st.markdown("**Step 3:** Copy and execute the following SQL:")
        drop_sql = f"DROP FUNCTION IF EXISTS match_site_pages(vector({vector_dim}), int, jsonb);\nDROP TABLE IF EXISTS site_pages CASCADE;"
        st.code(drop_sql, language="sql")
        
        st.markdown("**Step 4:** Then copy and execute this SQL:")
        st.code(sql, language="sql")
    else:
        st.markdown("**Step 3:** Copy and execute the following SQL:")
        st.code(sql, language="sql")
    
    st.success("After executing the SQL, return to this page and refresh to see the updated table status.")

def database_tab(supabase):
    """Display the database configuration interface"""
    st.header("Database Configuration")
    st.write("Set up and manage your Supabase database tables for Archon.")
    
    # Check if Supabase is configured
    if not supabase:
        st.error("Supabase is not configured. Please set your Supabase URL and Service Key in the Environment tab.")
        return
    
    # Site Pages Table Setup
    st.subheader("Site Pages Table")
    st.write("This table stores web page content and embeddings for semantic search.")
    
    # Add information about the table
    with st.expander("About the Site Pages Table", expanded=False):
        st.markdown("""
        This table is used to store:
        - Web page content split into chunks
        - Vector embeddings for semantic search
        - Metadata for filtering results
        
        The table includes:
        - URL and chunk number (unique together)
        - Title and summary of the content
        - Full text content
        - Vector embeddings for similarity search
        - Metadata in JSON format
        
        It also creates:
        - A vector similarity search function
        - Appropriate indexes for performance
        - Row-level security policies for Supabase
        """)
    
    # Check if the table already exists
    table_exists = False
    table_has_data = False
    
    try:
        # Try to query the table to see if it exists
        response = supabase.table("site_pages").select("id").limit(1).execute()
        table_exists = True
        
        # Check if the table has data
        count_response = supabase.table("site_pages").select("*", count="exact").execute()
        row_count = count_response.count if hasattr(count_response, 'count') else 0
        table_has_data = row_count > 0
        
        st.success("✅ The site_pages table already exists in your database.")
        if table_has_data:
            st.info(f"The table contains data ({row_count} rows).")
        else:
            st.info("The table exists but contains no data.")
    except Exception as e:
        error_str = str(e)
        if "relation" in error_str and "does not exist" in error_str:
            st.info("The site_pages table does not exist yet. You can create it below.")
        else:
            st.error(f"Error checking table status: {error_str}")
            st.info("Proceeding with the assumption that the table needs to be created.")
        table_exists = False
    
    # Vector dimensions selection
    st.write("### Vector Dimensions")
    st.write("Select the embedding dimensions based on your embedding model:")
    
    vector_dim = st.selectbox(
        "Embedding Dimensions",
        options=[1536, 768, 384, 1024],
        index=0,
        help="Use 1536 for OpenAI embeddings, 768 for nomic-embed-text with Ollama, or select another dimension based on your model."
    )
    
    # Get the SQL with the selected vector dimensions
    sql_template = load_sql_template()
    
    # Replace the vector dimensions in the SQL
    sql = sql_template.replace("vector(1536)", f"vector({vector_dim})")
    
    # Also update the match_site_pages function dimensions
    sql = sql.replace("query_embedding vector(1536)", f"query_embedding vector({vector_dim})")
    
    # Show the SQL
    with st.expander("View SQL", expanded=False):
        st.code(sql, language="sql")
    
    # Create table button
    if not table_exists:
        if st.button("Get Instructions for Creating Site Pages Table"):
            show_manual_sql_instructions(sql, vector_dim)
    else:
        # Option to recreate the table or clear data
        col1, col2 = st.columns(2)
        
        with col1:
            st.warning("⚠️ Recreating will delete all existing data.")
            if st.button("Get Instructions for Recreating Site Pages Table"):
                show_manual_sql_instructions(sql, vector_dim, recreate=True)
        
        with col2:
            if table_has_data:
                st.warning("⚠️ Clear all data but keep structure.")
                if st.button("Clear Table Data"):
                    try:
                        with st.spinner("Clearing table data..."):
                            # Use the Supabase client to delete all rows
                            response = supabase.table("site_pages").delete().neq("id", 0).execute()
                            st.success("✅ Table data cleared successfully!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing table data: {str(e)}")
                        # Fall back to manual SQL
                        truncate_sql = "TRUNCATE TABLE site_pages;"
                        st.code(truncate_sql, language="sql")
                        st.info("Execute this SQL in your Supabase SQL Editor to clear the table data.")
                        
                        # Provide a link to the Supabase SQL Editor
                        supabase_url = get_env_var("SUPABASE_URL")
                        if supabase_url:
                            dashboard_url = get_supabase_sql_editor_url(supabase_url)
                            st.markdown(f"[Open Your Supabase SQL Editor with this URL]({dashboard_url})")

    # Knowledge Management Schema Setup
    st.divider()
    st.subheader("📚 Knowledge Management Schema")
    st.write("Enhanced schema for project management, task tracking, and knowledge attachment.")

    with st.expander("About the Knowledge Management Schema", expanded=False):
        st.markdown("""
        This enhanced schema adds powerful features to Archon:

        **New Tables:**
        - `knowledge_sources` - Track external documentation sources
        - `projects` - Manage projects with knowledge context
        - `tasks` - Tasks with attached knowledge and agent assignment
        - `task_knowledge_links` - Link relevant knowledge to tasks
        - `task_dependencies` - Define task dependencies for scheduling
        - `knowledge_relationships` - Build knowledge graphs
        - `agent_schedules` - Track agent execution schedules

        **Enhanced site_pages:**
        - `tags` - Tag knowledge chunks (e.g., ['fastapi', 'authentication'])
        - `knowledge_type` - Classify knowledge (documentation, tutorial, etc.)
        - `framework` - Framework/library name (e.g., 'fastapi', 'react')
        - `language` - Programming language

        **Key Features:**
        - Attach relevant documentation to tasks automatically
        - Track which knowledge agents need for tasks
        - Schedule tasks based on dependencies
        - Build knowledge graphs showing relationships
        - Learn from task completions

        This schema enables Archon to use knowledge-aware project management!
        """)

    # Check knowledge schema status
    try:
        setup = KnowledgeDBSetup()
        status = setup.get_schema_status()

        # Display status
        if status['overall_status'] == 'complete':
            st.success("✅ Knowledge Management schema is fully set up!")

            # Show table details
            with st.expander("View Schema Details", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Core Tables:**")
                    for table in ['knowledge_sources', 'projects', 'tasks', 'task_dependencies']:
                        st.write(f"✓ {table}")

                with col2:
                    st.write("**Relationship Tables:**")
                    for table in ['task_knowledge_links', 'knowledge_relationships', 'agent_schedules']:
                        st.write(f"✓ {table}")

                st.write("**Enhanced Columns in site_pages:**")
                if 'site_pages' in status['enhanced_columns']:
                    for col, exists in status['enhanced_columns']['site_pages'].items():
                        st.write(f"{'✓' if exists else '✗'} {col}")

            # Test functions
            if st.button("Test Knowledge Functions"):
                with st.spinner("Testing RPC functions..."):
                    test_results = setup.test_knowledge_functions()

                    for func_name, result in test_results.items():
                        if result == 'working':
                            st.success(f"✓ {func_name} is working")
                        else:
                            st.error(f"✗ {func_name}: {result}")

            # Create sample data
            if st.button("Create Sample Project & Tasks"):
                with st.spinner("Creating sample data..."):
                    try:
                        setup.create_sample_data()
                        st.success("✅ Sample data created! Check the Projects tab to see it.")
                    except Exception as e:
                        st.error(f"Error creating sample data: {e}")

        elif status['overall_status'] == 'partial':
            st.warning("⚠️ Knowledge Management schema is partially set up.")

            # Show what's missing
            missing_tables = [t for t, exists in status['tables'].items() if not exists]
            if missing_tables:
                st.write("**Missing tables:**")
                for table in missing_tables:
                    st.write(f"- {table}")

            # Show missing columns
            for table, columns in status['enhanced_columns'].items():
                missing_cols = [c for c, exists in columns.items() if not exists]
                if missing_cols:
                    st.write(f"**Missing columns in {table}:**")
                    for col in missing_cols:
                        st.write(f"- {col}")

            st.info("Execute the SQL below to complete the setup.")

        else:
            st.info("Knowledge Management schema not yet set up.")

        # Show setup instructions button
        if status['overall_status'] != 'complete':
            if st.button("Get Setup Instructions for Knowledge Management"):
                # Load the knowledge SQL
                knowledge_sql = load_knowledge_sql_template()

                st.info("### Knowledge Management Schema Setup Instructions")

                supabase_url = get_env_var("SUPABASE_URL")
                if supabase_url:
                    dashboard_url = get_supabase_sql_editor_url(supabase_url)
                    st.markdown(f"**Step 1:** [Open Your Supabase SQL Editor]({dashboard_url})")
                else:
                    st.markdown("**Step 1:** Open your Supabase Dashboard → SQL Editor")

                st.markdown("**Step 2:** Create a new SQL query")
                st.markdown("**Step 3:** Copy and execute the SQL below:")

                with st.expander("📋 Click to view SQL (copy all of it)", expanded=True):
                    st.code(knowledge_sql, language="sql")

                st.success("**Step 4:** After executing, return here and click 'Verify Setup'")

        # Verify setup button
        if status['overall_status'] != 'complete':
            if st.button("Verify Setup"):
                st.cache_data.clear()  # Clear cache to re-check
                st.rerun()

    except Exception as e:
        st.error(f"Error checking knowledge schema status: {e}")
        st.info("You can still view and execute the SQL manually.")

        if st.button("View Knowledge Management SQL"):
            knowledge_sql = load_knowledge_sql_template()
            st.code(knowledge_sql, language="sql")