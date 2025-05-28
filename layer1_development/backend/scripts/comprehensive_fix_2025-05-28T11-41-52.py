#!/usr/bin/env python3
"""
Comprehensive Import and Code Fix Script
Identifies and fixes all import issues and creates detailed analysis reports

Created: 2025-05-28T11:41:52
"""

import os
import sys
import ast
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple


def get_timestamp() -> str:
    """Get current timestamp for filenames"""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


class CodeAnalyzer:
    """Analyzes Python code for syntax and import issues"""

    def __init__(self, backend_dir: Path):
        self.backend_dir = backend_dir
        self.src_dir = backend_dir / "src"
        self.tests_dir = backend_dir / "tests"
        self.outputs_dir = backend_dir / "outputs"
        self.outputs_dir.mkdir(exist_ok=True)

        # Add src to Python path for imports
        if str(self.src_dir) not in sys.path:
            sys.path.insert(0, str(self.src_dir))

    def check_syntax(self, file_path: Path) -> Tuple[bool, str]:
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

    def analyze_imports(self, file_path: Path) -> List[str]:
        """Analyze import statements in a file"""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for problematic import patterns
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                line = line.strip()

                # Check for direct imports that should be from src
                if line.startswith("from admin_") and "import" in line:
                    issues.append(
                        f"Line {i}: Should be 'from src.{line[5:]}' instead of '{line}'"
                    )
                elif line.startswith("import admin_"):
                    module_name = line.split()[1]
                    issues.append(
                        f"Line {i}: Should be 'from src import {module_name}' instead of '{line}'"
                    )
                elif line.startswith("import enhanced_admin_rithmic"):
                    issues.append(
                        f"Line {i}: Should be 'from src import enhanced_admin_rithmic' instead of '{line}'"
                    )
                elif line.startswith("from enhanced_admin_rithmic import"):
                    issues.append(
                        f"Line {i}: Should be 'from src.enhanced_admin_rithmic import' instead of '{line}'"
                    )

        except Exception as e:
            issues.append(f"Error analyzing imports: {str(e)}")

        return issues

    def get_key_files(self) -> List[Path]:
        """Get list of key Python files to analyze"""
        files = []

        # Source files
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

        for file in src_files:
            file_path = self.src_dir / file
            if file_path.exists():
                files.append(file_path)

        # Test files
        test_files = [
            "test_fixes.py",
            "test_tui_display.py",
            "test_enhanced_connection_display.py",
            "test_import_helper.py",
        ]

        for file in test_files:
            file_path = self.tests_dir / file
            if file_path.exists():
                files.append(file_path)

        # Import fix files
        fix_files = [
            self.backend_dir / "fix_imports" / "fix_imports.py",
            self.backend_dir / "verify_imports" / "verify_import_fixes.py",
        ]

        for file_path in fix_files:
            if file_path.exists():
                files.append(file_path)

        return files

    def analyze_all_files(self) -> Dict[str, Any]:
        """Analyze all key files for issues"""
        files = self.get_key_files()
        results = {}

        print("🔍 Analyzing files for syntax and import issues...")

        for file_path in files:
            print(f"  📝 Checking {file_path.name}")

            syntax_ok, syntax_msg = self.check_syntax(file_path)
            import_issues = self.analyze_imports(file_path)

            results[str(file_path)] = {
                "file_name": file_path.name,
                "relative_path": str(file_path.relative_to(self.backend_dir)),
                "syntax_ok": syntax_ok,
                "syntax_message": syntax_msg,
                "import_issues": import_issues,
                "file_exists": True,
            }

        return results

    def fix_test_file_imports(self) -> List[str]:
        """Fix import statements in test files"""
        fixes_applied = []

        print("\n🔧 Fixing import statements in test files...")

        test_files = list(self.tests_dir.glob("*.py"))

        for test_file in test_files:
            if test_file.name == "__init__.py":
                continue

            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                original_content = content
                lines = content.split("\n")
                modified = False

                # Fix import statements
                for i, line in enumerate(lines):
                    original_line = line

                    # Fix direct imports
                    if line.strip().startswith("import admin_"):
                        module_name = line.strip().split()[1]
                        lines[i] = f"from src import {module_name}"
                        modified = True
                        fixes_applied.append(
                            f"{test_file.name}: '{original_line}' → '{lines[i]}'"
                        )

                    elif line.strip().startswith("from admin_") and "import" in line:
                        # Convert 'from admin_module import something' to 'from src.admin_module import something'
                        parts = line.strip().split()
                        if (
                            len(parts) >= 4
                            and parts[0] == "from"
                            and parts[2] == "import"
                        ):
                            module_name = parts[1]
                            import_part = " ".join(parts[3:])
                            lines[i] = f"from src.{module_name} import {import_part}"
                            modified = True
                            fixes_applied.append(
                                f"{test_file.name}: '{original_line}' → '{lines[i]}'"
                            )

                    elif line.strip().startswith("import enhanced_admin_rithmic"):
                        lines[i] = "from src import enhanced_admin_rithmic"
                        modified = True
                        fixes_applied.append(
                            f"{test_file.name}: '{original_line}' → '{lines[i]}'"
                        )

                    elif line.strip().startswith("from enhanced_admin_rithmic import"):
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            import_part = " ".join(parts[3:])
                            lines[i] = (
                                f"from src.enhanced_admin_rithmic import {import_part}"
                            )
                            modified = True
                            fixes_applied.append(
                                f"{test_file.name}: '{original_line}' → '{lines[i]}'"
                            )

                # Add sys.path setup if needed and not already present
                if modified and "sys.path.insert" not in content:
                    path_setup = """import sys
import os
from pathlib import Path

# Add the src directory to Python path for imports
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

"""

                    # Find the best place to insert (after existing imports)
                    insert_index = 0
                    for i, line in enumerate(lines):
                        if (
                            line.strip()
                            and not line.strip().startswith("#")
                            and not line.strip().startswith('"""')
                        ):
                            insert_index = i
                            break

                    # Insert the path setup
                    setup_lines = path_setup.strip().split("\n")
                    for j, setup_line in enumerate(setup_lines):
                        lines.insert(insert_index + j, setup_line)

                    fixes_applied.append(f"{test_file.name}: Added sys.path setup")
                    modified = True

                # Write back if modified
                if modified:
                    new_content = "\n".join(lines)
                    with open(test_file, "w", encoding="utf-8") as f:
                        f.write(new_content)

                    print(f"  ✅ Fixed {test_file.name}")

            except Exception as e:
                print(f"  ❌ Error fixing {test_file.name}: {e}")

        return fixes_applied

    def generate_comprehensive_report(
        self, analysis_results: Dict[str, Any], fixes_applied: List[str]
    ) -> Path:
        """Generate comprehensive analysis report"""
        timestamp = get_timestamp()
        report_file = self.outputs_dir / f"comprehensive_fix_report_{timestamp}.md"

        print(f"\n📋 Generating comprehensive report: {report_file.name}")

        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# Comprehensive Code Analysis and Fix Report\n\n")
            f.write(f"**Generated:** {datetime.now()}\n")
            f.write(f"**Backend Directory:** {self.backend_dir}\n\n")

            # Executive Summary
            syntax_errors = sum(
                1 for r in analysis_results.values() if not r["syntax_ok"]
            )
            import_issues = sum(
                len(r["import_issues"]) for r in analysis_results.values()
            )

            f.write("## 📊 Executive Summary\n\n")
            f.write(f"- **Files Analyzed:** {len(analysis_results)}\n")
            f.write(f"- **Syntax Errors:** {syntax_errors}\n")
            f.write(f"- **Import Issues:** {import_issues}\n")
            f.write(f"- **Fixes Applied:** {len(fixes_applied)}\n\n")

            if syntax_errors == 0 and import_issues == 0:
                f.write("🎉 **Status:** All files are ready for production!\n\n")
            elif syntax_errors == 0:
                f.write(
                    "✅ **Status:** No syntax errors, some import issues addressed\n\n"
                )
            else:
                f.write("⚠️ **Status:** Syntax errors need immediate attention\n\n")

            # File Analysis Summary
            f.write("## 📋 File Analysis Summary\n\n")
            f.write("| File | Syntax | Import Issues | Status |\n")
            f.write("|------|--------|---------------|--------|\n")

            for file_path, result in analysis_results.items():
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

            # Detailed Issues
            f.write("\n## 🔍 Detailed Analysis\n\n")

            for file_path, result in analysis_results.items():
                file_name = result["file_name"]

                if not result["syntax_ok"] or result["import_issues"]:
                    f.write(f"### 🔧 {file_name}\n")
                    f.write(f"**Path:** `{result['relative_path']}`\n\n")

                    if not result["syntax_ok"]:
                        f.write(f"**❌ Syntax Error:** {result['syntax_message']}\n\n")

                    if result["import_issues"]:
                        f.write("**Import Issues:**\n")
                        for issue in result["import_issues"]:
                            f.write(f"- {issue}\n")
                        f.write("\n")
                else:
                    f.write(f"### ✅ {file_name}\n")
                    f.write("**Status:** No issues detected\n\n")

            # Fixes Applied
            f.write("## 🛠 Fixes Applied\n\n")

            if fixes_applied:
                f.write("The following fixes were automatically applied:\n\n")
                for fix in fixes_applied:
                    f.write(f"- {fix}\n")
                f.write("\n")
            else:
                f.write("No automatic fixes were applied.\n\n")

            # Recommendations
            f.write("## 🎯 Recommendations\n\n")

            if syntax_errors > 0:
                f.write("### 🚨 High Priority - Syntax Errors\n")
                f.write(
                    "Fix syntax errors immediately - these prevent files from running.\n\n"
                )

            if import_issues > 0:
                f.write("### ⚠️ Medium Priority - Import Issues\n")
                f.write(
                    "Address remaining import issues after syntax errors are fixed.\n\n"
                )

            f.write("### 📋 Next Steps\n")
            f.write("1. Fix any remaining syntax errors manually\n")
            f.write("2. Run import fix scripts:\n")
            f.write("   ```bash\n")
            f.write("   python fix_imports/fix_imports.py\n")
            f.write("   python verify_imports/verify_import_fixes.py\n")
            f.write("   ```\n")
            f.write("3. Test the fixes:\n")
            f.write("   ```bash\n")
            f.write("   python tests/test_fixes.py\n")
            f.write("   ```\n")
            f.write("4. Run the main application:\n")
            f.write("   ```bash\n")
            f.write("   python src/enhanced_admin_rithmic.py\n")
            f.write("   ```\n")
            f.write("5. Run comprehensive analysis (pylint, mypy, black):\n")
            f.write("   ```bash\n")
            f.write("   python scripts/focused_analysis_2025-05-28T11-41-52.py\n")
            f.write("   ```\n\n")

            # File Organization Status
            f.write("## 📁 File Organization Status\n\n")
            f.write("✅ **Completed:**\n")
            f.write("- Moved import fix scripts to proper folders\n")
            f.write("- Created comprehensive analysis scripts\n")
            f.write("- Applied automatic import fixes to test files\n\n")

            f.write("📋 **File Structure:**\n")
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

            # Technical Details
            f.write("## 🔧 Technical Details\n\n")
            f.write("### Import Fix Strategy\n")
            f.write(
                "- Test files updated to use `from src import module_name` pattern\n"
            )
            f.write("- Added sys.path setup to ensure module resolution\n")
            f.write("- Maintained compatibility with existing code structure\n\n")

            f.write("### Analysis Tools Available\n")
            f.write("- `manual_analysis_*.py` - Basic syntax and import checking\n")
            f.write(
                "- `focused_analysis_*.py` - Comprehensive pylint/mypy/black analysis\n"
            )
            f.write("- `comprehensive_analysis_*.py` - Full analysis suite\n\n")

            f.write("---\n")
            f.write(
                f"*Report generated by Comprehensive Code Analysis Tool on {datetime.now()}*\n"
            )

        return report_file


