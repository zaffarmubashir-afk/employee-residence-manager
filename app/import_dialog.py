"""
import_dialog.py
-----------------
Bulk "Import employees from PDF / scanned documents / photos" workflow:

  1. Pick any number of PDF or image files at once (passport copies,
     Emirates ID scans, visa PDFs, phone photos of documents - any mix,
     one file per employee - or a single multi-employee roster/list
     file, e.g. a MOHRE "List of Employees" export). Good for
     onboarding a company with thousands of employees without typing
     everything in by hand.
  2. Each file is processed through app.pdf_extract on a background
     thread so the window never freezes, with a live progress count and
     a Cancel button for very large batches.
  3. A CSV/Excel spreadsheet can also be imported directly (via
     app.tabular_import) - a fully reliable alternative for documents
     too low-quality for OCR to read (e.g. small/coloured table text in
     a low-resolution scan or screenshot). Type or paste the data in
     once and every row imports exactly as typed, no guessing involved.
  4. Results land in an editable table - NOTHING is written to the
     database yet. OCR and layout-guessing are never 100% reliable, so
     every row is reviewed (and fixable inline) before import.
  5. Checked rows are inserted as new employees under the chosen company.
"""
import os
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from app import database as db
from app import pdf_extract as pe
from app import tabular_import as ti
from app.widgets import FONT_BOLD

# (key, header, width)
COLUMNS = [
    ("include", "\u2713", 34),
    ("file", "Source File", 170),
    ("full_name", "Full Name", 160),
    ("nationality", "Nationality", 110),
    ("gender", "Gender", 65),
    ("date_of_birth", "Date of Birth", 100),
    ("job_title", "Job Title", 140),
    ("passport_no", "Passport No.", 105),
    ("passport_expiry", "Passport Expiry", 105),
    ("emirates_id_no", "Emirates ID No.", 140),
    ("emirates_id_expiry", "Emirates ID Expiry", 115),
    ("residence_visa_expiry", "Visa Expiry", 100),
    ("labour_card_no", "Labour Card No.", 115),
    ("labour_card_expiry", "Labour Card Expiry", 115),
    ("notes", "Notes", 140),
    ("status_note", "Extraction Status", 190),
]
EDITABLE_COLUMNS = {c for c, _, _ in COLUMNS} - {"include", "file", "status_note"}
ALLOWED_EXT = ("*.pdf", "*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tif", "*.tiff", "*.webp")


