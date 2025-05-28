#!/usr/bin/env python3
"""
Focused Code Analysis and Fix Script
Runs pylint, mypy, and black analysis on key Python files and generates timestamped reports.

Created: 2025-05-28T11:41:52
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
import json


def get_timestamp():
    """Get current timestamp for filenames"""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def ensure_venv_python():
    """Get the virtual environment Python path"""
    backend_dir = Path(__file__).parent.parent
    root_dir = backend_dir.parent.parent
    venv_dir = root_dir / "venv"

    if os.name == "nt":  # Windows
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:  # Linux/Mac
        python_exe = venv_dir / "bin" / "python"

    if python_exe.exists():
        return str(python_exe)
    else:
        print(f"❌ Virtual environment Python not found at: {python_exe}")
        print("Using system Python as fallback")
        return sys.executable


def get_key_python_files():
    """Get list of key Python files to analyze"""
    backend_dir = Path(__file__).parent.parent

    key_files = []

    # Main source files
    src_files = [
        "enhanced_admin_rithmic.py",
        "admin_display_manager.py",
        "admin_core_classes.py",
        "admin_database.py",
        "admin_rithmic_connection.py",
        "admin_rithmic_historical.py",
        "admin_rithmic_operations.py",
        "admin_rithmic_symbols.py",
    ]

    src_dir = backend_dir / "src"
    for file in src_files:
        file_path = src_dir / file
        if file_path.exists():
            key_files.append(file_path)

    # Key test files
    test_files = [
        "test_fixes.py",
        "test_tui_display.py",
        "test_enhanced_connection_display.py",
    ]

    tests_dir = backend_dir / "tests"
    for file in test_files:
        file_path = tests_dir / file
        if file_path.exists():
            key_files.append(file_path)

    # Import fix files
    fix_files = [
        backend_dir / "fix_imports" / "fix_imports.py",
        backend_dir / "verify_imports" / "verify_import_fixes.py",
    ]

    for file_path in fix_files:
        if file_path.exists():
            key_files.append(file_path)

    return key_files


def install_tool_if_needed(python_exe, tool_name):
    """Install analysis tool if not available"""
    try:
        result = subprocess.run(
            [python_exe, "-m", tool_name, "--version"],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"✅ {tool_name} is available: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"📦 Installing {tool_name}...")
        try:
            subprocess.run(
                [python_exe, "-m", "pip", "install", tool_name],
                check=True,
                capture_output=True,
            )
            print(f"✅ {tool_name} installed successfully")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {tool_name}: {e}")
            return False


def run_pylint_analysis(python_exe, files, output_dir):
    """Run pylint analysis on files"""
    print("\n🔍 Running Pylint Analysis...")
    print("=" * 40)

    timestamp = get_timestamp()
    output_file = output_dir / f"pylint_analysis_{timestamp}.txt"

    results = {}

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"PYLINT ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        for file_path in files:
            print(f"  📝 Analyzing: {file_path.name}")

            pylint_args = [
                python_exe,
                "-m",
                "pylint",
                "--reports=yes",
                "--score=yes",
                "--msg-template={path}:{line}:{column}: {msg_id}: {msg} ({symbol})",
                "--disable=missing-docstring,too-few-public-methods,invalid-name,line-too-long",
                "--max-line-length=120",
                str(file_path),
            ]

            try:
                result = subprocess.run(
                    pylint_args, capture_output=True, text=True, timeout=60
                )

                f.write(f"\n{'='*80}\n")
                f.write(f"FILE: {file_path}\n")
                f.write(f"{'='*80}\n")
                f.write(result.stdout)
                if result.stderr:
                    f.write("\nSTDERR:\n")
                    f.write(result.stderr)

                # Extract score
                score = "N/A"
                if "Your code has been rated at" in result.stdout:
                    try:
                        score_line = [
                            line
                            for line in result.stdout.split("\n")
                            if "Your code has been rated at" in line
                        ][0]
                        score = score_line.split()[6].split("/")[0]
                        print(f"    📊 Score: {score}/10.00")
                    except (IndexError, ValueError):
                        pass

                results[str(file_path)] = {
                    "score": score,
                    "returncode": result.returncode,
                    "has_issues": result.returncode != 0,
                }

            except subprocess.TimeoutExpired:
                print(f"    ⏰ Timeout analyzing {file_path.name}")
                f.write(f"\nTIMEOUT: Analysis exceeded 60 seconds\n")
                results[str(file_path)] = {
                    "score": "TIMEOUT",
                    "returncode": -1,
                    "has_issues": True,
                }
            except Exception as e:
                print(f"    ❌ Error analyzing {file_path.name}: {e}")
                f.write(f"\nERROR: {e}\n")
                results[str(file_path)] = {
                    "score": "ERROR",
                    "returncode": -1,
                    "has_issues": True,
                }

    print(f"✅ Pylint analysis complete. Report: {output_file}")
    return output_file, results


def run_mypy_analysis(python_exe, files, output_dir):
    """Run mypy analysis on files"""
    print("\n🔍 Running MyPy Analysis...")
    print("=" * 40)

    timestamp = get_timestamp()
    output_file = output_dir / f"mypy_analysis_{timestamp}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"MYPY ANALYSIS REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        for file_path in files:
            print(f"  📝 Analyzing: {file_path.name}")

            mypy_args = [
                python_exe,
                "-m",
                "mypy",
                "--ignore-missing-imports",
                "--show-error-codes",
                "--show-column-numbers",
                "--no-error-summary",
                str(file_path),
            ]

            try:
                result = subprocess.run(
                    mypy_args, capture_output=True, text=True, timeout=60
                )

                f.write(f"\n{'='*80}\n")
                f.write(f"FILE: {file_path}\n")
                f.write(f"{'='*80}\n")

                if result.stdout:
                    f.write("ISSUES FOUND:\n")
                    f.write(result.stdout)
                    issue_count = len(
                        [
                            line
                            for line in result.stdout.split("\n")
                            if ":" in line and ("error:" in line or "warning:" in line)
                        ]
                    )
                    print(f"    ⚠️  {issue_count} issues found")
                else:
                    f.write("✅ No type errors found\n")
                    print(f"    ✅ No type errors")

                if result.stderr:
                    f.write("\nSTDERR:\n")
                    f.write(result.stderr)

            except subprocess.TimeoutExpired:
                print(f"    ⏰ Timeout analyzing {file_path.name}")
                f.write(f"\nTIMEOUT: Analysis exceeded 60 seconds\n")
            except Exception as e:
                print(f"    ❌ Error analyzing {file_path.name}: {e}")
                f.write(f"\nERROR: {e}\n")

    print(f"✅ MyPy analysis complete. Report: {output_file}")
    return output_file


def run_black_check(python_exe, files, output_dir):
    """Run black formatting check on files"""
    print("\n🎨 Running Black Formatting Check...")
    print("=" * 40)

    timestamp = get_timestamp()
    output_file = output_dir / f"black_check_{timestamp}.txt"

    files_needing_format = []

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"BLACK FORMATTING CHECK REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        for file_path in files:
            print(f"  📝 Checking: {file_path.name}")

            black_args = [
                python_exe,
                "-m",
                "black",
                "--check",
                "--diff",
                "--line-length=120",
                str(file_path),
            ]

            try:
                result = subprocess.run(
                    black_args, capture_output=True, text=True, timeout=60
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
                    files_needing_format.append(str(file_path))
                    print(f"    🎨 Needs formatting")

                if result.stderr:
                    f.write("\nSTDERR:\n")
                    f.write(result.stderr)

            except subprocess.TimeoutExpired:
                print(f"    ⏰ Timeout checking {file_path.name}")
                f.write(f"\nTIMEOUT: Check exceeded 60 seconds\n")
            except Exception as e:
                print(f"    ❌ Error checking {file_path.name}: {e}")
                f.write(f"\nERROR: {e}\n")

        f.write(f"\n{'='*80}\n")
        f.write("SUMMARY\n")
        f.write(f"{'='*80}\n")
        f.write(f"Files checked: {len(files)}\n")
        f.write(f"Files needing formatting: {len(files_needing_format)}\n")

        if files_needing_format:
            f.write("\nFiles that need formatting:\n")
            for file_path in files_needing_format:
                f.write(f"  - {file_path}\n")

    print(f"✅ Black check complete. Report: {output_file}")

    # Ask if user wants to apply formatting
    if files_needing_format:
        print(f"\n🎨 {len(files_needing_format)} files need formatting.")
        apply_formatting = (
            input("Apply black formatting? (y/N): ").strip().lower() == "y"
        )

        if apply_formatting:
            apply_black_formatting(python_exe, files_needing_format, output_dir)

    return output_file


def apply_black_formatting(python_exe, file_paths, output_dir):
    """Apply black formatting to specified files"""
    print("\n🎨 Applying Black Formatting...")

    timestamp = get_timestamp()
    output_file = output_dir / f"black_applied_{timestamp}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"BLACK FORMATTING APPLICATION REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write("=" * 80 + "\n\n")

        for file_path in file_paths:
            print(f"  🎨 Formatting: {Path(file_path).name}")

            black_args = [python_exe, "-m", "black", "--line-length=120", file_path]

            try:
                result = subprocess.run(
                    black_args, capture_output=True, text=True, timeout=60
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

    print(f"✅ Black formatting applied. Log: {output_file}")


def generate_comprehensive_report(
    output_dir, pylint_file, mypy_file, black_file, pylint_results
):
    """Generate comprehensive analysis summary"""
    timestamp = get_timestamp()
    summary_file = output_dir / f"comprehensive_analysis_summary_{timestamp}.md"

    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("# Comprehensive Code Analysis Summary\n\n")
        f.write(f"**Generated:** {datetime.now()}\n\n")
        f.write("## 📊 Analysis Reports Generated\n\n")
        f.write(f"- **📋 Pylint Report:** `{pylint_file.name}`\n")
        f.write(f"- **🔍 MyPy Report:** `{mypy_file.name}`\n")
        f.write(f"- **🎨 Black Report:** `{black_file.name}`\n\n")

        f.write("## 🎯 Pylint Score Summary\n\n")
        f.write("| File | Score | Issues |\n")
        f.write("|------|-------|--------|\n")

        for file_path, result in pylint_results.items():
            file_name = Path(file_path).name
            score = result.get("score", "N/A")
            has_issues = "Yes" if result.get("has_issues", False) else "No"
            f.write(f"| {file_name} | {score}/10.00 | {has_issues} |\n")

        f.write("\n## 🔧 Recommended Actions\n\n")
        f.write("1. **Review pylint report** for code quality issues\n")
        f.write("2. **Review mypy report** for type annotation issues\n")
        f.write("3. **Apply black formatting** if not already done\n")
        f.write("4. **Fix import issues** using the reorganized import fix scripts\n")
        f.write("5. **Re-run analysis** after fixes to verify improvements\n\n")

        f.write("## 📁 File Organization Status\n\n")
        f.write("✅ Import fix scripts moved to proper folders:\n")
        f.write("- `fix_imports/fix_imports.py`\n")
        f.write("- `verify_imports/verify_import_fixes.py`\n\n")

        f.write("## 🧪 Testing\n\n")
        f.write("After fixing issues, run these tests:\n")
        f.write("```bash\n")
        f.write("python verify_imports/verify_import_fixes.py\n")
        f.write("python tests/test_fixes.py\n")
        f.write("python src/enhanced_admin_rithmic.py\n")
        f.write("```\n\n")

        f.write("## 📈 Next Steps\n\n")
        f.write("1. Address high-priority pylint issues (scores < 7.0)\n")
        f.write("2. Fix any mypy type errors\n")
        f.write("3. Ensure all imports work correctly after reorganization\n")
        f.write("4. Run comprehensive tests to verify functionality\n")

    print(f"\n📋 Comprehensive summary: {summary_file}")
    return summary_file


def main():
    """Main analysis function"""
    print("🚀 FOCUSED CODE ANALYSIS FOR FUTURES TRADING SYSTEM")
    print("=" * 65)

    # Setup paths
    backend_dir = Path(__file__).parent.parent
    output_dir = backend_dir / "outputs"
    output_dir.mkdir(exist_ok=True)

    print(f"Backend Directory: {backend_dir}")
    print(f"Output Directory: {output_dir}")

    # Get virtual environment Python
    python_exe = ensure_venv_python()
    print(f"Using Python: {python_exe}")

    # Get key files to analyze
    files = get_key_python_files()
    print(f"\nFound {len(files)} key files to analyze:")
    for f in files:
        print(f"  📝 {f.relative_to(backend_dir)}")

    if not files:
        print("❌ No files found to analyze!")
        return 1

    # Install required tools
    print("\n🔧 Ensuring analysis tools are available...")
    for tool in ["pylint", "mypy", "black"]:
        if not install_tool_if_needed(python_exe, tool):
            print(f"❌ Failed to install {tool}, continuing without it...")

    try:
        # Run analyses
        pylint_file, pylint_results = run_pylint_analysis(python_exe, files, output_dir)
        mypy_file = run_mypy_analysis(python_exe, files, output_dir)
        black_file = run_black_check(python_exe, files, output_dir)

        # Generate comprehensive summary
        summary_file = generate_comprehensive_report(
            output_dir, pylint_file, mypy_file, black_file, pylint_results
        )

        print("\n🎉 FOCUSED ANALYSIS COMPLETE!")
        print("=" * 35)
        print("Key reports generated in outputs/ directory")
        print(f"📋 Summary: {summary_file.name}")

        # Show quick summary
        issues_found = sum(
            1 for result in pylint_results.values() if result.get("has_issues", False)
        )
        print(
            f"\n📊 Quick Summary: {issues_found}/{len(files)} files have pylint issues"
        )

        return 0

    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
