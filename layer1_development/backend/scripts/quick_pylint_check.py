"""
Quick pylint analysis focused on the files we fixed
"""
import subprocess
import os
import sys

def run_targeted_pylint():
    """Run pylint on the specific files we modified"""
    
    files_to_check = [
        'admin_display_manager.py',
        'enhanced_admin_rithmic.py'
    ]
    
    print("🔍 Running targeted pylint analysis...")
    print("=" * 50)
    
    for py_file in files_to_check:
        if os.path.exists(py_file):
            print(f"\n📁 Analyzing {py_file}...")
            print("-" * 30)
            
            try:
                # Run pylint with focused output
                cmd = [
                    sys.executable, '-m', 'pylint', 
                    '--disable=C0103,C0114,C0115,C0116,R0903,R0913,W0613,C0301',  # Disable style warnings
                    '--enable=E,F',  # Focus on errors and fatal issues
                    '--output-format=text',
                    '--score=n',  # Don't show score
                    py_file
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                
                if result.returncode == 0:
                    print(f"✅ {py_file} - No errors found!")
                else:
                    print(f"⚠️  {py_file} - Issues found:")
                    if result.stdout.strip():
                        print(result.stdout)
                    if result.stderr.strip():
                        print("STDERR:", result.stderr)
                        
            except FileNotFoundError:
                print(f"❌ pylint not available. Install with: pip install pylint")
                return False
            except Exception as e:
                print(f"❌ Error running pylint on {py_file}: {e}")
        else:
            print(f"❌ File not found: {py_file}")
    
    print("\n" + "=" * 50)
    print("Analysis complete!")
    return True

if __name__ == "__main__":
    run_targeted_pylint()
