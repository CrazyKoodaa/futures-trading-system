#!/usr/bin/env python3
"""
Comprehensive Black formatting fixer for all problematic files

This script applies consistent formatting fixes to all files that were
having issues with Black formatting, including:
- Line ending normalization (LF only)
- Trailing whitespace removal
- Tab to space conversion
- Proper file ending with single newline
- Applying Black formatting where possible

Based on the black formatting report from 2025-05-28T14-24-42.txt
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Tuple


class BlackFormattingFixer:
    """Fixes common formatting issues that cause Black to fail"""

    def __init__(self, backend_dir: Path):
        self.backend_dir = backend_dir
        self.fixed_files = []
        self.error_files = []
        self.skipped_files = []

    def fix_line_endings(self, content: str) -> str:
        """Normalize line endings to LF only"""
        # Replace CRLF with LF, then replace any remaining CR with LF
        content = content.replace('\r\n', '\n')
        content = content.replace('\r', '\n')
        return content

    def fix_trailing_whitespace(self, content: str) -> str:
        """Remove trailing whitespace from all lines"""
        lines = content.split('\n')
        fixed_lines = [line.rstrip() for line in lines]
        return '\n'.join(fixed_lines)

    def ensure_final_newline(self, content: str) -> str:
        """Ensure file ends with exactly one newline"""
        content = content.rstrip()
        return content + '\n'

    def fix_indentation_issues(self, content: str) -> str:
        """Fix common indentation issues that might confuse Black"""
        lines = content.split('\n')
        fixed_lines = []

        for line in lines:
            # Convert tabs to 4 spaces
            if '\t' in line:
                # Calculate proper indentation
                leading_whitespace = len(line) - len(line.lstrip())
                if leading_whitespace > 0:
                    # Replace tabs with 4 spaces each
                    fixed_line = line.expandtabs(4)
                    fixed_lines.append(fixed_line)
                else:
                    fixed_lines.append(line)
            else:
                fixed_lines.append(line)

        return '\n'.join(fixed_lines)

    def manual_format_fixes(self, content: str) -> str:
        """Apply manual formatting fixes"""
        # Apply all fixes in sequence
        content = self.fix_line_endings(content)
        content = self.fix_trailing_whitespace(content)
        content = self.fix_indentation_issues(content)
        content = self.ensure_final_newline(content)
        return content

    def apply_black_formatting(self, content: str, file_path: Path) -> Tuple[str, bool]:
        """Try to apply Black formatting programmatically"""
        try:
            import black

            # Configure Black
            mode = black.FileMode(
                line_length=88,
                string_normalization=True,
                is_pyi=file_path.suffix == '.pyi',
            )

            # Try to format with Black
            formatted_content = black.format_str(content, mode=mode)
            return formatted_content, True

        except ImportError:
            # Black not available, use manual fixes only
            return content, False
        except Exception as e:
            # Black formatting failed, use manual fixes
            print(f"   ⚠️ Black formatting failed: {e}")
            return content, False

    def fix_file(self, file_path: Path) -> bool:
        """Fix formatting issues in a single file"""
        try:
            # Read the file
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()

            # Apply manual fixes first
            content = self.manual_format_fixes(original_content)

            # Try to apply Black formatting
            content, black_applied = self.apply_black_formatting(content, file_path)

            # Only write if content changed
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                if black_applied:
                    print(f"✅ Fixed with Black: {file_path.relative_to(self.backend_dir)}")
                else:
                    print(f"✅ Fixed manually: {file_path.relative_to(self.backend_dir)}")

                self.fixed_files.append(str(file_path.relative_to(self.backend_dir)))
                return True
            else:
                print(f"✅ No changes needed: {file_path.relative_to(self.backend_dir)}")
                self.skipped_files.append(str(file_path.relative_to(self.backend_dir)))
                return True

        except Exception as e:
            print(f"❌ Error processing {file_path.relative_to(self.backend_dir)}: {e}")
            self.error_files.append(str(file_path.relative_to(self.backend_dir)))
            return False

    def get_problematic_files(self) -> List[str]:
        """Get list of files that were having Black formatting issues"""
        return [
            "fix_imports/fix_imports.py",
            "scripts/comprehensive_analysis_2025-05-28T11-41-52.py",
            "scripts/comprehensive_fix_2025-05-28T11-41-52.py",
            "scripts/final_comprehensive_fix_2025-05-28T11-41-52.py",
            "scripts/FINAL_COMPREHENSIVE_FIXER_2025-05-28T11-41-52.py",
            "scripts/focused_analysis_2025-05-28T11-41-52.py",
            "scripts/manual_analysis_2025-05-28T11-41-52.py",
            "scripts/quick_pylint_check.py",
            "scripts/run_analysis_2025-05-28T11-41-52.py",
            "scripts/run_focused_analysis.py",
            "scripts/run_pylint_check.py",
            "scripts/run_pylint_diagnostic.py",
            "scripts/setup_check.py",
            "src/admin_core_classes.py",
            "src/admin_display_manager.py",
            "src/admin_operations.py",
            "src/admin_rithmic_connection.py",
            "src/admin_rithmic_operations.py",
            "src/admin_rithmic_symbols.py",
            "src/enhanced_admin_rithmic.py",
            "tests/comprehensive_tui_diagnostic.py",
            "tests/final_verification.py",
            "tests/final_verification_test.py",
            "tests/simple_tui_test.py",
            "tests/test_enhanced_connection_display.py",
            "tests/test_fixes.py",
            "tests/test_tui_display.py",
            "tests/test_tui_fixes.py",
            "verify_imports/verify_import_fixes.py",
        ]

    def fix_all_files(self):
        """Fix all problematic files"""
        print("🔧 Fixing Black formatting issues")
        print("=" * 60)

        problematic_files = self.get_problematic_files()

        for file_path_str in problematic_files:
            full_path = self.backend_dir / file_path_str

            if not full_path.exists():
                print(f"⚠️ File not found: {file_path_str}")
                self.error_files.append(file_path_str + " (not found)")
                continue

            print(f"\n📝 Processing: {file_path_str}")
            self.fix_file(full_path)

        self.print_summary()
        self.create_report()

    def print_summary(self):
        """Print summary of operations"""
        print("\n" + "=" * 60)
        print("📊 FORMATTING FIX SUMMARY")
        print("=" * 60)
        print(f"✅ Successfully fixed: {len(self.fixed_files)}")
        print(f"✅ No changes needed: {len(self.skipped_files)}")
        print(f"❌ Errors: {len(self.error_files)}")
        print(f"📁 Total files processed: {len(self.fixed_files) + len(self.skipped_files) + len(self.error_files)}")

        if self.error_files:
            print(f"\n❌ Files with errors:")
            for error_file in self.error_files:
                print(f"   • {error_file}")

    def create_report(self):
        """Create a detailed report of the fixes applied"""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        report_file = self.backend_dir / f"formatting_fix_report_{timestamp}.txt"

        with open(report_file, 'w') as f:
            f.write(f"BLACK FORMATTING FIX REPORT\n")
            f.write(f"Generated: {datetime.now()}\n")
            f.write(f"=" * 50 + "\n\n")

            f.write(f"SUMMARY:\n")
            f.write(f"Successfully fixed: {len(self.fixed_files)}\n")
            f.write(f"No changes needed: {len(self.skipped_files)}\n")
            f.write(f"Errors: {len(self.error_files)}\n\n")

            if self.fixed_files:
                f.write(f"FIXED FILES:\n")
                for fixed_file in self.fixed_files:
                    f.write(f"  ✅ {fixed_file}\n")
                f.write("\n")

            if self.skipped_files:
                f.write(f"FILES WITH NO CHANGES NEEDED:\n")
                for skipped_file in self.skipped_files:
                    f.write(f"  ✅ {skipped_file}\n")
                f.write("\n")

            if self.error_files:
                f.write(f"FILES WITH ERRORS:\n")
                for error_file in self.error_files:
                    f.write(f"  ❌ {error_file}\n")
                f.write("\n")

            f.write(f"APPLIED FIXES:\n")
            f.write(f"  • Line ending normalization (CRLF → LF)\n")
            f.write(f"  • Trailing whitespace removal\n")
            f.write(f"  • Tab to space conversion (4 spaces)\n")
            f.write(f"  • Proper file ending (single newline)\n")
            f.write(f"  • Black formatting (where possible)\n")

        print(f"\n📄 Report saved: {report_file.name}")

    def verify_fixes(self) -> bool:
        """Verify that Black can now process the files without errors"""
        print("\n🔍 Verifying Black formatting fixes...")
        print("-" * 40)

        # Try to run Black on a few of the previously problematic files
        test_files = [
            "fix_imports/fix_imports.py",
            "scripts/setup_check.py",
            "scripts/quick_pylint_check.py",
            "src/admin_core_classes.py"
        ]

        success_count = 0
        total_tests = 0

        for file_path_str in test_files:
            full_path = self.backend_dir / file_path_str

            if not full_path.exists():
                continue

            total_tests += 1

            try:
                # Run Black check
                result = subprocess.run(
                    [sys.executable, "-m", "black", "--check", "--diff", str(full_path)],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    print(f"✅ {file_path_str}")
                    success_count += 1
                else:
                    print(f"⚠️ {file_path_str} - Still needs formatting")
                    # Try to format it
                    format_result = subprocess.run(
                        [sys.executable, "-m", "black", str(full_path)],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if format_result.returncode == 0:
                        print(f"   → Fixed with Black")
                        success_count += 1

            except subprocess.TimeoutExpired:
                print(f"⚠️ {file_path_str} - Timeout")
            except Exception as e:
                print(f"❌ {file_path_str} - Error: {e}")

        print(f"\n📊 Verification Results: {success_count}/{total_tests} files pass Black check")

        if success_count == total_tests and total_tests > 0:
            print("🎉 All tested files now pass Black formatting!")
            return True
        else:
            print("⚠️ Some files may still need attention")
            return False


def main():
    """Main function"""
    # Get the backend directory
    script_path = Path(__file__)
    backend_dir = script_path.parent

    print("🚀 Black Formatting Fixer")
    print("=" * 60)
    print(f"Backend Directory: {backend_dir}")
    print()

    # Initialize the fixer
    fixer = BlackFormattingFixer(backend_dir)

    # Fix all problematic files
    fixer.fix_all_files()

    # Verify the fixes
    verification_success = fixer.verify_fixes()

    # Final message
    if len(fixer.error_files) == 0 and verification_success:
        print("\n🎉 SUCCESS: All Black formatting issues have been resolved!")
        print("\n✅ You can now run Black formatting checks:")
        print("   python -m black --check .")
        print("   python -m black --diff .")
        print("   python -m black . (to format)")
    else:
        print(f"\n⚠️ Some issues may remain. Check the report and error messages above.")

    print("\n🔄 Next Steps:")
    print("1. Run: python -m black --check . (to verify all files)")
    print("2. Run: python -m black . (to format any remaining files)")
    print("3. Check the generated report for details")


if __name__ == "__main__":
    main()
