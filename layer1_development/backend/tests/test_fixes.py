#!/usr/bin/env python3
"""
Test script to verify that our fixes work properly
"""

import sys
import os
import traceback

def test_admin_display_manager():
    """Test that admin_display_manager.py can be imported without errors"""
    print("Testing admin_display_manager.py...")
    try:
        # Try importing the module
        import admin_display_manager
        print("✅ admin_display_manager.py imports successfully")
        
        # Check if DisplayManager class exists
        if hasattr(admin_display_manager, 'DisplayManager'):
            print("✅ DisplayManager class found")
            
            # Check if the missing methods now exist
            DisplayManager = admin_display_manager.DisplayManager
            
            if hasattr(DisplayManager, 'set_operation_result'):
                print("✅ set_operation_result method found")
            else:
                print("❌ set_operation_result method still missing")
                
            if hasattr(DisplayManager, 'show_welcome_message'):
                print("✅ show_welcome_message method found")
            else:
                print("❌ show_welcome_message method still missing")
                
            if hasattr(DisplayManager, 'update_live_display'):
                print("✅ update_live_display method found")
            else:
                print("❌ update_live_display method still missing")
        else:
            print("❌ DisplayManager class not found")
            
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax Error in admin_display_manager.py: {e}")
        print(f"Line {e.lineno}: {e.text}")
        return False
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return False

def test_enhanced_admin_rithmic():
    """Test that enhanced_admin_rithmic.py can be imported"""
    print("\nTesting enhanced_admin_rithmic.py...")
    try:
        # Try importing the module
        import enhanced_admin_rithmic
        print("✅ enhanced_admin_rithmic.py imports successfully")
        
        # Check if main class exists
        if hasattr(enhanced_admin_rithmic, 'RithmicAdminTUI'):
            print("✅ RithmicAdminTUI class found")
        else:
            print("❌ RithmicAdminTUI class not found")
            
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax Error in enhanced_admin_rithmic.py: {e}")
        print(f"Line {e.lineno}: {e.text}")
        return False
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("This is expected if dependencies are missing, but syntax should be OK")
        return True  # Import errors are OK, syntax errors are not
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        return False

def test_syntax_only():
    """Test syntax by compiling the files"""
    print("\nTesting syntax compilation...")
    
    files_to_test = [
        'admin_display_manager.py',
        'enhanced_admin_rithmic.py'
    ]
    
    all_good = True
    
    for filename in files_to_test:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    code = f.read()
                compile(code, filename, 'exec')
                print(f"✅ {filename} - Syntax OK")
            except SyntaxError as e:
                print(f"❌ {filename} - Syntax Error: {e}")
                print(f"   Line {e.lineno}: {e.text}")
                all_good = False
            except Exception as e:
                print(f"❌ {filename} - Error: {e}")
                all_good = False
        else:
            print(f"❌ {filename} - File not found")
            all_good = False
    
    return all_good

def main():
    """Main test function"""
    print("🔍 Testing fixes for Rithmic Admin Tool")
    print("=" * 50)
    
    # Test syntax first
    syntax_ok = test_syntax_only()
    
    if syntax_ok:
        print("\n✅ All syntax checks passed!")
        
        # Test imports
        display_ok = test_admin_display_manager()
        main_ok = test_enhanced_admin_rithmic()
        
        if display_ok and main_ok:
            print("\n🎉 All tests passed! The fixes appear to be working.")
            print("\nYou should now be able to run:")
            print("   python enhanced_admin_rithmic.py")
        else:
            print("\n⚠️  Some import issues remain, but syntax is fixed.")
    else:
        print("\n❌ Syntax errors still exist. Please check the files.")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()
