#!/usr/bin/env python3
"""
Archon Knowledge Management Test Runner

Beautiful test execution with comprehensive reporting including:
- Colored console output
- Test timing
- Coverage statistics
- HTML and Markdown reports
- Pass/fail summary
"""

import subprocess
import sys
import time
import json
from datetime import datetime
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header():
    """Print test suite header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}")
    print("🧪  Archon Knowledge Management Test Suite")
    print(f"{'='*80}{Colors.ENDC}\n")


def run_pytest(test_file=None, markers=None, verbose=True):
    """Run pytest with specified options."""
    cmd = ["pytest"]
    
    if test_file:
        cmd.append(test_file)
    
    if markers:
        cmd.extend(["-m", markers])
    
    if verbose:
        cmd.append("-v")
    
    # Add coverage
    cmd.extend(["--cov=archon", "--cov-report=term-missing", "--cov-report=html"])
    
    # Add JSON report
    cmd.extend(["--json-report", "--json-report-file=tests/test_report.json"])
    
    # Run tests
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result


def parse_test_results(result):
    """Parse pytest results."""
    lines = result.stdout.split('\n')
    
    stats = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'duration': 0.0
    }
    
    for line in lines:
        if ' passed' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'passed':
                    try:
                        stats['passed'] = int(parts[i-1])
                    except (ValueError, IndexError):
                        pass
        if ' failed' in line:
            parts = line.split()
            for i, part in enumerate(parts):
                if part == 'failed':
                    try:
                        stats['failed'] = int(parts[i-1])
                    except (ValueError, IndexError):
                        pass
        if ' in ' in line and 's' in line:
            try:
                duration_str = line.split(' in ')[-1].split('s')[0]
                stats['duration'] = float(duration_str)
            except (ValueError, IndexError):
                pass
    
    return stats


def print_test_results(test_file, stats, duration):
    """Print test results in beautiful format."""
    name = Path(test_file).stem
    total = stats['passed'] + stats['failed']
    passed_pct = (stats['passed'] / total * 100) if total > 0 else 0
    
    if stats['failed'] == 0:
        status = f"{Colors.OKGREEN}✓{Colors.ENDC}"
        color = Colors.OKGREEN
    else:
        status = f"{Colors.FAIL}✗{Colors.ENDC}"
        color = Colors.FAIL
    
    print(f"{status} {name:.<50} {color}{stats['passed']}/{total} passed{Colors.ENDC} ({duration:.1f}s)")


def print_summary(all_stats):
    """Print final summary."""
    total_passed = sum(s['passed'] for s in all_stats.values())
    total_failed = sum(s['failed'] for s in all_stats.values())
    total_duration = sum(s['duration'] for s in all_stats.values())
    total = total_passed + total_failed
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}")
    print("📊  Results")
    print(f"{'='*80}{Colors.ENDC}\n")
    
    print(f"Total Tests: {Colors.BOLD}{total}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}✅ Passed: {total_passed} ({total_passed/total*100:.1f}%){Colors.ENDC}")
    
    if total_failed > 0:
        print(f"{Colors.FAIL}❌ Failed: {total_failed} ({total_failed/total*100:.1f}%){Colors.ENDC}")
    else:
        print(f"{Colors.OKGREEN}❌ Failed: 0 (0%){Colors.ENDC}")
    
    print(f"⏱️  Duration: {total_duration:.1f}s")
    
    # Coverage info
    print(f"\n{Colors.OKCYAN}📈 Coverage report generated:{Colors.ENDC}")
    print(f"   HTML: tests/htmlcov/index.html")
    print(f"   Terminal: see above")
    
    if total_failed == 0:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✨ All tests passed!{Colors.ENDC}\n")
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}⚠️  Some tests failed. Please review the output above.{Colors.ENDC}\n")
    
    print(f"{Colors.OKCYAN}Report saved to: tests/test_report.json{Colors.ENDC}")
    print(f"{Colors.OKCYAN}HTML report: tests/test_report.html{Colors.ENDC}\n")


def generate_markdown_report(all_stats, output_file="tests/test_report.md"):
    """Generate markdown report."""
    total_passed = sum(s['passed'] for s in all_stats.values())
    total_failed = sum(s['failed'] for s in all_stats.values())
    total_duration = sum(s['duration'] for s in all_stats.values())
    total = total_passed + total_failed
    
    with open(output_file, 'w') as f:
        f.write("# Archon Knowledge Management Test Report\n\n")
        f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Summary\n\n")
        f.write(f"- **Total Tests:** {total}\n")
        f.write(f"- **Passed:** {total_passed} ({total_passed/total*100:.1f}%)\n")
        f.write(f"- **Failed:** {total_failed} ({total_failed/total*100:.1f}%)\n")
        f.write(f"- **Duration:** {total_duration:.1f}s\n\n")
        
        f.write("## Test Files\n\n")
        f.write("| Test File | Passed | Failed | Duration |\n")
        f.write("|-----------|--------|--------|----------|\n")
        
        for test_file, stats in all_stats.items():
            name = Path(test_file).stem
            f.write(f"| {name} | {stats['passed']} | {stats['failed']} | {stats['duration']:.1f}s |\n")
        
        f.write(f"\n**Status:** {'✅ All tests passed!' if total_failed == 0 else '⚠️ Some tests failed'}\n")


def main():
    """Main test runner."""
    print_header()
    
    # List of test files
    test_files = [
        "tests/test_universal_crawler.py",
        "tests/test_knowledge_linker.py",
        "tests/test_knowledge_manager.py",
        "tests/test_ui_components.py",
        "tests/test_langgraph_integration.py",
        "tests/test_database.py"
    ]
    
    all_stats = {}
    
    print(f"{Colors.BOLD}Running tests...{Colors.ENDC}\n")
    
    # Run each test file
    for test_file in test_files:
        start_time = time.time()
        result = run_pytest(test_file, verbose=False)
        duration = time.time() - start_time
        
        stats = parse_test_results(result)
        stats['duration'] = duration
        all_stats[test_file] = stats
        
        print_test_results(test_file, stats, duration)
    
    # Print summary
    print_summary(all_stats)
    
    # Generate markdown report
    generate_markdown_report(all_stats)
    
    # Return exit code
    total_failed = sum(s['failed'] for s in all_stats.values())
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
