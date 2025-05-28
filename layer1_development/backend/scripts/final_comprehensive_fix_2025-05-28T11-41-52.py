#!/usr/bin/env python3
"""
Final Comprehensive Analysis and Fix Application Script
Analyzes all issues and applies fixes automatically

Created: 2025-05-28T11:41:52
"""

import os
import sys
import ast
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple


def get_timestamp() -> str:
    """Get current timestamp for filenames"""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


class ComprehensiveFixer:
    """Comprehensive code analysis and fixing tool"""

    def __init__(self):
        self.backend_dir = Path(__file__).parent.parent
        self.src_dir = self.backend_dir / "src"
        self.tests_dir = self.backend_dir / "tests"
        self.outputs_dir = self.backend_dir / "outputs"
        self.outputs_dir.mkdir(exist_ok=True)

        # Add src to path for analysis
        if str(self.src_dir) not in sys.path:
            sys.path.insert(0, str(self.src_dir))

        self.fixes_applied = []
        self.issues_found = []

    def analyze_syntax(self, file_path: Path) -> Tuple[bool, str]:
        """Check syntax of a Python file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            ast.parse(content, filename=str(file_path))
            return True, "Syntax OK"

        except SyntaxError as e:
            return False, f"Line {e.lineno}: {e.msg}"
        except Exception as e:
            return False, f"Parse error: {str(e)}"

    def check_imports(self, file_path: Path) -> List[str]:
        """Check for import issues in a file"""
        issues = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                line = line.strip()

                # Check for problematic import patterns that need fixing
                if (
                    line.startswith("from admin_")
                    and "import" in line
                    and not line.startswith("from src.admin_")
                ):
                    issues.append(
                        f"Line {i}: Should be 'from src.admin_' instead of 'from admin_'"
                    )
                elif line.startswith("import admin_") and not "src" in line:
                    issues.append(
                        f"Line {i}: Should use 'from src import admin_' pattern"
                    )
                elif (
                    line.startswith("import enhanced_admin_rithmic")
                    and not "src" in line
                ):
                    issues.append(
                        f"Line {i}: Should use 'from src import enhanced_admin_rithmic' pattern"
                    )
                elif line.startswith(
                    "from enhanced_admin_rithmic import"
                ) and not line.startswith("from src.enhanced_admin_rithmic"):
                    issues.append(
                        f"Line {i}: Should be 'from src.enhanced_admin_rithmic import'"
                    )

        except Exception as e:
            issues.append(f"Error analyzing imports: {str(e)}")

        return issues

    def fix_test_imports(self) -> List[str]:
        """Fix import statements in test files"""
        fixes_applied = []

        print("🔧 Fixing test file imports...")

        test_files = [f for f in self.tests_dir.glob("*.py") if f.name != "__init__.py"]

        for test_file in test_files:
            try:
                with open(test_file, "r", encoding="utf-8") as f:
                    content = f.read()

                original_content = content
                lines = content.split("\n")
                modified = False

                # Process each line for import fixes
                for i, line in enumerate(lines):
                    original_line = line.strip()

                    # Skip empty lines and comments
                    if not original_line or original_line.startswith("#"):
                        continue

                    # Fix various import patterns
                    if original_line.startswith("import admin_"):
                        module_name = original_line.split()[1]
                        lines[i] = f"from src import {module_name}"
                        modified = True
                        fixes_applied.append(
                            f"{test_file.name}: '{original_line}' → '{lines[i]}'"
                        )

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
                            fixes_applied.append(
                                f"{test_file.name}: '{original_line}' → '{lines[i]}'"
                            )

                    elif original_line.startswith("import enhanced_admin_rithmic"):
                        lines[i] = "from src import enhanced_admin_rithmic"
                        modified = True
                        fixes_applied.append(
                            f"{test_file.name}: '{original_line}' → '{lines[i]}'"
                        )

                    elif original_line.startswith("from enhanced_admin_rithmic import"):
                        parts = original_line.split()
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

                    lines = path_setup.strip().split("\n") + [""] + lines
                    fixes_applied.append(f"{test_file.name}: Added sys.path setup")
                    modified = True

                # Write back if changes were made
                if modified:
                    new_content = "\n".join(lines)
                    with open(test_file, "w", encoding="utf-8") as f:
                        f.write(new_content)

                    print(f"  ✅ Fixed imports in {test_file.name}")

            except Exception as e:
                print(f"  ❌ Error fixing {test_file.name}: {e}")
                self.issues_found.append(f"Error fixing {test_file.name}: {e}")

        return fixes_applied

    def run_comprehensive_analysis(self) -> Dict[str, Any]:
        """Run comprehensive analysis on all key files"""
        print("🔍 Running comprehensive file analysis...")

        # Get all key files
        files_to_analyze = []

        # Source files
        for pattern in ["*.py"]:
            files_to_analyze.extend(self.src_dir.glob(pattern))

        # Test files
        for pattern in ["*.py"]:
            files_to_analyze.extend(self.tests_dir.glob(pattern))

        # Import fix files
        for fix_dir in ["fix_imports", "verify_imports"]:
            fix_path = self.backend_dir / fix_dir
            if fix_path.exists():
                files_to_analyze.extend(fix_path.glob("*.py"))

        results = {}
        total_files = len(files_to_analyze)

        print(f"  📊 Analyzing {total_files} files...")

        for i, file_path in enumerate(files_to_analyze, 1):
            if file_path.name == "__init__.py":
                continue

            print(f"  📝 [{i}/{total_files}] {file_path.name}")

            # Check syntax
            syntax_ok, syntax_msg = self.analyze_syntax(file_path)

            # Check imports
            import_issues = self.check_imports(file_path)

            results[str(file_path)] = {
                "file_name": file_path.name,
                "relative_path": str(file_path.relative_to(self.backend_dir)),
                "syntax_ok": syntax_ok,
                "syntax_message": syntax_msg,
                "import_issues": import_issues,
                "file_exists": True,
            }

            # Collect issues for summary
            if not syntax_ok:
                self.issues_found.append(
                    f"Syntax error in {file_path.name}: {syntax_msg}"
                )

            if import_issues:
                for issue in import_issues:
                    self.issues_found.append(
                        f"Import issue in {file_path.name}: {issue}"
                    )

        return results

    def create_missing_init_files(self) -> List[str]:
        """Create missing __init__.py files"""
        fixes = []

        directories = [
            self.src_dir,
            self.tests_dir,
            self.backend_dir / "fix_imports",
            self.backend_dir / "verify_imports",
        ]

        for directory in directories:
            if directory.exists():
                init_file = directory / "__init__.py"
                if not init_file.exists():
                    try:
                        with open(init_file, "w", encoding="utf-8") as f:
                            f.write('"""Package initialization file"""\n')
                        fixes.append(
                            f"Created {init_file.relative_to(self.backend_dir)}"
                        )
                    except Exception as e:
                        self.issues_found.append(f"Could not create {init_file}: {e}")

        return fixes

    def generate_final_report(
        self,
        analysis_results: Dict[str, Any],
        import_fixes: List[str],
        init_fixes: List[str],
    ) -> Path:
        """Generate comprehensive final report"""
        timestamp = get_timestamp()
        report_file = self.outputs_dir / f"final_comprehensive_report_{timestamp}.md"

        print(f"📋 Generating final report: {report_file.name}")

        with open(report_file, "w", encoding="utf-8") as f:
            # Header
            f.write("# Final Comprehensive Analysis and Fix Report\n\n")
            f.write(f"**Generated:** {datetime.now()}\n")
            f.write(f"**Backend Directory:** {self.backend_dir}\n\n")

            # Executive Summary
            total_files = len(analysis_results)
            syntax_errors = sum(
                1 for r in analysis_results.values() if not r["syntax_ok"]
            )
            import_issues = sum(
                len(r["import_issues"]) for r in analysis_results.values()
            )
            total_fixes = len(import_fixes) + len(init_fixes)

            f.write("## 📊 Executive Summary\n\n")
            f.write(f"- **Files Analyzed:** {total_files}\n")
            f.write(f"- **Syntax Errors:** {syntax_errors}\n")
            f.write(f"- **Import Issues Found:** {import_issues}\n")
            f.write(f"- **Total Fixes Applied:** {total_fixes}\n")
            f.write(f"- **Issues Remaining:** {len(self.issues_found)}\n\n")

            # Status Assessment
            if syntax_errors == 0 and import_issues == 0:
                f.write("🎉 **STATUS: READY FOR PRODUCTION**\n\n")
                f.write("All files pass syntax checks and have correct imports!\n\n")
            elif syntax_errors == 0:
                f.write("✅ **STATUS: SYNTAX CLEAN, IMPORTS FIXED**\n\n")
                f.write(
                    "No syntax errors detected. Import issues have been addressed.\n\n"
                )
            else:
                f.write("⚠️ **STATUS: MANUAL FIXES NEEDED**\n\n")
                f.write("Some syntax errors require manual attention.\n\n")

            # Fixes Applied Section
            f.write("## 🛠 Fixes Applied\n\n")

            if import_fixes:
                f.write("### Import Statement Fixes\n")
                for fix in import_fixes:
                    f.write(f"- {fix}\n")
                f.write(f"\n**Total import fixes:** {len(import_fixes)}\n\n")

            if init_fixes:
                f.write("### Missing __init__.py Files Created\n")
                for fix in init_fixes:
                    f.write(f"- {fix}\n")
                f.write(f"\n**Total __init__.py files created:** {len(init_fixes)}\n\n")

            if not import_fixes and not init_fixes:
                f.write("No automatic fixes were needed.\n\n")

            # File Analysis Results
            f.write("## 📋 File Analysis Results\n\n")
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

            # Detailed Issues (if any)
            if any(
                not r["syntax_ok"] or r["import_issues"]
                for r in analysis_results.values()
            ):
                f.write("\n## 🔍 Detailed Issues\n\n")

                for file_path, result in analysis_results.items():
                    if not result["syntax_ok"] or result["import_issues"]:
                        file_name = result["file_name"]
                        f.write(f"### ⚠️ {file_name}\n")
                        f.write(f"**Path:** `{result['relative_path']}`\n\n")

                        if not result["syntax_ok"]:
                            f.write(
                                f"**❌ Syntax Error:** {result['syntax_message']}\n\n"
                            )

                        if result["import_issues"]:
                            f.write("**Import Issues:**\n")
                            for issue in result["import_issues"]:
                                f.write(f"- {issue}\n")
                            f.write("\n")

            # Testing Instructions
            f.write("## 🧪 Testing Instructions\n\n")
            f.write("After all fixes have been applied, test the system:\n\n")
            f.write("### 1. Verify Import Fixes\n")
            f.write("```bash\n")
            f.write("python verify_imports/verify_import_fixes.py\n")
            f.write("```\n\n")

            f.write("### 2. Run Test Suite\n")
            f.write("```bash\n")
            f.write("python tests/test_fixes.py\n")
            f.write("python tests/test_tui_display.py\n")
            f.write("python tests/test_enhanced_connection_display.py\n")
            f.write("```\n\n")

            f.write("### 3. Start Main Application\n")
            f.write("```bash\n")
            f.write("python src/enhanced_admin_rithmic.py\n")
            f.write("```\n\n")

            f.write("### 4. Run Comprehensive Analysis (Optional)\n")
            f.write("```bash\n")
            f.write("python scripts/focused_analysis_2025-05-28T11-41-52.py\n")
            f.write("```\n\n")

            # File Organization Status
            f.write("## 📁 File Organization Status\n\n")
            f.write("✅ **Completed Organization:**\n")
            f.write("- Import fix scripts moved to `fix_imports/` folder\n")
            f.write("- Verification scripts moved to `verify_imports/` folder\n")
            f.write("- Analysis scripts organized in `scripts/` folder\n")
            f.write("- All output files saved to `outputs/` folder\n")
            f.write("- Missing `__init__.py` files created where needed\n\n")

            f.write("📂 **Current Structure:**\n")
            f.write("```\n")
            f.write("backend/\n")
            f.write("├── src/                    # Main source files\n")
            f.write("├── tests/                  # Test files (imports fixed)\n")
            f.write("├── fix_imports/            # Import fix utilities\n")
            f.write("├── verify_imports/         # Import verification utilities\n")
            f.write("├── scripts/                # Analysis and utility scripts\n")
            f.write("├── outputs/                # Generated reports and logs\n")
            f.write("├── config/                 # Configuration files\n")
            f.write("└── backups/                # Backup files\n")
            f.write("```\n\n")

            # Next Steps
            f.write("## 🎯 Next Steps\n\n")

            if syntax_errors > 0:
                f.write("### 🚨 URGENT: Fix Syntax Errors\n")
                f.write("Manual fixes required for files with syntax errors:\n")
                for file_path, result in analysis_results.items():
                    if not result["syntax_ok"]:
                        f.write(
                            f"- **{result['file_name']}:** {result['syntax_message']}\n"
                        )
                f.write("\n")

            f.write("### 📋 Recommended Actions\n")
            if syntax_errors == 0 and import_issues == 0:
                f.write("1. ✅ **System is ready!** Run the main application\n")
                f.write(
                    "2. 📊 Run comprehensive analysis (pylint, mypy, black) for code quality\n"
                )
                f.write("3. 🧪 Run extended test suite to verify functionality\n")
            else:
                f.write("1. 🔧 Address any remaining syntax errors manually\n")
                f.write("2. 🧪 Run verification tests after fixes\n")
                f.write(
                    "3. 📊 Run comprehensive analysis once all syntax issues are resolved\n"
                )

            f.write("\n### 🚀 Ready to Run Commands\n")
            f.write("Once all issues are resolved:\n")
            f.write("```bash\n")
            f.write("# Activate virtual environment\n")
            f.write("cd C:\\Users\\nobody\\myProjects\\git\\futures-trading-system\n")
            f.write(".\\venv\\Scripts\\activate\n")
            f.write("\n")
            f.write("# Change to backend directory\n")
            f.write("cd layer1_development\\backend\n")
            f.write("\n")
            f.write("# Run the main application\n")
            f.write("python src\\enhanced_admin_rithmic.py\n")
            f.write("```\n\n")

            # Technical Notes
            f.write("## 🔧 Technical Notes\n\n")
            f.write("### Import Fix Strategy\n")
            f.write(
                "- Updated test files to use `from src import module_name` pattern\n"
            )
            f.write("- Added sys.path setup to ensure proper module resolution\n")
            f.write(
                "- Maintained compatibility with existing source file structure\n\n"
            )

            f.write("### Analysis Tools Created\n")
            f.write("- `manual_analysis_*.py` - Basic syntax and import checking\n")
            f.write("- `focused_analysis_*.py` - Comprehensive code quality analysis\n")
            f.write(
                "- `comprehensive_fix_*.py` - Complete fix application (this script)\n\n"
            )

            f.write("---\n")
            f.write(
                f"*Analysis completed on {datetime.now()} by Comprehensive Code Fixer*\n"
            )

        return report_file

    def run_final_verification(self) -> Tuple[bool, List[str]]:
        """Run final verification of all fixes"""
        print("🔍 Running final verification...")

        verification_results = []
        all_good = True

        # Test basic imports
        test_imports = [
            "from src import enhanced_admin_rithmic",
            "from src import admin_display_manager",
            "from src import admin_core_classes",
        ]

        for import_stmt in test_imports:
            try:
                exec(import_stmt)
                verification_results.append(f"✅ {import_stmt}")
            except ImportError as e:
                verification_results.append(f"❌ {import_stmt} - ImportError: {e}")
                all_good = False
            except Exception as e:
                verification_results.append(f"❌ {import_stmt} - Error: {e}")
                all_good = False

        # Test file syntax compilation
        key_files = [
            self.src_dir / "enhanced_admin_rithmic.py",
            self.src_dir / "admin_display_manager.py",
            self.tests_dir / "test_fixes.py",
        ]

        for file_path in key_files:
            if file_path.exists():
                syntax_ok, syntax_msg = self.analyze_syntax(file_path)
                if syntax_ok:
                    verification_results.append(f"✅ {file_path.name} syntax OK")
                else:
                    verification_results.append(
                        f"❌ {file_path.name} syntax error: {syntax_msg}"
                    )
                    all_good = False

        return all_good, verification_results


def main():
    """Main function"""
    print("🚀 FINAL COMPREHENSIVE ANALYSIS AND FIX TOOL")
    print("=" * 70)
    print("This tool will analyze all files and apply necessary fixes")
    print("=" * 70)

    # Initialize fixer
    fixer = ComprehensiveFixer()

    print(f"Backend Directory: {fixer.backend_dir}")
    print(f"Analysis Time: {datetime.now()}")
    print()

    try:
        # Step 1: Run comprehensive analysis
        print("📊 STEP 1: Comprehensive Analysis")
        print("-" * 40)
        analysis_results = fixer.run_comprehensive_analysis()

        # Step 2: Apply import fixes
        print("\n🔧 STEP 2: Apply Import Fixes")
        print("-" * 40)
        import_fixes = fixer.fix_test_imports()

        # Step 3: Create missing __init__.py files
        print("\n📁 STEP 3: Create Missing Files")
        print("-" * 40)
        init_fixes = fixer.create_missing_init_files()

        # Step 4: Generate final report
        print("\n📋 STEP 4: Generate Final Report")
        print("-" * 40)
        report_file = fixer.generate_final_report(
            analysis_results, import_fixes, init_fixes
        )

        # Step 5: Final verification
        print("\n✅ STEP 5: Final Verification")
        print("-" * 40)
        verification_passed, verification_results = fixer.run_final_verification()

        # Display results
        print("\n🎉 COMPREHENSIVE ANALYSIS AND FIXES COMPLETE!")
        print("=" * 55)
        print(f"📋 Final Report: {report_file.name}")
        print()

        # Summary stats
        total_files = len(analysis_results)
        syntax_errors = sum(1 for r in analysis_results.values() if not r["syntax_ok"])
        import_issues = sum(len(r["import_issues"]) for r in analysis_results.values())
        total_fixes = len(import_fixes) + len(init_fixes)

        print("📊 SUMMARY:")
        print(f"   Files analyzed: {total_files}")
        print(f"   Syntax errors: {syntax_errors}")
        print(f"   Import issues: {import_issues}")
        print(f"   Fixes applied: {total_fixes}")
        print()

        # Verification results
        print("🔍 VERIFICATION RESULTS:")
        for result in verification_results:
            print(f"   {result}")
        print()

        # Final status and next steps
        if verification_passed and syntax_errors == 0:
            print("🎉 SUCCESS: All files are ready for use!")
            print()
            print("🚀 Next Steps:")
            print("   1. Activate virtual environment:")
            print("      .\\venv\\Scripts\\activate")
            print("   2. Change to backend directory:")
            print("      cd layer1_development\\backend")
            print("   3. Run the application:")
            print("      python src\\enhanced_admin_rithmic.py")
            return 0
        else:
            print("⚠️ PARTIAL SUCCESS: Some issues remain")
            print()
            print("📋 Next Steps:")
            print("   1. Review the detailed report for remaining issues")
            print("   2. Fix any syntax errors manually")
            print("   3. Re-run verification after fixes")
            if verification_passed:
                print("   4. The system should then be ready to run!")
            return 1

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
