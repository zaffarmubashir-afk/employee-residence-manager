"""
UAE Employee & Company Residence / Document Management System
================================================================
Entry point. Run with:  python main.py

The core app needs only the Python standard library (tkinter +
sqlite3), both of which ship with the standard Windows installer from
python.org.

Optional packages unlock extra features - see requirements-optional.txt
and README.md for details:
  - openpyxl                          Excel export on the Reports tab
  - pymupdf / pypdf                   read text-based PDFs for employee import
  - pymupdf + pillow + pytesseract    + OCR scanned PDFs/photos for import
    (pytesseract also needs the separate Tesseract-OCR program)

Your data lives in %APPDATA%\\EmployeeResidenceManager\\ (see
app/database.py), not in this folder, so it's safe across app
restarts, reinstalls, and rebuilding a packaged .exe.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import database as db
from app import backup as bk
from app.main_window import App


def main():
    db.init_db()
    app = App()
    app.dashboard_tab.refresh()
    app.companies_tab.refresh()
    app.employees_tab.refresh()

    def on_close():
        # Safety-net copy of the database, kept automatically every time
        # the app closes (rotated - see app/backup.py). Never blocks
        # closing even if it fails for some reason.
        try:
            bk.auto_backup()
        except Exception:
            pass
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)

    # Keep a rolling safety snapshot even if Windows/app is terminated
    # unexpectedly before the normal close handler runs.
    def periodic_backup():
        try:
            bk.auto_backup()
        except Exception:
            pass
        try:
            app.after(5 * 60 * 1000, periodic_backup)
        except Exception:
            pass

    app.after(5 * 60 * 1000, periodic_backup)
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal error", str(e))
        except Exception:
            print("Fatal error:", e)
        raise
