#!/usr/bin/env python3
"""
Script to activate virtual environment and run comprehensive analysis
"""

import subprocess
import os
import sys
from pathlib import Path


def run_comprehensive_analysis():
    """Run the comprehensive analysis with virtual environment activated"""

    print("🚀 RUNNING COMPREHENSIVE CODE ANALYSIS")
    print("=" * 60)

    # Get paths
    root_dir = Path(__file__).parent.parent.parent
    backend_dir = Path(__file__).parent.parent
    venv_dir = root_dir / "venv"

    print(f"Root Directory: {root_dir}")
    print(f"Backend Directory: {backend_dir}")
    print(f"Virtual Environment: {venv_dir}")

    # Check if virtual environment exists
    if not venv_dir.exists():
        print("❌ Virtual environment not found!")
        return 1

    # Determine the Python executable in the virtual environment
    if os.name == "nt":  # Windows
        python_exe = venv_dir / "Scripts" / "python.exe"
        activate_script = venv_dir / "Scripts" / "activate"
    else:  # Linux/Mac
        python_exe = venv_dir / "bin" / "python"
        activate_script = venv_dir / "bin" / "activate"

    if not python_exe.exists():
        print(f"❌ Python executable not found at: {python_exe}")
        return 1

    print(f"✅ Using Python: {python_exe}")

    # Get the analysis script path
    analysis_script = (
        backend_dir / "scripts" / "comprehensive_analysis_2025-05-28T11-41-52.py"
    )

    if not analysis_script.exists():
        print(f"❌ Analysis script not found: {analysis_script}")
        return 1

    print(f"✅ Analysis script: {analysis_script}")

    # Change to backend directory
    os.chdir(backend_dir)
    print(f"✅ Changed directory to: {backend_dir}")

    # Run the comprehensive analysis using the virtual environment Python
    try:
        print("\n🔄 Running comprehensive analysis...")
        print("-" * 40)

        result = subprocess.run(
            [str(python_exe), str(analysis_script)],
            cwd=str(backend_dir),
            text=True,
            capture_output=False,  # Let output show in real-time
        )

        if result.returncode == 0:
            print("\n✅ COMPREHENSIVE ANALYSIS COMPLETED SUCCESSFULLY!")
        else:
            print(f"\n❌ Analysis completed with exit code: {result.returncode}")

        return result.returncode

    except Exception as e:
        print(f"\n❌ Error running analysis: {e}")
        return 1


if __name__ == "__main__":
    exit_code = run_comprehensive_analysis()
    sys.exit(exit_code)
