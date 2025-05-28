#!/usr/bin/env python3
"""
Rithmic Admin Tool - Setup and Troubleshooting Script
Python 3.11.9 compatible

This script helps set up the environment and troubleshoot common issues.
"""

import sys
import os
import subprocess
import importlib.util


def check_python_version():
    """Check if we're running Python 3.11.9"""
    version = sys.version_info
    print(f"Python Version: {version.major}.{version.minor}.{version.micro}")

    if version.major != 3:
        print("❌ ERROR: Python 3 is required")
        return False

    if version.minor < 11:
        print("⚠️  WARNING: Python 3.11+ recommended for best compatibility")
    elif version.minor == 11 and version.micro == 9:
        print("✅ Perfect! Python 3.11.9 detected")
    else:
        print("✅ Python 3.11+ detected - should work fine")

    return True


def check_virtual_environment():
    """Check if we're in a virtual environment"""
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )

    if in_venv:
        print("✅ Virtual environment detected")
        print(f"   Environment: {sys.prefix}")
    else:
        print("⚠️  WARNING: Not in a virtual environment")
        print("   Recommendation: Create and activate a virtual environment")
        print("   Commands:")
        print("     python -m venv venv")
        print("     .\\venv\\Scripts\\activate  (Windows)")
        print("     source venv/bin/activate  (Linux/Mac)")

    return in_venv


def check_required_packages():
    """Check if required packages are installed"""
    required_packages = [
        "rich",
        "sqlalchemy",
        "asyncpg",
        "pandas",
        "numpy",
        "pytz",
        "keyboard",
        "pynput",
    ]

    missing_packages = []
    installed_packages = []

    for package in required_packages:
        spec = importlib.util.find_spec(package)
        if spec is None:
            missing_packages.append(package)
        else:
            installed_packages.append(package)

    print(f"\n📦 Package Status:")
    for package in installed_packages:
        print(f"   ✅ {package}")

    for package in missing_packages:
        print(f"   ❌ {package} - MISSING")

    if missing_packages:
        print(f"\n🔧 To install missing packages:")
        print(f"   pip install {' '.join(missing_packages)}")
        print(f"   OR: pip install -r requirements_core.txt")

    return len(missing_packages) == 0


def check_project_structure():
    """Check if all required project files exist"""
    required_files = [
        "admin_core_classes.py",
        "admin_database.py",
        "admin_display_manager.py",
        "admin_operations.py",
        "admin_rithmic_connection.py",
        "admin_rithmic_historical.py",
        "admin_rithmic_operations.py",
        "admin_rithmic_symbols.py",
        "enhanced_admin_rithmic_fixed.py",
        "__init__.py",
    ]

    current_dir = os.path.dirname(os.path.abspath(__file__))
    missing_files = []
    existing_files = []

    for file in required_files:
        file_path = os.path.join(current_dir, file)
        if os.path.exists(file_path):
            existing_files.append(file)
        else:
            missing_files.append(file)

    print(f"\n📁 Project Structure:")
    for file in existing_files:
        print(f"   ✅ {file}")

    for file in missing_files:
        print(f"   ❌ {file} - MISSING")

    return len(missing_files) == 0


def check_config_files():
    """Check for configuration files"""
    config_locations = [
        "config/chicago_gateway_config.py",
        "../config/chicago_gateway_config.py",
        "../../config/chicago_gateway_config.py",
    ]

    config_found = False
    for config_path in config_locations:
        if os.path.exists(config_path):
            print(f"✅ Configuration found: {config_path}")
            config_found = True
            break

    if not config_found:
        print("❌ Configuration file not found")
        print("   Expected: config/chicago_gateway_config.py")
        print("   This file should contain your Rithmic connection settings")

    return config_found


def run_diagnostics():
    """Run all diagnostic checks"""
    print("🔍 Rithmic Admin Tool - Diagnostic Check\n")
    print("=" * 50)

    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Required Packages", check_required_packages),
        ("Project Structure", check_project_structure),
        ("Configuration", check_config_files),
    ]

    results = {}
    for check_name, check_func in checks:
        print(f"\n🔍 Checking {check_name}...")
        results[check_name] = check_func()

    # Summary
    print("\n" + "=" * 50)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 50)

    all_good = True
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {check_name}")
        if not result:
            all_good = False

    if all_good:
        print("\n🎉 All checks passed! You should be ready to run the application.")
        print("\nTo start the application:")
        print("   python enhanced_admin_rithmic_fixed.py")
    else:
        print(
            "\n⚠️  Some issues found. Please address them before running the application."
        )
        print("\nQuick setup commands:")
        print("   1. pip install -r requirements_core.txt")
        print("   2. Set up your Rithmic configuration")
        print("   3. python enhanced_admin_rithmic_fixed.py")


def install_requirements():
    """Install requirements automatically"""
    print("📦 Installing required packages...")

    requirements_files = ["requirements_core.txt", "requirements.txt"]

    for req_file in requirements_files:
        if os.path.exists(req_file):
            print(f"Installing from {req_file}...")
            try:
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", "-r", req_file]
                )
                print(f"✅ Successfully installed packages from {req_file}")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Error installing from {req_file}: {e}")
                continue

    print("❌ No requirements file found or installation failed")
    return False


def main():
    """Main function"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "install":
            install_requirements()
        elif sys.argv[1] == "check":
            run_diagnostics()
        else:
            print("Usage: python setup_check.py [install|check]")
    else:
        run_diagnostics()


if __name__ == "__main__":
    main()
