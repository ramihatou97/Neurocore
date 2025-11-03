"""
Pytest configuration and fixtures for test suite

This file configures the Python path for proper module imports when running tests
inside Docker containers.
"""

import sys
from pathlib import Path

# Add project root to Python path for imports
# This allows 'from backend.xxx import yyy' to work correctly
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
