@echo off
echo 🚀 Enhanced Rithmic Admin Tool - Connection Test Fixes
echo ========================================================
echo.

echo 📁 Navigating to enhanced_rithmic_admin directory...
cd /d "%~dp0.."

echo 🔧 Activating Python virtual environment...
call "..\..\venv\Scripts\activate.bat"

if errorlevel 1 (
    echo ❌ Failed to activate virtual environment
    echo 💡 Make sure the virtual environment exists at: ..\..\venv
    pause
    exit /b 1
)

echo ✅ Virtual environment activated
echo.

echo 📋 Choose an option:
echo   1. Run Enhanced Admin Tool
echo   2. Test Connection Display Improvements 
echo   3. Run Pylint Check
echo   4. Exit
echo.

set /p choice="Enter your choice (1-4): "

if "%choice%"=="1" (
    echo 🎮 Starting Enhanced Rithmic Admin Tool...
    echo 💡 Use Test Connections to see the improved results display!
    echo.
    python src\enhanced_admin_rithmic.py
) else if "%choice%"=="2" (
    echo 🧪 Testing connection display improvements...
    echo.
    python tests\test_enhanced_connection_display.py
) else if "%choice%"=="3" (
    echo 🔍 Running pylint check...
    echo.
    python scripts\run_pylint_check.py
) else if "%choice%"=="4" (
    echo 👋 Goodbye!
    exit /b 0
) else (
    echo ❌ Invalid choice. Please run the script again.
    pause
    exit /b 1
)

echo.
echo ✅ Operation completed!
pause
