#!/usr/bin/env python3
"""
Script to run pylint on enhanced_admin_rithmic.py and save output
"""

import subprocess
import sys
from datetime import datetime
import os


def run_pylint_check():
    """Run pylint and save output to file"""

    # Get current timestamp for filename
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_filename = f"pylint_output-{timestamp}.txt"

    # Target file to check
    target_file = "enhanced_admin_rithmic.py"

    try:
        print(f"Running pylint on {target_file}...")

        # Run pylint
        result = subprocess.run(
            [sys.executable, "-m", "pylint", target_file],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )

        # Combine stdout and stderr
        output = f"Pylint check for {target_file}\n"
        output += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        output += "=" * 60 + "\n\n"

        if result.stdout:
            output += "STDOUT:\n" + result.stdout + "\n\n"

        if result.stderr:
            output += "STDERR:\n" + result.stderr + "\n\n"

        output += f"Return code: {result.returncode}\n"

        # Save to file
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(output)

        print(f"Pylint output saved to: {output_filename}")
        print(f"Return code: {result.returncode}")

        # Also print summary to console
        if result.returncode == 0:
            print("✅ Pylint check passed with no issues!")
        else:
            print("⚠️ Pylint found some issues. Check the output file for details.")

        return result.returncode == 0

    except FileNotFoundError:
        error_msg = (
            "Error: pylint not found. Please install it with: pip install pylint"
        )
        print(error_msg)

        # Save error to file
        with open(output_filename, "w") as f:
            f.write(f"Error running pylint: {error_msg}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        return False

    except Exception as e:
        error_msg = f"Unexpected error running pylint: {str(e)}"
        print(error_msg)

        # Save error to file
        with open(output_filename, "w") as f:
            f.write(f"Error running pylint: {error_msg}\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        return False


if __name__ == "__main__":
    success = run_pylint_check()
    sys.exit(0 if success else 1)
