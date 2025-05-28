#!/usr/bin/env python3
"""
Run pylint analysis on enhanced_admin_rithmic.py and capture issues
"""

import subprocess
import sys
import os
from datetime import datetime

def run_pylint_analysis():
    """Run pylint on the main TUI file and save results"""
    
    # Get current timestamp
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output_file = f"pylint_output-{timestamp}.txt"
    
    print(f"🔍 Running pylint analysis on enhanced_admin_rithmic.py...")
    print(f"📄 Output will be saved to: {output_file}")
    
    try:
        # Run pylint on the main file
        result = subprocess.run([
            sys.executable, "-m", "pylint", 
            "enhanced_admin_rithmic.py",
            "--output-format=text",
            "--reports=yes",
            "--score=yes"
        ], capture_output=True, text=True, timeout=60)
        
        # Prepare output content
        output_content = f"PYLINT ANALYSIS RESULTS\n"
        output_content += f"=" * 50 + "\n"
        output_content += f"File: enhanced_admin_rithmic.py\n"
        output_content += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        output_content += f"Return Code: {result.returncode}\n"
        output_content += f"=" * 50 + "\n\n"
        
        if result.stdout:
            output_content += "PYLINT OUTPUT:\n"
            output_content += "-" * 30 + "\n"
            output_content += result.stdout + "\n\n"
        
        if result.stderr:
            output_content += "PYLINT ERRORS:\n"
            output_content += "-" * 30 + "\n"
            output_content += result.stderr + "\n\n"
        
        # Write to file
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(output_content)
        
        print(f"✅ Pylint analysis completed")
        print(f"📋 Results saved to: {output_file}")
        
        # Show summary
        if result.returncode == 0:
            print("🎉 No major pylint issues found!")
        else:
            print(f"⚠️  Pylint found issues (return code: {result.returncode})")
            
        return output_file, result.returncode
        
    except subprocess.TimeoutExpired:
        print("❌ Pylint analysis timed out")
        return None, -1
    except Exception as e:
        print(f"❌ Error running pylint: {e}")
        return None, -1

if __name__ == "__main__":
    output_file, return_code = run_pylint_analysis()
    
    if output_file:
        print(f"\n📖 To view results, check: {output_file}")
        print("\nNext steps:")
        print("1. Review the pylint output file")
        print("2. Fix any critical issues found")
        print("3. Test the TUI application")
    
    sys.exit(0 if return_code == 0 else 1)
