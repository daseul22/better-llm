"""Pytest configuration and fixtures."""

import os
import sys
import pytest
from pathlib import Path
from typing import Generator

# Add src directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Environment setup
os.environ.setdefault("CLAUDE_CODE_OAUTH_TOKEN", "test-token")
os.environ.setdefault("LOG_LEVEL", "DEBUG")


@pytest.fixture
def project_root_path() -> Path:
    """Get project root path."""
    return project_root


@pytest.fixture
def test_data_path() -> Path:
    """Get test data path."""
    path = project_root / "tests" / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path
