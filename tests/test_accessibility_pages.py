"""Accessibility tests skipped - React SPA has no server-side rendering."""
import pytest

pytestmark = pytest.mark.skip(reason="React SPA - no server-side rendering")
