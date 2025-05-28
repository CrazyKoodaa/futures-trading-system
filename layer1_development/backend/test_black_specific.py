#!/usr/bin/env python3
"""
Test Black formatting on specific problematic files
"""

import subprocess
import sys
import os
from pathlib import Path

def test_black_formatting():
    """Test Black formatting and capture specific errors"""
    
    # Set working directory to backend
    backend_dir = Path(__file__).parent
    os.chdir(backend_dir)
    
    # List of files that are having issues according to the report
    problematic_files = [
        "fix_imports/fix_imports.py",
        "scripts/setup_check.py",
        "scripts/quick_pylint_check.py",
        "src/admin_core_classes.py",
    ]
    
    results = {}
    
    for file_path in problematic_files:
        if not os.path.exists(file_path):
            results[file_path] = {"error": "File not found"}
            continue
            
        print(f"\n=== Testing {file_path} ===")
        
        try:
            # Test Black check first
            cmd = [sys.executable, "-m", "black", "--check", "--diff", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            print(f"Return code: {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            
            # If check fails, try to format
            if result.returncode != 0:
                print(f"\nTrying to format {file_path}...")
                cmd = [sys.executable, "-m", "black", file_path]
                format_result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                print(f"Format return code: {format_result.returncode}")
                print(f"Format STDOUT: {format_result.stdout}")
                print(f"Format STDERR: {format_result.stderr}")
                
                results[file_path] = {
                    "check_result": result.returncode,
                    "check_stdout": result.stdout,
                    "check_stderr": result.stderr,
                    "format_result": format_result.returncode,
                    "format_stdout": format_result.stdout,
                    "format_stderr": format_result.stderr
                }
            else:
                results[file_path] = {
                    "check_result": result.returncode,
                    "check_stdout": result.stdout,
                    "check_stderr": result.stderr,
                    "status": "already_formatted"
                }
                
        except subprocess.TimeoutExpired:
            results[file_path] = {"error": "Timeout"}
        except Exception as e:
            results[file_path] = {"error": str(e)}
    
    print("\n" + "="*50)
    print("SUMMARY")
    print("="*50)
    
    for file_path, result in results.items():
        print(f"\n{file_path}:")
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        elif "status" in result and result["status"] == "already_formatted":
            print(f"  ✅ Already formatted correctly")
        else:
            print(f"  Check result: {result.get('check_result', 'N/A')}")
            print(f"  Format result: {result.get('format_result', 'N/A')}")
            if result.get('format_stderr'):
                print(f"  Format error: {result['format_stderr']}")

if __name__ == "__main__":
    test_black_formatting()
