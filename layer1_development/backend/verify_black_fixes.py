#!/usr/bin/env python3
"""
Simple Black formatting verification script
Tests the files we've fixed to ensure Black formatting works
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path


def test_black_formatting():
    """Test Black formatting on our fixed files"""
    
    # Get timestamp for output file
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_file = f"command_output-{timestamp}.txt"
    
    # Files we've fixed
    test_files = [
        "fix_imports/fix_imports.py",
        "scripts/setup_check.py",
        "scripts/quick_pylint_check.py", 
        "src/admin_core_classes.py",
        "src/admin_display_manager.py"
    ]
    
    results = []
    
    print("🔍 Testing Black formatting on fixed files...")
    print(f"📄 Creating output file: {output_file}")
    
    # Test each file
    for file_path in test_files:
        if not os.path.exists(file_path):
            result = f"❌ {file_path} - File not found"
            print(result)
            results.append(result)
            continue
        
        try:
            # Test Black check
            cmd = [sys.executable, "-m", "black", "--check", "--diff", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                status = f"✅ {file_path} - Already formatted correctly"
                print(status)
                results.append(status)
                results.append(f"   Output: {result.stdout if result.stdout else 'No changes needed'}")
            else:
                # Try to format the file
                print(f"⚠️  {file_path} - Needs formatting, attempting to fix...")
                format_cmd = [sys.executable, "-m", "black", file_path]
                format_result = subprocess.run(format_cmd, capture_output=True, text=True, timeout=30)
                
                if format_result.returncode == 0:
                    status = f"✅ {file_path} - Successfully formatted"
                    print(status)
                    results.append(status)
                    results.append(f"   Output: {format_result.stdout if format_result.stdout else 'Formatted successfully'}")
                else:
                    status = f"❌ {file_path} - Formatting failed"
                    print(status)
                    results.append(status)
                    results.append(f"   Error: {format_result.stderr}")
        
        except subprocess.TimeoutExpired:
            status = f"❌ {file_path} - Timeout"
            print(status)
            results.append(status)
        except Exception as e:
            status = f"❌ {file_path} - Error: {e}"
            print(status)
            results.append(status)
    
    # Test pylint on a few key files if available
    print("\n🔍 Testing pylint on key files...")
    key_files = ["src/admin_core_classes.py", "src/admin_display_manager.py"]
    
    for file_path in key_files:
        if not os.path.exists(file_path):
            continue
            
        try:
            cmd = [
                sys.executable, "-m", "pylint",
                "--disable=C0103,C0114,C0115,C0116,R0903,R0913,W0613,C0301",
                "--output-format=text",
                "--score=n",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                status = f"✅ Pylint {file_path} - No errors"
                print(status)
                results.append(status)
            else:
                status = f"⚠️  Pylint {file_path} - Issues found"
                print(status)
                results.append(status)
                # Add first few lines of output
                output_lines = result.stdout.split('\n')[:5]
                for line in output_lines:
                    if line.strip():
                        results.append(f"   {line}")
                        
        except subprocess.TimeoutExpired:
            status = f"❌ Pylint {file_path} - Timeout"
            print(status)
            results.append(status)
        except FileNotFoundError:
            status = f"⚠️  Pylint not available"
            print(status)
            results.append(status)
            break  # Don't try other files if pylint isn't available
        except Exception as e:
            status = f"❌ Pylint {file_path} - Error: {e}"
            print(status)
            results.append(status)
    
    # Create output file
    with open(output_file, 'w') as f:
        f.write(f"BLACK FORMATTING VERIFICATION REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"="*60 + "\n\n")
        
        f.write(f"FILES TESTED:\n")
        for file_path in test_files:
            f.write(f"  - {file_path}\n")
        f.write("\n")
        
        f.write(f"RESULTS:\n")
        f.write(f"-"*40 + "\n")
        for result in results:
            f.write(f"{result}\n")
        
        f.write(f"\n" + "="*60 + "\n")
        f.write(f"SUMMARY:\n")
        
        success_count = sum(1 for r in results if "✅" in r)
        warning_count = sum(1 for r in results if "⚠️" in r) 
        error_count = sum(1 for r in results if "❌" in r)
        
        f.write(f"Successful: {success_count}\n")
        f.write(f"Warnings: {warning_count}\n") 
        f.write(f"Errors: {error_count}\n")
        
        if error_count == 0:
            f.write(f"\n🎉 All Black formatting checks passed!\n")
        else:
            f.write(f"\n⚠️  Some files still have formatting issues.\n")
    
    print(f"\n📊 Summary:")
    print(f"✅ Successful: {success_count}")
    print(f"⚠️  Warnings: {warning_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📄 Full report: {output_file}")
    
    return error_count == 0


if __name__ == "__main__":
    success = test_black_formatting()
    if success:
        print("\n🎉 All formatting checks passed!")
    else:
        print("\n⚠️  Some issues remain - check the report file")
