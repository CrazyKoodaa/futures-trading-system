#!/usr/bin/env python3
"""
Runner script for focused code analysis
"""

import subprocess
import sys
import os
from pathlib import Path


def main():
    """Run the focused analysis"""
    # Get paths
    backend_dir = Path(__file__).parent.parent
    root_dir = backend_dir.parent.parent
    venv_dir = root_dir / "venv"

    # Determine Python executable
    if os.name == "nt":  # Windows
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:  # Linux/Mac
        python_exe = venv_dir / "bin" / "python"

    if not python_exe.exists():
        print(f"❌ Virtual environment Python not found: {python_exe}")
        print("Using system Python as fallback")
        python_exe = sys.executable

    # Get analysis script
    analysis_script = (
        backend_dir / "scripts" / "focused_analysis_2025-05-28T11-41-52.py"
    )

    if not analysis_script.exists():
        print(f"❌ Analysis script not found: {analysis_script}")
        return 1

    print("🚀 Running Focused Code Analysis")
    print("=" * 40)
    print(f"Python: {python_exe}")
    print(f"Script: {analysis_script}")
    print(f"Working Directory: {backend_dir}")

    # Change to backend directory
    os.chdir(backend_dir)

    # Run the analysis
    try:
        result = subprocess.run([str(python_exe), str(analysis_script)], check=False)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running analysis: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
