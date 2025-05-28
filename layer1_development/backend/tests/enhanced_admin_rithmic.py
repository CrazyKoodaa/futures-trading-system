"""
Import proxy for enhanced_admin_rithmic module.

This file allows tests to import the enhanced_admin_rithmic module directly.
"""

import sys
import os

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
src_dir = os.path.join(parent_dir, "src")
sys.path.insert(0, src_dir)

# Import the main module and re-export everything
from src.enhanced_admin_rithmic import *
