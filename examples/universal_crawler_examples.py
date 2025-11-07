"""
Universal Crawler Usage Examples

This file demonstrates various ways to use the Universal Web Scraper Agent
for Archon's knowledge management system.
"""

import asyncio
import sys
import os

# Add archon to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.universal_crawler import (
    SourceConfig,
    CrawlProfile,
    CRAWL_PROFILES,
    crawl_source,
    start_crawl_async,
    crawl_from_config_dict
)


# ============================================================================
# EXAMPLE 1: Simple Documentation Crawl
# ============================================================================

async def example_simple_crawl():
    """Crawl a documentation site with default settings."""

    config = SourceConfig(
        source_url="https://fastapi.tiangolo.com",
        source_type="documentation",
        framework="fastapi",
        language="python"
    )

    # Run the crawl
    stats = await crawl_source(config, profile_name='quick')

    print(f"\n✓ Crawled {stats['urls_succeeded']} pages")
    print(f"✓ Created {stats['chunks_stored']} knowledge chunks")
    print(f"✓ Completed in {stats['duration_seconds']} seconds")


# ============================================================================
# EXAMPLE 2: Deep Crawl with Progress Tracking
# ============================================================================

async def example_deep_crawl_with_progress():
    """Deep crawl with real-time progress updates."""

    config = SourceConfig(
        source_url="https://docs.pydantic.dev",
        source_type="documentation",
        framework="pydantic",
        language="python"
    )

    # Define progress callback
    def on_progress(status):
        if status['urls_found'] > 0:
            progress = status['progress_percentage']
            phase = status['current_phase']
            print(f"[{phase}] Progress: {progress:.1f}% | "
                  f"URLs: {status['urls_processed']}/{status['urls_found']} | "
                  f"Chunks: {status['chunks_stored']}")

    # Start async crawl with callback
    tracker = start_crawl_async(
        config=config,
        profile_name='deep',
        progress_callback=on_progress
    )

    # Wait for completion
    while tracker.is_running:
        await asyncio.sleep(2)

    # Show final stats
    final_status = tracker.get_status()
    print(f"\n✓ Crawl completed!")
    print(f"✓ Success rate: {final_status['urls_succeeded']}/{final_status['urls_found']}")
    print(f"✓ Total chunks stored: {final_status['chunks_stored']}")


# ============================================================================
# EXAMPLE 3: API-Only Crawl with Custom Patterns
# ============================================================================

async def example_api_only_crawl():
    """Crawl only API reference pages."""

    config = SourceConfig(
        source_url="https://api.github.com",
        source_type="api",
        framework="github-api",
        crawl_profile="api-only",
        url_patterns=[
            r'/v3/',  # API v3 endpoints
            r'/reference/',  # Reference docs
        ],
        exclude_patterns=[
            r'/guides/',  # Exclude guides
            r'/tutorials/',  # Exclude tutorials
        ],
        metadata={
            "api_version": "v3",
            "vendor": "github"
        }
    )

    stats = await crawl_source(config, profile_name='api-only')

    print(f"\n✓ Crawled {stats['urls_succeeded']} API pages")
    print(f"✓ Stored {stats['chunks_stored']} API reference chunks")


# ============================================================================
# EXAMPLE 4: Custom Crawl Profile
# ============================================================================

async def example_custom_profile():
    """Use a custom crawling profile for specific needs."""

    # Define custom profile
    custom_profile = CrawlProfile(
        name="tutorial-focused",
        depth=3,
        chunk_size=4000,
        max_pages=150,
        extract_code=True,
        summary_only=False,
        filter_pattern=r'/(tutorial|guide|example)/',
        max_concurrent=8,
        retry_count=2,
        request_delay=0.8
    )

    # Add to profiles
    from archon.universal_crawler import CRAWL_PROFILES
    CRAWL_PROFILES['tutorial-focused'] = custom_profile

    config = SourceConfig(
        source_url="https://www.djangoproject.com",
        source_type="tutorial",
        framework="django",
        language="python"
    )

    stats = await crawl_source(config, profile_name='tutorial-focused')

    print(f"\n✓ Tutorial crawl completed")
    print(f"✓ Pages: {stats['urls_succeeded']}")
    print(f"✓ Chunks: {stats['chunks_stored']}")


# ============================================================================
# EXAMPLE 5: Crawl from Database Configuration
# ============================================================================

