#!/usr/bin/env python3
"""
Script to run pylint on all Python files in the directory
"""
import os
import subprocess
import sys
from pathlib import Path


def run_pylint():
    """Run pylint on all Python files in current directory"""

    # Get current directory
    current_dir = Path.cwd()
    print(f"Running pylint in: {current_dir}")

    # Find all Python files
    py_files = list(current_dir.glob("*.py"))
    py_files = [f for f in py_files if f.name != __file__.split(os.sep)[-1]]  # Exclude this script

    if not py_files:
        print("No Python files found!")
        return

    print(f"Found {len(py_files)} Python files:")
    for f in py_files:
        print(f"  - {f.name}")
    print()

    # Open results file for writing
    results_file = current_dir / "pylint_results.txt"

    with open(results_file, "w", encoding="utf-8") as f:
        f.write("=== PYLINT RESULTS ===\n")
        f.write(f"Generated: {os.popen('date /t & time /t').read().strip()}\n")
        f.write(f"Directory: {current_dir}\n")
        f.write("\n")

        for py_file in py_files:
            print(f"Checking {py_file.name}...")
            f.write(f"=== PYLINT for {py_file.name} ===\n")

            try:
                # Run pylint and capture output
                result = subprocess.run(
                    [sys.executable, "-m", "pylint", str(py_file)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )

                # Write stdout and stderr
                if result.stdout:
                    f.write(result.stdout)
                if result.stderr:
                    f.write("\nSTDERR:\n")
                    f.write(result.stderr)

                f.write(f"\nReturn code: {result.returncode}\n")

            except subprocess.TimeoutExpired:
                f.write("ERROR: Pylint timed out after 60 seconds\n")
            except Exception as e:
                f.write(f"ERROR running pylint: {e}\n")

            f.write("\n" + "-" * 80 + "\n\n")

    print(f"\nPylint results saved to: {results_file}")

    # Also append to the results file for easier access
    print("\n=== SUMMARY ===")
    print(f"Processed {len(py_files)} files")
    print(f"Results saved to: {results_file}")


if __name__ == "__main__":
    run_pylint()
