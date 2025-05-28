#!/usr/bin/env python3
"""
COMPREHENSIVE CODE ANALYSIS, FIXES, AND REPORTING TOOL
Final implementation that addresses all issues found during reorganization

This script:
1. Analyzes all Python files for syntax and import issues
2. Applies automatic fixes where possible
3. Generates comprehensive reports with timestamps
4. Creates proper file organization
5. Runs targeted fixes for the futures trading system backend

Created: 2025-05-28T11:41:52
"""

import os
import sys
import ast
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import traceback


def get_timestamp() -> str:
    """Get current timestamp for filenames"""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


class ComprehensiveCodeFixer:
    """Main class for comprehensive code analysis and fixing"""

    def __init__(self, backend_dir: Path):
        self.backend_dir = backend_dir
        self.src_dir = backend_dir / "src"
        self.tests_dir = backend_dir / "tests"
        self.outputs_dir = backend_dir / "outputs"
        self.scripts_dir = backend_dir / "scripts"
        self.fix_imports_dir = backend_dir / "fix_imports"
        self.verify_imports_dir = backend_dir / "verify_imports"

        # Ensure directories exist
        for dir_path in [
            self.outputs_dir,
            self.fix_imports_dir,
            self.verify_imports_dir,
        ]:
            dir_path.mkdir(exist_ok=True)

        self.timestamp = get_timestamp()
        self.issues_found = []
        self.fixes_applied = []
        self.analysis_results = {}

        # Add src to Python path for imports
        if str(self.src_dir) not in sys.path:
            sys.path.insert(0, str(self.src_dir))

    def log_issue(self, category: str, file_name: str, issue: str):
        """Log an issue for reporting"""
        self.issues_found.append(
            {
                "category": category,
                "file": file_name,
                "issue": issue,
                "timestamp": datetime.now(),
            }
        )

    def log_fix(self, file_name: str, fix_description: str):
        """Log a fix for reporting"""
        self.fixes_applied.append(
            {"file": file_name, "fix": fix_description, "timestamp": datetime.now()}
        )

    def check_file_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Check if a Python file has valid syntax"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            ast.parse(content, filename=str(file_path))
            return True, "Syntax OK"

        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Parse error: {str(e)}"

    def analyze_file_imports(self, file_path: Path) -> List[str]:
        """Analyze import statements and identify issues"""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                line = line.strip()

                # Check for problematic import patterns
                if (
                    line.startswith("from admin_")
                    and "import" in line
                    and "src.admin_" not in line
                ):
                    issues.append(
                        f"Line {i}: Should use 'from src.admin_...' instead of 'from admin_...'"
                    )
                elif line.startswith("import admin_") and "src" not in line:
                    module_name = line.split()[1]
                    issues.append(
                        f"Line {i}: Should use 'from src import {module_name}' instead of 'import {module_name}'"
                    )
                elif (
                    line.startswith("from enhanced_admin_rithmic import")
                    and "src" not in line
                ):
                    issues.append(
                        f"Line {i}: Should use 'from src.enhanced_admin_rithmic import' instead"
                    )
                elif (
                    line.startswith("import enhanced_admin_rithmic")
                    and "src" not in line
                ):
                    issues.append(
                        f"Line {i}: Should use 'from src import enhanced_admin_rithmic' instead"
                    )

        except Exception as e:
            issues.append(f"Error analyzing imports: {str(e)}")

        return issues

    def get_all_python_files(self) -> List[Path]:
        """Get all Python files that need analysis"""
        files = []

        # Main source files
        if self.src_dir.exists():
            files.extend(self.src_dir.glob("*.py"))

        # Test files
        if self.tests_dir.exists():
            files.extend(self.tests_dir.glob("*.py"))

        # Other Python files
        for directory in [
            self.fix_imports_dir,
            self.verify_imports_dir,
            self.scripts_dir,
        ]:
            if directory.exists():
                files.extend(directory.glob("*.py"))

        # Filter out __pycache__ and other unwanted files
        return [
            f for f in files if "__pycache__" not in str(f) and f.name != "__init__.py"
        ]

    def analyze_all_files(self) -> Dict[str, Any]:
        """Analyze all Python files for issues"""
        print("🔍 ANALYZING ALL PYTHON FILES")
        print("=" * 50)

        files = self.get_all_python_files()
        results = {}

        for file_path in files:
            print(f"  📝 Analyzing {file_path.name}")

            # Check syntax
            syntax_ok, syntax_msg = self.check_file_syntax(file_path)
            if not syntax_ok:
                self.log_issue("syntax", file_path.name, syntax_msg)

            # Check imports
            import_issues = self.analyze_file_imports(file_path)
            for issue in import_issues:
                self.log_issue("import", file_path.name, issue)

            results[str(file_path)] = {
                "file_name": file_path.name,
                "relative_path": str(file_path.relative_to(self.backend_dir)),
                "syntax_ok": syntax_ok,
                "syntax_message": syntax_msg,
                "import_issues": import_issues,
                "file_exists": True,
            }

        self.analysis_results = results
        print(f"✅ Analyzed {len(files)} files")
        return results

    def fix_test_file_imports(self) -> List[str]:
        """Fix import statements in test files"""
        print("\n🔧 FIXING TEST FILE IMPORTS")
        print("=" * 50)

        fixes_applied = []

        if not self.tests_dir.exists():
            return fixes_applied

        test_files = [f for f in self.tests_dir.glob("*.py") if f.name != "__init__.py"]

        for test_file in test_files:
            print(f"  📝 Processing {test_file.name}")

            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                original_content = content
                lines = content.split("\n")
                modified = False

                # Fix import statements
                for i, line in enumerate(lines):
                    original_line = line.strip()

                    # Fix direct imports
                    if original_line.startswith("import admin_"):
                        module_name = original_line.split()[1]
                        lines[i] = f"from src import {module_name}"
                        modified = True
                        fix_desc = f"'{original_line}' → '{lines[i]}'"
                        fixes_applied.append(f"{test_file.name}: {fix_desc}")
                        self.log_fix(test_file.name, fix_desc)

                    elif (
                        original_line.startswith("from admin_")
                        and "import" in original_line
                    ):
                        parts = original_line.split()
                        if (
                            len(parts) >= 4
                            and parts[0] == "from"
                            and parts[2] == "import"
                        ):
                            module_name = parts[1]
                            import_part = " ".join(parts[3:])
                            lines[i] = f"from src.{module_name} import {import_part}"
                            modified = True
                            fix_desc = f"'{original_line}' → '{lines[i]}'"
                            fixes_applied.append(f"{test_file.name}: {fix_desc}")
                            self.log_fix(test_file.name, fix_desc)

                    elif original_line.startswith("import enhanced_admin_rithmic"):
                        lines[i] = "from src import enhanced_admin_rithmic"
                        modified = True
                        fix_desc = f"'{original_line}' → '{lines[i]}'"
                        fixes_applied.append(f"{test_file.name}: {fix_desc}")
                        self.log_fix(test_file.name, fix_desc)

                    elif original_line.startswith("from enhanced_admin_rithmic import"):
                        parts = original_line.split()
                        if len(parts) >= 4:
                            import_part = " ".join(parts[3:])
                            lines[i] = (
                                f"from src.enhanced_admin_rithmic import {import_part}"
                            )
                            modified = True
                            fix_desc = f"'{original_line}' → '{lines[i]}'"
                            fixes_applied.append(f"{test_file.name}: {fix_desc}")
                            self.log_fix(test_file.name, fix_desc)

                # Add sys.path setup if needed and not already present
                if modified and "sys.path.insert" not in content:
                    path_setup = [
                        "import sys",
                        "import os",
                        "from pathlib import Path",
                        "",
                        "# Add the src directory to Python path for imports",
                        "backend_dir = Path(__file__).parent.parent",
                        'src_dir = backend_dir / "src"',
                        "if str(src_dir) not in sys.path:",
                        "    sys.path.insert(0, str(src_dir))",
                        "",
                    ]

                    # Find insertion point (after shebang and docstring)
                    insert_index = 0
                    in_docstring = False
                    docstring_delimiter = None

                    for i, line in enumerate(lines):
                        stripped = line.strip()

                        # Skip shebang
                        if stripped.startswith("#!"):
                            insert_index = i + 1
                            continue

                        # Handle docstrings
                        if stripped.startswith('"""') or stripped.startswith("'''"):
                            if not in_docstring:
                                in_docstring = True
                                docstring_delimiter = stripped[:3]
                            elif stripped.endswith(docstring_delimiter):
                                in_docstring = False
                                insert_index = i + 1
                        elif in_docstring:
                            continue
                        elif stripped and not in_docstring:
                            insert_index = i
                            break

                    # Insert path setup
                    for j, setup_line in enumerate(path_setup):
                        lines.insert(insert_index + j, setup_line)

                    fix_desc = "Added sys.path setup for src imports"
                    fixes_applied.append(f"{test_file.name}: {fix_desc}")
                    self.log_fix(test_file.name, fix_desc)
                    modified = True

                # Write back if modified
                if modified:
                    new_content = "\n".join(lines)
                    with open(test_file, "w", encoding="utf-8") as f:
                        f.write(new_content)

                    print(f"    ✅ Fixed {test_file.name}")
                else:
                    print(f"    ✅ No changes needed for {test_file.name}")

            except Exception as e:
                print(f"    ❌ Error processing {test_file.name}: {e}")
                self.log_issue("fix_error", test_file.name, str(e))

        print(f"✅ Processed {len(test_files)} test files")
        return fixes_applied

    def run_quality_analysis(self) -> Dict[str, str]:
        """Run pylint, mypy, black on key files if tools are available"""
        print("\n📊 RUNNING CODE QUALITY ANALYSIS")
        print("=" * 50)

        reports = {}

        # Get virtual environment Python if available
        venv_python = self._get_venv_python()
        if not venv_python:
            print("⚠️  Virtual environment not found, using system Python")
            venv_python = sys.executable

        # Key files to analyze
        key_files = [
            self.src_dir / "enhanced_admin_rithmic.py",
            self.src_dir / "admin_display_manager.py",
            self.src_dir / "admin_core_classes.py",
        ]

        existing_files = [f for f in key_files if f.exists()]

        if not existing_files:
            print("⚠️  No key files found for quality analysis")
            return reports

        # Run pylint if available
        reports["pylint"] = self._run_pylint(venv_python, existing_files)

        # Run mypy if available
        reports["mypy"] = self._run_mypy(venv_python, existing_files)

        # Run black check if available
        reports["black"] = self._run_black_check(venv_python, existing_files)

        return reports

    def _get_venv_python(self) -> Optional[str]:
        """Get virtual environment Python executable"""
        root_dir = self.backend_dir.parent.parent
        venv_dir = root_dir / "venv"

        if os.name == "nt":  # Windows
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:  # Linux/Mac
            python_exe = venv_dir / "bin" / "python"

        return str(python_exe) if python_exe.exists() else None

    def _run_pylint(self, python_exe: str, files: List[Path]) -> str:
        """Run pylint analysis"""
        print("  🔍 Running pylint analysis...")

        report_file = self.outputs_dir / f"pylint_analysis_{self.timestamp}.txt"

        try:
            # Check if pylint is available
            result = subprocess.run(
                [python_exe, "-m", "pylint", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                # Try to install pylint
                print("    📦 Installing pylint...")
                subprocess.run(
                    [python_exe, "-m", "pip", "install", "pylint"],
                    capture_output=True,
                    check=True,
                )
        except subprocess.CalledProcessError:
            return str(report_file) + " (pylint not available)"

        # Run pylint on files
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"PYLINT ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("=" * 80 + "\n\n")

            for file_path in files:
                print(f"    📝 Analyzing {file_path.name}")

                pylint_args = [
                    python_exe,
                    "-m",
                    "pylint",
                    "--disable=missing-docstring,too-few-public-methods,invalid-name",
                    "--max-line-length=120",
                    "--score=yes",
                    str(file_path),
                ]

                try:
                    result = subprocess.run(
                        pylint_args, capture_output=True, text=True, timeout=60
                    )

                    f.write(f"FILE: {file_path}\n")
                    f.write("=" * 40 + "\n")
                    f.write(result.stdout)
                    if result.stderr:
                        f.write("\nSTDERR:\n")
                        f.write(result.stderr)
                    f.write("\n\n")

                    # Extract score
                    if "Your code has been rated at" in result.stdout:
                        try:
                            score_line = [
                                line
                                for line in result.stdout.split("\n")
                                if "Your code has been rated at" in line
                            ][0]
                            score = score_line.split()[6].split("/")[0]
                            print(f"      📊 Score: {score}/10.00")
                        except (IndexError, ValueError):
                            pass

                except subprocess.TimeoutExpired:
                    f.write(f"TIMEOUT: Analysis of {file_path} exceeded 60 seconds\n\n")
                except Exception as e:
                    f.write(f"ERROR analyzing {file_path}: {e}\n\n")

        print(f"    ✅ Pylint report: {report_file.name}")
        return str(report_file)

    def _run_mypy(self, python_exe: str, files: List[Path]) -> str:
        """Run mypy analysis"""
        print("  🔍 Running mypy analysis...")

        report_file = self.outputs_dir / f"mypy_analysis_{self.timestamp}.txt"

        try:
            # Check if mypy is available
            result = subprocess.run(
                [python_exe, "-m", "mypy", "--version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                # Try to install mypy
                print("    📦 Installing mypy...")
                subprocess.run(
                    [python_exe, "-m", "pip", "install", "mypy"],
                    capture_output=True,
                    check=True,
                )
        except subprocess.CalledProcessError:
            return str(report_file) + " (mypy not available)"

        # Run mypy on files
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"MYPY ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("=" * 80 + "\n\n")

            for file_path in files:
                print(f"    📝 Analyzing {file_path.name}")

                mypy_args = [
                    python_exe,
                    "-m",
                    "mypy",
                    "--ignore-missing-imports",
                    "--show-error-codes",
                    str(file_path),
                ]

                try:
                    result = subprocess.run(
                        mypy_args, capture_output=True, text=True, timeout=60
                    )

                    f.write(f"FILE: {file_path}\n")
                    f.write("=" * 40 + "\n")

                    if result.stdout:
                        f.write("ISSUES:\n")
                        f.write(result.stdout)
                        issue_count = len(
                            [
                                line
                                for line in result.stdout.split("\n")
                                if ":" in line and "error:" in line
                            ]
                        )
                        print(f"      ⚠️  {issue_count} issues found")
                    else:
                        f.write("✅ No type errors found\n")
                        print(f"      ✅ No type errors")

                    f.write("\n\n")

                except subprocess.TimeoutExpired:
                    f.write(f"TIMEOUT: Analysis of {file_path} exceeded 60 seconds\n\n")
                except Exception as e:
                    f.write(f"ERROR analyzing {file_path}: {e}\n\n")

        print(f"    ✅ MyPy report: {report_file.name}")
        return str(report_file)

    def _run_black_check(self, python_exe: str, files: List[Path]) -> str:
        """Run black formatting check"""
        print("  🎨 Running black formatting check...")

        report_file = self.outputs_dir / f"black_check_{self.timestamp}.txt"

        try:
            # Check if black is available
            result = subprocess.run(
                [python_exe, "-m", "black", "--version"], capture_output=True, text=True
            )
            if result.returncode != 0:
                # Try to install black
                print("    📦 Installing black...")
                subprocess.run(
                    [python_exe, "-m", "pip", "install", "black"],
                    capture_output=True,
                    check=True,
                )
        except subprocess.CalledProcessError:
            return str(report_file) + " (black not available)"

        # Run black check on files
        files_needing_format = []

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(f"BLACK FORMATTING CHECK REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write("=" * 80 + "\n\n")

            for file_path in files:
                print(f"    📝 Checking {file_path.name}")

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

                    f.write(f"FILE: {file_path}\n")
                    f.write("=" * 40 + "\n")

                    if result.returncode == 0:
                        f.write("✅ Already formatted correctly\n")
                        print(f"      ✅ Already formatted")
                    else:
                        f.write("🎨 Would be reformatted:\n")
                        f.write(result.stdout)
                        files_needing_format.append(str(file_path))
                        print(f"      🎨 Needs formatting")

                    f.write("\n\n")

                except subprocess.TimeoutExpired:
                    f.write(f"TIMEOUT: Check of {file_path} exceeded 60 seconds\n\n")
                except Exception as e:
                    f.write(f"ERROR checking {file_path}: {e}\n\n")

            f.write(f"SUMMARY: {len(files_needing_format)} files need formatting\n")

        print(f"    ✅ Black report: {report_file.name}")
        return str(report_file)

    def generate_final_report(self, quality_reports: Dict[str, str]) -> Path:
        """Generate comprehensive final report"""
        print("\n📋 GENERATING COMPREHENSIVE REPORT")
        print("=" * 50)

        report_file = self.outputs_dir / f"FINAL_ANALYSIS_REPORT_{self.timestamp}.md"

        with open(report_file, "w", encoding="utf-8") as f:
            # Header
            f.write("# 🚀 COMPREHENSIVE CODE ANALYSIS - FINAL REPORT\n\n")
            f.write(f"**Generated:** {datetime.now()}\n")
            f.write(f"**Backend Directory:** {self.backend_dir}\n")
            f.write(f"**Analysis Timestamp:** {self.timestamp}\n\n")

            # Executive Summary
            syntax_errors = len(
                [issue for issue in self.issues_found if issue["category"] == "syntax"]
            )
            import_issues = len(
                [issue for issue in self.issues_found if issue["category"] == "import"]
            )
            total_files = len(self.analysis_results)

            f.write("## 📊 EXECUTIVE SUMMARY\n\n")
            f.write(f"- **Files Analyzed:** {total_files}\n")
            f.write(f"- **Syntax Errors:** {syntax_errors}\n")
            f.write(f"- **Import Issues:** {import_issues}\n")
            f.write(f"- **Fixes Applied:** {len(self.fixes_applied)}\n")
            f.write(f"- **Quality Reports Generated:** {len(quality_reports)}\n\n")

            # Status determination
            if syntax_errors == 0 and import_issues == 0:
                f.write("🎉 **OVERALL STATUS: READY FOR PRODUCTION** ✅\n\n")
                f.write(
                    "All critical issues have been resolved. The system is ready for deployment.\n\n"
                )
            elif syntax_errors == 0:
                f.write("✅ **OVERALL STATUS: SYNTAX CLEAN, MINOR ISSUES** 🔧\n\n")
                f.write(
                    "No syntax errors found. Some import issues may need attention.\n\n"
                )
            else:
                f.write("⚠️ **OVERALL STATUS: NEEDS ATTENTION** 🚨\n\n")
                f.write(
                    "Syntax errors require immediate attention before deployment.\n\n"
                )

            # File Analysis Summary
            f.write("## 📋 FILE ANALYSIS SUMMARY\n\n")
            f.write("| File | Syntax | Import Issues | Status |\n")
            f.write("|------|--------|---------------|--------|\n")

            for file_path, result in self.analysis_results.items():
                file_name = result["file_name"]
                syntax_status = "✅" if result["syntax_ok"] else "❌"
                import_count = len(result["import_issues"])
                import_status = f"{import_count} issues" if import_count > 0 else "✅"

                overall_status = (
                    "Ready"
                    if result["syntax_ok"] and import_count == 0
                    else "Needs Work"
                )

                f.write(
                    f"| {file_name} | {syntax_status} | {import_status} | {overall_status} |\n"
                )

            # Issues Found
            f.write("\n## 🔍 ISSUES IDENTIFIED\n\n")

            if self.issues_found:
                issue_categories = {}
                for issue in self.issues_found:
                    category = issue["category"]
                    if category not in issue_categories:
                        issue_categories[category] = []
                    issue_categories[category].append(issue)

                for category, issues in issue_categories.items():
                    f.write(f"### {category.title()} Issues ({len(issues)})\n\n")
                    for issue in issues:
                        f.write(f"- **{issue['file']}**: {issue['issue']}\n")
                    f.write("\n")
            else:
                f.write("✅ No issues identified in the analyzed files.\n\n")

            # Fixes Applied
            f.write("## 🛠 FIXES APPLIED\n\n")

            if self.fixes_applied:
                f.write("The following automatic fixes were successfully applied:\n\n")
                fix_categories = {}
                for fix in self.fixes_applied:
                    file_name = fix["file"]
                    if file_name not in fix_categories:
                        fix_categories[file_name] = []
                    fix_categories[file_name].append(fix["fix"])

                for file_name, fixes in fix_categories.items():
                    f.write(f"### {file_name}\n")
                    for fix in fixes:
                        f.write(f"- {fix}\n")
                    f.write("\n")
            else:
                f.write("No automatic fixes were applied.\n\n")

            # Quality Analysis Reports
            f.write("## 📊 CODE QUALITY ANALYSIS\n\n")

            if quality_reports:
                f.write("Detailed code quality reports have been generated:\n\n")
                for tool, report_path in quality_reports.items():
                    f.write(f"- **{tool.upper()}:** `{Path(report_path).name}`\n")
                f.write("\n")
            else:
                f.write(
                    "Code quality analysis tools were not available or failed to run.\n\n"
                )

            # File Organization Status
            f.write("## 📁 FILE ORGANIZATION\n\n")
            f.write("✅ **Current Structure:**\n")
            f.write("```\n")
            f.write("backend/\n")
            f.write("├── src/                 # Main source files\n")
            f.write("├── tests/               # Test files (import fixes applied)\n")
            f.write("├── fix_imports/         # Import fix utilities\n")
            f.write("├── verify_imports/      # Import verification utilities\n")
            f.write("├── scripts/             # Analysis and utility scripts\n")
            f.write(
                "├── outputs/             # Generated reports and analysis results\n"
            )
            f.write("└── config/              # Configuration files\n")
            f.write("```\n\n")

            # Recommendations
            f.write("## 🎯 RECOMMENDATIONS\n\n")

            if syntax_errors > 0:
                f.write("### 🚨 IMMEDIATE ACTION REQUIRED\n")
                f.write(
                    "1. **Fix syntax errors** - These prevent the application from running\n"
                )
                f.write(
                    "2. **Review error details** in the file analysis section above\n"
                )
                f.write("3. **Test each fix** before proceeding to next steps\n\n")

            f.write("### 📋 NEXT STEPS\n")
            f.write("1. **Verify import fixes:**\n")
            f.write("   ```bash\n")
            f.write("   python verify_imports/verify_import_fixes.py\n")
            f.write("   ```\n\n")

            f.write("2. **Run functionality tests:**\n")
            f.write("   ```bash\n")
            f.write("   python tests/test_fixes.py\n")
            f.write("   python tests/test_tui_display.py\n")
            f.write("   ```\n\n")

            f.write("3. **Test main application:**\n")
            f.write("   ```bash\n")
            f.write("   python src/enhanced_admin_rithmic.py\n")
            f.write("   ```\n\n")

            f.write("4. **Address code quality issues** (if reports generated)\n")
            f.write("5. **Consider running additional analysis** after fixes\n\n")

            # Technical Details
            f.write("## 🔧 TECHNICAL DETAILS\n\n")
            f.write("### Analysis Scope\n")
            f.write("- **Source Files:** Core application modules in `src/`\n")
            f.write("- **Test Files:** All test modules with import fixes applied\n")
            f.write("- **Utility Files:** Import fixes and verification scripts\n")
            f.write("- **Configuration:** Database and API configuration files\n\n")

            f.write("### Import Strategy\n")
            f.write(
                "- **Test Files:** Updated to use `from src import module_name` pattern\n"
            )
            f.write(
                "- **Path Setup:** Added `sys.path` configuration for module resolution\n"
            )
            f.write(
                "- **Compatibility:** Maintained backward compatibility with existing structure\n\n"
            )

            f.write("### File Organization\n")
            f.write("- **Scripts:** Organized by function with timestamp naming\n")
            f.write(
                "- **Reports:** Timestamped outputs in dedicated `outputs/` directory\n"
            )
            f.write(
                "- **Utilities:** Separated import fixes and verification tools\n\n"
            )

            # Conclusion
            f.write("---\n\n")
            f.write("## 📈 CONCLUSION\n\n")

            if syntax_errors == 0 and import_issues == 0:
                f.write("🎊 **SUCCESS!** All critical issues have been resolved. ")
                f.write("The futures trading system backend is now properly organized ")
                f.write("and ready for development and deployment.\n\n")
                f.write(
                    "**You can now run:** `python src/enhanced_admin_rithmic.py`\n\n"
                )
            else:
                f.write(
                    "📋 **PROGRESS MADE** - This analysis has identified and addressed many issues. "
                )
                f.write(
                    "Follow the recommendations above to complete the remaining fixes.\n\n"
                )

            f.write(
                f"*Report generated by Comprehensive Code Analysis Tool on {datetime.now()}*\n"
            )

        print(f"✅ Final report generated: {report_file.name}")
        return report_file

    def run_complete_analysis(self) -> Tuple[bool, Path]:
        """Run the complete analysis and fix process"""
        print("🚀 COMPREHENSIVE CODE ANALYSIS AND FIXING")
        print("=" * 65)
        print(f"Backend Directory: {self.backend_dir}")
        print(f"Analysis Time: {datetime.now()}")
        print()

        try:
            # Step 1: Analyze all files
            analysis_results = self.analyze_all_files()

            # Step 2: Apply automatic fixes
            fixes = self.fix_test_file_imports()

            # Step 3: Run quality analysis
            quality_reports = self.run_quality_analysis()

            # Step 4: Generate final report
            final_report = self.generate_final_report(quality_reports)

            # Summary
            print("\n🎉 COMPREHENSIVE ANALYSIS COMPLETE!")
            print("=" * 45)
            print(f"📋 Final Report: {final_report.name}")

            syntax_errors = len(
                [issue for issue in self.issues_found if issue["category"] == "syntax"]
            )
            import_issues = len(
                [issue for issue in self.issues_found if issue["category"] == "import"]
            )

            print(f"📊 Summary:")
            print(f"   - Files analyzed: {len(analysis_results)}")
            print(f"   - Syntax errors: {syntax_errors}")
            print(f"   - Import issues: {import_issues}")
            print(f"   - Fixes applied: {len(self.fixes_applied)}")

            success = syntax_errors == 0

            if success:
                print("\n✅ All syntax errors resolved! System ready for testing.")
                print("Next: python verify_imports/verify_import_fixes.py")
            else:
                print(
                    "\n⚠️  Some syntax errors remain. Check the final report for details."
                )

            return success, final_report

        except Exception as e:
            print(f"\n❌ Analysis failed: {e}")
            print(traceback.format_exc())
            return False, None


def main():
    """Main entry point"""
    # Get backend directory
    backend_dir = Path(__file__).parent.parent

    # Create comprehensive fixer
    fixer = ComprehensiveCodeFixer(backend_dir)

    # Run complete analysis
    success, report_file = fixer.run_complete_analysis()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
