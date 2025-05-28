#!/usr/bin/env python3
"""
Manual Black formatting fixer for files having issues
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def fix_line_endings(content):
    """Normalize line endings to LF only"""
    # Replace CRLF with LF, then replace any remaining CR with LF
    content = content.replace('\r\n', '\n')
    content = content.replace('\r', '\n')
    return content


def fix_trailing_whitespace(content):
    """Remove trailing whitespace from all lines"""
    lines = content.split('\n')
    fixed_lines = [line.rstrip() for line in lines]
    return '\n'.join(fixed_lines)


def ensure_final_newline(content):
    """Ensure file ends with exactly one newline"""
    content = content.rstrip()
    return content + '\n'


def fix_indentation_issues(content):
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


def manual_black_format(file_path):
    """Apply manual Black-like formatting"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply fixes
        content = fix_line_endings(content)
        content = fix_trailing_whitespace(content)
        content = fix_indentation_issues(content)
        content = ensure_final_newline(content)
        
        # Try to run Black programmatically
        try:
            import black
            
            # Configure Black
            mode = black.FileMode(
                line_length=88,
                string_normalization=True,
                is_pyi=False,
            )
            
            # Try to format with Black
            try:
                formatted_content = black.format_str(content, mode=mode)
                content = formatted_content
                print(f"✅ Successfully formatted {file_path} with Black")
            except Exception as black_error:
                print(f"⚠️ Black formatting failed for {file_path}: {black_error}")
                print("   Using manual fixes only")
        
        except ImportError:
            print(f"⚠️ Black not available, using manual fixes for {file_path}")
        
        # Only write if content changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed formatting issues in {file_path}")
            return True
        else:
            print(f"✅ No changes needed for {file_path}")
            return True
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return False


def fix_all_problematic_files():
    """Fix all files that were having Black formatting issues"""
    
    # Get the backend directory
    backend_dir = Path(__file__).parent
    
    # List of files from the Black report that had issues
    problematic_files = [
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
    
    success_count = 0
    error_count = 0
    not_found_count = 0
    
    print("🔧 Fixing Black formatting issues")
    print("=" * 50)
    
    for file_path in problematic_files:
        full_path = backend_dir / file_path
        
        if not full_path.exists():
            print(f"⚠️ File not found: {file_path}")
            not_found_count += 1
            continue
        
        print(f"\n📝 Processing: {file_path}")
        
        if manual_black_format(full_path):
            success_count += 1
        else:
            error_count += 1
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 FORMATTING FIX SUMMARY")
    print("=" * 50)
    print(f"✅ Successfully processed: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"⚠️ Files not found: {not_found_count}")
    print(f"📁 Total files processed: {success_count + error_count}")
    
    # Create a report
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    report_file = backend_dir / f"formatting_fix_report_{timestamp}.txt"
    
    with open(report_file, 'w') as f:
        f.write(f"FORMATTING FIX REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"Successfully processed: {success_count}\n")
        f.write(f"Errors: {error_count}\n")
        f.write(f"Files not found: {not_found_count}\n")
    
    print(f"\n📄 Report saved: {report_file.name}")
    
    if error_count == 0:
        print("\n🎉 All files processed successfully!")
        print("✅ Black formatting issues should now be resolved")
        print("\n🔄 You can now run Black again to verify:")
        print("   python -m black --check .")
    else:
        print(f"\n⚠️ {error_count} files had issues and may need manual attention")


if __name__ == "__main__":
    fix_all_problematic_files()
