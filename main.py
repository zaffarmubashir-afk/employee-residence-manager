"""
UAE Employee & Company Residence / Document Management System
================================================================
Entry point. Run with:  python main.py

Requires only the Python standard library (tkinter + sqlite3), both of
which ship with the standard Windows installer from python.org.

Optional: `pip install openpyxl` enables the "Export to Excel" button on
the Reports tab (CSV export always works without it).
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import database as db
from app.main_window import App


def main():
    db.init_db()
    app = App()
    app.dashboard_tab.refresh()
    app.companies_tab.refresh()
    app.employees_tab.refresh()

    def on_close():
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)
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
