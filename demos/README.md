# Archon Knowledge Management Demos

Comprehensive demonstration suite for Archon's knowledge management system. These demos prove that everything works and provide interactive walkthroughs of key features.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Demo Overview](#demo-overview)
- [Prerequisites](#prerequisites)
- [Running the Demos](#running-the-demos)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

```bash
# 1. Verify system is working
python demos/phase3_verification.py

# 2. Run end-to-end demo (quick mode)
python demos/end_to_end_demo.py

# 3. Try the interactive demo
python demos/interactive_demo.py

# 4. Run performance benchmark
python demos/performance_benchmark.py --quick
```

## 📊 Demo Overview

### 1. End-to-End Demo (`end_to_end_demo.py`)

**Purpose:** Demonstrates the complete knowledge management workflow from start to finish.

**What it shows:**
- Crawling documentation sources
- Creating knowledge-aware projects
- Automatic task decomposition
- Knowledge linking and coverage analysis
- Task execution with knowledge context
- Project analytics

**Usage:**
```bash
# Quick demo (skip crawling, uses existing knowledge)
python demos/end_to_end_demo.py

# Full demo (includes crawling FastAPI docs)
python demos/end_to_end_demo.py --full
```

**Expected Output:**
```
🎬 Archon Knowledge Management - End-to-End Demo
════════════════════════════════════════════════

Step 1: Crawling FastAPI Documentation
────────────────────────────────────────────────
✓ Documentation crawling completed!
  • URLs Processed: 45
  • Chunks Stored: 127

Step 2: Creating Knowledge-Aware Project
────────────────────────────────────────────────
✓ Project created successfully!
  • Coverage Score: 85.3% (Excellent)
  • Total Chunks Available: 127

...
```

**Duration:** 2-5 minutes (quick), 10-15 minutes (full)

---

### 2. Phase 3 Verification (`phase3_verification.py`)

**Purpose:** Automated verification that all components are properly installed and working.

**What it checks:**
- Database schema (tables, RPC functions, triggers, indexes)
- Module imports (all Python modules load correctly)
- Function calls (key functions are callable)
- Workflow execution (end-to-end test)

**Usage:**
```bash
# Run all verification checks
python demos/phase3_verification.py

# Verbose output
python demos/phase3_verification.py --verbose

# Generate markdown report
python demos/phase3_verification.py --report
```

**Expected Output:**
```
🔍 ARCHON PHASE 3 VERIFICATION
════════════════════════════════════════════════

DATABASE SCHEMA VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ PASS Table: site_pages
  ✓ PASS Table: projects
  ✓ PASS Table: tasks
  ✓ PASS RPC: match_knowledge_advanced
  ...

VERIFICATION SUMMARY
════════════════════════════════════════════════
✓ Database Schema              8/8 passed (100.0%)
✓ Module Imports               4/4 passed (100.0%)
✓ Function Calls               3/3 passed (100.0%)
✓ Workflow Execution           3/3 passed (100.0%)

Total: 18/18 passed (100.0%)
✅ System Status: PRODUCTION READY
```

**Duration:** 30-60 seconds

---

### 3. Interactive Demo (`interactive_demo.py`)

**Purpose:** User-guided exploration of features with an interactive menu system.

**What it offers:**
- Menu-driven interface
- Step-by-step walkthroughs
- Real-time feedback
- Exploration at your own pace

**Usage:**
```bash
python demos/interactive_demo.py
```

**Features:**

1. **Crawl Documentation**
   - Enter any documentation URL
   - Watch real-time progress
   - See crawl statistics

2. **Create Knowledge-Aware Project**
   - Enter project details
   - See automatic knowledge discovery
   - View coverage analysis

3. **Decompose Project into Tasks**
   - LLM-powered task breakdown
   - See generated tasks with priorities
   - View knowledge coverage per task

4. **Link Knowledge to Task**
   - Automatic knowledge linking
   - See relevance scores
   - View suggested sources

5. **View Task Knowledge**
   - See all linked knowledge chunks
   - Browse by relevance
   - View tags and summaries

6. **View Project Analytics**
   - Task statistics
   - Knowledge coverage
   - Progress tracking

7. **Explore Knowledge Base**
   - View database statistics
   - Browse frameworks
   - See available sources

**Expected Output:**
```
🎮 Archon Interactive Demo
════════════════════════════════════════════════

Knowledge Management System - Interactive Walkthrough

Main Menu
────────────────────────────────────────────────
  1. Crawl Documentation
  2. Create Knowledge-Aware Project
  3. Decompose Project into Tasks
  4. Link Knowledge to Task
  5. View Task Knowledge
  6. View Project Analytics
  7. Explore Knowledge Base
  8. Exit
────────────────────────────────────────────────

Select an option: _
```

**Duration:** Variable (user-paced)

---

### 4. Performance Benchmark (`performance_benchmark.py`)

**Purpose:** Measure performance and identify bottlenecks in key operations.

**What it benchmarks:**
- Embedding generation speed
- Knowledge search performance
- Task analysis (LLM calls)
- Database operations (insert, query)
- End-to-end workflow timing

**Usage:**
```bash
# Quick benchmark (5 iterations)
python demos/performance_benchmark.py --quick

# Full benchmark (20 iterations)
python demos/performance_benchmark.py --full

# Export results to CSV
python demos/performance_benchmark.py --export --output results.csv
```

**Expected Output:**
```
Archon Performance Benchmark Suite
════════════════════════════════════════════════
Mode: QUICK
Iterations: 5

Embedding Generation
────────────────────────────────────────────────
  Embedding Generation
    Iterations: 5
    Average:    127.45ms
    Min:        115.23ms
    Max:        145.67ms
    Median:     125.34ms
    Std Dev:    10.23ms
    Throughput: 7.85 ops/sec

...

BENCHMARK SUMMARY
════════════════════════════════════════════════

Operation                                Avg Time        Throughput
───────────────────────────────────────────────────────────────────
Embedding Generation                     127.45ms        7.85 ops/sec
Knowledge Search (Vector Similarity)     43.21ms         23.14 ops/sec
Task Requirements Analysis (LLM)         892.34ms        1.12 ops/sec
Database Insert (Project)                56.78ms         17.61 ops/sec
Database Query (Single Record)           12.45ms         80.32 ops/sec
End-to-End Workflow                      1234.56ms       0.81 ops/sec

PERFORMANCE ANALYSIS
════════════════════════════════════════════════
✓ Embedding generation: Excellent (<100ms)
✓ Knowledge search: Excellent (<50ms)
⚠ Task analysis: Good (500-1000ms)
✓ Database operations: Excellent (<50ms)
✓ End-to-end workflow: Excellent (<2s)
```

**Duration:** 1-2 minutes (quick), 5-10 minutes (full)

---

## 🔧 Prerequisites

### Required

1. **Database Setup**
   ```bash
   # Ensure Supabase schema is deployed
   # Check connection
   python -c "from utils.utils import get_clients; get_clients()"
   ```

2. **Environment Variables**
   ```bash
   # Check .env file has:
   SUPABASE_URL=your-supabase-url
   SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
   LLM_API_KEY=your-openai-key
   EMBEDDING_MODEL=text-embedding-3-small
   PRIMARY_MODEL=gpt-4o-mini
   ```

3. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### Optional (for full features)

- Knowledge base populated with documentation
- Active internet connection (for crawling)

## 📝 Running the Demos

### First-Time Setup

```bash
# 1. Navigate to Archon directory
cd /home/user/Archon

# 2. Verify environment
python demos/phase3_verification.py

# 3. If verification fails, check:
#    - Database connection
#    - Environment variables
#    - Dependencies installed

# 4. Once verification passes, run any demo
```

### Recommended Order

For first-time users, we recommend this order:

1. **Verification** - Ensure everything works
   ```bash
   python demos/phase3_verification.py
   ```

2. **Interactive Demo** - Explore features hands-on
   ```bash
   python demos/interactive_demo.py
   ```

3. **End-to-End Demo** - See complete workflow
   ```bash
   python demos/end_to_end_demo.py
   ```

4. **Performance Benchmark** - Measure your setup
   ```bash
   python demos/performance_benchmark.py --quick
   ```

### Common Use Cases

**"I just set up the system and want to verify it works"**
```bash
python demos/phase3_verification.py --report
# Check the generated report in docs/PHASE_3_VERIFICATION_REPORT.md
```

**"I want to see the full workflow in action"**
```bash
# If you have knowledge already:
python demos/end_to_end_demo.py

# If starting fresh:
python demos/end_to_end_demo.py --full
```

**"I want to explore features interactively"**
```bash
python demos/interactive_demo.py
# Follow the menu prompts
```

**"I want to measure performance"**
```bash
python demos/performance_benchmark.py --quick --export
# Check performance_results.csv for detailed metrics
```

**"I want to demo to stakeholders"**
```bash
# Run the interactive demo for best visual experience
python demos/interactive_demo.py
```

## 🐛 Troubleshooting

### Common Issues

#### "Module not found" errors

**Problem:** Python can't find Archon modules

**Solution:**
```bash
# Ensure you're in the Archon directory
cd /home/user/Archon

# Run from project root
python demos/end_to_end_demo.py
```

#### "Database connection failed"

**Problem:** Can't connect to Supabase

**Solution:**
```bash
# Check environment variables
cat .env | grep SUPABASE

# Test connection
python -c "from utils.utils import get_clients; get_clients()"
```

#### "RPC function not found"

**Problem:** Database schema not deployed

**Solution:**
```bash
# Deploy the schema
# Check docs/PHASE_2_IMPLEMENTATION_SUMMARY.md for instructions

# Verify tables exist
python demos/phase3_verification.py
```

#### "No knowledge found"

**Problem:** Knowledge base is empty

**Solution:**
```bash
# Use interactive demo to crawl some documentation
python demos/interactive_demo.py
# Choose option 1: Crawl Documentation
# Enter: https://fastapi.tiangolo.com
```

#### "Embedding generation failed"

**Problem:** OpenAI API issue

**Solution:**
```bash
# Check API key
echo $LLM_API_KEY

# Verify in .env
cat .env | grep LLM_API_KEY

# Test embedding
python -c "from archon.knowledge_linker import get_embedding; import asyncio; asyncio.run(get_embedding('test'))"
```

#### "Demo runs but nothing happens"

**Problem:** Async event loop issue

**Solution:**
```bash
# Ensure Python 3.7+
python --version

# Try running with explicit asyncio
python3 demos/end_to_end_demo.py
```

### Performance Issues

#### Slow embedding generation

- Check your OpenAI API rate limits
- Consider using a faster embedding model
- Verify network connection

#### Slow database queries

- Check Supabase region (closer is faster)
- Verify indexes are created
- Check connection latency: `ping your-supabase-url`

#### LLM calls timeout

- Increase timeout in configuration
- Check LLM_API_KEY is valid
- Try a faster model (gpt-3.5-turbo vs gpt-4)

### Getting Help

If issues persist:

1. **Check Logs**
   ```bash
   # Logs are in archon_logs/
   tail -f archon_logs/archon.log
   ```

2. **Run Verification**
   ```bash
   python demos/phase3_verification.py --verbose
   # This will show detailed error messages
   ```

3. **Review Documentation**
   - `docs/KNOWLEDGE_MANAGER_USAGE.md`
   - `docs/PHASE_2_IMPLEMENTATION_SUMMARY.md`

4. **Open an Issue**
   - Include verification output
   - Include error messages
   - Include environment details

## 📈 Expected Results

### Successful Verification

- All database tables accessible
- All RPC functions callable
- All modules importable
- Workflow executes without errors
- Status: "PRODUCTION READY"

### Successful End-to-End Demo

- Documentation crawled (if running full mode)
- Project created with knowledge coverage > 40%
- Tasks generated (typically 5-15 tasks)
- Knowledge linked to tasks
- Analytics displayed

### Successful Performance Benchmark

Typical performance on standard setup:

| Operation | Expected Time |
|-----------|--------------|
| Embedding Generation | 50-200ms |
| Knowledge Search | 20-100ms |
| Task Analysis (LLM) | 500-2000ms |
| Database Insert | 30-100ms |
| Database Query | 10-50ms |
| End-to-End Workflow | 1-3 seconds |

If your results are significantly slower, check:
- Network latency to Supabase
- OpenAI API response times
- System resources (CPU, memory)

## 🎯 Next Steps

After running the demos:

1. **Integrate into your workflow**
   - Use `KnowledgeManager` in your code
   - Set up automated crawling
   - Create production projects

2. **Customize for your needs**
   - Add domain-specific knowledge sources
   - Adjust crawling profiles
   - Configure coverage thresholds

3. **Monitor performance**
   - Run benchmarks regularly
   - Track knowledge growth
   - Measure coverage improvements

4. **Explore advanced features**
   - LangGraph workflow integration
   - Parallel task execution
   - Custom agent types

## 📄 License

These demos are part of the Archon project. See main repository for license information.

## 🙏 Acknowledgments

Built with:
- FastAPI (example documentation)
- Supabase (database)
- OpenAI (embeddings & LLM)
- Python asyncio (concurrency)

---

**Happy Demoing! 🚀**

For more information, see the main Archon documentation in `/docs`.
