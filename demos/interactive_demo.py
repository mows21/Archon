"""
Interactive Archon Demo

A user-guided walkthrough of the Archon Knowledge Management System features.
This interactive CLI demo allows users to explore different capabilities at their own pace.

Usage:
    python demos/interactive_demo.py

Features:
- Interactive menu system
- Step-by-step guided workflows
- Real-time feedback
- Exploration of all major features
"""

import os
import sys
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.knowledge_manager import KnowledgeManager
from archon.universal_crawler import SourceConfig, crawl_source, CrawlProgressTracker
from archon.knowledge_linker import auto_link_task_knowledge
from utils.utils import get_clients

# ============================================================================
# UI HELPERS
# ============================================================================

class Colors:
    """ANSI color codes."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def clear_screen():
    """Clear terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_header(text: str):
    """Print a styled header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")


def print_menu(title: str, options: List[str]):
    """Print a menu with numbered options."""
    print(f"\n{Colors.BOLD}{title}{Colors.END}")
    print(f"{Colors.CYAN}{'─'*80}{Colors.END}")
    for i, option in enumerate(options, 1):
        print(f"  {Colors.YELLOW}{i}.{Colors.END} {option}")
    print(f"{Colors.CYAN}{'─'*80}{Colors.END}")


def get_choice(prompt: str, valid_range: range) -> int:
    """Get user's menu choice."""
    while True:
        try:
            choice = input(f"\n{Colors.GREEN}{prompt}{Colors.END} ")
            choice_int = int(choice)
            if choice_int in valid_range:
                return choice_int
            else:
                print(f"{Colors.RED}Invalid choice. Please enter a number between {valid_range.start} and {valid_range.stop-1}.{Colors.END}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number.{Colors.END}")
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Demo interrupted by user.{Colors.END}")
            sys.exit(0)


def wait_for_enter(prompt: str = "Press Enter to continue..."):
    """Wait for user to press Enter."""
    input(f"\n{Colors.CYAN}{prompt}{Colors.END}")


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.END}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


# ============================================================================
# DEMO STATE
# ============================================================================

class DemoState:
    """Maintains state across demo sessions."""

    def __init__(self):
        self.km: Optional[KnowledgeManager] = None
        self.current_project_id: Optional[str] = None
        self.current_task_id: Optional[str] = None
        self.crawled_sources: List[str] = []

    async def initialize(self):
        """Initialize Knowledge Manager."""
        if self.km is None:
            print_info("Initializing Knowledge Manager...")
            self.km = KnowledgeManager()
            print_success("Knowledge Manager initialized!")

    def is_ready(self) -> bool:
        """Check if demo is ready."""
        return self.km is not None


# Global state
state = DemoState()


# ============================================================================
# DEMO FEATURES
# ============================================================================

async def demo_crawl_documentation():
    """Demo: Crawl documentation source."""
    clear_screen()
    print_header("📚 Crawl Documentation")

    print("This demo will crawl a documentation source and store it in the knowledge base.\n")

    # Get source URL
    print("Enter the documentation URL to crawl:")
    print("  Examples:")
    print("    - https://fastapi.tiangolo.com")
    print("    - https://docs.pydantic.dev")
    print("    - https://streamlit.io/docs")

    url = input(f"\n{Colors.GREEN}URL:{Colors.END} ").strip()

    if not url:
        print_warning("No URL provided. Returning to menu...")
        wait_for_enter()
        return

    # Get framework name
    framework = input(f"{Colors.GREEN}Framework name (optional):{Colors.END} ").strip()

    # Configure crawler
    print_info(f"Configuring crawler for: {url}")

    config = SourceConfig(
        source_url=url,
        source_type="documentation",
        framework=framework if framework else None,
        crawl_profile="quick"
    )

    # Progress callback
    def progress_callback(status: Dict[str, Any]):
        progress = status['progress_percentage']
        phase = status['current_phase']
        print(f"\r{Colors.CYAN}Progress: {progress:5.1f}% - {phase}{Colors.END}", end='', flush=True)

    tracker = CrawlProgressTracker(progress_callback=progress_callback)

    print_info("Starting crawl (this may take a few minutes)...")

    try:
        stats = await crawl_source(config, profile_name="quick", tracker=tracker)
        print()  # New line after progress
        print_success("Crawl completed!")
        print(f"  • URLs processed: {stats['urls_processed']}")
        print(f"  • URLs succeeded: {stats['urls_succeeded']}")
        print(f"  • Chunks stored: {stats['chunks_stored']}")
        print(f"  • Duration: {stats['duration_seconds']} seconds")

        state.crawled_sources.append(url)

    except Exception as e:
        print()
        print_error(f"Crawl failed: {e}")

    wait_for_enter()


