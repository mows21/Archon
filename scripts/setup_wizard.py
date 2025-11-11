#!/usr/bin/env python3
"""
Archon Knowledge Management Setup Wizard

Interactive setup script that guides you through configuring Archon.
Includes validation, testing, and helpful error messages.

Usage:
    python scripts/setup_wizard.py
    python scripts/setup_wizard.py --dry-run
    python scripts/setup_wizard.py --skip-crawl
"""

import os
import sys
import json
import asyncio
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Rich imports for beautiful CLI output
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown
from rich import box
from rich.syntax import Syntax

console = Console()


class ArchonSetupWizard:
    """Interactive setup wizard for Archon Knowledge Management System."""

    def __init__(self, dry_run: bool = False, skip_crawl: bool = False):
        """Initialize the setup wizard.

        Args:
            dry_run: If True, don't actually make changes
            skip_crawl: If True, skip the test crawl step
        """
        self.dry_run = dry_run
        self.skip_crawl = skip_crawl
        self.workbench_dir = Path(__file__).parent.parent / "workbench"
        self.env_vars_file = self.workbench_dir / "env_vars.json"
        self.schema_file = Path(__file__).parent.parent / "utils" / "knowledge_schema.sql"
        self.config = {}
        self.validation_results = {}

    def print_banner(self):
        """Print welcome banner."""
        banner = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   🤖  ARCHON KNOWLEDGE MANAGEMENT SETUP WIZARD  🤖       ║
