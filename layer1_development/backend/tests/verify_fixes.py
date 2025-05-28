#!/usr/bin/env python3
"""Quick verification of fixes"""
import sys
import os
import ast

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

print("Testing imports and critical fixes...")
errors = []
successes = []

# 1. Test DisplayManager methods
try:
    with open('../src/admin_display_manager.py', 'r') as f:
        content = f.read()
    
    if 'def set_operation_result' in content:
        successes.append("✅ set_operation_result method exists")
    else:
        errors.append("❌ set_operation_result method missing")
        
    if 'def show_welcome_message' in content:
        successes.append("✅ show_welcome_message method exists")
    else:
        errors.append("❌ show_welcome_message method missing")
        
    if 'def update_live_display' in content:
        successes.append("✅ update_live_display method exists")
    else:
        errors.append("❌ update_live_display method missing")
except Exception as e:
    errors.append(f"❌ Error reading admin_display_manager.py: {e}")

# 2. Test RithmicHistoricalManager fix
try:
    with open('../src/enhanced_admin_rithmic.py', 'r') as f:
        content = f.read()
    
    if 'RithmicHistoricalManager(\n            self.connection_manager, self.database_ops, self._progress_callback\n        )' in content:
        successes.append("✅ RithmicHistoricalManager initialized with 3 parameters")
    else:
        errors.append("❌ RithmicHistoricalManager initialization not fixed")
except Exception as e:
    errors.append(f"❌ Error checking RithmicHistoricalManager: {e}")

# 3. Test bulk_insert_market_data
try:
    with open('../src/admin_database.py', 'r') as f:
        content = f.read()
    
    if 'async def bulk_insert_market_data' in content:
        successes.append("✅ bulk_insert_market_data method exists")
    else:
        errors.append("❌ bulk_insert_market_data method missing")
except Exception as e:
    errors.append(f"❌ Error checking bulk_insert_market_data: {e}")

# 4. Test traceback imports
try:
    with open('../src/admin_rithmic_historical.py', 'r') as f:
        content = f.read()
    
    if 'import traceback' in content:
        successes.append("✅ traceback imported in admin_rithmic_historical.py")
    else:
        errors.append("❌ traceback import missing in admin_rithmic_historical.py")
except Exception as e:
    errors.append(f"❌ Error checking traceback import: {e}")

# 5. Test syntax of all main files
files_to_check = [
    '../src/enhanced_admin_rithmic.py',
    '../src/admin_display_manager.py',
    '../src/admin_database.py',
    '../src/admin_rithmic_historical.py'
]

for file in files_to_check:
    try:
        with open(file, 'r') as f:
            ast.parse(f.read())
        successes.append(f"✅ {os.path.basename(file)} - Valid syntax")
    except SyntaxError as e:
        errors.append(f"❌ {os.path.basename(file)} - Syntax error: {e}")
    except Exception as e:
        errors.append(f"❌ {os.path.basename(file)} - Error: {e}")

# Print results
print("\n" + "="*50)
print("VERIFICATION RESULTS")
print("="*50)

print("\nSuccesses:")
for s in successes:
    print(s)

if errors:
    print("\nErrors:")
    for e in errors:
        print(e)
    print("\n❌ Some issues remain")
else:
    print("\n✅ ALL CHECKS PASSED!")
    print("\nThe backend should now be ready to run.")
    print("To start the admin tool:")
    print("  1. Activate venv: ..\\..\\venv\\Scripts\\activate")
    print("  2. Run: python src\\enhanced_admin_rithmic.py")
