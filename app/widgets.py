"""
widgets.py
----------
Small reusable Tkinter building blocks used throughout the app:
  - CalendarPopup / DateEntry : lightweight pure-Tkinter date picker
  - FormDialog                : builds an Add/Edit form from a field spec list
  - StatCard                  : colored KPI card used on the Dashboard
No third-party dependencies - stdlib tkinter only, so it runs on any
Windows machine with a standard Python install.
"""

import tkinter as tk
from tkinter import ttk
import calendar
from datetime import date

FONT_NORMAL = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_HEADER = ("Segoe UI", 16, "bold")
FONT_SUBHEADER = ("Segoe UI", 12, "bold")


# ---------------------------------------------------------------- calendar
class CalendarPopup(tk.Toplevel):
    def __init__(self, parent, on_pick, initial=None):
        super().__init__(parent)
        self.overrideredirect(True)
        self.configure(bg="#2c3e50", padx=1, pady=1)
        self.on_pick = on_pick
        today = initial or date.today()
        self.year = today.year
        self.month = today.month
        self.frame = tk.Frame(self, bg="white")
        self.frame.pack()
        self._build()
        self.bind("<FocusOut>", lambda e: self.destroy())
        self.focus_set()

    def _build(self):
        for w in self.frame.winfo_children():
            w.destroy()

        nav = tk.Frame(self.frame, bg="#34495e")
        nav.pack(fill="x")
        tk.Button(nav, text="<", command=self._prev_month, bd=0, bg="#34495e", fg="white",
                  activebackground="#2c3e50", font=FONT_BOLD).pack(side="left", padx=4, pady=2)
        tk.Label(nav, text=f"{calendar.month_name[self.month]} {self.year}", bg="#34495e",
                  fg="white", font=FONT_BOLD, width=16).pack(side="left")
        tk.Button(nav, text=">", command=self._next_month, bd=0, bg="#34495e", fg="white",
                  activebackground="#2c3e50", font=FONT_BOLD).pack(side="left", padx=4, pady=2)

        days = tk.Frame(self.frame, bg="white")
        days.pack()
        for i, d in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
            tk.Label(days, text=d, width=3, bg="#ecf0f1", font=FONT_BOLD).grid(row=0, column=i, sticky="nsew")

        cal = calendar.Calendar(firstweekday=0)
        row = 1
        for week in cal.monthdayscalendar(self.year, self.month):
            for col, day in enumerate(week):
                if day == 0:
                    tk.Label(days, text="", width=3, bg="white").grid(row=row, column=col)
                else:
                    tk.Button(days, text=str(day), width=3, bd=0, bg="white",
                              activebackground="#3498db", activeforeground="white",
                              command=lambda d=day: self._pick(d)).grid(row=row, column=col)
            row += 1

        today_btn = tk.Button(self.frame, text="Today", bd=0, bg="#ecf0f1",
                               command=lambda: self._pick(date.today().day, force_today=True))
        today_btn.pack(fill="x")

    def _pick(self, day, force_today=False):
        if force_today:
            d = date.today()
        else:
            d = date(self.year, self.month, day)
        self.on_pick(d)
        self.destroy()

    def _prev_month(self):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self._build()

    def _next_month(self):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self._build()


class DateEntry(tk.Frame):
    """Text entry (YYYY-MM-DD) + calendar-pick button."""

    def __init__(self, parent, initial=""):
        super().__init__(parent)
        self.var = tk.StringVar(value=initial)
        self.entry = ttk.Entry(self, textvariable=self.var, width=13, font=FONT_NORMAL)
        self.entry.pack(side="left")
        self.btn = ttk.Button(self, text="\U0001F4C5", width=3, command=self._open_calendar)
        self.btn.pack(side="left", padx=(2, 0))

    def _open_calendar(self):
        x = self.btn.winfo_rootx()
        y = self.btn.winfo_rooty() + self.btn.winfo_height()
        try:
            initial = date.fromisoformat(self.var.get()) if self.var.get() else None
        except ValueError:
            initial = None
        popup = CalendarPopup(self, self._set_date, initial)
        popup.geometry(f"+{x}+{y}")

    def _set_date(self, d: date):
        self.var.set(d.isoformat())

    def get(self):
        return self.var.get().strip()

    def set(self, value):
        self.var.set(value or "")


# ---------------------------------------------------------------- form dialog
class FormDialog(tk.Toplevel):
    """
    Generic Add/Edit dialog.
    fields: list of tuples (key, label, kind, options)
        kind in {"text","date","combo","textarea","number","readonly"}
        options: list of choices for "combo", else None
    """

    def __init__(self, parent, title, fields, initial=None, on_save=None, width=560):
        super().__init__(parent)
        self.title(title)
        self.on_save = on_save
        self.fields = fields
        self.vars = {}
        self.result = None
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        initial = initial or {}

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, width=width, height=480, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        inner = ttk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        for i, (key, label, kind, *rest) in enumerate(fields):
            options = rest[0] if rest else None
            row = ttk.Frame(inner)
            row.pack(fill="x", pady=4)
            ttk.Label(row, text=label, width=26, font=FONT_NORMAL).pack(side="left")

            if kind == "date":
                w = DateEntry(row, initial.get(key, ""))
                w.pack(side="left")
            elif kind == "combo":
                var = tk.StringVar(value=initial.get(key, options[0] if options else ""))
                w = ttk.Combobox(row, textvariable=var, values=options, width=28, state="readonly")
                w.pack(side="left")
                w.var = var
            elif kind == "textarea":
                w = tk.Text(row, width=32, height=3, font=FONT_NORMAL)
                w.insert("1.0", initial.get(key, ""))
                w.pack(side="left")
            elif kind == "readonly":
                var = tk.StringVar(value=initial.get(key, ""))
                w = ttk.Entry(row, textvariable=var, width=30, state="readonly")
                w.pack(side="left")
                w.var = var
            else:  # text / number
                var = tk.StringVar(value=initial.get(key, ""))
                w = ttk.Entry(row, textvariable=var, width=30)
                w.pack(side="left")
                w.var = var

            self.vars[key] = (kind, w)

        btns = ttk.Frame(self, padding=(14, 0, 14, 14))
        btns.pack(fill="x")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(btns, text="Save", command=self._save, style="Accent.TButton").pack(side="right")

    def _save(self):
        data = {}
        for key, (kind, w) in self.vars.items():
            if kind == "date":
                data[key] = w.get()
            elif kind == "textarea":
                data[key] = w.get("1.0", "end").strip()
            else:
                data[key] = w.var.get()
        self.result = data
        if self.on_save:
            ok = self.on_save(data)
            if ok is False:
                return
        self.destroy()


# ---------------------------------------------------------------- stat card
class StatCard(tk.Frame):
    def __init__(self, parent, title, value, color, on_click=None):
        super().__init__(parent, bg=color, padx=14, pady=10, highlightthickness=0)
        self.value_lbl = tk.Label(self, text=str(value), font=("Segoe UI", 22, "bold"),
                                   bg=color, fg="white")
        self.value_lbl.pack(anchor="w")
        tk.Label(self, text=title, font=FONT_BOLD, bg=color, fg="white").pack(anchor="w")
        if on_click:
            for w in (self, self.value_lbl):
                w.bind("<Button-1>", lambda e: on_click())
                w.configure(cursor="hand2")

    def set_value(self, value):
        self.value_lbl.configure(text=str(value))
