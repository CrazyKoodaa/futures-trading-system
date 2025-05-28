@echo off
echo Starting Rithmic Admin Tool (Quick Start Version)...
cd /d "%~dp0"
call venv\Scripts\activate.bat
python layer1_development\scripts\rithmic_admin\quick_start.py
pause