import sys
import traceback
from rich.console import Console

def test_display_manager():
    try:
        from layer1_development.enhanced_rithmic_admin.admin_core_classes import SystemStatus, TUIComponents
        from layer1_development.enhanced_rithmic_admin.admin_display_manager_fixed import DisplayManager
        
        print("Imports successful")
        
        console = Console()
        status = SystemStatus()
        tui_components = TUIComponents(status)
        
        print("Objects created")
        
        # Test initialization
        display_manager = DisplayManager(console, tui_components, status)
        
        print("DisplayManager initialized")
        
        # Test rendering
        layout = display_manager.render_layout()
        
        print("Layout rendered")
        print("DisplayManager test successful!")
    except Exception as e:
        print(f"Error: {e}")
        print(f"Type: {type(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    test_display_manager()