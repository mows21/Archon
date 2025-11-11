# Archon Knowledge Management - Quick Start Guide

Welcome to Archon! This guide will get you up and running with Archon's knowledge-aware AI agent builder in just 5-10 minutes.

## Table of Contents

- [Prerequisites](#prerequisites)
- [5-Minute Setup](#5-minute-setup)
- [Your First Knowledge-Aware Project](#your-first-knowledge-aware-project)
- [CLI Quick Reference](#cli-quick-reference)
- [Next Steps](#next-steps)

## Prerequisites

Before you begin, make sure you have:

- **Docker** (recommended) OR **Python 3.11+**
- **Supabase Account** (free tier works great!)
  - Sign up at: https://supabase.com
  - Create a new project (takes ~2 minutes)
- **API Keys** (at least one):
  - OpenAI API key (recommended for best results)
  - OR Anthropic API key
  - OR OpenRouter API key
  - OR Ollama installed locally (for free local LLMs)

### Quick Supabase Setup

1. Go to https://supabase.com and sign up
2. Create a new project (give it any name)
3. Wait for the project to initialize (~2 minutes)
4. Go to **Settings** → **API** and copy:
   - **Project URL** (looks like `https://xxxxx.supabase.co`)
   - **Service Role Key** (the `service_role` secret key)

## 5-Minute Setup

### Option 1: Automated Setup (Recommended)

We've created an interactive setup wizard that handles everything for you!

```bash
# Clone the repository
git clone https://github.com/coleam00/archon.git
cd archon

# Run the setup wizard
python scripts/setup_wizard.py
```

The wizard will:
- Check your Python version and dependencies
- Prompt for your API keys (with validation)
- Test your database connection
- Set up the knowledge management schema
- Run a test crawl to verify everything works
- Launch the Streamlit UI

**That's it!** Skip to [Your First Knowledge-Aware Project](#your-first-knowledge-aware-project).

---

### Option 2: Manual Setup (Docker)

**Step 1: Clone and Configure**

```bash
# Clone the repository
git clone https://github.com/coleam00/archon.git
cd archon

# Create .env file (optional - you can also configure via UI)
cat > .env << 'EOF'
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_KEY=your_supabase_key_here
LLM_API_KEY=your_openai_key_here
LLM_PROVIDER=OpenAI
PRIMARY_MODEL=gpt-4o-mini
REASONING_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_PROVIDER=OpenAI
EMBEDDING_API_KEY=your_openai_key_here
EOF
```

**Step 2: Start Docker**

```bash
# Build and run (this handles everything automatically)
python run_docker.py
```

**Step 3: Access the UI**

Open your browser to: http://localhost:8501

**Step 4: Follow the Guided Setup**

The Streamlit UI will walk you through:
1. Environment configuration (if not using .env)
2. Database schema setup
3. Documentation crawling
4. Agent service startup

---

### Option 3: Manual Setup (Local Python)

**Step 1: Clone and Install**

```bash
# Clone the repository
git clone https://github.com/coleam00/archon.git
cd archon

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

**Step 2: Configure Environment**

You can configure via the UI or manually create `workbench/env_vars.json`:

```bash
mkdir -p workbench
cat > workbench/env_vars.json << 'EOF'
{
  "SUPABASE_URL": "your_supabase_url_here",
  "SUPABASE_SERVICE_KEY": "your_supabase_key_here",
  "LLM_API_KEY": "your_openai_key_here",
  "LLM_PROVIDER": "OpenAI",
  "PRIMARY_MODEL": "gpt-4o-mini",
  "REASONING_MODEL": "gpt-4o-mini",
  "EMBEDDING_MODEL": "text-embedding-3-small",
  "EMBEDDING_PROVIDER": "OpenAI",
  "EMBEDDING_API_KEY": "your_openai_key_here"
}
EOF
```

**Step 3: Set Up Database**

```bash
# Run the knowledge management schema setup
python -c "
import asyncio
from utils.utils import get_clients

async def setup():
    _, supabase = get_clients()
    with open('utils/knowledge_schema.sql', 'r') as f:
        schema = f.read()

    # Execute the schema (note: this is simplified)
    print('Please run the schema manually in Supabase SQL Editor')
    print('Schema file: utils/knowledge_schema.sql')

asyncio.run(setup())
"
```

Or use the Streamlit UI (recommended):

```bash
# Start Streamlit
streamlit run streamlit_ui.py

# Then:
# 1. Go to "Database" tab
# 2. Click "Get Setup Instructions for Knowledge Management"
# 3. Follow the instructions to execute the SQL in Supabase
```

**Step 4: Crawl Documentation**

```bash
# Crawl Pydantic AI documentation (takes 5-10 minutes)
python archon/crawl_pydantic_ai_docs.py
```

Or use the UI:
1. Go to "Documentation" tab
2. Click "Start Crawling Pydantic AI Docs"
3. Watch the progress bar

**Step 5: Start the Agent Service**

```bash
# Start the FastAPI service (in a separate terminal)
python graph_service.py
```

Or use the UI:
1. Go to "Agent Service" tab
2. Click "Start Agent Service"

**Step 6: Start Using Archon!**

```bash
# Launch Streamlit UI
streamlit run streamlit_ui.py
```

Open your browser to: http://localhost:8501

---

## Your First Knowledge-Aware Project

Let's walk through creating your first project that uses Archon's knowledge management system!

### Scenario: Build a FastAPI Authentication System

This example demonstrates how Archon automatically attaches relevant documentation to your tasks.

#### Step 1: Create a Project

1. Go to the **Projects** tab in the Streamlit UI
2. Click **"Create New Project"**
3. Fill in the details:
   - **Name**: "FastAPI Authentication System"
   - **Description**: "Build a complete JWT authentication system with user registration, login, and password reset using FastAPI and PostgreSQL"
   - **Priority**: 1 (High)
   - **Deadline**: Set a date 30 days from now
   - **Required Tags**: authentication, jwt, fastapi, security
   - **Required Frameworks**: fastapi, pydantic
   - Check **"Auto-discover knowledge"**
   - Set **Minimum Coverage**: 0.4 (40%)

4. Click **"Create Project"**

**What happens behind the scenes:**
- Archon generates an embedding of your project description
- Searches the knowledge base for relevant documentation
- Calculates a "coverage score" (0-1) indicating how much relevant knowledge exists
- If coverage < 40%, automatically triggers the scraper to fetch missing docs
- Links the top 20 most relevant knowledge chunks to your project

#### Step 2: Review Knowledge Coverage

After creating the project, you'll see:

```
✓ Project created successfully!
📊 Knowledge Coverage: 0.75 (75%)
📚 Linked Knowledge: 20 chunks
🏷️  Available Frameworks: fastapi, pydantic
```

If coverage is low:
```
⚠️  Knowledge Coverage: 0.25 (25%)
🔍 Missing Tags: oauth2, jwt
🤖 Triggering scraper to acquire missing knowledge...
```

#### Step 3: Decompose into Tasks

Click **"Decompose Project"** to automatically break it down into tasks.

Archon's AI will analyze your project and create tasks like:

1. **Setup Database Models**
   - Description: "Create SQLAlchemy models for users, sessions, and tokens"
   - Coverage: 0.82
   - Linked Knowledge: 8 chunks (SQLAlchemy docs, FastAPI database integration)

2. **Implement Password Hashing**
   - Description: "Use bcrypt for secure password hashing and validation"
   - Coverage: 0.68
   - Linked Knowledge: 5 chunks (Security best practices, bcrypt usage)

3. **Create JWT Token Generation**
   - Description: "Implement JWT token creation and validation with RS256"
   - Coverage: 0.91
   - Linked Knowledge: 12 chunks (JWT docs, FastAPI security)

4. **Build Authentication Endpoints**
   - Description: "/register, /login, /logout, /refresh endpoints"
   - Coverage: 0.88
   - Linked Knowledge: 10 chunks (FastAPI routing, dependency injection)

5. **Implement Password Reset Flow**
   - Description: "Email-based password reset with secure tokens"
   - Coverage: 0.45
   - Linked Knowledge: 3 chunks (might need more docs on email)

**Each task automatically has:**
- Relevant documentation chunks attached
- Knowledge coverage score
- Suggested frameworks and tags
- Dependencies on other tasks (if applicable)

#### Step 4: Execute a Task

Let's build Task 3: JWT Token Generation.

1. Click on **"Create JWT Token Generation"** task
2. Click **"View Linked Knowledge"** to see attached docs:
   - "JWT Authentication in FastAPI" (similarity: 0.89)
   - "Creating and Validating Tokens" (similarity: 0.86)
   - "Security Best Practices for JWTs" (similarity: 0.84)
   - ... 9 more chunks

3. Click **"Execute Task"**
4. Archon opens the Chat interface with:
   - Task description pre-filled
   - All linked knowledge automatically injected into context
   - Agent ready to build with full documentation access

5. Review the generated code
6. Provide feedback or click **"Refine"** for autonomous improvements
7. Click **"Complete Task"** when satisfied

**What just happened:**
- The agent had access to all relevant JWT and FastAPI documentation
- No hallucinations about API usage (it referenced real docs!)
- Code follows best practices from the documentation
- Agent can cite specific docs: "According to the FastAPI security guide..."

#### Step 5: Learn from Execution

After completing the task, Archon can extract learnings:

```
🧠 New Insights Learned:
- "FastAPI's dependency injection works perfectly for JWT validation"
- "Using python-jose library is recommended for JWT in FastAPI"
- "Store tokens in HTTPOnly cookies for better security"
```

These insights are:
- Stored as new knowledge chunks
- Tagged with ['learned_insight', 'jwt', 'fastapi']
- Automatically linked to future similar tasks
- Available for all future projects

#### Step 6: Verify Everything Works

Run the verification checklist:

- [ ] Project shows high coverage score (>60%)
- [ ] Tasks have relevant documentation attached
- [ ] Can view linked knowledge for each task
- [ ] Agent service is running
- [ ] Can execute tasks via Chat interface
- [ ] Generated code references actual documentation

If everything is checked, congratulations! You're ready to use Archon.

---

## CLI Quick Reference

### Project Management

```bash
# Create a project (via Python)
python -c "
import asyncio
from archon.knowledge_manager import KnowledgeManager

async def create():
    km = KnowledgeManager()
    project = await km.create_project(
        name='My Project',
        description='Build something amazing',
        auto_discover=True
    )
    print(f'Created: {project}')

asyncio.run(create())
"

# List all projects
python -c "
import asyncio
from utils.utils import get_clients

async def list_projects():
    _, supabase = get_clients()
    result = supabase.table('projects').select('*').execute()
    for p in result.data:
        print(f'{p[\"name\"]}: {p[\"status\"]}')

asyncio.run(list_projects())
"
```

### Documentation Crawling

```bash
# Crawl Pydantic AI docs
python archon/crawl_pydantic_ai_docs.py

# Crawl custom documentation (coming soon)
python scripts/universal_crawler.py https://docs.example.com
```

### Database Operations

```bash
# Apply knowledge management schema
# (Use Supabase SQL Editor - copy from utils/knowledge_schema.sql)

# Check knowledge coverage
python -c "
import asyncio
from archon.knowledge_manager import KnowledgeManager

async def check():
    km = KnowledgeManager()
    coverage = await km.check_and_acquire_knowledge(
        tags=['fastapi', 'authentication'],
        min_coverage=0.4
    )
    print(f'Coverage: {coverage.coverage_score:.2f}')
    print(f'Total chunks: {coverage.total_chunks}')

asyncio.run(check())
"
```

### Agent Service

```bash
# Start agent service
python graph_service.py

# Or via Docker
python run_docker.py
```

---

## Next Steps

### Explore Advanced Features

1. **Multi-Framework Projects**
   - Create projects using React + FastAPI
   - Archon automatically separates frontend/backend knowledge

2. **Knowledge Graph Browser** (Coming Soon)
   - Visualize relationships between documentation chunks
   - See how concepts connect

3. **Automatic Dependency Detection**
   - Let Archon figure out task dependencies
   - Auto-schedule tasks based on knowledge availability

4. **Learning from Execution**
   - Extract insights from completed tasks
   - Build your own knowledge base over time

### Read More Documentation

- **[Knowledge Management Guide](KNOWLEDGE_MANAGEMENT.md)** - Deep dive into the system
- **[Knowledge Manager Usage](KNOWLEDGE_MANAGER_USAGE.md)** - API reference and examples
- **[Universal Crawler Guide](universal_crawler_guide.md)** - Crawl any documentation
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

### Join the Community

- **GitHub Issues**: https://github.com/coleam00/archon/issues
- **Community Forum**: https://thinktank.ottomator.ai/c/archon/30
- **Project Board**: https://github.com/users/coleam00/projects/1

### Contribute

We welcome contributions! Areas where you can help:

- **Add prebuilt tools** to `agent-resources/tools/`
- **Create example agents** in `agent-resources/examples/`
- **Submit documentation crawlers** for popular frameworks
- **Improve the knowledge linker** with better relevance scoring
- **Build UI components** for the Streamlit interface

---

## Common Issues

If you run into problems, check our **[Troubleshooting Guide](TROUBLESHOOTING.md)** or:

1. Check logs in `workbench/logs.txt`
2. Verify environment variables in `workbench/env_vars.json`
3. Test Supabase connection in the Database tab
4. Ensure Agent Service is running in the Agent Service tab
5. Ask for help in the [Community Forum](https://thinktank.ottomator.ai/c/archon/30)

---

## What's Next?

Now that you're set up, try building:

- A real-time chat application with WebSockets
- A full-stack app with React + FastAPI
- A data processing pipeline with background tasks
- A multi-tenant SaaS application

Archon will automatically find and attach the right documentation for each task!

**Happy building!** 🚀

---

*Built with Archon - The world's first Agenteer*
