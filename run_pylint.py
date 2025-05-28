import subprocess
import os
import sys
from datetime import datetime

# Change to the project directory
os.chdir(r"C:\Users\nobody\myProjects\git\futures-trading-system")

# Activate virtual environment and run pylint
try:
    # Run pylint with virtual environment
    result = subprocess.run([
        r".\venv\Scripts\python.exe", 
        "-m", "pylint", 
        r"layer1_development\enhanced_rithmic_admin\admin_display_manager.py"
    ], capture_output=True, text=True, cwd=r"C:\Users\nobody\myProjects\git\futures-trading-system")
    
    # Create timestamp for filename
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_filename = f"layer1_development/enhanced_rithmic_admin/pylint_output-{timestamp}.txt"
    
    # Write output to file
    with open(output_filename, 'w') as f:
        f.write("PYLINT STDOUT:\n")
        f.write(result.stdout)
        f.write("\n\nPYLINT STDERR:\n")
        f.write(result.stderr)
        f.write(f"\n\nReturn code: {result.returncode}")
    
    print(f"Pylint output saved to {output_filename}")
    print(f"Return code: {result.returncode}")
    print("STDOUT:")
    print(result.stdout)
    if result.stderr:
        print("STDERR:")
        print(result.stderr)

except Exception as e:
    print(f"Error running pylint: {str(e)}")
