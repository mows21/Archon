"""
Performance Benchmark Suite for Archon Knowledge Management

Benchmarks key operations to measure performance and identify bottlenecks:
- Embedding generation speed
- Knowledge search performance
- Task linking speed
- Database operations
- End-to-end workflow timing

Usage:
    python demos/performance_benchmark.py
    python demos/performance_benchmark.py --quick     # Run quick benchmark
    python demos/performance_benchmark.py --full      # Run comprehensive benchmark
    python demos/performance_benchmark.py --export    # Export results to CSV

Output:
    - Terminal output with timing statistics
    - Optional CSV export for analysis
    - Performance recommendations
"""

import os
import sys
import asyncio
import time
import statistics
from datetime import datetime
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field
import csv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from archon.knowledge_manager import KnowledgeManager
from archon.knowledge_linker import get_embedding, analyze_task_requirements
from utils.utils import get_clients

# ============================================================================
# BENCHMARK CONFIGURATION
# ============================================================================

@dataclass
class BenchmarkConfig:
    """Configuration for benchmark tests."""
    quick_mode: bool = False
    iterations_quick: int = 5
    iterations_full: int = 20
    export_results: bool = False
    export_path: str = "performance_results.csv"


@dataclass
class BenchmarkResult:
    """Result of a benchmark test."""
    name: str
    operation: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    median_time: float
    std_dev: float
    throughput: float  # operations per second
    unit: str = "ms"
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# BENCHMARK UTILITIES
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
    END = '\033[0m'


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*80}{Colors.END}\n")


def print_subheader(text: str):
    """Print formatted subheader."""
    print(f"\n{Colors.BOLD}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'─'*80}{Colors.END}")


def format_time(ms: float) -> str:
    """Format time in ms with appropriate unit."""
    if ms < 1:
        return f"{ms*1000:.2f}μs"
    elif ms < 1000:
        return f"{ms:.2f}ms"
    else:
        return f"{ms/1000:.2f}s"


def format_throughput(ops_per_sec: float) -> str:
    """Format throughput."""
    if ops_per_sec >= 1000:
        return f"{ops_per_sec/1000:.2f}k ops/sec"
    else:
        return f"{ops_per_sec:.2f} ops/sec"


def print_result(result: BenchmarkResult):
    """Print benchmark result."""
    print(f"\n  {Colors.BOLD}{result.name}{Colors.END}")
    print(f"    Iterations: {result.iterations}")
    print(f"    Average:    {format_time(result.avg_time)}")
    print(f"    Min:        {format_time(result.min_time)}")
    print(f"    Max:        {format_time(result.max_time)}")
    print(f"    Median:     {format_time(result.median_time)}")
    print(f"    Std Dev:    {format_time(result.std_dev)}")
    print(f"    Throughput: {format_throughput(result.throughput)}")


async def time_async_operation(operation, *args, **kwargs) -> float:
    """Time an async operation and return duration in ms."""
    start = time.perf_counter()
    await operation(*args, **kwargs)
    end = time.perf_counter()
    return (end - start) * 1000


def time_sync_operation(operation, *args, **kwargs) -> float:
    """Time a sync operation and return duration in ms."""
    start = time.perf_counter()
    operation(*args, **kwargs)
    end = time.perf_counter()
    return (end - start) * 1000


# ============================================================================
# BENCHMARK TESTS
# ============================================================================