║                                                           ║
║   Welcome! This wizard will guide you through            ║
║   setting up Archon's knowledge-aware AI system.         ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
        """
        console.print(banner, style="bold cyan")
        console.print()

    def check_prerequisites(self) -> bool:
        """Check system prerequisites.

        Returns:
            True if all prerequisites are met
        """
        console.print(Panel.fit("📋 Checking Prerequisites", style="bold yellow"))

        # Check Python version
        python_version = sys.version_info
        if python_version >= (3, 11):
            console.print(f"✓ Python {python_version.major}.{python_version.minor}.{python_version.micro} detected", style="green")
        else:
            console.print(f"✗ Python 3.11+ required (found {python_version.major}.{python_version.minor})", style="red")
            return False

        # Check pip
        try:
            import pip
            console.print("✓ pip available", style="green")
        except ImportError:
            console.print("✗ pip not found", style="red")
            return False

        # Check required packages
        required_packages = [
            ("rich", "Rich"),
            ("openai", "OpenAI"),
            ("supabase", "Supabase"),
            ("requests", "Requests"),
        ]

        missing_packages = []
        for module_name, display_name in required_packages:
            try:
                __import__(module_name)
                console.print(f"✓ {display_name} installed", style="green")
            except ImportError:
                console.print(f"✗ {display_name} not installed", style="red")
                missing_packages.append(display_name)

        if missing_packages:
            console.print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}", style="yellow")
            console.print("Run: pip install -r requirements.txt", style="yellow")
            return False

        # Check workbench directory
        if not self.workbench_dir.exists():
            console.print(f"Creating workbench directory: {self.workbench_dir}", style="yellow")
            if not self.dry_run:
                self.workbench_dir.mkdir(parents=True, exist_ok=True)
            console.print("✓ Workbench directory ready", style="green")
        else:
            console.print(f"✓ Workbench directory exists", style="green")

        console.print()
        return True

    def load_existing_config(self) -> Dict[str, Any]:
        """Load existing configuration if available.

        Returns:
            Existing config or empty dict
        """
        if self.env_vars_file.exists():
            try:
                with open(self.env_vars_file, 'r') as f:
                    config = json.load(f)
                console.print(f"✓ Loaded existing configuration from {self.env_vars_file}", style="green")
                return config
            except Exception as e:
                console.print(f"⚠️  Could not load existing config: {e}", style="yellow")
        return {}

    def prompt_for_config(self):
        """Prompt user for configuration values."""
        console.print(Panel.fit("📝 Configuration", style="bold yellow"))
        console.print("Please provide the following configuration values.\n")
        console.print("Press Enter to keep existing values (shown in brackets).\n", style="dim")

        existing_config = self.load_existing_config()

        # Supabase configuration
        console.print("[bold cyan]Supabase Configuration[/bold cyan]")
        console.print("Get these from: https://supabase.com → Your Project → Settings → API\n", style="dim")

        self.config['SUPABASE_URL'] = Prompt.ask(
            "Supabase Project URL",
            default=existing_config.get('SUPABASE_URL', '')
        )

        self.config['SUPABASE_SERVICE_KEY'] = Prompt.ask(
            "Supabase Service Role Key",
            default=existing_config.get('SUPABASE_SERVICE_KEY', ''),
            password=True
        )

        console.print()

        # LLM configuration
        console.print("[bold cyan]LLM Configuration[/bold cyan]")

        llm_provider = Prompt.ask(
            "LLM Provider",
            choices=["OpenAI", "Anthropic", "OpenRouter", "Ollama"],
            default=existing_config.get('LLM_PROVIDER', 'OpenAI')
        )
        self.config['LLM_PROVIDER'] = llm_provider

        if llm_provider != "Ollama":
            self.config['LLM_API_KEY'] = Prompt.ask(
                f"{llm_provider} API Key",
                default=existing_config.get('LLM_API_KEY', ''),
                password=True
            )
        else:
            self.config['LLM_API_KEY'] = "NOT_REQUIRED"

        # Model selection based on provider
        if llm_provider == "OpenAI":
            default_model = "gpt-4o-mini"
            model_choices = ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        elif llm_provider == "Anthropic":
            default_model = "claude-3-5-sonnet-20241022"
            model_choices = ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"]
        elif llm_provider == "Ollama":
            default_model = "llama3.1"
            model_choices = ["llama3.1", "mistral", "codellama", "phi3"]
        else:
            default_model = "gpt-4o-mini"
            model_choices = None

        if model_choices:
            self.config['PRIMARY_MODEL'] = Prompt.ask(
                "Primary Model",
                choices=model_choices,
                default=existing_config.get('PRIMARY_MODEL', default_model)
            )
            self.config['REASONING_MODEL'] = Prompt.ask(
                "Reasoning Model",
                choices=model_choices,
                default=existing_config.get('REASONING_MODEL', default_model)
            )
        else:
            self.config['PRIMARY_MODEL'] = Prompt.ask(
                "Primary Model",
                default=existing_config.get('PRIMARY_MODEL', default_model)
            )
            self.config['REASONING_MODEL'] = Prompt.ask(
                "Reasoning Model",
                default=existing_config.get('REASONING_MODEL', default_model)
            )

        # Base URL for Ollama or custom endpoints
        if llm_provider == "Ollama":
            self.config['BASE_URL'] = Prompt.ask(
                "Ollama Base URL",
                default=existing_config.get('BASE_URL', 'http://localhost:11434/v1')
            )
        elif llm_provider == "OpenRouter":
            self.config['BASE_URL'] = "https://openrouter.ai/api/v1"
        else:
            self.config['BASE_URL'] = existing_config.get('BASE_URL', 'https://api.openai.com/v1')

        console.print()

        # Embedding configuration
        console.print("[bold cyan]Embedding Configuration[/bold cyan]")

        embedding_provider = Prompt.ask(
            "Embedding Provider",
            choices=["OpenAI", "Ollama"],
            default=existing_config.get('EMBEDDING_PROVIDER', 'OpenAI')
        )
        self.config['EMBEDDING_PROVIDER'] = embedding_provider

        if embedding_provider == "OpenAI":
            self.config['EMBEDDING_API_KEY'] = Prompt.ask(
                "OpenAI API Key (for embeddings)",
                default=self.config.get('LLM_API_KEY', existing_config.get('EMBEDDING_API_KEY', '')),
                password=True
            )
            self.config['EMBEDDING_MODEL'] = Prompt.ask(
                "Embedding Model",
                choices=["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"],
                default=existing_config.get('EMBEDDING_MODEL', 'text-embedding-3-small')
            )
        else:  # Ollama
            self.config['EMBEDDING_API_KEY'] = "NOT_REQUIRED"
            self.config['EMBEDDING_MODEL'] = Prompt.ask(
                "Embedding Model",
                default=existing_config.get('EMBEDDING_MODEL', 'nomic-embed-text')
            )

        console.print()

    def test_supabase_connection(self) -> bool:
        """Test Supabase connection.

        Returns:
            True if connection successful
        """
        console.print(Panel.fit("🗄️  Testing Database Connection", style="bold yellow"))

        if self.dry_run:
            console.print("✓ Dry run - skipping connection test", style="yellow")
            return True

        try:
            from supabase import create_client, Client

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("Connecting to Supabase...", total=None)

                supabase: Client = create_client(
                    self.config['SUPABASE_URL'],
                    self.config['SUPABASE_SERVICE_KEY']
                )

                progress.update(task, description="Testing query...")

                # Try a simple query
                result = supabase.table('site_pages').select('id').limit(1).execute()

                progress.update(task, description="Connection successful!", completed=True)

            console.print("✓ Supabase connection successful", style="green")

            # Check if knowledge schema exists
            try:
                result = supabase.table('projects').select('id').limit(1).execute()
                console.print("✓ Knowledge management tables detected", style="green")
                self.validation_results['schema_exists'] = True
            except Exception:
                console.print("⚠️  Knowledge management tables not found", style="yellow")
                console.print("   (We'll set this up in the next step)", style="dim")
                self.validation_results['schema_exists'] = False

            console.print()
            return True

        except Exception as e:
            console.print(f"✗ Supabase connection failed: {str(e)}", style="red")
            console.print("\nTroubleshooting:", style="yellow")
            console.print("1. Verify your Supabase URL format: https://xxxxx.supabase.co")
            console.print("2. Ensure you're using the Service Role Key (not anon key)")
            console.print("3. Check that your Supabase project is running")
            console.print()
            return False

    def test_llm_connection(self) -> bool:
        """Test LLM API connection.

        Returns:
            True if connection successful
        """
        console.print(Panel.fit("🤖 Testing LLM Connection", style="bold yellow"))

        if self.dry_run:
            console.print("✓ Dry run - skipping LLM test", style="yellow")
            return True

        try:
            from openai import OpenAI

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("Connecting to LLM API...", total=None)

                client = OpenAI(
                    api_key=self.config['LLM_API_KEY'],
                    base_url=self.config.get('BASE_URL', 'https://api.openai.com/v1')
                )

                progress.update(task, description="Testing API call...")

                response = client.chat.completions.create(
                    model=self.config['PRIMARY_MODEL'],
                    messages=[{"role": "user", "content": "Say 'test' if you can read this."}],
                    max_tokens=10
                )

                progress.update(task, description="Connection successful!", completed=True)

            console.print(f"✓ LLM API connection successful", style="green")
            console.print(f"  Model: {self.config['PRIMARY_MODEL']}", style="dim")
            console.print(f"  Response: {response.choices[0].message.content}", style="dim")
            console.print()
            return True

        except Exception as e:
            console.print(f"✗ LLM API connection failed: {str(e)}", style="red")
            console.print("\nTroubleshooting:", style="yellow")
            console.print("1. Verify your API key is correct")
            console.print("2. Check that you have credits/quota available")
            console.print("3. Ensure the model name is correct")
            console.print("4. For Ollama: ensure Ollama is running (ollama serve)")
            console.print()
            return False

    def test_embedding_connection(self) -> bool:
        """Test embedding API connection.

        Returns:
            True if connection successful
        """
        console.print(Panel.fit("🔢 Testing Embedding Connection", style="bold yellow"))

        if self.dry_run:
            console.print("✓ Dry run - skipping embedding test", style="yellow")
            return True

        try:
            from openai import OpenAI

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("Connecting to Embedding API...", total=None)

                if self.config['EMBEDDING_PROVIDER'] == 'OpenAI':
                    client = OpenAI(api_key=self.config['EMBEDDING_API_KEY'])
                else:  # Ollama
                    client = OpenAI(
                        api_key="ollama",
                        base_url=self.config.get('BASE_URL', 'http://localhost:11434/v1')
                    )

                progress.update(task, description="Generating test embedding...")

                response = client.embeddings.create(
                    model=self.config['EMBEDDING_MODEL'],
                    input="test"
                )

                embedding_dim = len(response.data[0].embedding)
                progress.update(task, description="Connection successful!", completed=True)

            console.print(f"✓ Embedding API connection successful", style="green")
            console.print(f"  Model: {self.config['EMBEDDING_MODEL']}", style="dim")
            console.print(f"  Dimensions: {embedding_dim}", style="dim")

            # Warn if dimension mismatch
            if embedding_dim != 1536:
                console.print(f"\n⚠️  Warning: Embedding dimension is {embedding_dim}, but schema expects 1536", style="yellow")
                console.print("   You may need to update the database schema to match.", style="dim")

            console.print()
            return True

        except Exception as e:
            console.print(f"✗ Embedding API connection failed: {str(e)}", style="red")
            console.print("\nTroubleshooting:", style="yellow")
            console.print("1. Verify your API key is correct")
            console.print("2. For Ollama: ensure the embedding model is pulled (ollama pull nomic-embed-text)")
            console.print()
            return False

    def save_config(self) -> bool:
        """Save configuration to file.

        Returns:
            True if save successful
        """
        console.print(Panel.fit("💾 Saving Configuration", style="bold yellow"))

        if self.dry_run:
            console.print("✓ Dry run - configuration not saved", style="yellow")
            console.print("\nConfiguration that would be saved:", style="dim")
            # Redact sensitive info for display
            display_config = self.config.copy()
            for key in ['SUPABASE_SERVICE_KEY', 'LLM_API_KEY', 'EMBEDDING_API_KEY']:
                if key in display_config and display_config[key]:
                    display_config[key] = display_config[key][:8] + "..." if len(display_config[key]) > 8 else "***"
            syntax = Syntax(json.dumps(display_config, indent=2), "json", theme="monokai")
            console.print(syntax)
            console.print()
            return True

        try:
            # Ensure workbench directory exists
            self.workbench_dir.mkdir(parents=True, exist_ok=True)

            # Save configuration
            with open(self.env_vars_file, 'w') as f:
                json.dump(self.config, f, indent=2)

            console.print(f"✓ Configuration saved to {self.env_vars_file}", style="green")
            console.print()
            return True

        except Exception as e:
            console.print(f"✗ Failed to save configuration: {e}", style="red")
            console.print()
            return False

    def setup_database_schema(self) -> bool:
        """Offer to set up database schema.

        Returns:
            True if setup successful or skipped
        """
        console.print(Panel.fit("🗄️  Database Schema Setup", style="bold yellow"))

        if self.validation_results.get('schema_exists', False):
            console.print("✓ Knowledge management schema already exists", style="green")

            if Confirm.ask("Do you want to re-run the schema (safe - won't delete data)?", default=False):
                pass  # Continue to schema execution
            else:
                console.print("Skipping schema setup", style="dim")
                console.print()
                return True

        if not self.schema_file.exists():
            console.print(f"✗ Schema file not found: {self.schema_file}", style="red")
            console.print()
            return False

        console.print(f"Schema file: {self.schema_file}", style="dim")
        console.print()
        console.print("The schema includes:", style="cyan")
        console.print("  • Enhanced site_pages table with tags and metadata")
        console.print("  • Projects and tasks tables")
        console.print("  • Knowledge linking tables")
        console.print("  • Advanced RPC functions for knowledge search")
        console.print()

        if not Confirm.ask("Run database schema setup?", default=True):
            console.print("Skipping database schema setup", style="yellow")
            console.print()
            console.print("⚠️  You'll need to run this manually:", style="yellow")
            console.print(f"   1. Open Supabase SQL Editor")
            console.print(f"   2. Copy contents of: {self.schema_file}")
            console.print(f"   3. Execute the SQL")
            console.print()
            return True

        if self.dry_run:
            console.print("✓ Dry run - schema not executed", style="yellow")
            console.print()
            return True

        try:
            from supabase import create_client, Client

            # Read schema file
            with open(self.schema_file, 'r') as f:
                schema_sql = f.read()

            # Connect to Supabase
            supabase: Client = create_client(
                self.config['SUPABASE_URL'],
                self.config['SUPABASE_SERVICE_KEY']
            )

            console.print("⚠️  Note: Supabase client doesn't support direct SQL execution", style="yellow")
            console.print("   You'll need to run the schema manually in Supabase SQL Editor\n")

            console.print("Instructions:", style="cyan")
            console.print("1. Open Supabase Dashboard → SQL Editor")
            console.print("2. Create a new query")
            console.print(f"3. Copy contents of: {self.schema_file}")
            console.print("4. Paste and execute")
            console.print()

            if Confirm.ask("Have you executed the schema in Supabase?", default=False):
                # Verify schema was created
                try:
                    result = supabase.table('projects').select('id').limit(1).execute()
                    console.print("✓ Schema verified successfully!", style="green")
                    console.print()
                    return True
                except Exception as e:
                    console.print(f"⚠️  Could not verify schema: {e}", style="yellow")
                    console.print("   Continuing anyway...", style="dim")
                    console.print()
                    return True
            else:
                console.print("⚠️  Schema not executed - you'll need to do this manually", style="yellow")
                console.print()
                return True

        except Exception as e:
            console.print(f"✗ Schema setup failed: {e}", style="red")
            console.print()
            return False

    async def run_test_crawl(self) -> bool:
        """Run a small test crawl.

        Returns:
            True if crawl successful
        """
        if self.skip_crawl:
            console.print("Skipping test crawl (--skip-crawl flag)", style="yellow")
            console.print()
            return True

        console.print(Panel.fit("🧪 Test Crawl", style="bold yellow"))
        console.print("Let's test the system by crawling a small documentation page.\n")

        if not Confirm.ask("Run test crawl?", default=True):
            console.print("Skipping test crawl", style="yellow")
            console.print()
            return True

        if self.dry_run:
            console.print("✓ Dry run - crawl not executed", style="yellow")
            console.print()
            return True

        try:
            # Import crawler
            from archon.crawl_pydantic_ai_docs import process_and_store_document, fetch_url_content

            # Test URL
            test_url = "https://ai.pydantic.dev/"

            console.print(f"Crawling: {test_url}", style="dim")
            console.print()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task = progress.add_task("Fetching page...", total=3)

                # Fetch content
                loop = asyncio.get_event_loop()
                markdown = await loop.run_in_executor(None, fetch_url_content, test_url)
                progress.update(task, advance=1, description="Processing document...")

                # Process and store
                await process_and_store_document(test_url, markdown, None)
                progress.update(task, advance=1, description="Storing chunks...")

                progress.update(task, advance=1, description="Complete!", completed=True)

            console.print("✓ Test crawl successful!", style="green")
            console.print(f"  Crawled: {test_url}", style="dim")
            console.print()
            return True

        except Exception as e:
            console.print(f"✗ Test crawl failed: {e}", style="red")
            console.print("\nThis is okay - you can crawl documentation later from the UI.", style="yellow")
            console.print()
            return True  # Don't fail setup on crawl failure

    def verify_setup(self) -> bool:
        """Verify entire setup.

        Returns:
            True if all checks pass
        """
        console.print(Panel.fit("✅ Verifying Setup", style="bold yellow"))

        checks = [
            ("Configuration file exists", self.env_vars_file.exists()),
            ("Supabase connection", self.validation_results.get('supabase_connection', False)),
            ("LLM connection", self.validation_results.get('llm_connection', False)),
            ("Embedding connection", self.validation_results.get('embedding_connection', False)),
        ]

        table = Table(show_header=True, header_style="bold cyan", box=box.ROUNDED)
        table.add_column("Check", style="white")
        table.add_column("Status", style="white")

        all_passed = True
        for check_name, passed in checks:
            status = "✓ Pass" if passed else "✗ Fail"
            style = "green" if passed else "red"
            table.add_row(check_name, f"[{style}]{status}[/{style}]")
            all_passed = all_passed and passed

        console.print(table)
        console.print()

        return all_passed

    def print_next_steps(self):
        """Print next steps for the user."""
        console.print(Panel.fit("🎉 Setup Complete!", style="bold green"))

        console.print("Next steps:", style="bold cyan")
        console.print()
        console.print("1. Start the Streamlit UI:")
        console.print("   [bold]streamlit run streamlit_ui.py[/bold]")
        console.print()
        console.print("2. Go to the [cyan]Documentation[/cyan] tab and crawl documentation:")
        console.print("   • Pydantic AI docs (built-in)")
        console.print("   • Any other framework docs you need")
        console.print()
        console.print("3. Go to the [cyan]Projects[/cyan] tab and create your first project:")
        console.print("   • Enter project name and description")
        console.print("   • Enable 'Auto-discover knowledge'")
        console.print("   • Archon will automatically find relevant docs!")
        console.print()
        console.print("4. Explore the knowledge management features:")
        console.print("   • View linked knowledge for tasks")
        console.print("   • Check coverage scores")
        console.print("   • Execute tasks with injected context")
        console.print()
        console.print("Need help?", style="bold yellow")
        console.print("  • Quick Start Guide: docs/QUICK_START_GUIDE.md")
        console.print("  • Troubleshooting: docs/TROUBLESHOOTING.md")
        console.print("  • Community Forum: https://thinktank.ottomator.ai/c/archon/30")
        console.print()
        console.print("Happy building! 🚀", style="bold green")

    async def run(self):
        """Run the setup wizard."""
        self.print_banner()

        # Step 1: Check prerequisites
        if not self.check_prerequisites():
            console.print("❌ Prerequisites not met. Please install required packages.", style="red")
            return False

        # Step 2: Prompt for configuration
        self.prompt_for_config()

        # Step 3: Test Supabase connection
        self.validation_results['supabase_connection'] = self.test_supabase_connection()
        if not self.validation_results['supabase_connection']:
            if not Confirm.ask("Supabase connection failed. Continue anyway?", default=False):
                return False

        # Step 4: Test LLM connection
        self.validation_results['llm_connection'] = self.test_llm_connection()
        if not self.validation_results['llm_connection']:
            if not Confirm.ask("LLM connection failed. Continue anyway?", default=False):
                return False

        # Step 5: Test embedding connection
        self.validation_results['embedding_connection'] = self.test_embedding_connection()
        if not self.validation_results['embedding_connection']:
            if not Confirm.ask("Embedding connection failed. Continue anyway?", default=False):
                return False

        # Step 6: Save configuration
        if not self.save_config():
            console.print("❌ Failed to save configuration", style="red")
            return False

        # Step 7: Set up database schema
        if not self.setup_database_schema():
            console.print("⚠️  Database schema setup incomplete", style="yellow")

        # Step 8: Run test crawl
        await self.run_test_crawl()

        # Step 9: Verify setup
        if self.verify_setup():
            self.print_next_steps()
            return True
        else:
            console.print("⚠️  Some checks failed, but you can continue.", style="yellow")
            console.print("Check the Troubleshooting guide if you encounter issues.", style="yellow")
            return True


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Archon Knowledge Management Setup Wizard")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--skip-crawl", action="store_true", help="Skip the test crawl step")
    args = parser.parse_args()

    wizard = ArchonSetupWizard(dry_run=args.dry_run, skip_crawl=args.skip_crawl)

    try:
        success = await wizard.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        console.print("\n\n❌ Setup cancelled by user", style="red")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n\n❌ Unexpected error: {e}", style="red")
        console.print("\nPlease report this issue: https://github.com/coleam00/archon/issues", style="yellow")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
