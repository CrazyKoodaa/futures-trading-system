@echo off
cd /d "C:\Users\nobody\myProjects\git\futures-trading-system"
call .\venv\Scripts\activate
cd layer1_development\enhanced_rithmic_admin
pylint admin_display_manager.py > pylint_output-2025-05-28T07-18-14.txt 2>&1
echo Pylint output saved to pylint_output-2025-05-28T07-18-14.txt
