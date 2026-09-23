@echo off
REM Run this ON WINDOWS to build a standalone EmployeeResidenceManager.exe
REM Requires Python installed and available on PATH.

echo Installing PyInstaller (and optional Excel export support)...
pip install pyinstaller openpyxl

echo Building EmployeeResidenceManager.exe ...
pyinstaller --onefile --windowed --name "EmployeeResidenceManager" --add-data "data;data" main.py

echo.
echo Done. Find your .exe at: dist\EmployeeResidenceManager.exe
pause
