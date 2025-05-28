#!/usr/bin/env python3
"""
Simple syntax and import checker for Python files
Identifies immediate issues that need fixing
"""

import os
import sys
import ast
import traceback
from pathlib import Path
from datetime import datetime


def check_file_syntax(file_path):
    """Check syntax of a Python file"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Try to parse the AST
        ast.parse(content, filename=str(file_path))
        return True, "Syntax OK"

    except SyntaxError as e:
        return False, f"Syntax Error: {e.msg} at line {e.lineno}"
    except Exception as e:
        return False, f"Parse Error: {str(e)}"


def check_imports(file_path):
    """Check if imports can be resolved"""
    import_issues = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module_name = alias.name
                    try:
                        __import__(module_name)
                    except ImportError:
                        import_issues.append(f"Cannot import: {module_name}")

            elif isinstance(node, ast.ImportFrom):
                module_name = node.module
                if module_name:
                    try:
                        __import__(module_name)
                    except ImportError:
                        import_issues.append(f"Cannot import from: {module_name}")

    except Exception as e:
        import_issues.append(f"Error analyzing imports: {str(e)}")

    return import_issues


def analyze_files():
    """Analyze all key Python files"""
    backend_dir = Path(__file__).parent.parent

    # Add src to path for imports
    src_dir = backend_dir / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    files_to_check = [
        src_dir / "enhanced_admin_rithmic.py",
        src_dir / "admin_display_manager.py",
        src_dir / "admin_core_classes.py",
        src_dir / "admin_database.py",
        src_dir / "admin_rithmic_connection.py",
        src_dir / "admin_rithmic_historical.py",
        src_dir / "admin_rithmic_operations.py",
        src_dir / "admin_rithmic_symbols.py",
        backend_dir / "tests" / "test_fixes.py",
        backend_dir / "fix_imports" / "fix_imports.py",
        backend_dir / "verify_imports" / "verify_import_fixes.py",
    ]

    results = {}

    for file_path in files_to_check:
        if file_path.exists():
            print(f"Checking {file_path.name}...")

            # Check syntax
            syntax_ok, syntax_msg = check_file_syntax(file_path)

            # Check imports (only if syntax is OK)
            import_issues = []
            if syntax_ok:
                import_issues = check_imports(file_path)

            results[str(file_path)] = {
                "syntax_ok": syntax_ok,
                "syntax_message": syntax_msg,
                "import_issues": import_issues,
                "file_exists": True,
            }
        else:
            results[str(file_path)] = {
                "syntax_ok": False,
                "syntax_message": "File not found",
                "import_issues": [],
                "file_exists": False,
            }

    return results


def generate_report(results):
    """Generate a detailed report"""
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    backend_dir = Path(__file__).parent.parent
    outputs_dir = backend_dir / "outputs"
    outputs_dir.mkdir(exist_ok=True)

    report_file = outputs_dir / f"manual_analysis_report_{timestamp}.md"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# Manual Code Analysis Report\n\n")
        f.write(f"**Generated:** {datetime.now()}\n\n")

        f.write("## 📊 File Analysis Summary\n\n")
        f.write("| File | Syntax | Import Issues | Status |\n")
        f.write("|------|--------|---------------|--------|\n")

        syntax_errors = 0
        import_errors = 0

        for file_path, result in results.items():
            file_name = Path(file_path).name

            if not result["file_exists"]:
                f.write(f"| {file_name} | ❌ | N/A | File Missing |\n")
                continue

            syntax_status = "✅" if result["syntax_ok"] else "❌"
            if not result["syntax_ok"]:
                syntax_errors += 1

            import_count = len(result["import_issues"])
            import_status = f"{import_count} issues" if import_count > 0 else "✅"
            if import_count > 0:
                import_errors += 1

            status = "OK" if result["syntax_ok"] and import_count == 0 else "Issues"

            f.write(f"| {file_name} | {syntax_status} | {import_status} | {status} |\n")

        f.write(
            f"\n**Summary:** {syntax_errors} syntax errors, {import_errors} files with import issues\n\n"
        )

        f.write("## 🔍 Detailed Issues\n\n")

        for file_path, result in results.items():
            file_name = Path(file_path).name

            if not result["file_exists"]:
                f.write(f"### ❌ {file_name}\n")
                f.write("**Status:** File not found\n\n")
                continue

            if not result["syntax_ok"] or result["import_issues"]:
                f.write(f"### 🔧 {file_name}\n")

                if not result["syntax_ok"]:
                    f.write(f"**Syntax Error:** {result['syntax_message']}\n\n")

                if result["import_issues"]:
                    f.write("**Import Issues:**\n")
                    for issue in result["import_issues"]:
                        f.write(f"- {issue}\n")
                    f.write("\n")
            else:
                f.write(f"### ✅ {file_name}\n")
                f.write("**Status:** No issues found\n\n")

        f.write("## 🎯 Priority Fixes Needed\n\n")
        f.write("### High Priority\n")
        f.write("1. **Fix syntax errors** - These prevent files from running at all\n")
        f.write("2. **Resolve import issues** - Update import paths for reorganized files\n")
        f.write("3. **Missing files** - Create or restore missing files\n\n")

        f.write("### Medium Priority\n")
        f.write("1. **Code quality improvements** - Run pylint after fixing syntax\n")
        f.write("2. **Type annotations** - Add proper type hints\n")
        f.write("3. **Code formatting** - Apply black formatting\n\n")

        f.write("## 🛠 Recommended Fix Actions\n\n")
        f.write("1. **Run import fixes:**\n")
        f.write("   ```bash\n")
        f.write("   python fix_imports/fix_imports.py\n")
        f.write("   ```\n\n")

        f.write("2. **Verify fixes:**\n")
        f.write("   ```bash\n")
        f.write("   python verify_imports/verify_import_fixes.py\n")
        f.write("   ```\n\n")

        f.write("3. **Test functionality:**\n")
        f.write("   ```bash\n")
        f.write("   python tests/test_fixes.py\n")
        f.write("   ```\n\n")

        f.write("4. **Run main application:**\n")
        f.write("   ```bash\n")
        f.write("   python src/enhanced_admin_rithmic.py\n")
        f.write("   ```\n\n")

        f.write("## 📁 File Organization Status\n\n")
        f.write("✅ **Completed:**\n")
        f.write("- Moved `fix_imports.py` to `fix_imports/` folder\n")
        f.write("- Moved `verify_import_fixes.py` to `verify_imports/` folder\n")
        f.write("- Created timestamped analysis scripts in `scripts/` folder\n\n")

        f.write("⏳ **Still Needed:**\n")
        f.write("- Fix syntax errors in source files\n")
        f.write("- Update import statements for new file locations\n")
        f.write("- Run comprehensive pylint/mypy/black analysis\n")
        f.write("- Test all functionality after fixes\n\n")

    return report_file


def main():
    """Main analysis function"""
    print("🔍 MANUAL CODE ANALYSIS")
    print("=" * 40)
    print("Checking syntax and imports in key Python files...")

    # Run analysis
    results = analyze_files()

    # Generate report
    report_file = generate_report(results)

    print(f"\n📋 Analysis complete! Report saved: {report_file}")

    # Show quick summary
    issues_found = sum(1 for r in results.values() if not r["syntax_ok"] or r["import_issues"])
    total_files = len(results)

    print(f"📊 Quick Summary: {issues_found}/{total_files} files have issues")

    if issues_found == 0:
        print("🎉 No immediate issues found! Ready for comprehensive analysis.")
    else:
        print("⚠️  Issues found. Please review the report and fix syntax errors first.")

    return 0 if issues_found == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
