#!/usr/bin/env python3
"""
Command execution script to run pylint, mypy, and black on fixed files
Creates a command output file as specified in the rules
"""

import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path


def run_command(cmd, description, timeout=60):
    """Run a command and capture its output"""
    print(f"\n{'='*60}")
    print(f"RUNNING: {description}")
    print(f"COMMAND: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent
        )
        
        output = {
            'command': ' '.join(cmd),
            'description': description,
            'return_code': result.returncode,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'success': result.returncode == 0
        }
        
        print(f"Return Code: {result.returncode}")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
            
        return output
        
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT: Command timed out after {timeout} seconds")
        return {
            'command': ' '.join(cmd),
            'description': description,
            'return_code': -1,
            'stdout': '',
            'stderr': f'Command timed out after {timeout} seconds',
            'success': False
        }
    except Exception as e:
        print(f"ERROR: {e}")
        return {
            'command': ' '.join(cmd),
            'description': description,
            'return_code': -1,
            'stdout': '',
            'stderr': str(e),
            'success': False
        }


def main():
    """Main function to run all commands and create output file"""
    
    # Files we've been working on and need to check
    files_to_check = [
        "fix_imports/fix_imports.py",
        "scripts/setup_check.py", 
        "scripts/quick_pylint_check.py",
        "src/admin_core_classes.py",
        "src/admin_display_manager.py",
        "src/admin_database.py"
    ]
    
    # Timestamp for the output file
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_file = Path(f"command_output-{timestamp}.txt")
    
    print(f"🔧 Running code quality checks on fixed files")
    print(f"📄 Output will be saved to: {output_file}")
    
    results = []
    
    # Test if tools are available first
    tools_check = [
        ([sys.executable, "-m", "black", "--version"], "Check Black availability"),
        ([sys.executable, "-m", "pylint", "--version"], "Check Pylint availability"),
        ([sys.executable, "-m", "mypy", "--version"], "Check MyPy availability")
    ]
    
    for cmd, desc in tools_check:
        result = run_command(cmd, desc, timeout=10)
        results.append(result)
    
    # Check if files exist and run formatting/linting
    backend_dir = Path(__file__).parent
    
    for file_path in files_to_check:
        full_path = backend_dir / file_path
        
        if not full_path.exists():
            print(f"⚠️ File not found: {file_path}")
            results.append({
                'command': f'check_file_exists {file_path}',
                'description': f'Check if {file_path} exists',
                'return_code': 1,
                'stdout': '',
                'stderr': f'File not found: {file_path}',
                'success': False
            })
            continue
        
        print(f"\n🔍 Checking file: {file_path}")
        
        # Run Black check
        black_cmd = [sys.executable, "-m", "black", "--check", "--diff", str(full_path)]
        result = run_command(black_cmd, f"Black check on {file_path}")
        results.append(result)
        
        # If Black check fails, try to format
        if result['return_code'] != 0:
            format_cmd = [sys.executable, "-m", "black", str(full_path)]
            format_result = run_command(format_cmd, f"Black format {file_path}")
            results.append(format_result)
        
        # Run Pylint
        pylint_cmd = [
            sys.executable, "-m", "pylint",
            "--disable=C0103,C0114,C0115,C0116,R0903,R0913,W0613,C0301",
            "--output-format=text",
            "--score=n",
            str(full_path)
        ]
        result = run_command(pylint_cmd, f"Pylint check on {file_path}")
        results.append(result)
        
        # Run MyPy (if available)
        mypy_cmd = [sys.executable, "-m", "mypy", "--ignore-missing-imports", str(full_path)]
        result = run_command(mypy_cmd, f"MyPy check on {file_path}")
        results.append(result)
    
    # Create comprehensive output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"COMMAND OUTPUT REPORT\n")
        f.write(f"Generated: {datetime.now()}\n")
        f.write(f"{'='*80}\n\n")
        
        f.write(f"SUMMARY:\n")
        f.write(f"Total commands executed: {len(results)}\n")
        successful = sum(1 for r in results if r['success'])
        f.write(f"Successful: {successful}\n")
        f.write(f"Failed: {len(results) - successful}\n\n")
        
        f.write(f"FILES CHECKED:\n")
        for file_path in files_to_check:
            f.write(f"  - {file_path}\n")
        f.write("\n")
        
        f.write(f"DETAILED RESULTS:\n")
        f.write(f"{'='*80}\n")
        
        for i, result in enumerate(results, 1):
            f.write(f"\n{i}. {result['description']}\n")
            f.write(f"Command: {result['command']}\n")
            f.write(f"Return Code: {result['return_code']}\n")
            f.write(f"Success: {result['success']}\n")
            
            if result['stdout']:
                f.write(f"STDOUT:\n{result['stdout']}\n")
            
            if result['stderr']:
                f.write(f"STDERR:\n{result['stderr']}\n")
            
            f.write(f"{'-'*60}\n")
        
        # Add recommendations
        f.write(f"\nRECOMMENDATIONS:\n")
        failed_results = [r for r in results if not r['success']]
        
        if not failed_results:
            f.write("✅ All checks passed! Code quality looks good.\n")
        else:
            f.write("⚠️ Some issues found:\n")
            for result in failed_results:
                f.write(f"  - {result['description']}: {result['stderr'][:100]}...\n")
        
        f.write(f"\nNEXT STEPS:\n")
        f.write(f"1. Review any errors or warnings above\n")
        f.write(f"2. Fix any remaining formatting issues\n")
        f.write(f"3. Address any pylint warnings if needed\n")
        f.write(f"4. Run the comprehensive Black fixer if needed\n")
    
    print(f"\n{'='*60}")
    print(f"📊 SUMMARY")
    print(f"{'='*60}")
    print(f"Total commands: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"📄 Full report saved to: {output_file}")
    
    if failed_results:
        print(f"\n⚠️ {len(failed_results)} commands had issues")
        print("📋 Check the output file for details")
    else:
        print(f"\n🎉 All commands completed successfully!")
    
    return len(failed_results) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