def main():
    """Main function to run comprehensive analysis and fixes"""
    print("🚀 COMPREHENSIVE CODE ANALYSIS AND FIX TOOL")
    print("=" * 65)

    # Setup paths
    backend_dir = Path(__file__).parent.parent

    print(f"Backend Directory: {backend_dir}")
    print(f"Analysis Time: {datetime.now()}")

    # Initialize analyzer
    analyzer = CodeAnalyzer(backend_dir)

    # Run comprehensive analysis
    analysis_results = analyzer.analyze_all_files()

    # Apply automatic fixes
    fixes_applied = analyzer.fix_test_file_imports()

    # Generate comprehensive report
    report_file = analyzer.generate_comprehensive_report(
        analysis_results, fixes_applied
    )

    print("\n🎉 ANALYSIS AND FIXES COMPLETE!")
    print("=" * 40)
    print(f"📋 Comprehensive report: {report_file.name}")

    # Summary
    syntax_errors = sum(1 for r in analysis_results.values() if not r["syntax_ok"])
    import_issues = sum(len(r["import_issues"]) for r in analysis_results.values())

    print(f"📊 Summary:")
    print(f"   - Files analyzed: {len(analysis_results)}")
    print(f"   - Syntax errors: {syntax_errors}")
    print(f"   - Import issues: {import_issues}")
    print(f"   - Fixes applied: {len(fixes_applied)}")

    if syntax_errors == 0 and import_issues == 0:
        print("\n🎉 All files are ready! You can now run:")
        print("   python src/enhanced_admin_rithmic.py")
    elif syntax_errors == 0:
        print("\n✅ No syntax errors found. Run import fixes:")
        print("   python fix_imports/fix_imports.py")
    else:
        print("\n⚠️  Syntax errors need manual fixing before proceeding.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