async def example_crawl_from_database():
    """Crawl using configuration stored in the knowledge_sources table."""

    # This would typically come from your database
    db_config = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "source_url": "https://react.dev",
        "source_type": "documentation",
        "framework": "react",
        "language": "javascript",
        "crawl_config": {
            "profile": "deep",
            "sitemap_url": "https://react.dev/sitemap.xml",
            "url_patterns": [r'/learn/', r'/reference/'],
            "exclude_patterns": [r'/blog/']
        },
        "metadata": {
            "category": "frontend",
            "version": "18.x"
        }
    }

    # Crawl from config
    stats = await crawl_from_config_dict(db_config)

    print(f"\n✓ Crawled React documentation")
    print(f"✓ Success: {stats['urls_succeeded']}/{stats['urls_found']}")
    print(f"✓ Knowledge chunks: {stats['chunks_stored']}")


# ============================================================================
# EXAMPLE 6: Multiple Sources in Sequence
# ============================================================================

async def example_multiple_sources():
    """Crawl multiple documentation sources sequentially."""

    sources = [
        SourceConfig(
            source_url="https://numpy.org/doc/stable/",
            framework="numpy",
            language="python",
            source_type="documentation"
        ),
        SourceConfig(
            source_url="https://pandas.pydata.org/docs/",
            framework="pandas",
            language="python",
            source_type="documentation"
        ),
        SourceConfig(
            source_url="https://scikit-learn.org/stable/",
            framework="scikit-learn",
            language="python",
            source_type="documentation"
        )
    ]

    total_chunks = 0

    for i, config in enumerate(sources, 1):
        print(f"\n[{i}/{len(sources)}] Crawling {config.framework}...")

        stats = await crawl_source(config, profile_name='quick')
        total_chunks += stats['chunks_stored']

        print(f"  ✓ Stored {stats['chunks_stored']} chunks")

    print(f"\n✓ Total knowledge chunks across all sources: {total_chunks}")


# ============================================================================
# EXAMPLE 7: Crawl with Error Handling and Logging
# ============================================================================

async def example_robust_crawl():
    """Crawl with comprehensive error handling."""

    import logging

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    config = SourceConfig(
        source_url="https://vuejs.org",
        framework="vue",
        language="javascript",
        source_type="documentation"
    )

    try:
        # Track progress with detailed logging
        def log_progress(status):
            if status['is_running']:
                logging.info(
                    f"Phase: {status['current_phase']} | "
                    f"Progress: {status['progress_percentage']:.1f}% | "
                    f"Chunks: {status['chunks_stored']}"
                )
            else:
                logging.info("Crawl completed!")

        tracker = start_crawl_async(
            config=config,
            profile_name='default',
            progress_callback=log_progress
        )

        # Monitor until completion
        while tracker.is_running:
            await asyncio.sleep(1)

        # Check results
        status = tracker.get_status()

        if status['urls_failed'] > 0:
            logging.warning(f"{status['urls_failed']} URLs failed to crawl")

        if status['chunks_stored'] == 0:
            logging.error("No content was stored!")
        else:
            logging.info(f"Successfully stored {status['chunks_stored']} chunks")

    except Exception as e:
        logging.error(f"Crawl failed with error: {e}")
        raise


# ============================================================================
# EXAMPLE 8: Quick Knowledge Update
# ============================================================================

async def example_quick_update():
    """Quick update of existing knowledge base."""

    # Use quick profile for fast updates
    config = SourceConfig(
        source_url="https://docs.python.org/3/",
        framework="python",
        language="python",
        source_type="documentation"
    )

    print("Running quick knowledge update...")

    stats = await crawl_source(config, profile_name='quick')

    print(f"\n✓ Update completed in {stats['duration_seconds']}s")
    print(f"✓ Refreshed {stats['urls_succeeded']} pages")
    print(f"✓ Updated {stats['chunks_stored']} knowledge chunks")


# ============================================================================
# MAIN RUNNER
# ============================================================================

async def main():
    """Run all examples (comment out as needed)."""

    print("=" * 80)
    print("UNIVERSAL CRAWLER EXAMPLES")
    print("=" * 80)

    # Run one example at a time (uncomment the one you want to test)

    # await example_simple_crawl()
    # await example_deep_crawl_with_progress()
    # await example_api_only_crawl()
    # await example_custom_profile()
    # await example_crawl_from_database()
    # await example_multiple_sources()
    # await example_robust_crawl()
    await example_quick_update()

    print("\n" + "=" * 80)
    print("EXAMPLES COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