async def demo_create_project():
    """Demo: Create a knowledge-aware project."""
    clear_screen()
    print_header("🎯 Create Knowledge-Aware Project")

    print("This demo will create a new project with automatic knowledge discovery.\n")

    # Get project details
    name = input(f"{Colors.GREEN}Project name:{Colors.END} ").strip()
    if not name:
        print_warning("No name provided. Returning to menu...")
        wait_for_enter()
        return

    description = input(f"{Colors.GREEN}Project description:{Colors.END} ").strip()
    if not description:
        print_warning("No description provided. Returning to menu...")
        wait_for_enter()
        return

    priority = input(f"{Colors.GREEN}Priority (1-5, default=3):{Colors.END} ").strip()
    priority = int(priority) if priority else 3

    print_info("Creating project with knowledge discovery...")

    try:
        result = await state.km.create_project(
            name=name,
            description=description,
            priority=priority,
            auto_discover=True,
            min_coverage=0.4
        )

        project = result['project']
        coverage = result['coverage']

        state.current_project_id = project['id']

        print_success("Project created!")
        print(f"  • Project ID: {project['id']}")
        print(f"  • Status: {project['status']}")

        if coverage:
            print(f"\n  Knowledge Coverage:")
            print(f"    • Score: {coverage['coverage_score']*100:.1f}%")
            print(f"    • Total chunks: {coverage['total_chunks']}")
            print(f"    • Available frameworks: {coverage['available_frameworks']}")
            if coverage['missing_tags']:
                print(f"    • Missing tags: {coverage['missing_tags'][:5]}")
            if coverage['needs_scraping']:
                print_warning("  Low coverage - consider crawling more documentation!")

    except Exception as e:
        print_error(f"Failed to create project: {e}")

    wait_for_enter()


async def demo_decompose_project():
    """Demo: Decompose project into tasks."""
    clear_screen()
    print_header("🔨 Decompose Project into Tasks")

    if not state.current_project_id:
        print_warning("No active project. Please create a project first.")
        wait_for_enter()
        return

    print(f"This will decompose project {state.current_project_id[:8]}... into tasks.\n")

    confirm = input(f"{Colors.GREEN}Continue? (y/n):{Colors.END} ").strip().lower()
    if confirm != 'y':
        return

    print_info("Using LLM to decompose project...")

    try:
        tasks = await state.km.decompose_project(
            project_id=state.current_project_id,
            decomposition_strategy="auto",
            auto_link_knowledge=True
        )

        print_success(f"Project decomposed into {len(tasks)} tasks!")

        for i, task_result in enumerate(tasks[:10], 1):
            task = task_result['task']
            coverage = task_result.get('coverage_score', 0)

            print(f"\n  {i}. {task['name']}")
            print(f"     Priority: {task['priority']} | Coverage: {coverage*100:.1f}%")

        if len(tasks) > 10:
            print(f"\n  ... and {len(tasks) - 10} more tasks")

        if tasks:
            state.current_task_id = tasks[0]['task']['id']
            print_info(f"Set first task as current: {state.current_task_id[:8]}...")

    except Exception as e:
        print_error(f"Failed to decompose project: {e}")

    wait_for_enter()