class BulkImportDialog(tk.Toplevel):
    def __init__(self, parent, app, default_company_id=None):
        super().__init__(parent)
        self.app = app
        self.title("Import Employees from PDF / Scanned Documents / Photos")
        self.geometry("1200x650")
        self.minsize(900, 500)
        self.transient(parent)
        self.grab_set()

        self.rows = []  # list of dicts (or None once removed), one per source file
        self._queue = queue.Queue()
        self._worker = None
        self._cancel_flag = threading.Event()
        self._editor = None

        # ---------------------------------------------------------- top bar
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="Company for imported employees *", font=FONT_BOLD).pack(side="left")
        companies = db.list_companies()
        self.company_map = {c["company_name"]: c["id"] for c in companies}
        default_label = next((n for n, cid in self.company_map.items() if cid == default_company_id),
                              next(iter(self.company_map), ""))
        self.company_var = tk.StringVar(value=default_label)
        ttk.Combobox(top, textvariable=self.company_var, values=list(self.company_map.keys()),
                     state="readonly", width=28).pack(side="left", padx=8)

        ttk.Button(top, text="Add Files...", command=self.pick_files).pack(side="left", padx=(16, 4))
        ttk.Button(top, text="Import CSV/Excel...", command=self.pick_spreadsheet).pack(side="left", padx=4)
        self.cancel_btn = ttk.Button(top, text="Cancel Processing", command=self._cancel, state="disabled")
        self.cancel_btn.pack(side="left", padx=4)
        self.progress_lbl = ttk.Label(top, text="", foreground="#555")
        self.progress_lbl.pack(side="left", padx=10)

        if not pe.CAN_OCR:
            ttk.Label(top, text="\u26A0 OCR not available on this machine - only text-based PDFs "
                                 "will auto-fill. See Settings, or use 'Import CSV/Excel' instead.",
                      foreground="#b9770e", wraplength=380, justify="left").pack(side="right")

        # ---------------------------------------------------------- table
        table_frame = ttk.Frame(self, padding=(10, 0))
        table_frame.pack(fill="both", expand=True)
        cols = [c for c, _, _ in COLUMNS]
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)
        for c, h, w in COLUMNS:
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w", stretch=False)
        vs = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        hs = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-1>", self._on_single_click)

        ttk.Label(self, text="Double-click any cell to correct it before importing. "
                              "Click the \u2713 column to include/exclude a row. "
                              "Scroll right to see every extracted field. "
                              "If a scan/photo is too low-quality to read automatically, retype "
                              "just that file's data into a CSV/Excel sheet and use 'Import CSV/Excel' "
                              "instead - it's 100% reliable since nothing has to be guessed.",
                  foreground="#666", wraplength=1160, justify="left").pack(anchor="w", padx=12, pady=(4, 0))

        # ---------------------------------------------------------- bottom bar
        bottom = ttk.Frame(self, padding=10)
        bottom.pack(fill="x")
        ttk.Button(bottom, text="Select All", command=lambda: self._set_all_included(True)).pack(side="left")
        ttk.Button(bottom, text="Select None", command=lambda: self._set_all_included(False)).pack(
            side="left", padx=4)
        ttk.Button(bottom, text="Remove Row(s)", command=self._remove_selected).pack(side="left", padx=4)
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right", padx=4)
        ttk.Button(bottom, text="Import Checked Rows", style="Accent.TButton",
                   command=self._import_checked).pack(side="right", padx=4)

        self.after(150, self._poll_queue)

    # ------------------------------------------------------------- files
    def pick_files(self):
        if not self.company_map:
            messagebox.showwarning("No companies", "Add a company first (Companies tab), then try again.")
            return
        paths = filedialog.askopenfilenames(
            title="Select passport / Emirates ID / visa PDFs or photos",
            filetypes=[
                ("Documents & Images", " ".join(ALLOWED_EXT)),
                ("PDF files", "*.pdf"),
                ("Image files", " ".join(e for e in ALLOWED_EXT if e != "*.pdf")),
                ("All files", "*.*"),
            ])
        if not paths:
            return
        self._start_worker(list(paths))

    def pick_spreadsheet(self):
        if not self.company_map:
            messagebox.showwarning("No companies", "Add a company first (Companies tab), then try again.")
            return
        path = filedialog.askopenfilename(
            title="Select a CSV or Excel file of employees",
            filetypes=[("Spreadsheet files", "*.csv *.xlsx *.xlsm"), ("CSV files", "*.csv"),
                       ("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")])
        if not path:
            return
        try:
            rows, unmatched = ti.read_tabular_file(path)
        except Exception as e:
            messagebox.showerror("Couldn't read file", str(e))
            return
        if not rows:
            messagebox.showinfo("Nothing found", "No data rows were found in that file.")
            return
        base_name = os.path.basename(path)
        for fields in rows:
            self._add_row(base_name, fields, "From spreadsheet")
        self.progress_lbl.configure(text=f"Added {len(rows)} row(s) from {base_name}.")
        if unmatched:
            messagebox.showinfo(
                "Some columns weren't recognised",
                "These column headers weren't understood and were skipped:\n\n"
                + ", ".join(unmatched) +
                "\n\nRename them to something like 'Full Name', 'Passport Number', "
                "'Nationality', 'Emirates ID No', etc. and re-import if you need that data, "
                "or fill it in manually in the table.")

    def _start_worker(self, paths):
        self._cancel_flag.clear()
        self.cancel_btn.configure(state="normal")
        self.progress_lbl.configure(text=f"Processing 0/{len(paths)}...")

        def work():
            for i, p in enumerate(paths, start=1):
                if self._cancel_flag.is_set():
                    break
                try:
                    records = pe.extract_employee_records(p)
                except Exception as e:
                    records = [({}, False, f"Extraction error: {e}")]
                base_name = os.path.basename(p)
                multi = len(records) > 1
                for fields, used_ocr, note in records:
                    if not note:
                        note = "Read via OCR - please verify" if used_ocr else "Read from PDF text"
                    if not fields and "couldn't be read" not in note and "error" not in note.lower():
                        note = "Nothing recognised - fill in manually"
                    label = f"{base_name} (roster)" if multi else base_name
                    self._queue.put(("row", label, fields, note))
                self._queue.put(("progress", i, len(paths), None))
            self._queue.put(("done", len(paths), None, None))

        self._worker = threading.Thread(target=work, daemon=True)
        self._worker.start()

    def _cancel(self):
        self._cancel_flag.set()

    def _poll_queue(self):
        try:
            while True:
                kind, a, b, _c = self._queue.get_nowait()
                if kind == "row":
                    self._add_row(a, b, _c)
                elif kind == "progress":
                    self.progress_lbl.configure(text=f"Processing {a}/{b}...")
                elif kind == "done":
                    self.cancel_btn.configure(state="disabled")
                    self.progress_lbl.configure(text=f"Done - {len(self.tree.get_children())} file(s) in the table.")
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    # ------------------------------------------------------------- rows
    def _add_row(self, filename, fields, note):
        row = {"include": True, "file": filename, "status_note": note}
        for c in EDITABLE_COLUMNS:
            row[c] = fields.get(c, "")
        self.rows.append(row)
        iid = str(len(self.rows) - 1)
        self.tree.insert("", "end", iid=iid, values=self._row_values(row))

    def _row_values(self, row):
        vals = []
        for c, _, _ in COLUMNS:
            if c == "include":
                vals.append("\u2611" if row["include"] else "\u2610")
            else:
                vals.append(row.get(c, ""))
        return vals

    def _set_all_included(self, val):
        for iid in self.tree.get_children():
            row = self.rows[int(iid)]
            if row is None:
                continue
            row["include"] = val
            self.tree.set(iid, "include", "\u2611" if val else "\u2610")

    def _remove_selected(self):
        for iid in self.tree.selection():
            self.rows[int(iid)] = None
            self.tree.delete(iid)

    def _on_single_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col = self.tree.identify_column(event.x)
        iid = self.tree.identify_row(event.y)
        if not iid or col != "#1":
            return
        row = self.rows[int(iid)]
        if row is None:
            return
        row["include"] = not row["include"]
        self.tree.set(iid, "include", "\u2611" if row["include"] else "\u2610")

    def _on_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        col_id = self.tree.identify_column(event.x)
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        col_index = int(col_id.replace("#", "")) - 1
        col_key = COLUMNS[col_index][0]
        if col_key not in EDITABLE_COLUMNS:
            return
        bbox = self.tree.bbox(iid, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        if self._editor is not None:
            self._editor.destroy()
            self._editor = None

        var = tk.StringVar(value=self.tree.set(iid, col_key))
        editor = ttk.Entry(self.tree, textvariable=var)
        editor.place(x=x, y=y, width=w, height=h)
        editor.focus_set()
        editor.select_range(0, "end")

        def commit(_evt=None):
            if self._editor is None:
                return
            val = var.get()
            self.tree.set(iid, col_key, val)
            row = self.rows[int(iid)]
            if row is not None:
                row[col_key] = val
            editor.destroy()
            self._editor = None

        def cancel_edit(_evt=None):
            editor.destroy()
            self._editor = None

        editor.bind("<Return>", commit)
        editor.bind("<FocusOut>", commit)
        editor.bind("<Escape>", cancel_edit)
        self._editor = editor

    # ------------------------------------------------------------- import
    def _import_checked(self):
        if not self.company_map:
            return
        company_id = self.company_map.get(self.company_var.get())
        if not company_id:
            messagebox.showwarning("Company required", "Choose a company for the imported employees.")
            return
        imported, skipped = 0, 0
        for iid in self.tree.get_children():
            row = self.rows[int(iid)]
            if row is None or not row.get("include"):
                continue
            if not row.get("full_name", "").strip():
                skipped += 1
                continue
            data = {k: row.get(k, "") for k in EDITABLE_COLUMNS}
            data["company_id"] = company_id
            data["status"] = "Active"
            db.add_employee(data)
            imported += 1
            self.rows[int(iid)] = None
            self.tree.delete(iid)

        msg = f"Imported {imported} employee(s)."
        if skipped:
            msg += f"\n{skipped} row(s) were skipped because they have no name - fix and re-check them, then import again."
        messagebox.showinfo("Import complete", msg)
        if imported:
            self.app.employees_tab.refresh()
            self.app.dashboard_tab.refresh()
