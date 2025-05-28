#!/usr/bin/env python3
"""
Comprehensive TUI Diagnostic Script
Tests all panels, keyboard navigation, and identifies live TUI issues
"""

import sys
import os
import asyncio
import traceback
from datetime import datetime

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


class TUIDiagnostics:
    """Comprehensive TUI testing and diagnostics"""

    def __init__(self):
        self.results = []
        self.errors = []
        self.warnings = []

    def log_result(
        self, test_name: str, status: str, message: str = "", details: str = ""
    ):
        """Log a test result"""
        result = {
            "test": test_name,
            "status": status,  # "PASS", "FAIL", "WARN"
            "message": message,
            "details": details,
            "timestamp": datetime.now().strftime("%H:%M:%S"),
        }
        self.results.append(result)

        # Also categorize
        if status == "FAIL":
            self.errors.append(f"{test_name}: {message}")
        elif status == "WARN":
            self.warnings.append(f"{test_name}: {message}")

    def test_imports(self):
        """Test all required module imports"""
        print("🔍 Testing Module Imports...")

        try:
            from enhanced_admin_rithmic import RithmicAdminTUI

            self.log_result(
                "Main TUI Import", "PASS", "Successfully imported RithmicAdminTUI"
            )
        except Exception as e:
            self.log_result(
                "Main TUI Import",
                "FAIL",
                f"Failed to import: {str(e)}",
                traceback.format_exc(),
            )
            return False

        # Test admin module imports
        admin_modules = [
            "admin_core_classes",
            "admin_display_manager",
            "admin_rithmic_connection",
            "admin_rithmic_symbols",
            "admin_rithmic_historical",
            "admin_rithmic_operations",
            "admin_database",
        ]

        for module in admin_modules:
            try:
                __import__(module)
                self.log_result(f"Import {module}", "PASS", "Successfully imported")
            except Exception as e:
                self.log_result(f"Import {module}", "FAIL", f"Import failed: {str(e)}")

        return True

    def test_tui_initialization(self):
        """Test TUI application initialization"""
        print("🔍 Testing TUI Initialization...")

        try:
            from enhanced_admin_rithmic import RithmicAdminTUI

            app = RithmicAdminTUI()

            # Test basic properties
            self.log_result("TUI Creation", "PASS", "TUI object created successfully")

            # Test keyboard handler setup
            if hasattr(app, "keyboard_handler"):
                self.log_result(
                    "Keyboard Handler", "PASS", f"Handler type: {app.keyboard_handler}"
                )
            else:
                self.log_result(
                    "Keyboard Handler", "FAIL", "No keyboard_handler attribute"
                )

            # Test display manager
            if hasattr(app, "display_manager"):
                self.log_result(
                    "Display Manager", "PASS", "Display manager initialized"
                )
            else:
                self.log_result(
                    "Display Manager", "FAIL", "No display_manager attribute"
                )

            return app

        except Exception as e:
            self.log_result(
                "TUI Initialization",
                "FAIL",
                f"Initialization failed: {str(e)}",
                traceback.format_exc(),
            )
            return None

    def test_display_panels(self, app):
        """Test all display panel rendering"""
        print("🔍 Testing Display Panel Rendering...")

        if not app or not hasattr(app, "display_manager"):
            self.log_result("Panel Testing", "FAIL", "No display manager available")
            return

        display_manager = app.display_manager

        # Test individual panel methods
        panel_tests = [
            ("Header Panel", "render_header"),
            ("Menu Panel", "render_menu"),
            ("Content Panel", "render_content"),
            ("Results Panel", "render_results"),
            ("Status Panel", "render_status"),
        ]

        for panel_name, method_name in panel_tests:
            try:
                if hasattr(display_manager, method_name):
                    method = getattr(display_manager, method_name)
                    if method_name == "render_menu":
                        panel = method(0)  # Pass selected index
                    else:
                        panel = method()

                    if panel:
                        self.log_result(
                            panel_name, "PASS", "Panel rendered successfully"
                        )

                        # Check if panel uses Live (TUI live)
                        if hasattr(panel, "__class__") and "Panel" in str(
                            panel.__class__
                        ):
                            self.log_result(
                                f"{panel_name} Live Check",
                                "PASS",
                                "Uses Rich Panel (compatible with Live)",
                            )
                    else:
                        self.log_result(
                            panel_name, "FAIL", "Panel method returned None"
                        )
                else:
                    self.log_result(
                        panel_name, "FAIL", f"Method {method_name} not found"
                    )

            except Exception as e:
                self.log_result(
                    panel_name,
                    "FAIL",
                    f"Panel rendering failed: {str(e)}",
                    traceback.format_exc(),
                )

    def test_layout_rendering(self, app):
        """est complete layout rendering"""
        print("🔍 Testing Layout Rendering...")

        if not app or not hasattr(app, "display_manager"):
            self.log_result("Layout Test", "FAIL", "No display manager available")
            return

        try:
            layout = app.display_manager.render_layout(0)
            if layout:
                self.log_result(
                    "Complete Layout", "PASS", "Layout rendered successfully"
                )

                # Check if it's a Rich Layout (compatible with Live)
                if hasattr(layout, "__class__") and "Layout" in str(layout.__class__):
                    self.log_result(
                        "Layout Live Compatibility",
                        "PASS",
                        "Uses Rich Layout (Live compatible)",
                    )
                else:
                    self.log_result(
                        "Layout Live Compatibility",
                        "WARN",
                        f"Unknown layout type: {type(layout)}",
                    )
            else:
                self.log_result(
                    "Complete Layout", "FAIL", "Layout rendering returned None"
                )

        except Exception as e:
            self.log_result(
                "Complete Layout",
                "FAIL",
                f"Layout rendering failed: {str(e)}",
                traceback.format_exc(),
            )

    def test_live_display(self, app):
        """Test Live display functionality"""
        print("🔍 Testing Live Display...")

        if not app or not hasattr(app, "display_manager"):
            self.log_result("Live Display Test", "FAIL", "No display manager available")
            return

        try:
            # Test start_live_display
            if hasattr(app.display_manager, "start_live_display"):
                app.display_manager.start_live_display()
                self.log_result("Start Live Display", "PASS", "Live display started")

                # Test update_live_display
                if hasattr(app.display_manager, "update_live_display"):
                    app.display_manager.update_live_display(0)
                    self.log_result(
                        "Update Live Display", "PASS", "Live display updated"
                    )
                else:
                    self.log_result(
                        "Update Live Display",
                        "FAIL",
                        "update_live_display method missing",
                    )

                # Test stop_live_display
                if hasattr(app.display_manager, "stop_live_display"):
                    app.display_manager.stop_live_display()
                    self.log_result("Stop Live Display", "PASS", "Live display stopped")
                else:
                    self.log_result(
                        "Stop Live Display", "FAIL", "stop_live_display method missing"
                    )

            else:
                self.log_result(
                    "Live Display Methods", "FAIL", "start_live_display method missing"
                )

        except Exception as e:
            self.log_result(
                "Live Display Test",
                "FAIL",
                f"Live display test failed: {str(e)}",
                traceback.format_exc(),
            )

    def test_keyboard_navigation(self, app):
        """Test keyboard navigation functionality"""
        print("🔍 Testing Keyboard Navigation...")

        if not app:
            self.log_result("Keyboard Test", "FAIL", "No app available")
            return

        try:
            # Test get_key_input method
            if hasattr(app, "get_key_input"):
                result = app.get_key_input()  # Should return None if no input
                self.log_result(
                    "Key Input Method", "PASS", f"Method exists, returned: {result}"
                )
            else:
                self.log_result(
                    "Key Input Method", "FAIL", "get_key_input method missing"
                )

            # Test process_key method
            if hasattr(app, "process_key"):
                self.log_result(
                    "Process Key Method", "PASS", "process_key method exists"
                )
            else:
                self.log_result(
                    "Process Key Method", "FAIL", "process_key method missing"
                )

            # Test keyboard handler setup
            keyboard_handler = getattr(app, "keyboard_handler", None)
            if keyboard_handler:
                self.log_result(
                    "Keyboard Handler Setup", "PASS", f"Handler: {keyboard_handler}"
                )
            else:
                self.log_result(
                    "Keyboard Handler Setup", "WARN", "No keyboard handler detected"
                )

        except Exception as e:
            self.log_result(
                "Keyboard Navigation",
                "FAIL",
                f"Keyboard test failed: {str(e)}",
                traceback.format_exc(),
            )

    async def test_async_operations(self, app):
        """Test async operation handling"""
        print("🔍 Testing Async Operations...")

        if not app:
            self.log_result("Async Test", "FAIL", "No app available")
            return

        try:
            # Test process_key async method
            if hasattr(app, "process_key"):
                await app.process_key("k")  # Simulate up key
                self.log_result(
                    "Async Key Processing", "PASS", "process_key handled async call"
                )
            else:
                self.log_result(
                    "Async Key Processing", "FAIL", "process_key method missing"
                )

        except Exception as e:
            self.log_result(
                "Async Operations",
                "FAIL",
                f"Async test failed: {str(e)}",
                traceback.format_exc(),
            )

    def generate_report(self):
        """Generate comprehensive diagnostic report"""
        print("\n" + "=" * 60)
        print("🚀 TUI COMPREHENSIVE DIAGNOSTIC REPORT")
        print("=" * 60)
        print(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Total tests run: {len(self.results)}")

        # Count results
        passed = len([r for r in self.results if r["status"] == "PASS"])
        failed = len([r for r in self.results if r["status"] == "FAIL"])
        warnings = len([r for r in self.results if r["status"] == "WARN"])

        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Warnings: {warnings}")

        if failed > 0:
            print("\n🔴 CRITICAL FAILURES:")
            for error in self.errors:
                print(f"  • {error}")

        if warnings > 0:
            print("\n🟡 WARNINGS:")
            for warning in self.warnings:
                print(f"  • {warning}")

        print("\n📋 DETAILED RESULTS:")
        print("-" * 60)
        for result in self.results:
            status_icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}[result["status"]]
            print(
                f"{status_icon} [{result['timestamp']}] {result['test']}: {result['message']}"
            )

        # TUI Live Analysis
        print("\n🖥️  TUI LIVE ANALYSIS:")
        print("-" * 30)
        live_compatible_panels = [
            r for r in self.results if "Live" in r["test"] and r["status"] == "PASS"
        ]
        if live_compatible_panels:
            print("✅ All panels appear to be Live TUI compatible")
            for panel in live_compatible_panels:
                print(f"  • {panel['test']}")
        else:
            print("❌ Live TUI compatibility issues detected")

        # Keyboard Navigation Analysis
        print("\n⌨️  KEYBOARD NAVIGATION ANALYSIS:")
        print("-" * 40)
        keyboard_tests = [
            r for r in self.results if "Key" in r["test"] or "Keyboard" in r["test"]
        ]
        keyboard_issues = [r for r in keyboard_tests if r["status"] != "PASS"]

        if not keyboard_issues:
            print("✅ Keyboard navigation should work properly")
        else:
            print("❌ Keyboard navigation issues detected:")
            for issue in keyboard_issues:
                print(f"  • {issue['test']}: {issue['message']}")

        return failed == 0


async def main():
    """Run comprehensive diagnostics"""
    diagnostics = TUIDiagnostics()

    # Run all tests
    if not diagnostics.test_imports():
        print("❌ Cannot proceed - critical import failures")
        return False

    app = diagnostics.test_tui_initialization()
    diagnostics.test_display_panels(app)
    diagnostics.test_layout_rendering(app)
    diagnostics.test_live_display(app)
    diagnostics.test_keyboard_navigation(app)

    # Run async tests
    await diagnostics.test_async_operations(app)

    # Generate report
    success = diagnostics.generate_report()

    if success:
        print("\n🎉 ALL TESTS PASSED! TUI should work correctly.")
        print("\nTo run the application:")
        print("  python enhanced_admin_rithmic.py")
    else:
        print("\n🔧 ISSUES FOUND - Review the failures above")

    return success


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal diagnostic error: {e}")
        traceback.print_exc()
        sys.exit(1)
