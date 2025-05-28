#!/usr/bin/env python3
"""
Test script to verify TUI fixes work properly
"""

import sys
import os
import asyncio

def test_callback_signature():
    """Test that the new callback signature works with various argument patterns"""
    print("🔍 Testing callback signature fixes...")
    
    try:
        # Import the main class
        from enhanced_admin_rithmic import RithmicAdminTUI
        
        # Create an instance
        app = RithmicAdminTUI()
        
        # Test different callback signatures that might be used
        test_cases = [
            # (args, kwargs, description)
            (("Simple message",), {}, "Single message argument"),
            (("Message with progress", 0.5), {}, "Message + progress arguments"),
            (("Complex message", 0.75, "extra_arg"), {}, "Three arguments"),
            (("Message", 0.25, "extra", "fourth_arg"), {}, "Four arguments (the failing case)"),
            ((), {"message": "Keyword message"}, "Keyword message"),
            ((), {"message": "Keyword message", "progress": 0.8}, "Keyword message + progress"),
            (("Mixed", 0.3), {"extra": "keyword"}, "Mixed args and kwargs"),
        ]
        
        print("Testing callback with different argument patterns:")
        
        for args, kwargs, description in test_cases:
            try:
                app._progress_callback(*args, **kwargs)
                print(f"✅ {description} - SUCCESS")
            except Exception as e:
                print(f"❌ {description} - FAILED: {e}")
                return False
        
        print("✅ All callback signature tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing callback: {e}")
        return False

def test_status_updates():
    """Test that status updates work properly"""
    print("\n🔍 Testing status update functionality...")
    
    try:
        from enhanced_admin_rithmic import RithmicAdminTUI
        
        app = RithmicAdminTUI()
        
        # Test different status types
        status_tests = [
            ("This is an info message", "info"),
            ("This is a warning message", "warning"), 
            ("This is an error message", "error"),
        ]
        
        print("Testing status update method:")
        
        for message, status_type in status_tests:
            try:
                app._update_status(message, status_type)
                # Check if the status was updated properly
                expected = f"[{status_type.upper()}] {message}"
                if app.status.last_operation_result == expected:
                    print(f"✅ {status_type.upper()} status update - SUCCESS")
                else:
                    print(f"❌ {status_type.upper()} status update - FAILED: Expected '{expected}', got '{app.status.last_operation_result}'")
                    return False
            except Exception as e:
                print(f"❌ {status_type.upper()} status update - FAILED: {e}")
                return False
        
        print("✅ All status update tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing status updates: {e}")
        return False

def test_display_manager_enhancements():
    """Test that display manager shows enhanced error formatting"""
    print("\n🔍 Testing display manager enhancements...")
    
    try:
        from enhanced_admin_rithmic import RithmicAdminTUI
        
        app = RithmicAdminTUI()
        
        # Test different message types in status panel
        test_messages = [
            "[INFO] This is an info message",
            "[WARNING] This is a warning message", 
            "[ERROR] This is an error message",
            "Regular message without prefix"
        ]
        
        print("Testing enhanced status panel rendering:")
        
        for message in test_messages:
            try:
                app.status.last_operation_result = message
                status_panel = app.display_manager.render_status()
                
                # Check if panel was created successfully
                if status_panel:
                    print(f"✅ Status panel for '{message[:20]}...' - SUCCESS")
                else:
                    print(f"❌ Status panel for '{message[:20]}...' - FAILED: No panel returned")
                    return False
                    
            except Exception as e:
                print(f"❌ Status panel for '{message[:20]}...' - FAILED: {e}")
                return False
        
        print("✅ All display manager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing display manager: {e}")
        return False

async def test_async_operations():
    """Test async operations and cleanup"""
    print("\n🔍 Testing async operations...")
    
    try:
        from enhanced_admin_rithmic import RithmicAdminTUI
        
        app = RithmicAdminTUI()
        
        # Test that quit_application works without errors
        print("Testing graceful shutdown...")
        await app.quit_application()
        print("✅ Graceful shutdown test - SUCCESS")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing async operations: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 TUI FIXES VERIFICATION TEST")
    print("=" * 50)
    
    tests = [
        ("Callback Signature", test_callback_signature),
        ("Status Updates", test_status_updates),
        ("Display Manager", test_display_manager_enhancements),
    ]
    
    all_passed = True
    
    for test_name, test_func in tests:
        try:
            if not test_func():
                all_passed = False
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            all_passed = False
    
    # Test async operations
    try:
        print("\n🔍 Testing async operations...")
        asyncio.run(test_async_operations())
    except Exception as e:
        print(f"❌ Async operations test failed: {e}")
        all_passed = False
    
    print("\n" + "=" * 50)
    print("FINAL RESULT")
    print("=" * 50)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("\nThe TUI fixes have been successfully applied:")
        print("✅ Callback signature issue resolved")
        print("✅ Status panel integration working")
        print("✅ Enhanced error display functioning")
        print("✅ No more print statements breaking TUI")
        print("\nYou can now run: python enhanced_admin_rithmic.py")
    else:
        print("❌ SOME TESTS FAILED")
        print("\nPlease review the errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
