import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Test configuration
pytest_plugins = ["pytest_asyncio"]

# Environment variables for testing
os.environ.setdefault("BAM_TEST_MODE", "true")
os.environ.setdefault("BAM_LOG_LEVEL", "DEBUG")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def setup_test_environment():
    """Setup test environment before each test."""
    # Any global test setup can go here
    yield
    # Cleanup after each test
    pass
