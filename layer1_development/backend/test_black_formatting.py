#!/usr/bin/env python3
"""
Test script to check Black formatting
"""

import subprocess
import sys
from pathlib import Path


def test_black_on_single_file():
    """Test Black formatting on a single problematic file"""
    
    # Path to a file that's having issues
    test_file = Path("fix_imports/fix_imports.py")
    
    if not test_file.exists():
        print(f"File not found: {test_file}")
        return False
    
    try:
        # Try to run Black on the file
        cmd = [sys.executable, "-m", "black", "--check", "--diff", str(test_file)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("Black command timed out")
        return False
    except Exception as e:
        print(f"Error running Black: {e}")
        return False


if __name__ == "__main__":
    test_black_on_single_file()
