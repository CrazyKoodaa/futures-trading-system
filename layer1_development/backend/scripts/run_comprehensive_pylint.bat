@echo off
echo Activating virtual environment and running comprehensive pylint analysis...
echo.

REM Navigate to the project root to activate venv
cd /d "C:\Users\nobody\myProjects\git\futures-trading-system"

REM Activate virtual environment
call .\venv\Scripts\activate

REM Navigate back to the enhanced_rithmic_admin directory
cd "layer1_development\enhanced_rithmic_admin"

REM Run the comprehensive pylint analysis
python run_comprehensive_pylint.py

echo.
echo Pylint analysis complete!
pause
