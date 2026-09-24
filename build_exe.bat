@echo off
REM Run this ON WINDOWS to build a standalone EmployeeResidenceManager.exe
REM Requires Python installed and available on PATH.

echo Installing PyInstaller and optional feature packages...
echo   (Excel export, PDF/photo employee import, OCR support)
pip install pyinstaller openpyxl pymupdf pillow pytesseract

echo.
echo NOTE: OCR of scanned documents/photos also needs the separate
echo Tesseract-OCR program (not a pip package). Get it from:
echo   https://github.com/UB-Mannheim/tesseract/wiki
echo Text-based PDF reading works fine without it.
echo.

echo Building EmployeeResidenceManager.exe ...
pyinstaller --onefile --windowed --name "EmployeeResidenceManager" main.py

echo.
echo Done. Find your .exe at: dist\EmployeeResidenceManager.exe
echo.
echo Your data is stored in %%APPDATA%%\EmployeeResidenceManager\ - not
echo next to the .exe - so it's safe across reinstalls and rebuilds.
pause
