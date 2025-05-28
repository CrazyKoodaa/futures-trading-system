#!/usr/bin/env python3
"""
Comprehensive fix for test import issues in the futures-trading-system
"""

import os
import sys
from pathlib import Path


def fix_test_file_imports():
    """
    Fix import statements in all test files to work with the new src/ structure
    """

    # Get the backend directory path
    backend_dir = Path(
        r"C:\Users\nobody\myProjects\git\futures-trading-system\layer1_development\backend"
    )
    tests_dir = backend_dir / "tests"
    src_dir = backend_dir / "src"

    print("🔧 Fixing Test Import Issues")
    print("=" * 50)
    print(f"Backend Directory: {backend_dir}")
    print(f"Tests Directory: {tests_dir}")
    print(f"Source Directory: {src_dir}")
    print()

    # Define the import fixes needed
    import_fixes = {
        # Direct module imports that need to be prefixed with 'src.'
        "import admin_display_manager": "from src import admin_display_manager",
        "import admin_core_classes": "from src import admin_core_classes",
        "import admin_database": "from src import admin_database",
        "import admin_operations": "from src import admin_operations",
        "import admin_rithmic_connection": "from src import admin_rithmic_connection",
        "import admin_rithmic_historical": "from src import admin_rithmic_historical",
        "import admin_rithmic_operations": "from src import admin_rithmic_operations",
        "import admin_rithmic_symbols": "from src import admin_rithmic_symbols",
        "import enhanced_admin_rithmic": "from src import enhanced_admin_rithmic",
        # From imports that need to be prefixed with 'src.'
        "from enhanced_admin_rithmic import": "from src.enhanced_admin_rithmic import",
        "from admin_display_manager import": "from src.admin_display_manager import",
        "from admin_core_classes import": "from src.admin_core_classes import",
        "from admin_database import": "from src.admin_database import",
        "from admin_operations import": "from src.admin_operations import",
        "from admin_rithmic_connection import": "from src.admin_rithmic_connection import",
        "from admin_rithmic_historical import": "from src.admin_rithmic_historical import",
        "from admin_rithmic_operations import": "from src.admin_rithmic_operations import",
        "from admin_rithmic_symbols import": "from src.admin_rithmic_symbols import",
    }

    # Common sys.path fix to add at the beginning of test files
    sys_path_fix = """import sys
import os
from pathlib import Path

# Add the src directory to Python path for imports
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

"""

    # Process all Python files in the tests directory
    test_files = list(tests_dir.glob("*.py"))

    for test_file in test_files:
        if test_file.name == "__init__.py":
            continue

        print(f"📝 Processing: {test_file.name}")

        try:
            # Read the file
            with open(test_file, "r", encoding="utf-8") as f:
                content = f.read()

            original_content = content
            needs_sys_path_fix = False

            # Check if any of our target imports are present
            for old_import, new_import in import_fixes.items():
                if old_import in content:
                    content = content.replace(old_import, new_import)
                    needs_sys_path_fix = True
                    print(f"   ✅ Fixed: {old_import} → {new_import}")

            # Add sys.path fix if needed and not already present
            if needs_sys_path_fix and "sys.path.insert" not in content:
                # Find the first import statement and insert sys.path fix before it
                lines = content.split("\n")
                insert_index = 0

                # Find first non-comment, non-shebang line
                for i, line in enumerate(lines):
                    stripped = line.strip()
                    if (
                        stripped
                        and not stripped.startswith("#")
                        and not stripped.startswith('"""')
                        and not stripped.startswith("'''")
                    ):
                        insert_index = i
                        break

                # Insert the sys.path fix
                lines.insert(insert_index, sys_path_fix)
                content = "\n".join(lines)
                print(f"   ✅ Added sys.path fix")

            # Write back if changes were made
            if content != original_content:
                with open(test_file, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"   💾 Saved changes to {test_file.name}")
            else:
                print(f"   ✅ No changes needed for {test_file.name}")

        except Exception as e:
            print(f"   ❌ Error processing {test_file.name}: {e}")

    print()
    print("🎯 Import Fix Summary")
    print("=" * 30)
    print("✅ Updated all test files to use proper src/ imports")
    print("✅ Added sys.path configuration for Python module resolution")
    print("✅ Test files should now be able to find and import src/ modules")
    print()
    print("🚀 Next Steps:")
    print("1. Test the fixes by running individual test files")
    print("2. Run: python -m pytest tests/ (if pytest is installed)")
    print("3. Or run individual tests like: python tests/test_fixes.py")


def create_import_helper():
    """
    Create a helper module for consistent imports across test files
    """
    backend_dir = Path(
        r"C:\Users\nobody\myProjects\git\futures-trading-system\layer1_development\backend"
    )
    tests_dir = backend_dir / "tests"

    helper_content = '''"""
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
        'RithmicAdminTUI',
        'DisplayManager', 
        'SystemStatus',
        'DatabaseManager',
        'DatabaseConnection',
        'RithmicConnection',
        'setup_test_imports'
    ]
    
except ImportError as e:
    print(f"Warning: Could not import some modules from src/: {e}")
    __all__ = ['setup_test_imports']
'''

    helper_file = tests_dir / "test_import_helper.py"

    with open(helper_file, "w", encoding="utf-8") as f:
        f.write(helper_content)

    print(f"📦 Created test import helper: {helper_file}")
    print("   Use: from test_import_helper import RithmicAdminTUI, DisplayManager")


def verify_fixes():
    """
    Verify that the import fixes work by attempting imports
    """
    backend_dir = Path(
        r"C:\Users\nobody\myProjects\git\futures-trading-system\layer1_development\backend"
    )
    os.chdir(backend_dir)

    print("🔍 Verifying Import Fixes")
    print("=" * 30)

    # Test basic imports
    try:
        sys.path.insert(0, str(backend_dir / "src"))

        import enhanced_admin_rithmic

        print("✅ enhanced_admin_rithmic imports successfully")

        import admin_display_manager

        print("✅ admin_display_manager imports successfully")

        import admin_core_classes

        print("✅ admin_core_classes imports successfully")

        # Test class access
        from enhanced_admin_rithmic import RithmicAdminTUI

        print("✅ RithmicAdminTUI class accessible")

        from admin_display_manager import DisplayManager

        print("✅ DisplayManager class accessible")

        print("🎉 All core imports working correctly!")
        return True

    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Futures Trading System - Test Import Fixer")
    print("=" * 50)

    # Fix the import issues
    fix_test_file_imports()

    # Create helper module
    create_import_helper()

    # Verify the fixes work
    success = verify_fixes()

    if success:
        print("\n🎉 SUCCESS: All import issues should now be resolved!")
        print("\n📋 What was fixed:")
        print("   ✅ Updated all test file imports to use src/ prefix")
        print("   ✅ Added proper sys.path configuration")
        print("   ✅ Created test_import_helper.py for easy imports")
        print("   ✅ Verified core modules can be imported")
        print("\n🎮 Try running your tests now!")
    else:
        print("\n❌ Some issues remain. Check the error messages above.")
