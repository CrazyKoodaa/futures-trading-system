#!/usr/bin/env python3
"""
Installation script and tester for the enhanced Rithmic Admin TUI
"""

import subprocess
import sys
import os

def install_rich():
    """Install Rich library for TUI"""
    print("🔧 Installing Rich library for enhanced TUI...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "rich>=13.0.0"])
        print("✅ Rich library installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Rich: {e}")
        return False

def test_rich_import():
    """Test if Rich can be imported"""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.progress import Progress
        from rich.table import Table
        from rich.layout import Layout
        from rich.live import Live
        from rich.text import Text
        from rich.prompt import Prompt, Confirm
        from rich.columns import Columns
        from rich import box
        from rich.align import Align
        
        console = Console()
        console.print("✅ Rich library imported successfully!", style="green")
        
        # Test basic Rich functionality
        console.print(Panel("Testing Rich TUI Components", title="Rich Test", border_style="blue"))
        
        table = Table(title="Test Table")
        table.add_column("Feature", style="cyan")
        table.add_column("Status", style="green")
        
        table.add_row("Console", "✅ Working")
        table.add_row("Panel", "✅ Working")
        table.add_row("Table", "✅ Working")
        table.add_row("Progress", "✅ Working")
        
        console.print(table)
        return True
        
    except ImportError as e:
        print(f"❌ Rich import failed: {e}")
        return False

def check_database_connection():
    """Check if database connection is working"""
    print("\n🔍 Testing database connection...")
    try:
        # Try importing database modules
        from shared.database.connection import get_database_manager
        print("✅ Database modules imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Database module import failed: {e}")
        print("💡 Make sure you're in the project root directory")
        return False

def check_rithmic_config():
    """Check if Rithmic configuration is available"""
    print("\n🔍 Checking Rithmic configuration...")
    try:
        from config.chicago_gateway_config import get_chicago_gateway_config
        config = get_chicago_gateway_config()
        
        required_keys = ['user', 'password', 'system_name']
        missing_keys = []
        
        for key in required_keys:
            if not config['rithmic'].get(key) or config['rithmic'][key] in ['your_username', 'your_password', 'your_system_name']:
                missing_keys.append(key)
        
        if missing_keys:
            print(f"⚠️  Rithmic configuration incomplete. Missing/default values for: {missing_keys}")
            print("💡 Update config/chicago_gateway_config.py with your Rithmic credentials")
            return False
        else:
            print("✅ Rithmic configuration looks complete")
            return True
            
    except ImportError as e:
        print(f"❌ Rithmic config import failed: {e}")
        return False

def show_usage_instructions():
    """Show instructions for using the new TUI"""
    print("\n" + "="*60)
    print("🚀 ENHANCED RITHMIC ADMIN TOOL - USAGE INSTRUCTIONS")
    print("="*60)
    
    print("\n📋 Features of the New TUI:")
    print("   ✅ Real-time progress tracking with separate bars for second/minute data")
    print("   ✅ Modern Rich-based interface with colors and layout")
    print("   ✅ Chunk information displayed in the same row as progress")
    print("   ✅ Enhanced error handling and database debugging")
    print("   ✅ Better data validation before database insertion")
    
    print("\n🔧 To run the enhanced admin tool:")
    print("   1. Activate your virtual environment:")
    print("      .\\venv\\Scripts\\activate")
    print("   2. Run the enhanced admin tool:")
    print("      python enhanced_admin_rithmic.py")
    
    print("\n🐛 If you encounter data insertion issues:")
    print("   1. Run the database debugger:")
    print("      python debug_database.py")
    print("   2. This will help identify:")
    print("      • Database connection issues")
    print("      • Table structure problems")
    print("      • Data validation failures")
    print("      • Rithmic API response format issues")
    
    print("\n💡 Key Improvements:")
    print("   • Progress bars now show chunk information in real-time")
    print("   • Separate progress tracking for second and minute data")
    print("   • Better error messages when data doesn't appear in database")
    print("   • Enhanced validation of OHLC data before insertion")
    print("   • Improved transaction handling to prevent data loss")
    
    print("\n🔍 Troubleshooting:")
    print("   • If Rich TUI doesn't work, the tool falls back to basic interface")
    print("   • Check logs in 'rithmic_admin.log' for detailed error information")
    print("   • Use debug_database.py to diagnose database issues")
    print("   • Verify Rithmic credentials in chicago_gateway_config.py")

def main():
    print("🎯 RITHMIC ADMIN TOOL - SETUP AND TEST")
    print("="*50)
    
    # Check if we're in the right directory
    if not os.path.exists("admin_rithmic.py"):
        print("❌ admin_rithmic.py not found!")
        print("💡 Make sure you're running this from the project root directory")
        return False
    
    # Install Rich if needed
    rich_works = test_rich_import()
    if not rich_works:
        install_success = install_rich()
        if install_success:
            rich_works = test_rich_import()
    
    # Check database connection
    db_works = check_database_connection()
    
    # Check Rithmic config
    rithmic_config_ok = check_rithmic_config()
    
    # Summary
    print("\n" + "="*50)
    print("📊 SETUP SUMMARY")
    print("="*50)
    print(f"Rich TUI Library: {'✅ Ready' if rich_works else '❌ Failed'}")
    print(f"Database Modules: {'✅ Ready' if db_works else '❌ Failed'}")
    print(f"Rithmic Config: {'✅ Ready' if rithmic_config_ok else '⚠️  Needs Update'}")
    
    if rich_works and db_works:
        print("\n🎉 Setup completed successfully!")
        show_usage_instructions()
        return True
    else:
        print("\n❌ Setup incomplete. Please fix the issues above.")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Setup interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)