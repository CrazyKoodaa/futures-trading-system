@echo off
echo Activating virtual environment...
call .\venv\Scripts\activate

echo Running pylint on Python files...
echo.

echo === PYLINT RESULTS === > pylint_results.txt
echo Generated on %date% %time% >> pylint_results.txt
echo. >> pylint_results.txt

for %%f in (*.py) do (
    echo Checking %%f...
    echo === PYLINT for %%f === >> pylint_results.txt
    pylint "%%f" >> pylint_results.txt 2>&1
    echo. >> pylint_results.txt
    echo ----------------------------------------- >> pylint_results.txt
    echo. >> pylint_results.txt
)

echo.
echo Pylint results saved to pylint_results.txt
echo.
type pylint_results.txt
pause
