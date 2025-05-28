#!/usr/bin/env python3
"""
Simple TUI test to check keyboard navigation and identify issues
"""

import sys
import os
import asyncio
from datetime import datetime

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from enhanced_admin_rithmic import RithmicAdminTUI
        print("✅ Main TUI class imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_tui_initialization():
    """Test TUI initialization"""
    print("\n🔍 Testing TUI initialization...")
    
    try:
        from enhanced_admin_rithmic import RithmicAdminTUI
        app = RithmicAdminTUI()
        print("✅ TUI application initialized successfully")
        
        # Check keyboard handler setup
        print(f"  Keyboard handler: {app.keyboard_handler}")
        
        # Check if display manager is working
        if hasattr(app, 'display_manager'):
            print("✅ Display manager created")
        else:
            print("❌ Display manager missing")
            
        return True
    except Exception as e:
        print(f"❌ TUI initialization error: {e}")
        return False

def test_keyboard_input_method():
    """Test keyboard input handling methods"""
    print("\n🔍 Testing keyboard input methods...")
    
    try:
        from enhanced_admin_rithmic import RithmicAdminTUI
        app = RithmicAdminTUI()
        
        # Test get_key_input method
        if hasattr(app, 'get_key_input'):
            print("✅ get_key_input method exists")
            
            # Try calling it (should return None if no input)
            result = app.get_key_input()
            print(f"  get_key_input() returned: {result}")
        else:
            print("❌ get_key_input method missing")
            
        return True
    except Exception as e:
        print(f"❌ Keyboard input test error: {e}")
        return False

async def main():
    """Run all tests"""
    print("🚀 SIMPLE TUI DIAGNOSTIC TEST")
    print("=" * 50)
    print(f"Test run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
        print("\n❌ Cannot proceed - import failed")
        return False
    
    # Test initialization
    if not test_tui_initialization():
        all_passed = False
    
    # Test keyboard methods
    if not test_keyboard_input_method():
        all_passed = False
    
    print("\n" + "=" * 50)
    print("DIAGNOSTIC RESULTS")
    print("=" * 50)
    
    if all_passed:
        print("🎉 BASIC TESTS PASSED!")
        print("\nThe TUI can be initialized. Keyboard issues may be runtime-specific.")
        print("\nTo test full functionality, try running:")
        print("  python enhanced_admin_rithmic.py")
    else:
        print("❌ BASIC TESTS FAILED")
        print("\nThere are fundamental issues that need to be fixed.")
    
    return all_passed

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"Fatal test error: {e}")
        sys.exit(1)