async def demo_link_knowledge():
    """Demo: Link knowledge to a task."""
    clear_screen()
    print_header("🔗 Link Knowledge to Task")

    if not state.current_task_id:
        print_warning("No active task. Please create or select a task first.")
        wait_for_enter()
        return

    print(f"This will link knowledge to task {state.current_task_id[:8]}...\n")

    print_info("Analyzing task and finding relevant knowledge...")

    try:
        result = await auto_link_task_knowledge(state.current_task_id)

        print_success("Knowledge linking completed!")
        print(f"  • Chunks found: {result.total_chunks_found}")
        print(f"  • Links created: {result.links_created}")
        print(f"  • Coverage score: {result.coverage_score*100:.1f}%")

        if result.missing_knowledge:
            print(f"\n  Missing knowledge:")
            for item in result.missing_knowledge[:5]:
                print(f"    • {item}")

        if result.suggested_crawl_sources:
            print(f"\n  Suggested sources to crawl:")
            for source in result.suggested_crawl_sources[:3]:
                print(f"    • {source}")

    except Exception as e:
        print_error(f"Failed to link knowledge: {e}")

    wait_for_enter()


async def demo_view_knowledge():
    """Demo: View linked knowledge for a task."""
    clear_screen()
    print_header("📖 View Task Knowledge")

    if not state.current_task_id:
        print_warning("No active task. Please create or select a task first.")
        wait_for_enter()
        return

    print_info("Fetching task with linked knowledge...")

    try:
        result = await state.km.get_task_with_knowledge(state.current_task_id)
        task = result['task']
        knowledge = result['linked_knowledge']

        print_success("Task knowledge retrieved!")
        print(f"\n  Task: {task['name']}")
        print(f"  Description: {task['description'][:100]}...")
        print(f"  Linked chunks: {len(knowledge)}")

        if knowledge:
            print(f"\n  Top knowledge chunks:")
            for i, chunk in enumerate(knowledge[:5], 1):
                print(f"\n  {i}. {chunk.get('title', 'Untitled')}")
                print(f"     URL: {chunk.get('url', 'N/A')[:60]}...")
                print(f"     Relevance: {chunk.get('relevance_score', 0)*100:.1f}%")
                print(f"     Tags: {', '.join(chunk.get('tags', [])[:5])}")
        else:
            print_warning("  No knowledge linked to this task yet.")

    except Exception as e:
        print_error(f"Failed to retrieve knowledge: {e}")

    wait_for_enter()


async def demo_view_analytics():
    """Demo: View project analytics."""
    clear_screen()
    print_header("📊 View Analytics")

    if not state.current_project_id:
        print_warning("No active project. Please create a project first.")
        wait_for_enter()
        return

    print_info("Gathering analytics...")

    try:
        # Get project
        project = await state.km.get_project(state.current_project_id)

        # Get tasks
        embedding_client, supabase = get_clients()
        tasks_result = supabase.table("tasks").select("*").eq("project_id", state.current_project_id).execute()
        tasks = tasks_result.data

        print_success("Analytics gathered!")

        print(f"\n  Project: {project['name']}")
        print(f"  Status: {project['status']}")
        print(f"  Priority: {project['priority']}")
        print(f"  Coverage: {(project.get('knowledge_coverage_score', 0)*100):.1f}%")

        print(f"\n  Tasks:")
        print(f"    • Total: {len(tasks)}")
        print(f"    • Completed: {sum(1 for t in tasks if t['status'] == 'completed')}")
        print(f"    • In Progress: {sum(1 for t in tasks if t['status'] == 'in_progress')}")
        print(f"    • Pending: {sum(1 for t in tasks if t['status'] == 'pending')}")

        # Knowledge stats
        all_tags = set()
        all_frameworks = set()
        for task in tasks:
            all_tags.update(task.get('required_knowledge_tags', []))
            all_frameworks.update(task.get('required_frameworks', []))

        print(f"\n  Knowledge Requirements:")
        print(f"    • Unique tags: {len(all_tags)}")
        print(f"    • Frameworks: {', '.join(all_frameworks) if all_frameworks else 'None'}")

    except Exception as e:
        print_error(f"Failed to gather analytics: {e}")

    wait_for_enter()


