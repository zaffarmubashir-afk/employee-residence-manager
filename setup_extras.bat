@echo off
title EmployeeResidenceManager - One-Time Setup
color 0B

echo ============================================================
echo   EmployeeResidenceManager - One-Time Setup
echo ============================================================
echo.
echo This installs the optional extras: Excel export, PDF reading,
echo and photo/scan text recognition (OCR).
echo.
echo You only need to run this ONCE. After this finishes, just
echo double-click the app as normal - no more command windows.
echo.
pause

echo.
echo [1/2] Installing Python packages (this may take a minute)...
echo.
pip install --upgrade openpyxl pymupdf pillow pytesseract pypdf pdf2image

echo.
echo ============================================================
echo [2/2] One more thing needed for reading SCANS and PHOTOS:
echo ============================================================
echo.
echo Text-based PDFs already work now. But reading a scanned page
echo or a photo of a document needs one more free program called
echo Tesseract-OCR (it is NOT a Python package, so pip can't install
echo it - it needs its own installer, just like any other program).
echo.
echo Opening the download page for you now...
echo.
echo   1. Click the top .exe link (e.g. tesseract-ocr-w64-...exe)
echo   2. Run the installer, click Next through the defaults
echo   3. Come back here and press any key to finish
echo.
start https://github.com/UB-Mannheim/tesseract/wiki
pause

echo.
echo ============================================================
echo   Setup complete! Close this window and open the app normally.
echo ============================================================
pause