class PerformanceBenchmark:
    """Performance benchmark suite."""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.results: List[BenchmarkResult] = []
        self.km: KnowledgeManager = None
        self.embedding_client = None
        self.supabase = None

    async def setup(self):
        """Setup benchmark environment."""
        print_header("Setting up benchmark environment...")
        self.km = KnowledgeManager()
        self.embedding_client, self.supabase = get_clients()
        print(f"{Colors.GREEN}✓ Setup complete!{Colors.END}")

    def get_iterations(self) -> int:
        """Get number of iterations based on mode."""
        return self.config.iterations_quick if self.config.quick_mode else self.config.iterations_full

    # ========================================================================
    # EMBEDDING BENCHMARKS
    # ========================================================================

    async def benchmark_embedding_generation(self):
        """Benchmark embedding generation speed."""
        print_subheader("Embedding Generation")

        iterations = self.get_iterations()
        test_texts = [
            "Build a FastAPI authentication system with JWT tokens",
            "Create a machine learning pipeline with scikit-learn",
            "Implement OAuth2 authentication flow",
            "Design a REST API with proper error handling",
            "Build a real-time chat application"
        ]

        times = []
        for i in range(iterations):
            text = test_texts[i % len(test_texts)]
            duration = await time_async_operation(get_embedding, text)
            times.append(duration)
            print(f"  Iteration {i+1}/{iterations}: {format_time(duration)}")

        result = BenchmarkResult(
            name="Embedding Generation",
            operation="generate_embedding",
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            throughput=1000 / statistics.mean(times),
            metadata={'text_samples': len(test_texts)}
        )

        self.results.append(result)
        print_result(result)

    # ========================================================================
    # KNOWLEDGE SEARCH BENCHMARKS
    # ========================================================================

    async def benchmark_knowledge_search(self):
        """Benchmark knowledge search performance."""
        print_subheader("Knowledge Search")

        iterations = self.get_iterations()

        # Generate a query embedding
        query = "FastAPI authentication with JWT tokens"
        query_embedding = await get_embedding(query)

        times = []
        for i in range(iterations):
            start = time.perf_counter()

            result = self.supabase.rpc(
                'match_knowledge_advanced',
                {
                    'query_embedding': query_embedding,
                    'match_count': 10,
                    'match_threshold': 0.5
                }
            ).execute()

            end = time.perf_counter()
            duration = (end - start) * 1000
            times.append(duration)
            print(f"  Iteration {i+1}/{iterations}: {format_time(duration)} ({len(result.data)} results)")

        result = BenchmarkResult(
            name="Knowledge Search (Vector Similarity)",
            operation="match_knowledge_advanced",
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            throughput=1000 / statistics.mean(times),
            metadata={'match_count': 10}
        )

        self.results.append(result)
        print_result(result)

    # ========================================================================
    # TASK ANALYSIS BENCHMARKS
    # ========================================================================

    async def benchmark_task_analysis(self):
        """Benchmark task requirements analysis."""
        print_subheader("Task Requirements Analysis")

        iterations = self.get_iterations()
        test_descriptions = [
            "Build a FastAPI authentication system with JWT tokens and OAuth2",
            "Create a React frontend with TypeScript and Material-UI",
            "Implement a data pipeline with Pandas and Apache Airflow",
            "Design a microservices architecture with Docker and Kubernetes",
            "Build a machine learning model with PyTorch and CUDA"
        ]

        times = []
        for i in range(iterations):
            desc = test_descriptions[i % len(test_descriptions)]
            duration = await time_async_operation(
                analyze_task_requirements,
                desc,
                f"Test Task {i}"
            )
            times.append(duration)
            print(f"  Iteration {i+1}/{iterations}: {format_time(duration)}")

        result = BenchmarkResult(
            name="Task Requirements Analysis (LLM)",
            operation="analyze_task_requirements",
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            throughput=1000 / statistics.mean(times)
        )

        self.results.append(result)
        print_result(result)

    # ========================================================================
    # DATABASE BENCHMARKS
    # ========================================================================

    async def benchmark_database_operations(self):
        """Benchmark common database operations."""
        print_subheader("Database Operations")

        iterations = self.get_iterations()

        # Test 1: Insert project
        print("\n  Testing: Insert Project")
        insert_times = []
        created_ids = []

        for i in range(iterations):
            start = time.perf_counter()

            result = self.supabase.table("projects").insert({
                "name": f"Benchmark Test {i}",
                "description": "Benchmark test project",
                "status": "planning",
                "priority": 3
            }).execute()

            end = time.perf_counter()
            duration = (end - start) * 1000
            insert_times.append(duration)
            created_ids.append(result.data[0]['id'])
            print(f"    Iteration {i+1}/{iterations}: {format_time(duration)}")

        insert_result = BenchmarkResult(
            name="Database Insert (Project)",
            operation="db_insert",
            iterations=iterations,
            total_time=sum(insert_times),
            avg_time=statistics.mean(insert_times),
            min_time=min(insert_times),
            max_time=max(insert_times),
            median_time=statistics.median(insert_times),
            std_dev=statistics.stdev(insert_times) if len(insert_times) > 1 else 0,
            throughput=1000 / statistics.mean(insert_times)
        )
        self.results.append(insert_result)
        print_result(insert_result)

        # Test 2: Query project
        print("\n  Testing: Query Project")
        query_times = []

        for i in range(iterations):
            project_id = created_ids[i % len(created_ids)]
            start = time.perf_counter()

            result = self.supabase.table("projects").select("*").eq("id", project_id).execute()

            end = time.perf_counter()
            duration = (end - start) * 1000
            query_times.append(duration)
            print(f"    Iteration {i+1}/{iterations}: {format_time(duration)}")

        query_result = BenchmarkResult(
            name="Database Query (Single Record)",
            operation="db_query",
            iterations=iterations,
            total_time=sum(query_times),
            avg_time=statistics.mean(query_times),
            min_time=min(query_times),
            max_time=max(query_times),
            median_time=statistics.median(query_times),
            std_dev=statistics.stdev(query_times) if len(query_times) > 1 else 0,
            throughput=1000 / statistics.mean(query_times)
        )
        self.results.append(query_result)
        print_result(query_result)

        # Cleanup
        print("\n  Cleaning up test data...")
        for project_id in created_ids:
            try:
                self.supabase.table("projects").delete().eq("id", project_id).execute()
            except:
                pass

    # ========================================================================
    # END-TO-END BENCHMARKS
    # ========================================================================

    async def benchmark_end_to_end_workflow(self):
        """Benchmark complete workflow."""
        print_subheader("End-to-End Workflow")

        iterations = min(3, self.get_iterations())  # Limit to 3 for full workflow

        times = []
        for i in range(iterations):
            print(f"\n  Iteration {i+1}/{iterations}")

            workflow_start = time.perf_counter()

            # Step 1: Create project
            step1_start = time.perf_counter()
            project_result = await self.km.create_project(
                name=f"E2E Benchmark {i}",
                description="Build a FastAPI authentication system with JWT",
                priority=3,
                auto_discover=False  # Skip for speed
            )
            step1_time = (time.perf_counter() - step1_start) * 1000
            print(f"    Create project: {format_time(step1_time)}")

            project_id = project_result['project']['id']

            # Step 2: Create task
            step2_start = time.perf_counter()
            task_result = await self.km.create_task(
                project_id=project_id,
                name="Implement JWT authentication",
                description="Create JWT authentication endpoints with FastAPI",
                priority=2,
                auto_link=False  # Skip for speed
            )
            step2_time = (time.perf_counter() - step2_start) * 1000
            print(f"    Create task: {format_time(step2_time)}")

            task_id = task_result['task']['id']

            # Step 3: Link knowledge (if knowledge exists)
            step3_start = time.perf_counter()
            try:
                link_result = await self.km.link_task_knowledge(task_id)
                step3_time = (time.perf_counter() - step3_start) * 1000
                print(f"    Link knowledge: {format_time(step3_time)} ({link_result['links_created']} links)")
            except Exception as e:
                step3_time = 0
                print(f"    Link knowledge: Skipped (no knowledge available)")

            # Total workflow time
            workflow_end = time.perf_counter()
            total_time = (workflow_end - workflow_start) * 1000
            times.append(total_time)

            print(f"    Total workflow: {format_time(total_time)}")

            # Cleanup
            try:
                await self.km.delete_project(project_id)
            except:
                pass

        result = BenchmarkResult(
            name="End-to-End Workflow",
            operation="complete_workflow",
            iterations=iterations,
            total_time=sum(times),
            avg_time=statistics.mean(times),
            min_time=min(times),
            max_time=max(times),
            median_time=statistics.median(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            throughput=1000 / statistics.mean(times),
            metadata={'steps': ['create_project', 'create_task', 'link_knowledge']}
        )

        self.results.append(result)
        print_result(result)

    # ========================================================================
    # MAIN BENCHMARK RUNNER
    # ========================================================================

    async def run_all_benchmarks(self):
        """Run all benchmarks."""
        print_header("Archon Performance Benchmark Suite")
        print(f"Mode: {'QUICK' if self.config.quick_mode else 'FULL'}")
        print(f"Iterations: {self.get_iterations()}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        await self.setup()

        # Run benchmarks
        try:
            await self.benchmark_embedding_generation()
            await self.benchmark_knowledge_search()
            await self.benchmark_task_analysis()
            await self.benchmark_database_operations()
            await self.benchmark_end_to_end_workflow()

        except Exception as e:
            print(f"\n{Colors.RED}Error during benchmark: {e}{Colors.END}")
            import traceback
            traceback.print_exc()

    # ========================================================================
    # REPORTING
    # ========================================================================

    def print_summary(self):
        """Print summary of all benchmarks."""
        print_header("Benchmark Summary")

        # Summary table
        print(f"\n{Colors.BOLD}{'Operation':<40} {'Avg Time':<15} {'Throughput':<20}{Colors.END}")
        print(f"{Colors.CYAN}{'─'*75}{Colors.END}")

        for result in self.results:
            print(f"{result.name:<40} {format_time(result.avg_time):<15} {format_throughput(result.throughput):<20}")

        # Performance recommendations
        print_header("Performance Analysis")

        # Embedding speed
        embedding_results = [r for r in self.results if 'embedding' in r.operation.lower()]
        if embedding_results:
            avg_embedding_time = embedding_results[0].avg_time
            if avg_embedding_time < 100:
                print(f"{Colors.GREEN}✓ Embedding generation: Excellent (<100ms){Colors.END}")
            elif avg_embedding_time < 500:
                print(f"{Colors.YELLOW}⚠ Embedding generation: Good (100-500ms){Colors.END}")
            else:
                print(f"{Colors.RED}✗ Embedding generation: Slow (>500ms){Colors.END}")
                print("  Recommendation: Consider using a faster embedding model")

        # Search speed
        search_results = [r for r in self.results if 'search' in r.name.lower()]
        if search_results:
            avg_search_time = search_results[0].avg_time
            if avg_search_time < 50:
                print(f"{Colors.GREEN}✓ Knowledge search: Excellent (<50ms){Colors.END}")
            elif avg_search_time < 200:
                print(f"{Colors.YELLOW}⚠ Knowledge search: Good (50-200ms){Colors.END}")
            else:
                print(f"{Colors.RED}✗ Knowledge search: Slow (>200ms){Colors.END}")
                print("  Recommendation: Check database indexes and connection latency")

        # Database ops
        db_results = [r for r in self.results if 'database' in r.name.lower()]
        if db_results:
            avg_db_time = statistics.mean([r.avg_time for r in db_results])
            if avg_db_time < 50:
                print(f"{Colors.GREEN}✓ Database operations: Excellent (<50ms){Colors.END}")
            elif avg_db_time < 150:
                print(f"{Colors.YELLOW}⚠ Database operations: Good (50-150ms){Colors.END}")
            else:
                print(f"{Colors.RED}✗ Database operations: Slow (>150ms){Colors.END}")
                print("  Recommendation: Check Supabase region and connection")

        # Workflow speed
        workflow_results = [r for r in self.results if 'workflow' in r.name.lower()]
        if workflow_results:
            avg_workflow_time = workflow_results[0].avg_time
            if avg_workflow_time < 2000:
                print(f"{Colors.GREEN}✓ End-to-end workflow: Excellent (<2s){Colors.END}")
            elif avg_workflow_time < 5000:
                print(f"{Colors.YELLOW}⚠ End-to-end workflow: Good (2-5s){Colors.END}")
            else:
                print(f"{Colors.RED}✗ End-to-end workflow: Slow (>5s){Colors.END}")
                print("  Recommendation: Profile individual steps to identify bottlenecks")

    def export_to_csv(self):
        """Export results to CSV."""
        if not self.config.export_results:
            return

        filepath = self.config.export_path
        print(f"\nExporting results to {filepath}...")

        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [
                'name', 'operation', 'iterations', 'total_time_ms',
                'avg_time_ms', 'min_time_ms', 'max_time_ms',
                'median_time_ms', 'std_dev_ms', 'throughput_ops_per_sec'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for result in self.results:
                writer.writerow({
                    'name': result.name,
                    'operation': result.operation,
                    'iterations': result.iterations,
                    'total_time_ms': result.total_time,
                    'avg_time_ms': result.avg_time,
                    'min_time_ms': result.min_time,
                    'max_time_ms': result.max_time,
                    'median_time_ms': result.median_time,
                    'std_dev_ms': result.std_dev,
                    'throughput_ops_per_sec': result.throughput
                })

        print(f"{Colors.GREEN}✓ Results exported successfully!{Colors.END}")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Archon Performance Benchmark")
    parser.add_argument('--quick', action='store_true', help='Run quick benchmark (fewer iterations)')
    parser.add_argument('--full', action='store_true', help='Run full benchmark (more iterations)')
    parser.add_argument('--export', action='store_true', help='Export results to CSV')
    parser.add_argument('--output', '-o', default='performance_results.csv', help='CSV output path')

    args = parser.parse_args()

    config = BenchmarkConfig(
        quick_mode=args.quick or not args.full,
        export_results=args.export,
        export_path=args.output
    )

    benchmark = PerformanceBenchmark(config)

    try:
        await benchmark.run_all_benchmarks()
        benchmark.print_summary()
        benchmark.export_to_csv()

        print(f"\n{Colors.BOLD}Benchmark completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}\n")

    except Exception as e:
        print(f"\n{Colors.RED}Benchmark failed: {e}{Colors.END}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
