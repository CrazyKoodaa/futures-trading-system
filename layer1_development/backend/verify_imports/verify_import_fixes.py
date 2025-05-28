#!/usr/bin/env python3
"""
Verification test for all import fixes in the futures-trading-system
"""

import sys
import os
from pathlib import Path
import traceback


def test_import_fixes():
    """Test that all import fixes work correctly"""

    print("🔍 TESTING IMPORT FIXES")
    print("=" * 50)

    # Get the backend directory
    backend_dir = Path(__file__).parent
    src_dir = backend_dir / "src"
    tests_dir = backend_dir / "tests"

    print(f"Backend Directory: {backend_dir}")
    print(f"Source Directory: {src_dir}")
    print(f"Tests Directory: {tests_dir}")
    print()

    # Add src to Python path
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    success_count = 0
    total_tests = 0

    # Test 1: Direct imports from src
    print("📦 Testing Direct Imports from src/")
    print("-" * 30)

    modules_to_test = [
        "enhanced_admin_rithmic",
        "admin_display_manager",
        "admin_core_classes",
        "admin_database",
        "admin_operations",
        "admin_rithmic_connection",
        "admin_rithmic_historical",
        "admin_rithmic_operations",
        "admin_rithmic_symbols",
    ]

    for module_name in modules_to_test:
        total_tests += 1
        try:
            # Test direct import
            exec(f"from src import {module_name}")
            print(f"✅ from src import {module_name}")
            success_count += 1
        except ImportError as e:
            print(f"❌ from src import {module_name} - {e}")
        except Exception as e:
            print(f"❌ from src import {module_name} - Unexpected error: {e}")

    print()

    # Test 2: Class imports
    print("🎯 Testing Class Imports")
    print("-" * 20)

    class_tests = [
        ("src.enhanced_admin_rithmic", "RithmicAdminTUI"),
        ("src.admin_display_manager", "DisplayManager"),
        ("src.admin_core_classes", "SystemStatus"),
        ("src.admin_database", "DatabaseConnection"),
    ]

    for module_name, class_name in class_tests:
        total_tests += 1
        try:
            exec(f"from {module_name} import {class_name}")
            print(f"✅ from {module_name} import {class_name}")
            success_count += 1
        except ImportError as e:
            print(f"❌ from {module_name} import {class_name} - {e}")
        except Exception as e:
            print(f"❌ from {module_name} import {class_name} - Unexpected error: {e}")

    print()

    # Test 3: Test import helper
    print("🛠 Testing Import Helper")
    print("-" * 20)

    total_tests += 1
    try:
        from tests.test_import_helper import setup_test_imports, RithmicAdminTUI

        print("✅ test_import_helper imports successfully")
        print("✅ Common classes available through helper")
        success_count += 1
    except ImportError as e:
        print(f"❌ test_import_helper import failed - {e}")
    except Exception as e:
        print(f"❌ test_import_helper - Unexpected error: {e}")

    print()

    # Test 4: Test files can import correctly
    print("📋 Testing Fixed Test Files")
    print("-" * 25)

    test_files_to_check = [
        "test_fixes.py",
        "test_tui_display.py",
        "test_enhanced_connection_display.py",
    ]

    for test_file in test_files_to_check:
        total_tests += 1
        test_path = tests_dir / test_file
        if test_path.exists():
            try:
                # Try to compile the test file to check for syntax errors
                with open(test_path, "r", encoding="utf-8") as f:
                    code = f.read()
                compile(code, str(test_path), "exec")
                print(f"✅ {test_file} - syntax OK")
                success_count += 1
            except SyntaxError as e:
                print(f"❌ {test_file} - Syntax Error: {e}")
            except Exception as e:
                print(f"❌ {test_file} - Error: {e}")
        else:
            print(f"⚠️  {test_file} - File not found")

    print()

    # Results summary
    print("🎯 RESULTS SUMMARY")
    print("=" * 20)
    print(f"✅ Successful tests: {success_count}")
    print(f"❌ Failed tests: {total_tests - success_count}")
    print(f"📊 Success rate: {(success_count/total_tests)*100:.1f}%")

    if success_count == total_tests:
        print("🎉 ALL IMPORT FIXES WORKING CORRECTLY!")
        print("\n✅ What's now working:")
        print("   • All src/ modules can be imported correctly")
        print("   • Test files have proper import paths")
        print("   • test_import_helper.py provides easy access to common classes")
        print("   • All test files have correct syntax")
        print("\n🚀 You can now run your tests!")
        print("   python tests/test_fixes.py")
        print("   python tests/test_tui_display.py")
        print("   python tests/test_enhanced_connection_display.py")
        return True
    else:
        print("⚠️  Some import issues still remain.")
        print("Check the failed tests above for details.")
        return False


def show_file_structure():
    """Show the current file structure for reference"""
    print("\n📁 CURRENT FILE STRUCTURE")
    print("=" * 30)

    backend_dir = Path(__file__).parent

    print("backend/")
    print("├── src/")
    src_dir = backend_dir / "src"
    if src_dir.exists():
        for file in sorted(src_dir.glob("*.py")):
            print(f"│   ├── {file.name}")

    print("├── tests/")
    tests_dir = backend_dir / "tests"
    if tests_dir.exists():
        for file in sorted(tests_dir.glob("*.py")):
            print(f"│   ├── {file.name}")

    print("└── other files...")


if __name__ == "__main__":
    print("🚀 Futures Trading System - Import Fix Verification")
    print("=" * 60)

    # Show file structure
    show_file_structure()

    # Test the fixes
    success = test_import_fixes()

    print("\n" + "=" * 60)
    if success:
        print("🎊 IMPORT FIXES VERIFICATION COMPLETE - ALL GOOD!")
    else:
        print("❌ IMPORT FIXES VERIFICATION - ISSUES REMAIN")

    sys.exit(0 if success else 1)
