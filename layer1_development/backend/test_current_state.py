import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testing imports and functionality...")
errors = []

# Test imports
try:
    from src.admin_core_classes import SystemStatus
    print("✅ admin_core_classes imported")
except Exception as e:
    errors.append(f"❌ admin_core_classes: {e}")

try:
    from src.admin_database import DatabaseOperations
    print("✅ admin_database imported")
except Exception as e:
    errors.append(f"❌ admin_database: {e}")

try:
    from src.admin_rithmic_connection import RithmicConnectionManager
    print("✅ admin_rithmic_connection imported")
except Exception as e:
    errors.append(f"❌ admin_rithmic_connection: {e}")

try:
    from src.admin_rithmic_symbols import RithmicSymbolManager
    print("✅ admin_rithmic_symbols imported")
except Exception as e:
    errors.append(f"❌ admin_rithmic_symbols: {e}")

try:
    from src.admin_rithmic_historical import RithmicHistoricalManager
    print("✅ admin_rithmic_historical imported")
except Exception as e:
    errors.append(f"❌ admin_rithmic_historical: {e}")

try:
    from src.admin_display_manager import DisplayManager
    print("✅ admin_display_manager imported")
except Exception as e:
    errors.append(f"❌ admin_display_manager: {e}")

# Check for bulk_insert_market_data in DatabaseOperations
try:
    from src.admin_database import DatabaseOperations
    db_ops = DatabaseOperations()
    if hasattr(db_ops, 'bulk_insert_market_data'):
        print("✅ bulk_insert_market_data method exists")
    else:
        errors.append("❌ bulk_insert_market_data method missing")
except Exception as e:
    errors.append(f"❌ Error checking bulk_insert_market_data: {e}")

# Check RithmicHistoricalManager initialization
try:
    from src.admin_rithmic_connection import RithmicConnectionManager
    from src.admin_database import DatabaseOperations
    from src.admin_rithmic_historical import RithmicHistoricalManager
    
    conn_mgr = RithmicConnectionManager()
    db_ops = DatabaseOperations()
    hist_mgr = RithmicHistoricalManager(conn_mgr, db_ops, None)
    print("✅ RithmicHistoricalManager initialization works with 3 parameters")
except Exception as e:
    errors.append(f"❌ RithmicHistoricalManager initialization: {e}")

print("\n" + "="*50)
if errors:
    print("ERRORS FOUND:")
    for error in errors:
        print(error)
else:
    print("✅ ALL TESTS PASSED! The backend is ready.")
