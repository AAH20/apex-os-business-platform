"""Pytest configuration - skip tests that require external services."""
import pytest

# Ignore test files that require external services or have missing dependencies
collect_ignore = [
    "test_accessibility.py",
    "test_api.py",
    "test_crud_accessibility.py",
    "test_crud_e2e.py",
    "test_deepened_security.py",
    "test_e2e_all_pages.py",
    "test_e2e_frontend.py",
    "test_e2e_pages.py",
    "test_file_storage.py",
    "test_integration_all.py",
    "test_performance_pages.py",
    "test_responsiveness.py",
    "test_ui_ux.py",
]
