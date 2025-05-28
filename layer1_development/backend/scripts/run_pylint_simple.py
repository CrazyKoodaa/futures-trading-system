import subprocess
import os
from pathlib import Path


def run_pylint_analysis():
    """Run pylint on all Python files and save results"""

    # List of Python files to analyze
    python_files = [
        "admin_core_classes.py",
        "admin_database.py",
        "admin_display_manager.py",
        "admin_operations.py",
        "admin_rithmic_connection.py",
        "admin_rithmic_historical.py",
        "admin_rithmic_operations.py",
        "admin_rithmic_symbols.py",
        "enhanced_admin_rithmic.py",
        "analyze_pylint.py",
        "run_pylint.py",
        "__init__.py",
    ]

    # Output file
    output_file = "comprehensive_pylint_results.txt"

    # Clear output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=== COMPREHENSIVE PYLINT ANALYSIS ===\n")
        f.write(f"Analysis of {len(python_files)} Python files\n")
        f.write("=" * 50 + "\n\n")

    print(f"Analyzing {len(python_files)} Python files...")

    for py_file in python_files:
        if os.path.exists(py_file):
            print(f"Running pylint on {py_file}...")

            try:
                # Run pylint
                cmd = ["python", "-m", "pylint", "--output-format=text", py_file]
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)

                # Append to results file
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"FILE: {py_file}\n")
                    f.write(f"{'='*60}\n")
                    f.write(result.stdout)
                    if result.stderr:
                        f.write(f"\nERRORS:\n{result.stderr}")
                    f.write(f"\nReturn code: {result.returncode}\n")
                    f.write("=" * 60 + "\n")

            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(f"\nERROR analyzing {py_file}: {e}\n")
        else:
            print(f"File not found: {py_file}")

    print(f"Analysis complete. Results saved to {output_file}")
    return output_file


if __name__ == "__main__":
    run_pylint_analysis()
