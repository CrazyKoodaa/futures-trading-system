#!/usr/bin/env python3
"""
Comprehensive Code Analysis Script for Futures Trading System
Runs pylint, mypy, and black on all Python files and generates detailed reports.

Created: 2025-05-28T11:41:52
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import json


def ensure_tools_installed():
    """Ensure pylint, mypy, and black are installed in the virtual environment"""
    print("🔧 Checking and installing required tools...")

    tools = ["pylint", "mypy", "black"]

    for tool in tools:
        try:
            result = subprocess.run(
                [sys.executable, "-m", tool, "--version"],
                capture_output=True,
                text=True,
                check=True,
            )
            print(f"✅ {tool} is installed: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"📦 Installing {tool}...")
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", tool],
                    check=True,
                    capture_output=True,
                )
                print(f"✅ {tool} installed successfully")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install {tool}: {e}")
                return False

    return True


def get_python_files(backend_dir):
    """Get all Python files in the backend directory"""
    python_files = []

    # Include files from src, tests, scripts, and other directories
    directories_to_scan = [
        backend_dir / "src",
        backend_dir / "tests",
        backend_dir / "scripts",
        backend_dir / "fix_imports",
        backend_dir / "verify_imports",
    ]

    for directory in directories_to_scan:
        if directory.exists():
            python_files.extend(directory.rglob("*.py"))

    # Filter out __pycache__ and .pyc files
    python_files = [f for f in python_files if "__pycache__" not in str(f)]

    return sorted(python_files)


def run_pylint_analysis(files, output_dir):
    """Run pylint analysis on all files"""
    print("\n🔍 Running Pylint Analysis...")
    print("=" * 40)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_file = output_dir / f"pylint_analysis_{timestamp}.txt"

    # Pylint configuration
    pylint_args = [
        sys.executable,
        "-m",
        "pylint",
        "--reports=yes",
        "--score=yes",
        "--msg-template={path}:{line}:{column}: {msg_id}: {msg} ({symbol})",
        "--disable=missing-docstring,too-few-public-methods,invalid-name",
        "--max-line-length=100",
    ]

    all_results = []
    total_score = 0
    file_count = 0

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"PYLINT ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        for file_path in files:
            print(f"  📝 Analyzing: {file_path.name}")

            try:
                result = subprocess.run(
                    pylint_args + [str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                f.write(f"\n{'='*80}\n")
                f.write(f"FILE: {file_path}\n")
                f.write(f"{'='*80}\n")
                f.write(result.stdout)
                f.write(result.stderr)

                # Extract score if available
                if "Your code has been rated at" in result.stdout:
                    try:
                        score_line = [
                            line
                            for line in result.stdout.split("\n")
                            if "Your code has been rated at" in line
                        ][0]
                        score = float(score_line.split()[6].split("/")[0])
                        total_score += score
                        file_count += 1
                        print(f"    📊 Score: {score}/10.00")
                    except (IndexError, ValueError):
                        pass

                all_results.append(
                    {
                        "file": str(file_path),
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                    }
                )

            except subprocess.TimeoutExpired:
                print(f"    ⏰ Timeout analyzing {file_path.name}")
                f.write(f"\nTIMEOUT: Analysis of {file_path} exceeded 60 seconds\n")
            except Exception as e:
                print(f"    ❌ Error analyzing {file_path.name}: {e}")
                f.write(f"\nERROR: {e}\n")

        # Write summary
        f.write(f"\n{'='*80}\n")
        f.write("SUMMARY\n")
        f.write(f"{'='*80}\n")
        f.write(f"Files analyzed: {len(files)}\n")
        if file_count > 0:
            avg_score = total_score / file_count
            f.write(f"Average score: {avg_score:.2f}/10.00\n")
        f.write(f"Report saved: {output_file}\n")

    print(f"✅ Pylint analysis complete. Report saved: {output_file}")
    return output_file, all_results


def run_mypy_analysis(files, output_dir):
    """Run mypy analysis on all files"""
    print("\n🔍 Running MyPy Analysis...")
    print("=" * 40)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_file = output_dir / f"mypy_analysis_{timestamp}.txt"

    # MyPy configuration
    mypy_args = [
        sys.executable,
        "-m",
        "mypy",
        "--ignore-missing-imports",
        "--show-error-codes",
        "--show-column-numbers",
        "--no-error-summary",
    ]

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"MYPY ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        for file_path in files:
            print(f"  📝 Analyzing: {file_path.name}")

            try:
                result = subprocess.run(
                    mypy_args + [str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                f.write(f"\n{'='*80}\n")
                f.write(f"FILE: {file_path}\n")
                f.write(f"{'='*80}\n")

                if result.stdout:
                    f.write("STDOUT:\n")
                    f.write(result.stdout)
                    f.write("\n")

                if result.stderr:
                    f.write("STDERR:\n")
                    f.write(result.stderr)
                    f.write("\n")

                if not result.stdout and not result.stderr:
                    f.write("✅ No type errors found\n")
                    print(f"    ✅ No type errors")
                else:
                    error_count = len(
                        [
                            line
                            for line in result.stdout.split("\n")
                            if ":" in line and ("error:" in line or "warning:" in line)
                        ]
                    )
                    if error_count > 0:
                        print(f"    ⚠️  {error_count} issues found")

            except subprocess.TimeoutExpired:
                print(f"    ⏰ Timeout analyzing {file_path.name}")
                f.write(f"\nTIMEOUT: Analysis of {file_path} exceeded 60 seconds\n")
            except Exception as e:
                print(f"    ❌ Error analyzing {file_path.name}: {e}")
                f.write(f"\nERROR: {e}\n")

    print(f"✅ MyPy analysis complete. Report saved: {output_file}")
    return output_file


def run_black_formatting(files, output_dir):
    """Run black formatting on all files"""
    print("\n🎨 Running Black Formatting...")
    print("=" * 40)

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_file = output_dir / f"black_formatting_{timestamp}.txt"

    # Black configuration
    black_args = [
        sys.executable,
        "-m",
        "black",
        "--line-length=100",
        "--check",
        "--diff",
    ]

    formatted_files = []

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"BLACK FORMATTING REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        for file_path in files:
            print(f"  📝 Checking: {file_path.name}")

            try:
                result = subprocess.run(
                    black_args + [str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                f.write(f"\n{'='*80}\n")
                f.write(f"FILE: {file_path}\n")
                f.write(f"{'='*80}\n")

                if result.returncode == 0:
                    f.write("✅ Already formatted correctly\n")
                    print(f"    ✅ Already formatted")
                else:
                    f.write("🎨 Would be reformatted:\n")
                    f.write(result.stdout)
                    formatted_files.append(str(file_path))
                    print(f"    🎨 Needs formatting")

                if result.stderr:
                    f.write("STDERR:\n")
                    f.write(result.stderr)
                    f.write("\n")

            except subprocess.TimeoutExpired:
                print(f"    ⏰ Timeout checking {file_path.name}")
                f.write(
                    f"\nTIMEOUT: Formatting check of {file_path} exceeded 60 seconds\n"
                )
            except Exception as e:
                print(f"    ❌ Error checking {file_path.name}: {e}")
                f.write(f"\nERROR: {e}\n")

        f.write(f"\n{'='*80}\n")
        f.write("SUMMARY\n")
        f.write(f"{'='*80}\n")
        f.write(f"Files checked: {len(files)}\n")
        f.write(f"Files needing formatting: {len(formatted_files)}\n")

        if formatted_files:
            f.write("\nFiles that need formatting:\n")
            for file_path in formatted_files:
                f.write(f"  - {file_path}\n")

    print(f"✅ Black formatting check complete. Report saved: {output_file}")

    # Ask user if they want to apply formatting
    if formatted_files:
        print(f"\n🎨 {len(formatted_files)} files need formatting.")
        response = input("Apply black formatting? (y/N): ").strip().lower()

        if response == "y":
            apply_black_formatting(formatted_files, output_dir)

    return output_file


def apply_black_formatting(file_paths, output_dir):
    """Apply black formatting to the specified files"""
    print("\n🎨 Applying Black Formatting...")

    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_file = output_dir / f"black_applied_{timestamp}.txt"

    black_args = [sys.executable, "-m", "black", "--line-length=100"]

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"BLACK FORMATTING APPLICATION REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        for file_path in file_paths:
            print(f"  🎨 Formatting: {Path(file_path).name}")

            try:
                result = subprocess.run(
                    black_args + [file_path], capture_output=True, text=True, timeout=60
                )

                f.write(f"FILE: {file_path}\n")
                f.write(
                    f"RESULT: {'SUCCESS' if result.returncode == 0 else 'FAILED'}\n"
                )
                if result.stdout:
                    f.write(f"STDOUT: {result.stdout}\n")
                if result.stderr:
                    f.write(f"STDERR: {result.stderr}\n")
                f.write("-" * 40 + "\n")

                if result.returncode == 0:
                    print(f"    ✅ Formatted successfully")
                else:
                    print(f"    ❌ Formatting failed")

            except Exception as e:
                print(f"    ❌ Error formatting {file_path}: {e}")
                f.write(f"ERROR: {e}\n")

    print(f"✅ Black formatting applied. Log saved: {output_file}")


def generate_summary_report(
    backend_dir, output_dir, pylint_file, mypy_file, black_file
):
    """Generate a comprehensive summary report"""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    summary_file = output_dir / f"comprehensive_analysis_summary_{timestamp}.txt"

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("COMPREHENSIVE CODE ANALYSIS SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Backend Directory: {backend_dir}\n\n")

        f.write("ANALYSIS REPORTS GENERATED:\n")
        f.write("-" * 40 + "\n")
        f.write(f"📊 Pylint Report: {pylint_file}\n")
        f.write(f"🔍 MyPy Report: {mypy_file}\n")
        f.write(f"🎨 Black Report: {black_file}\n\n")

        f.write("RECOMMENDED NEXT STEPS:\n")
        f.write("-" * 40 + "\n")
        f.write("1. Review pylint report for code quality issues\n")
        f.write("2. Review mypy report for type annotation issues\n")
        f.write("3. Apply black formatting if not already done\n")
        f.write("4. Fix any import issues found in the reports\n")
        f.write("5. Re-run analysis after fixes to verify improvements\n\n")

        f.write("IMPORT FIX INFORMATION:\n")
        f.write("-" * 40 + "\n")
        f.write("Import fixes have been moved to appropriate folders:\n")
        f.write("- fix_imports/fix_imports.py\n")
        f.write("- verify_imports/verify_import_fixes.py\n\n")

        f.write("RUN TESTS:\n")
        f.write("-" * 40 + "\n")
        f.write("After fixing issues, test the system:\n")
        f.write("1. python verify_imports/verify_import_fixes.py\n")
        f.write("2. python tests/test_fixes.py\n")
        f.write("3. python src/enhanced_admin_rithmic.py\n")

    print(f"\n📋 Comprehensive summary report saved: {summary_file}")
    return summary_file


def main():
    """Main analysis function"""
    print("🚀 COMPREHENSIVE CODE ANALYSIS")
    print("=" * 60)
    print("Running pylint, mypy, and black on all Python files")
    print("=" * 60)

    # Setup paths
    backend_dir = Path(__file__).parent.parent
    output_dir = backend_dir / "outputs"

    print(f"Backend Directory: {backend_dir}")
    print(f"Output Directory: {output_dir}")

    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)

    # Ensure tools are installed
    if not ensure_tools_installed():
        print("❌ Failed to install required tools")
        return 1

    # Get all Python files
    print("\n📁 Scanning for Python files...")
    python_files = get_python_files(backend_dir)
    print(f"Found {len(python_files)} Python files")

    if not python_files:
        print("❌ No Python files found!")
        return 1

    # Show files to be analyzed
    print("\nFiles to analyze:")
    for file_path in python_files[:10]:  # Show first 10
        print(f"  📝 {file_path.relative_to(backend_dir)}")
    if len(python_files) > 10:
        print(f"  ... and {len(python_files) - 10} more")

    try:
        # Run analyses
        pylint_file, _ = run_pylint_analysis(python_files, output_dir)
        mypy_file = run_mypy_analysis(python_files, output_dir)
        black_file = run_black_formatting(python_files, output_dir)

        # Generate summary
        summary_file = generate_summary_report(
            backend_dir, output_dir, pylint_file, mypy_file, black_file
        )

        print("\n🎉 ANALYSIS COMPLETE!")
        print("=" * 30)
        print("All reports have been generated and saved to the outputs/ directory")
        print(f"📋 Summary report: {summary_file}")

        return 0

    except KeyboardInterrupt:
        print("\n⚠️  Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
