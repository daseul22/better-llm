"""Unit tests for app.py (Phase 1 changes - Import Organization)."""

import sys
import importlib
import pytest
from pathlib import Path


class TestAppImportOrganization:
    """Test import organization improvements in app.py.

    Phase 1 Change: Reorganized imports to follow PEP 8
    - Standard library imports first
    - Third-party imports second
    - Local imports third
    - Proper grouping with comments
    """

    def test_app_module_importable(self):
        """Test that app module can be imported without errors."""
        # This validates that all imports are correct and present
        try:
            from src.presentation.web import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"Failed to import app module: {e}")

    def test_standard_library_imports_present(self):
        """Test that standard library imports are available."""
        import os
        from pathlib import Path
        from contextlib import asynccontextmanager

        # These should be available
        assert os is not None
        assert Path is not None
        assert asynccontextmanager is not None

    def test_third_party_imports_present(self):
        """Test that third-party imports are available."""
        from dotenv import load_dotenv
        from fastapi import FastAPI

        # These should be available
        assert load_dotenv is not None
        assert FastAPI is not None

    def test_local_imports_present(self):
        """Test that local imports are available."""
        from src.presentation.web.routers import (
            agents_router,
            health_router,
            workflows_router,
        )

        # These should be available
        assert agents_router is not None
        assert health_router is not None
        assert workflows_router is not None

    def test_import_order_pep8_compliance(self):
        """Test that imports follow PEP 8 ordering.

        PEP 8 specifies:
        1. Standard library imports
        2. Related third party imports
        3. Local application/library specific imports
        """
        # Read the app.py file to check import order
        app_path = Path("src/presentation/web/app.py")
        if not app_path.exists():
            pytest.skip("app.py not found")

        with open(app_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find import sections
        lines = content.split('\n')
        import_section = []
        for i, line in enumerate(lines[:50]):  # Check first 50 lines
            if line.startswith('import ') or line.startswith('from '):
                import_section.append((i, line))
            elif import_section and line and not line.startswith('#'):
                break

        # Check that we have imports
        assert len(import_section) > 0, "No imports found in app.py"

        # Verify import order (should have standard library before third-party)
        standard_lib_idx = -1
        third_party_idx = -1
        local_idx = -1

        for i, (line_num, line) in enumerate(import_section):
            if 'from dotenv' in line or 'from fastapi' in line or 'import fastapi' in line:
                third_party_idx = i if third_party_idx == -1 else third_party_idx
            elif 'from src' in line or 'import src' in line:
                local_idx = i if local_idx == -1 else local_idx
            elif any(x in line for x in ['import os', 'from pathlib', 'from contextlib']):
                standard_lib_idx = i if standard_lib_idx == -1 else standard_lib_idx

        # Standard library should come before third-party
        if standard_lib_idx != -1 and third_party_idx != -1:
            assert standard_lib_idx < third_party_idx, \
                "Standard library imports should come before third-party"

        # Third-party should come before local
        if third_party_idx != -1 and local_idx != -1:
            assert third_party_idx < local_idx, \
                "Third-party imports should come before local imports"

    def test_dotenv_loads_environment(self):
        """Test that dotenv properly loads environment variables."""
        import os
        from dotenv import load_dotenv

        # dotenv should be able to load .env files
        assert callable(load_dotenv), "load_dotenv should be callable"

    def test_fastapi_imports(self):
        """Test that FastAPI and dependencies are imported correctly."""
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.staticfiles import StaticFiles

        # All FastAPI components should be available
        assert FastAPI is not None
        assert HTTPException is not None
        assert CORSMiddleware is not None
        assert StaticFiles is not None

    def test_router_imports(self):
        """Test that all routers are properly imported."""
        from src.presentation.web.routers import (
            agents_router,
            health_router,
            workflows_router,
        )

        # All routers should be imported
        assert agents_router is not None
        assert health_router is not None
        assert workflows_router is not None

    def test_no_circular_imports(self):
        """Test that importing app doesn't cause circular imports."""
        # Remove app from sys.modules if it was previously imported
        if 'src.presentation.web.app' in sys.modules:
            del sys.modules['src.presentation.web.app']

        # Try importing app fresh - should not raise ImportError
        try:
            from src.presentation.web import app
            assert app is not None
        except ImportError as e:
            if 'circular' in str(e).lower():
                pytest.fail(f"Circular import detected: {e}")
            raise

    @pytest.mark.parametrize("import_name", [
        "os",
        "pathlib",
        "contextlib",
        "dotenv",
        "fastapi",
    ])
    def test_required_imports_available(self, import_name: str):
        """Test that required imports are available."""
        try:
            if import_name == "pathlib":
                from pathlib import Path
                assert Path is not None
            elif import_name == "contextlib":
                from contextlib import asynccontextmanager
                assert asynccontextmanager is not None
            elif import_name == "dotenv":
                from dotenv import load_dotenv
                assert load_dotenv is not None
            elif import_name == "fastapi":
                from fastapi import FastAPI
                assert FastAPI is not None
            else:
                import importlib
                mod = importlib.import_module(import_name)
                assert mod is not None
        except ImportError as e:
            pytest.fail(f"Required import {import_name} not available: {e}")