async def demo_explore_knowledge_base():
    """Demo: Explore the knowledge base."""
    clear_screen()
    print_header("🗄️ Explore Knowledge Base")

    print_info("Querying knowledge base...")

    try:
        embedding_client, supabase = get_clients()

        # Get total chunks
        result = supabase.table("site_pages").select("id", count="exact").execute()
        total_chunks = result.count

        # Get frameworks
        result = supabase.table("site_pages").select("framework").execute()
        frameworks = set(row['framework'] for row in result.data if row.get('framework'))

        # Get knowledge types
        result = supabase.table("site_pages").select("knowledge_type").execute()
        types = set(row['knowledge_type'] for row in result.data if row.get('knowledge_type'))

        # Get sources
        result = supabase.table("knowledge_sources").select("*").execute()
        sources = result.data

        print_success("Knowledge base explored!")

        print(f"\n  Database Statistics:")
        print(f"    • Total knowledge chunks: {total_chunks}")
        print(f"    • Frameworks: {len(frameworks)}")
        print(f"    • Knowledge types: {len(types)}")
        print(f"    • Sources: {len(sources)}")

        if frameworks:
            print(f"\n  Available Frameworks:")
            for fw in sorted(frameworks)[:10]:
                print(f"    • {fw}")

        if sources:
            print(f"\n  Knowledge Sources:")
            for source in sources[:5]:
                print(f"    • {source.get('name', 'Unnamed')}: {source.get('source_url', 'N/A')}")

    except Exception as e:
        print_error(f"Failed to explore knowledge base: {e}")

    wait_for_enter()


# ============================================================================
# MAIN MENU
# ============================================================================

async def main_menu():
    """Display and handle main menu."""
    while True:
        clear_screen()
        print_header("🎮 Archon Interactive Demo")

        print(f"{Colors.BOLD}Knowledge Management System - Interactive Walkthrough{Colors.END}\n")

        # Show current context
        if state.current_project_id:
            print(f"  Active Project: {Colors.CYAN}{state.current_project_id[:8]}...{Colors.END}")
        if state.current_task_id:
            print(f"  Active Task: {Colors.CYAN}{state.current_task_id[:8]}...{Colors.END}")
        if state.crawled_sources:
            print(f"  Crawled Sources: {Colors.CYAN}{len(state.crawled_sources)}{Colors.END}")
        print()

        options = [
            "Crawl Documentation",
            "Create Knowledge-Aware Project",
            "Decompose Project into Tasks",
            "Link Knowledge to Task",
            "View Task Knowledge",
            "View Project Analytics",
            "Explore Knowledge Base",
            "Exit"
        ]

        print_menu("Main Menu", options)

        choice = get_choice("Select an option:", range(1, len(options) + 1))

        if choice == 1:
            await demo_crawl_documentation()
        elif choice == 2:
            await demo_create_project()
        elif choice == 3:
            await demo_decompose_project()
        elif choice == 4:
            await demo_link_knowledge()
        elif choice == 5:
            await demo_view_knowledge()
        elif choice == 6:
            await demo_view_analytics()
        elif choice == 7:
            await demo_explore_knowledge_base()
        elif choice == 8:
            print_info("Thank you for using the Archon Interactive Demo!")
            break


# ============================================================================
# ENTRY POINT
# ============================================================================

async def main():
    """Main entry point."""
    try:
        # Initialize
        await state.initialize()

        # Welcome message
        clear_screen()
        print_header("Welcome to Archon Knowledge Management")
        print("\nThis interactive demo will guide you through the key features of Archon's")
        print("knowledge management system. You can explore at your own pace.\n")
        wait_for_enter("Press Enter to start...")

        # Run main menu
        await main_menu()

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted by user.{Colors.END}")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
