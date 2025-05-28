"""
Test import helper module

This module ensures consistent imports across all test files and handles
the path setup required to import from the src/ directory.
"""

import sys
import os
from pathlib import Path


# Ensure src directory is in Python path
def setup_test_imports():
    """Setup Python path to allow imports from src/ directory"""
    backend_dir = Path(__file__).parent.parent
    src_dir = backend_dir / "src"

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    return str(src_dir)


# Auto-setup when this module is imported
setup_test_imports()

# Import commonly used classes for easy access
try:
    from src.enhanced_admin_rithmic import RithmicAdminTUI
    from src.admin_display_manager import DisplayManager
    from src.admin_core_classes import SystemStatus, DatabaseManager
    from src.admin_database import DatabaseConnection
    from src.admin_rithmic_connection import RithmicConnection

    # Make them available for import
    __all__ = [
        "RithmicAdminTUI",
        "DisplayManager",
        "SystemStatus",
        "DatabaseManager",
        "DatabaseConnection",
        "RithmicConnection",
        "setup_test_imports",
    ]

except ImportError as e:
    print(f"Warning: Could not import some modules from src/: {e}")
    __all__ = ["setup_test_imports"]
