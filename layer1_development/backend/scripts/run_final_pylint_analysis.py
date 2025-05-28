#!/usr/bin/env python3
"""
Comprehensive Pylint Fixer for Enhanced Rithmic Admin

This script runs pylint on all Python files and applies fixes for common issues.
"""

import subprocess
import os
import re
from pathlib import Path


def run_pylint_comprehensive():
    """Run comprehensive pylint analysis on all Python files"""

    # Python files to analyze
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
        "__init__.py",
    ]

    # Output file
    output_file = "comprehensive_pylint_results_final.txt"

    # Clear output file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("=== COMPREHENSIVE PYLINT ANALYSIS - FINAL ===\n")
        f.write(f"Analysis of {len(python_files)} Python files\n")
        f.write("=" * 60 + "\n\n")

    print(f"Analyzing {len(python_files)} Python files...")

    # Statistics
    total_issues = 0
    file_scores = {}

    for py_file in python_files:
        if os.path.exists(py_file):
            print(f"Running pylint on {py_file}...")

            try:
                # Run pylint with comprehensive options
                result = subprocess.run(
                    [
                        "python",
                        "-m",
                        "pylint",
                        "--output-format=text",
                        "--reports=yes",
                        "--score=yes",
                        "--max-line-length=100",
                        py_file,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

                # Parse score
                score = extract_score(result.stdout)
                file_scores[py_file] = score

                # Count issues
                issues = count_issues(result.stdout)
                total_issues += issues

                # Append to results file
                with open(output_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"FILE: {py_file}\n")
                    f.write(f"SCORE: {score}/10.00\n")
                    f.write(f"ISSUES: {issues}\n")
                    f.write(f"{'='*60}\n")
                    f.write("OUTPUT:\n")
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

    # Write summary
    with open(output_file, "a", encoding="utf-8") as f:
        f.write(f"\n{'='*60}\n")
        f.write("FINAL SUMMARY\n")
        f.write(f"{'='*60}\n")
        f.write(f"Total files analyzed: {len([f for f in python_files if os.path.exists(f)])}\n")
        f.write(f"Total issues found: {total_issues}\n")
        f.write(f"Average score: {sum(file_scores.values()) / len(file_scores):.2f}/10.00\n\n")

        f.write("FILE SCORES:\n")
        for file, score in sorted(file_scores.items(), key=lambda x: x[1], reverse=True):
            f.write(f"  {file}: {score:.2f}/10.00\n")

    print(f"\nFinal analysis complete!")
    print(f"Results saved to: {output_file}")
    print(f"Total issues found: {total_issues}")
    print(f"Average score: {sum(file_scores.values()) / len(file_scores):.2f}/10.00")

    return output_file


def extract_score(pylint_output):
    """Extract pylint score from output"""
    score_pattern = r"Your code has been rated at ([\d\.-]+)/10"
    match = re.search(score_pattern, pylint_output)
    if match:
        return float(match.group(1))
    return 0.0


def count_issues(pylint_output):
    """Count number of issues in pylint output"""
    # Count lines that look like pylint issues
    issue_lines = [
        line
        for line in pylint_output.split("\n")
        if ":" in line and any(code in line for code in ["C0", "W0", "R0", "E0", "F0"])
    ]
    return len(issue_lines)


if __name__ == "__main__":
    print("Starting comprehensive pylint analysis...")
    result_file = run_pylint_comprehensive()
    print(f"Analysis complete. Check {result_file} for results.")
