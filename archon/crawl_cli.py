#!/usr/bin/env python3
"""
Universal Crawler CLI Tool

Quick command-line interface for crawling documentation sources.

Usage:
    python archon/crawl_cli.py https://fastapi.tiangolo.com --profile deep
    python archon/crawl_cli.py https://docs.python.org --framework python --language python
    python archon/crawl_cli.py --from-db source-id-here
"""

import asyncio
import argparse
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.universal_crawler import (
    SourceConfig,
    CRAWL_PROFILES,
    crawl_source,
    start_crawl_async,
    crawl_from_config_dict
)
from utils.utils import get_clients


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Universal Web Scraper for Archon Knowledge Management',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Quick crawl of FastAPI docs
  %(prog)s https://fastapi.tiangolo.com --profile quick

  # Deep crawl with framework and language specified
  %(prog)s https://docs.pydantic.dev --framework pydantic --language python --profile deep

  # Crawl with custom sitemap
  %(prog)s https://docs.example.com --sitemap https://docs.example.com/sitemap.xml

  # API-only crawl with URL patterns
  %(prog)s https://api.github.com --profile api-only --include "/v3/" --include "/reference/"

  # Crawl from database configuration
  %(prog)s --from-db 550e8400-e29b-41d4-a716-446655440000

  # List available profiles
  %(prog)s --list-profiles
        """
    )

    # Main arguments
    parser.add_argument(
        'url',
        nargs='?',
        help='Documentation URL to crawl'
    )

    parser.add_argument(
        '--from-db',
        metavar='SOURCE_ID',
        help='Crawl from knowledge_sources table using source ID'
    )

    # Configuration
    parser.add_argument(
        '--profile',
        choices=['quick', 'deep', 'api-only', 'default'],
        default='default',
        help='Crawling profile to use (default: default)'
    )

    parser.add_argument(
        '--framework',
        help='Framework name (e.g., fastapi, react, django). Auto-detected if not specified.'
    )

    parser.add_argument(
        '--language',
        help='Programming language (e.g., python, javascript). Auto-detected if not specified.'
    )

    parser.add_argument(
        '--type',
        dest='source_type',
        choices=['documentation', 'github', 'tutorial', 'blog', 'api', 'other'],
        default='documentation',
        help='Type of source (default: documentation)'
    )

    # Advanced options
    parser.add_argument(
        '--sitemap',
        help='Explicit sitemap URL'
    )

    parser.add_argument(
        '--include',
        action='append',
        metavar='PATTERN',
        help='URL pattern to include (regex). Can be specified multiple times.'
    )

    parser.add_argument(
        '--exclude',
        action='append',
        metavar='PATTERN',
        help='URL pattern to exclude (regex). Can be specified multiple times.'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        help='Maximum number of pages to crawl (overrides profile setting)'
    )

    parser.add_argument(
        '--chunk-size',
        type=int,
        help='Text chunk size (overrides profile setting)'
    )

    # Output control
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Detailed output'
    )

    parser.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    # Utility
    parser.add_argument(
        '--list-profiles',
        action='store_true',
        help='List available crawling profiles and exit'
    )

    return parser.parse_args()


def list_profiles():
    """Display available crawling profiles."""
    print("\n" + "=" * 80)
    print("AVAILABLE CRAWLING PROFILES")
    print("=" * 80 + "\n")

    for name, profile in CRAWL_PROFILES.items():
        print(f"Profile: {name}")
        print(f"  Depth: {profile.depth} levels")
        print(f"  Chunk Size: {profile.chunk_size} characters")
        print(f"  Max Pages: {profile.max_pages}")
        print(f"  Extract Code: {profile.extract_code}")
        print(f"  Concurrency: {profile.max_concurrent}")
        print(f"  Request Delay: {profile.request_delay}s")
        if profile.filter_pattern:
            print(f"  Filter Pattern: {profile.filter_pattern}")
        print()


async def crawl_from_database(source_id: str, args):
    """Crawl using configuration from database."""
    _, supabase = get_clients()

    if not supabase:
        print("Error: Supabase client not configured")
        sys.exit(1)

    # Fetch source configuration
    try:
        result = supabase.table("knowledge_sources").select("*").eq("id", source_id).single().execute()
        if not result.data:
            print(f"Error: Source ID '{source_id}' not found in database")
            sys.exit(1)

        source_config = result.data
        print(f"\nCrawling source: {source_config['source_url']}")
        print(f"Framework: {source_config.get('framework', 'auto-detect')}")
        print(f"Type: {source_config.get('source_type', 'documentation')}\n")

    except Exception as e:
        print(f"Error fetching source from database: {e}")
        sys.exit(1)

    # Progress callback
    def progress_callback(status):
        if not args.quiet and not args.no_progress:
            if status['is_running']:
                print(f"\r[{status['current_phase']}] "
                      f"Progress: {status['progress_percentage']:.1f}% | "
                      f"URLs: {status['urls_processed']}/{status['urls_found']} | "
                      f"Chunks: {status['chunks_stored']}", end='', flush=True)
            else:
                print()  # New line after completion

    # Run crawl
    stats = await crawl_from_config_dict(source_config)

    # Display results
    if not args.quiet:
        print_results(stats)


async def crawl_from_url(args):
    """Crawl from URL with CLI arguments."""

    if not args.url:
        print("Error: URL required (or use --from-db)")
        sys.exit(1)

    # Build configuration
    config = SourceConfig(
        source_url=args.url,
        source_type=args.source_type,
        framework=args.framework,
        language=args.language,
        crawl_profile=args.profile,
        sitemap_url=args.sitemap,
        url_patterns=args.include or [],
        exclude_patterns=args.exclude or []
    )

    # Override profile settings if specified
    from archon.universal_crawler import CRAWL_PROFILES
    profile = CRAWL_PROFILES[args.profile]

    if args.max_pages:
        profile.max_pages = args.max_pages
    if args.chunk_size:
        profile.chunk_size = args.chunk_size

    # Display configuration
    if not args.quiet:
        print("\n" + "=" * 80)
        print("CRAWL CONFIGURATION")
        print("=" * 80)
        print(f"URL: {config.source_url}")
        print(f"Profile: {args.profile}")
        print(f"Framework: {config.framework or 'auto-detect'}")
        print(f"Language: {config.language or 'auto-detect'}")
        print(f"Type: {config.source_type}")
        if config.sitemap_url:
            print(f"Sitemap: {config.sitemap_url}")
        if config.url_patterns:
            print(f"Include patterns: {config.url_patterns}")
        if config.exclude_patterns:
            print(f"Exclude patterns: {config.exclude_patterns}")
        print("=" * 80 + "\n")

    # Progress callback
    last_phase = [None]

    def progress_callback(status):
        if args.quiet or args.no_progress:
            return

        # Show phase changes
        if status['current_phase'] != last_phase[0]:
            if last_phase[0] is not None:
                print()  # New line for new phase
            last_phase[0] = status['current_phase']

        if status['is_running']:
            print(f"\r[{status['current_phase']}] "
                  f"Progress: {status['progress_percentage']:.1f}% | "
                  f"URLs: {status['urls_processed']}/{status['urls_found']} | "
                  f"Chunks: {status['chunks_stored']}", end='', flush=True)
        else:
            print()  # New line after completion

    # Run crawl
    if args.verbose:
        # Show all logs
        def verbose_callback(status):
            for log in status['logs'][-1:]:  # Last log entry
                print(log)

        tracker = start_crawl_async(config, args.profile, verbose_callback)
        while tracker.is_running:
            await asyncio.sleep(0.5)
        stats = tracker.get_status()
    else:
        # Use progress bar
        tracker = start_crawl_async(config, args.profile, progress_callback)
        while tracker.is_running:
            await asyncio.sleep(0.5)
        stats = tracker.get_status()

    # Display results
    if not args.quiet:
        print_results(stats)


def print_results(stats):
    """Print crawl results."""
    print("\n" + "=" * 80)
    print("CRAWL RESULTS")
    print("=" * 80)

    # Success/failure
    total_urls = stats.get('urls_found', 0)
    succeeded = stats.get('urls_succeeded', 0)
    failed = stats.get('urls_failed', 0)
    chunks = stats.get('chunks_stored', 0)
    duration = stats.get('duration_seconds', 0)

    print(f"\nURLs Processed: {succeeded + failed}/{total_urls}")
    print(f"  ✓ Succeeded: {succeeded}")
    if failed > 0:
        print(f"  ✗ Failed: {failed}")

    print(f"\nKnowledge Chunks: {chunks}")

    if duration:
        print(f"Duration: {duration}s ({duration // 60}m {duration % 60}s)")

    # Success rate
    if total_urls > 0:
        success_rate = (succeeded / total_urls) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")

        # Status indicator
        if success_rate == 100:
            print("Status: ✓ Perfect!")
        elif success_rate >= 90:
            print("Status: ✓ Excellent")
        elif success_rate >= 75:
            print("Status: ⚠ Good (some failures)")
        else:
            print("Status: ⚠ Poor (many failures)")

    print("\n" + "=" * 80 + "\n")


async def main():
    """Main CLI entry point."""
    args = parse_args()

    # List profiles
    if args.list_profiles:
        list_profiles()
        sys.exit(0)

    # Validate arguments
    if not args.url and not args.from_db:
        print("Error: Either URL or --from-db is required")
        print("Use --help for usage information")
        sys.exit(1)

    # Run appropriate crawl
    try:
        if args.from_db:
            await crawl_from_database(args.from_db, args)
        else:
            await crawl_from_url(args)

    except KeyboardInterrupt:
        print("\n\nCrawl interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
