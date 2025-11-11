# Archon Knowledge Management System - Test Suite

Comprehensive test suite for Archon's knowledge management system with 80+ tests covering all components.

## 📋 Table of Contents

- [Overview](#overview)
- [Test Coverage](#test-coverage)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Test Data](#test-data)
- [Continuous Integration](#continuous-integration)

## 🎯 Overview

This test suite provides comprehensive coverage of:
- **Universal Crawler**: Web scraping, content extraction, and knowledge chunking
- **Knowledge Linker**: Semantic search, relevance scoring, and knowledge linking
- **Knowledge Manager**: Project/task management and orchestration
- **UI Components**: Streamlit interface components
- **LangGraph Integration**: Workflow nodes and state management
- **Database Schema**: Tables, constraints, and RPC functions

### Test Statistics

- **Total Tests**: 80+
- **Test Files**: 6
- **Coverage Target**: >90%
- **Execution Time**: ~12 seconds

## 🧪 Test Coverage

### test_universal_crawler.py (15+ tests)
Tests for the Universal Crawler Agent including:
- ✅ Framework detection from URLs
- ✅ Language detection from code blocks
- ✅ LLM tag extraction (mocked)
- ✅ Knowledge type classification
- ✅ Text chunking with intelligent boundaries
- ✅ Sitemap parsing
- ✅ URL filtering
- ✅ Link extraction
- ✅ Crawl profiles (deep, quick, api-only)
- ✅ Progress tracking
- ✅ Error handling
- ✅ Concurrent requests

### test_knowledge_linker.py (15+ tests)
Tests for the Knowledge Linker Agent including:
- ✅ Task requirement analysis
- ✅ Tag extraction with LLM
- ✅ Vector search operations
- ✅ Relevance score calculation
- ✅ Chunk deduplication
- ✅ Link type classification
- ✅ Coverage score calculation
- ✅ Crawl source suggestions
- ✅ Batch linking operations
- ✅ Refresh logic
- ✅ Error handling

### test_knowledge_manager.py (20+ tests)
Tests for the Knowledge Manager orchestrator including:
- ✅ Project CRUD operations
- ✅ Task CRUD operations
- ✅ Auto knowledge discovery
- ✅ Coverage checking
- ✅ Embedding generation
- ✅ Project decomposition
- ✅ Batch operations
- ✅ Dependency management
- ✅ Agent registry
- ✅ Error handling
- ✅ Edge cases

### test_ui_components.py (10+ tests)
Tests for Streamlit UI components including:
- ✅ Project list rendering
- ✅ Task board rendering
- ✅ Knowledge panel display
- ✅ Search functionality
- ✅ Form validation
- ✅ State management
- ✅ Error display
- ✅ Loading states

### test_langgraph_integration.py (10+ tests)
Tests for LangGraph workflow integration including:
- ✅ Node execution
- ✅ State transitions
- ✅ Routing logic
- ✅ Error handling in nodes
- ✅ Complete workflow execution
- ✅ Interrupt handling
- ✅ State persistence

### test_database.py (10+ tests)
Tests for database schema including:
- ✅ Table existence
- ✅ Column types
- ✅ Constraints
- ✅ Foreign keys
- ✅ RPC functions
- ✅ Data integrity

## 🚀 Getting Started

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock pytest-json-report
```

### Environment Setup

Create a `.env` file for testing:

```env
EMBEDDING_MODEL=text-embedding-3-small
PRIMARY_MODEL=gpt-4o-mini
BASE_URL=https://api.openai.com/v1
LLM_API_KEY=your-test-api-key
SUPABASE_URL=https://test.supabase.co
SUPABASE_KEY=your-test-key
```

## 🏃 Running Tests

### Run All Tests

```bash
# Using the test runner (recommended)
python tests/run_all_tests.py

# Using pytest directly
pytest
```

### Run Specific Test File

```bash
pytest tests/test_universal_crawler.py -v
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run all except slow tests
pytest -m "not slow"
```

### Run with Coverage

```bash
pytest --cov=archon --cov-report=html
```

Coverage report will be available at `tests/htmlcov/index.html`

### Run Specific Test

```bash
pytest tests/test_knowledge_linker.py::test_analyze_task_requirements_basic -v
```

## 📁 Test Structure

```
tests/
├── __init__.py                      # Test package initialization
├── conftest.py                      # Shared fixtures and mocks
├── test_universal_crawler.py        # Crawler tests (15+)
├── test_knowledge_linker.py         # Linker tests (15+)
├── test_knowledge_manager.py        # Manager tests (20+)
├── test_ui_components.py            # UI tests (10+)
├── test_langgraph_integration.py    # Workflow tests (10+)
├── test_database.py                 # Database tests (10+)
├── run_all_tests.py                 # Test runner with reporting
├── test_data/                       # Test data files
│   ├── sample_project.json
│   ├── sample_tasks.json
│   ├── sample_knowledge.json
│   └── sample_crawl_output.html
└── README.md                        # This file
```

## 🧩 Test Fixtures

### Available Fixtures (in conftest.py)

- `mock_supabase`: Mock Supabase client
- `mock_openai`: Mock OpenAI client
- `mock_openai_with_responses`: Customizable OpenAI responses
- `mock_env_vars`: Mock environment variables
- `sample_project`: Sample project data
- `sample_task`: Sample task data
- `sample_knowledge_chunk`: Sample knowledge chunk
- `sample_crawl_config`: Sample crawler configuration
- `sample_html_content`: Sample HTML for testing
- `sample_sitemap_xml`: Sample sitemap XML
- `mock_requests`: Mock requests library

### Using Fixtures

```python
@pytest.mark.asyncio
async def test_my_function(mock_supabase, mock_openai):
    # Your test code here
    pass
```

## 📊 Test Data

Test data is located in `tests/test_data/`:

- **sample_project.json**: Complete project definition
- **sample_tasks.json**: List of sample tasks
- **sample_knowledge.json**: Sample knowledge chunks
- **sample_crawl_output.html**: HTML for crawler testing

## 🔍 Mocking Strategy

The test suite uses extensive mocking to:
- Avoid external API calls
- Speed up test execution
- Ensure consistent results
- Test error conditions

### Mocked Services

- **Supabase**: Database operations
- **OpenAI API**: Embeddings and completions
- **Web Requests**: HTTP requests
- **File I/O**: File operations

## 📈 Coverage Reports

After running tests, coverage reports are generated:

- **Terminal**: Shows coverage summary
- **HTML**: `tests/htmlcov/index.html`
- **XML**: `coverage.xml` (for CI/CD)
- **JSON**: `tests/test_report.json`

### Coverage Goals

- Overall: >90%
- Core modules: >95%
- Critical paths: 100%

## 🎨 Test Output

The test runner provides beautiful, colored output:

```
🧪  Archon Knowledge Management Test Suite
================================================================================

Running tests...

✓ test_universal_crawler ................... 15/15 passed (2.3s)
✓ test_knowledge_linker .................... 15/15 passed (1.8s)
✓ test_knowledge_manager ................... 20/20 passed (3.1s)
✓ test_ui_components ....................... 10/10 passed (1.2s)
✓ test_langgraph_integration ............... 10/10 passed (2.5s)
✓ test_database ............................ 10/10 passed (0.8s)

================================================================================
📊  Results
================================================================================

Total Tests: 80
✅ Passed: 80 (100%)
❌ Failed: 0 (0%)
⏱️  Duration: 11.7s

✨ All tests passed!
```

## 🔧 Troubleshooting

### Common Issues

**Import Errors**
```bash
# Add parent directory to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Async Test Issues**
```bash
# Install asyncio support
pip install pytest-asyncio
```

**Coverage Not Working**
```bash
# Install coverage plugin
pip install pytest-cov
```

## 📝 Writing New Tests

### Test Template

```python
import pytest

@pytest.mark.unit
@pytest.mark.asyncio
async def test_my_feature(mock_supabase, mock_openai):
    """Test description."""
    # Arrange
    # ... setup test data
    
    # Act
    # ... call function
    
    # Assert
    # ... verify results
    assert result is not None
```

### Best Practices

1. **Use descriptive test names**: `test_analyze_task_requirements_basic`
2. **Use markers**: `@pytest.mark.unit`, `@pytest.mark.integration`
3. **Mock external services**: Use provided fixtures
4. **Test edge cases**: Empty inputs, errors, large data
5. **Keep tests independent**: Don't rely on test execution order
6. **Use async properly**: Mark async tests with `@pytest.mark.asyncio`

## 🚦 Continuous Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - run: pip install -r requirements.txt
      - run: python tests/run_all_tests.py
      - uses: codecov/codecov-action@v2
```

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Mock Documentation](https://docs.python.org/3/library/unittest.mock.html)

## 🤝 Contributing

When contributing tests:
1. Follow existing test patterns
2. Add tests for new features
3. Maintain >90% coverage
4. Update this README if needed
5. Run all tests before committing

## 📄 License

Same as parent project (see root LICENSE file)

---

**Happy Testing!** 🎉
