#!/usr/bin/env python3
"""
Comprehensive pylint runner for enhanced_rithmic_admin
"""
import os
import subprocess
import glob
from pathlib import Path

def run_pylint_on_directory():
    """Run pylint on all Python files in the current directory"""
    
    # Get current directory
    current_dir = Path(__file__).parent
    
    # Find all Python files (excluding __pycache__ and backups)
    python_files = []
    for pattern in ['*.py']:
        files = glob.glob(str(current_dir / pattern))
        for file in files:
            if '__pycache__' not in file and 'backups' not in file and 'run_comprehensive_pylint.py' not in file:
                python_files.append(file)
    
    print(f"Found {len(python_files)} Python files to analyze:")
    for file in python_files:
        print(f"  - {os.path.basename(file)}")
    
    # Output file for results
    output_file = current_dir / 'comprehensive_pylint_results.txt'
    
    # Clear the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== COMPREHENSIVE PYLINT ANALYSIS ===\n")
        f.write(f"Analysis of {len(python_files)} Python files\n")
        f.write("=" * 50 + "\n\n")
    
    # Run pylint on each file
    for py_file in python_files:
        print(f"Running pylint on {os.path.basename(py_file)}...")
        
        try:
            # Run pylint with comprehensive options
            result = subprocess.run([
                'python', '-m', 'pylint', 
                '--output-format=text',
                '--reports=yes',
                '--score=yes',
                py_file
            ], capture_output=True, text=True, check=False)
            
            # Append results to file
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"FILE: {os.path.basename(py_file)}\n")
                f.write(f"{'='*60}\n")
                f.write("STDOUT:\n")
                f.write(result.stdout)
                f.write("\nSTDERR:\n")
                f.write(result.stderr)
                f.write(f"\nReturn code: {result.returncode}\n")
                f.write("="*60 + "\n")
            
        except Exception as e:
            print(f"Error running pylint on {py_file}: {e}")
            with open(output_file, 'a', encoding='utf-8') as f:
                f.write(f"\nERROR analyzing {py_file}: {e}\n")
    
    print(f"\nPylint analysis complete. Results saved to: {output_file}")
    return output_file

if __name__ == "__main__":
    # Activate virtual environment first
    print("Make sure to activate virtual environment first:")
    print("Run: .\\venv\\Scripts\\activate")
    print("")
    
    result_file = run_pylint_on_directory()
    print(f"Results saved to: {result_file}")
