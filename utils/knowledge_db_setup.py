"""
Knowledge Management Database Setup Utility

This module provides utilities to set up and migrate the enhanced knowledge management
schema for Archon's project and task management system.
"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.utils import get_clients

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class KnowledgeDBSetup:
    """Handles database setup and migration for knowledge management."""

    def __init__(self):
        """Initialize database connection."""
        _, self.supabase = get_clients()
        self.schema_dir = Path(__file__).parent

    def read_sql_file(self, filename: str) -> str:
        """Read SQL file from utils directory."""
        file_path = self.schema_dir / filename
        if not file_path.exists():
            raise FileNotFoundError(f"SQL file not found: {file_path}")

        with open(file_path, 'r') as f:
            return f.read()

    def execute_sql(self, sql: str) -> Dict[str, Any]:
        """
        Execute SQL directly via Supabase RPC.
        Note: This requires a custom RPC function in Supabase for executing raw SQL.
        """
        try:
            # For Supabase, we'll need to execute SQL statements one at a time
            # or use the Supabase SQL editor directly
            logger.warning("Direct SQL execution not supported via Supabase client.")
            logger.info("Please execute SQL manually in Supabase SQL editor.")
            return {"status": "manual_execution_required", "sql": sql}
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            return {"status": "error", "error": str(e)}

    def verify_table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            # Try to select from the table (limit 0 to not fetch data)
            result = self.supabase.table(table_name).select("*").limit(0).execute()
            return True
        except Exception as e:
            logger.debug(f"Table {table_name} check: {e}")
            return False

    def verify_column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        try:
            result = self.supabase.table(table_name).select(column_name).limit(1).execute()
            return True
        except Exception as e:
            logger.debug(f"Column {table_name}.{column_name} check: {e}")
            return False

    def get_schema_status(self) -> Dict[str, Any]:
        """Check which parts of the schema are already set up."""
        tables_to_check = [
            'site_pages',
            'knowledge_sources',
            'projects',
            'tasks',
            'task_dependencies',
            'task_knowledge_links',
            'knowledge_relationships',
            'agent_schedules'
        ]

        enhanced_columns = {
            'site_pages': ['tags', 'knowledge_type', 'framework', 'language']
        }

        status = {
            'tables': {},
            'enhanced_columns': {},
            'overall_status': 'unknown'
        }

        # Check tables
        for table in tables_to_check:
            exists = self.verify_table_exists(table)
            status['tables'][table] = exists
            logger.info(f"Table '{table}': {'✓ exists' if exists else '✗ missing'}")

        # Check enhanced columns
        for table, columns in enhanced_columns.items():
            if status['tables'].get(table, False):
                status['enhanced_columns'][table] = {}
                for column in columns:
                    exists = self.verify_column_exists(table, column)
                    status['enhanced_columns'][table][column] = exists
                    logger.info(f"Column '{table}.{column}': {'✓ exists' if exists else '✗ missing'}")

        # Determine overall status
        all_tables_exist = all(status['tables'].values())
        all_columns_exist = all(
            all(cols.values())
            for cols in status['enhanced_columns'].values()
        ) if status['enhanced_columns'] else False

        if all_tables_exist and all_columns_exist:
            status['overall_status'] = 'complete'
        elif status['tables'].get('site_pages', False):
            status['overall_status'] = 'partial'
        else:
            status['overall_status'] = 'not_setup'

        return status

    def generate_setup_instructions(self) -> str:
        """Generate setup instructions based on current schema status."""
        status = self.get_schema_status()

        instructions = []
        instructions.append("=" * 80)
        instructions.append("ARCHON KNOWLEDGE MANAGEMENT DATABASE SETUP INSTRUCTIONS")
        instructions.append("=" * 80)
        instructions.append("")

        if status['overall_status'] == 'complete':
            instructions.append("✓ Your database schema is fully set up!")
            instructions.append("")
            instructions.append("All tables and columns are in place. You're ready to use")
            instructions.append("Archon's knowledge management and project features.")

        elif status['overall_status'] == 'partial':
            instructions.append("⚠ Your database schema is partially set up.")
            instructions.append("")
            instructions.append("Missing components:")

            # List missing tables
            missing_tables = [t for t, exists in status['tables'].items() if not exists]
            if missing_tables:
                instructions.append("")
                instructions.append("Missing tables:")
                for table in missing_tables:
                    instructions.append(f"  - {table}")

            # List missing columns
            for table, columns in status['enhanced_columns'].items():
                missing_cols = [c for c, exists in columns.items() if not exists]
                if missing_cols:
                    instructions.append("")
                    instructions.append(f"Missing columns in '{table}':")
                    for col in missing_cols:
                        instructions.append(f"  - {col}")

            instructions.append("")
            instructions.append("To complete setup, execute the SQL in:")
            instructions.append("  utils/knowledge_schema.sql")

        else:
            instructions.append("✗ Database schema not set up.")
            instructions.append("")
            instructions.append("To set up the complete knowledge management schema:")

        if status['overall_status'] != 'complete':
            instructions.append("")
            instructions.append("SETUP STEPS:")
            instructions.append("")
            instructions.append("1. Open your Supabase project dashboard")
            instructions.append("   https://app.supabase.com/project/<your-project-id>")
            instructions.append("")
            instructions.append("2. Navigate to: SQL Editor (left sidebar)")
            instructions.append("")
            instructions.append("3. Click 'New query'")
            instructions.append("")
            instructions.append("4. Copy and paste the contents of:")
            instructions.append("   utils/knowledge_schema.sql")
            instructions.append("")
            instructions.append("5. Click 'Run' to execute the SQL")
            instructions.append("")
            instructions.append("6. Return to this page and click 'Verify Setup'")
            instructions.append("")
            instructions.append("NOTE: The schema is designed to be idempotent - it's safe to")
            instructions.append("      run multiple times. It will not duplicate existing tables.")

        instructions.append("")
        instructions.append("=" * 80)

        return "\n".join(instructions)

    def test_knowledge_functions(self) -> Dict[str, Any]:
        """Test that RPC functions are working."""
        results = {}

        # Test match_knowledge_advanced
        try:
            test_embedding = [0.0] * 1536  # Zero vector for testing
            result = self.supabase.rpc('match_knowledge_advanced', {
                'query_embedding': test_embedding,
                'match_count': 1
            }).execute()
            results['match_knowledge_advanced'] = 'working'
            logger.info("✓ match_knowledge_advanced function working")
        except Exception as e:
            results['match_knowledge_advanced'] = f'error: {str(e)}'
            logger.warning(f"✗ match_knowledge_advanced function: {e}")

        # Test check_knowledge_coverage
        try:
            result = self.supabase.rpc('check_knowledge_coverage', {
                'required_tags_param': ['test'],
                'required_frameworks_param': []
            }).execute()
            results['check_knowledge_coverage'] = 'working'
            logger.info("✓ check_knowledge_coverage function working")
        except Exception as e:
            results['check_knowledge_coverage'] = f'error: {str(e)}'
            logger.warning(f"✗ check_knowledge_coverage function: {e}")

        return results

    def create_sample_data(self) -> None:
        """Create sample project and task data for testing."""
        try:
            # Create a sample project
            project_data = {
                'name': 'Sample Project: Build FastAPI Authentication',
                'description': 'Create a complete authentication system using FastAPI and JWT',
                'status': 'planning',
                'priority': 2,
                'required_knowledge_tags': ['fastapi', 'authentication', 'jwt', 'security'],
                'required_frameworks': ['fastapi', 'pydantic'],
                'metadata': {'sample': True, 'created_by': 'setup_script'}
            }

            project_result = self.supabase.table('projects').insert(project_data).execute()
            project_id = project_result.data[0]['id']
            logger.info(f"✓ Created sample project: {project_id}")

            # Create sample tasks
            tasks = [
                {
                    'project_id': project_id,
                    'name': 'Research FastAPI authentication patterns',
                    'description': 'Study FastAPI docs and best practices for auth',
                    'status': 'pending',
                    'priority': 1,
                    'required_knowledge_tags': ['fastapi', 'authentication'],
                    'required_frameworks': ['fastapi'],
                    'assigned_agent_type': 'scraper',
                    'estimated_duration_minutes': 30
                },
                {
                    'project_id': project_id,
                    'name': 'Implement JWT token generation',
                    'description': 'Create functions to generate and validate JWT tokens',
                    'status': 'pending',
                    'priority': 2,
                    'required_knowledge_tags': ['jwt', 'security', 'python'],
                    'assigned_agent_type': 'coder',
                    'estimated_duration_minutes': 60
                },
                {
                    'project_id': project_id,
                    'name': 'Create authentication endpoints',
                    'description': 'Build FastAPI endpoints for login, logout, and token refresh',
                    'status': 'pending',
                    'priority': 2,
                    'required_knowledge_tags': ['fastapi', 'jwt', 'api'],
                    'required_frameworks': ['fastapi'],
                    'assigned_agent_type': 'coder',
                    'estimated_duration_minutes': 90
                }
            ]

            tasks_result = self.supabase.table('tasks').insert(tasks).execute()
            task_ids = [t['id'] for t in tasks_result.data]
            logger.info(f"✓ Created {len(task_ids)} sample tasks")

            # Create task dependencies
            if len(task_ids) >= 3:
                dependencies = [
                    {
                        'task_id': task_ids[1],  # JWT task depends on research
                        'depends_on_task_id': task_ids[0],
                        'dependency_type': 'finish_to_start'
                    },
                    {
                        'task_id': task_ids[2],  # Endpoints depend on JWT
                        'depends_on_task_id': task_ids[1],
                        'dependency_type': 'finish_to_start'
                    }
                ]

                self.supabase.table('task_dependencies').insert(dependencies).execute()
                logger.info(f"✓ Created task dependencies")

            logger.info("✓ Sample data created successfully!")
            logger.info(f"  Project ID: {project_id}")
            logger.info(f"  Task IDs: {', '.join(task_ids)}")

        except Exception as e:
            logger.error(f"Error creating sample data: {e}")
            raise


def main():
    """Main function for CLI usage."""
    print("Archon Knowledge Management Database Setup")
    print("=" * 80)
    print()

    setup = KnowledgeDBSetup()

    # Check current status
    print("Checking database schema status...")
    print()

    instructions = setup.generate_setup_instructions()
    print(instructions)
    print()

    # Test functions if schema is complete
    status = setup.get_schema_status()
    if status['overall_status'] == 'complete':
        print("Testing RPC functions...")
        print()
        test_results = setup.test_knowledge_functions()
        print()

        # Ask to create sample data
        response = input("Would you like to create sample project/task data? (y/n): ")
        if response.lower() == 'y':
            print()
            print("Creating sample data...")
            setup.create_sample_data()


if __name__ == "__main__":
    main()
