#!/usr/bin/env python3
"""
Script to run pylint, mypy, and black on the fixed files
"""

import subprocess
import sys
import os
from datetime import datetime

def run_command(command, description):
    """Run a command and return the output"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            cwd=os.getcwd()
        )
        
        output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}\n\nReturn Code: {result.returncode}\n"
        print(output)
        return output
        
    except Exception as e:
        error_output = f"Error running command: {str(e)}\n"
        print(error_output)
        return error_output

def main():
    # Generate timestamp for output file
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    output_file = f"command_output-{timestamp}.txt"
    
    # Files to check
    files_to_check = [
        "src/admin_rithmic_connection.py",
        "src/admin_rithmic_historical.py", 
        "src/admin_rithmic_operations.py"
    ]
    
    # Collect all output
    all_output = []
    
    all_output.append(f"Code Quality Check Results - {datetime.now()}\n")
    all_output.append(f"{'='*80}\n\n")
    
    # Check if virtual environment activation is needed (Windows)
    venv_activate = ".\\venv\\Scripts\\activate"
    if os.path.exists("venv\\Scripts\\activate.bat"):
        all_output.append("Virtual environment found.\n")
    else:
        all_output.append("No virtual environment found - running with system Python.\n")
    
    # Run checks on each file
    for file_path in files_to_check:
        if not os.path.exists(file_path):
            all_output.append(f"Warning: File {file_path} not found!\n\n")
            continue
            
        all_output.append(f"\n{'*'*80}\n")
        all_output.append(f"CHECKING FILE: {file_path}\n")
        all_output.append(f"{'*'*80}\n")
        
        # Run pylint
        pylint_output = run_command(
            [sys.executable, "-m", "pylint", file_path, "--reports=y"],
            f"pylint on {file_path}"
        )
        all_output.append(f"\nPYLINT RESULTS FOR {file_path}:\n")
        all_output.append(pylint_output)
        
        # Run mypy
        mypy_output = run_command(
            [sys.executable, "-m", "mypy", file_path, "--show-error-codes"],
            f"mypy on {file_path}"
        )
        all_output.append(f"\nMYPY RESULTS FOR {file_path}:\n")
        all_output.append(mypy_output)
        
        # Run black (check mode)
        black_output = run_command(
            [sys.executable, "-m", "black", "--check", "--diff", file_path],
            f"black (check) on {file_path}"
        )
        all_output.append(f"\nBLACK RESULTS FOR {file_path}:\n")
        all_output.append(black_output)
    
    # Write all output to file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.writelines(all_output)
        print(f"\n\nAll output written to: {output_file}")
        
        # Also print a summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Checked {len(files_to_check)} files")
        print(f"Output saved to: {output_file}")
        print(f"Timestamp: {timestamp}")
        
    except Exception as e:
        print(f"Error writing output file: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
