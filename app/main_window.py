"""
main_window.py
---------------
The main Tkinter application: a tabbed (Notebook) window with
Dashboard / Companies / Employees / Other Documents / Reports / Settings.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from datetime import date

from app import database as db
from app import utils
from app import export as exp
from app.widgets import FormDialog, StatCard, FONT_HEADER, FONT_SUBHEADER, FONT_BOLD, FONT_NORMAL

APP_TITLE = "UAE Employee & Company Residence / Document Management System"


# ============================================================== MAIN APP
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1280x760")
        self.minsize(1024, 640)
        self._configure_style()

        header = ttk.Frame(self, padding=(16, 10))
        header.pack(fill="x")
        ttk.Label(header, text="\U0001F3E2  " + APP_TITLE, font=FONT_HEADER).pack(side="left")
        self.today_lbl = ttk.Label(header, text=date.today().strftime("Today: %d %b %Y"),
                                    font=FONT_NORMAL)
        self.today_lbl.pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.dashboard_tab = DashboardTab(self.notebook, self)
        self.companies_tab = CompaniesTab(self.notebook, self)
        self.employees_tab = EmployeesTab(self.notebook, self)
        self.documents_tab = DocumentsTab(self.notebook, self)
        self.reports_tab = ReportsTab(self.notebook, self)
        self.settings_tab = SettingsTab(self.notebook, self)

        self.notebook.add(self.dashboard_tab, text="  \U0001F4CA Dashboard  ")
        self.notebook.add(self.companies_tab, text="  \U0001F3E2 Companies  ")
        self.notebook.add(self.employees_tab, text="  \U0001F465 Employees  ")
        self.notebook.add(self.documents_tab, text="  \U0001F4C4 Other Documents  ")
        self.notebook.add(self.reports_tab, text="  \U0001F4C8 Reports / Export  ")
        self.notebook.add(self.settings_tab, text="  \u2699 Settings  ")

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _configure_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            style.theme_use(style.theme_use())
        style.configure("Treeview", rowheight=26, font=FONT_NORMAL)
        style.configure("Treeview.Heading", font=FONT_BOLD)
        style.configure("Accent.TButton", font=FONT_BOLD)

    def _on_tab_changed(self, event):
        tab_text = self.notebook.tab(self.notebook.select(), "text")
        if "Dashboard" in tab_text:
            self.dashboard_tab.refresh()
        elif "Companies" in tab_text:
            self.companies_tab.refresh()
        elif "Employees" in tab_text:
            self.employees_tab.refresh()
        elif "Other Documents" in tab_text:
            self.documents_tab.refresh()
        elif "Reports" in tab_text:
            self.reports_tab.refresh()

    def refresh_all(self):
        self.dashboard_tab.refresh()
        self.companies_tab.refresh()
        self.employees_tab.refresh()
        self.documents_tab.refresh()

    def goto_company(self, company_id):
        self.notebook.select(self.companies_tab)
        self.companies_tab.select_company(company_id)

    def goto_employee(self, employee_id):
        self.notebook.select(self.employees_tab)
        self.employees_tab.select_employee(employee_id)


def tag_rows(tree, status):
    return utils.STATUS_ROW_TAGS.get(status, "row_unknown")


def configure_status_tags(tree):
    for status, tagname in utils.STATUS_ROW_TAGS.items():
        color = utils.STATUS_COLORS[status]
        tree.tag_configure(tagname, background=color, foreground="white" if status != "Upcoming" else "#333333")


# ============================================================== DASHBOARD
class DashboardTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.filter_status = tk.StringVar(value="All")

        cards_frame = ttk.Frame(self)
        cards_frame.pack(fill="x", pady=(0, 10))
        self.cards = {}
        card_specs = [
            (utils.STATUS_EXPIRED, "Expired"),
            (utils.STATUS_CRITICAL, "Critical (\u226415 days)"),
            (utils.STATUS_WARNING, "Warning (\u226430 days)"),
            (utils.STATUS_UPCOMING, "Upcoming (\u226460 days)"),
            (utils.STATUS_OK, "Valid"),
        ]
        for i, (status_key, label) in enumerate(card_specs):
            card = StatCard(cards_frame, label, 0, utils.STATUS_COLORS[status_key],
                             on_click=lambda s=status_key: self._filter_by(s))
            card.grid(row=0, column=i, sticky="nsew", padx=5)
            cards_frame.columnconfigure(i, weight=1)
            self.cards[status_key] = card

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Label(toolbar, text="Filter:", font=FONT_BOLD).pack(side="left")
        combo = ttk.Combobox(toolbar, textvariable=self.filter_status, state="readonly", width=14,
                              values=["All", utils.STATUS_EXPIRED, utils.STATUS_CRITICAL,
                                      utils.STATUS_WARNING, utils.STATUS_UPCOMING, utils.STATUS_OK])
        combo.pack(side="left", padx=6)
        combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="left", padx=6)
        ttk.Label(toolbar, text="Double-click a row to open the record.", foreground="#666") \
            .pack(side="right")

        columns = ("category", "company", "name", "document", "number", "expiry", "status", "days")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=18)
        headers = ["Type", "Company", "Employee / Company", "Document", "No.", "Expiry",
                   "Status", "Days Left"]
        widths = [70, 190, 190, 220, 130, 90, 90, 80]
        for c, h, w in zip(columns, headers, widths):
            self.tree.heading(c, text=h, command=lambda c=c: self._sort_by(c))
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True)
        configure_status_tags(self.tree)
        self.tree.bind("<Double-1>", self._open_selected)

        self._items_cache = []

    def _filter_by(self, status):
        self.filter_status.set(status)
        self.refresh()

    def _sort_by(self, col):
        idx = {"category": "category", "company": "company_name", "name": "owner_name",
               "document": "document", "number": "number", "expiry": "expiry",
               "status": "status", "days": "days_left"}[col]
        self._items_cache.sort(key=lambda it: (it[idx] is None, it[idx]))
        self._populate(self._items_cache)

    def refresh(self):
        items = utils.gather_all_tracked_documents(active_only=True)
        self._items_cache = items
        counts = utils.summary_counts(items)
        for status_key, card in self.cards.items():
            card.set_value(counts.get(status_key, 0))

        f = self.filter_status.get()
        shown = items if f == "All" else [it for it in items if it["status"] == f]
        self._populate(shown)

    def _populate(self, items):
        self.tree.delete(*self.tree.get_children())
        for it in items:
            days = it["days_left"]
            days_txt = "-" if days is None else (f"{days}d overdue" if days < 0 else f"{days}")
            self.tree.insert("", "end",
                              values=(it["category"], it["company_name"], it["owner_name"],
                                      it["document"], it["number"], utils.fmt_date_display(it["expiry"]),
                                      it["status"], days_txt),
                              tags=(utils.STATUS_ROW_TAGS[it["status"]], it["owner_type"], it["owner_id"]))

    def _open_selected(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        tags = self.tree.item(sel[0], "tags")
        if len(tags) < 3:
            return
        owner_type, owner_id = tags[1], int(tags[2])
        if owner_type == "company":
            self.app.goto_company(owner_id)
        else:
            self.app.goto_employee(owner_id)


# ============================================================== COMPANIES
COMPANY_FORM_FIELDS = [
    ("company_name", "Company Name *", "text"),
    ("legal_type", "Legal Type", "combo", ["Mainland", "Free Zone", "Offshore"]),
    ("free_zone_name", "Free Zone Name (if any)", "text"),
    ("trade_license_no", "Trade License No.", "text"),
    ("trade_license_expiry", "Trade License Expiry", "date"),
    ("establishment_card_no", "Establishment / Immigration Card No.", "text"),
    ("establishment_card_expiry", "Establishment / Immigration Card Expiry", "date"),
    ("mohre_establishment_no", "MOHRE Establishment No.", "text"),
    ("immigration_file_no", "Immigration File No. (GDRFA/ICP)", "text"),
    ("chamber_of_commerce_no", "Chamber of Commerce No.", "text"),
    ("chamber_of_commerce_expiry", "Chamber of Commerce Expiry", "date"),
    ("tenancy_ejari_no", "Ejari / Tenancy No.", "text"),
    ("tenancy_ejari_expiry", "Ejari / Tenancy Expiry", "date"),
    ("vat_trn", "VAT TRN", "text"),
    ("address", "Address", "text"),
    ("phone", "Phone", "text"),
    ("email", "Email", "text"),
    ("status", "Status", "combo", ["Active", "Suspended", "Cancelled"]),
    ("notes", "Notes", "textarea"),
]


class CompaniesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.search_var = tk.StringVar()

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Label(toolbar, text="Search:", font=FONT_BOLD).pack(side="left")
        entry = ttk.Entry(toolbar, textvariable=self.search_var, width=30)
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda e: self.refresh())
        ttk.Button(toolbar, text="+ Add Company", command=self.add_company).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Edit", command=self.edit_company).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Delete", command=self.delete_company).pack(side="left", padx=4)
        ttk.Button(toolbar, text="View Employees", command=self.view_employees).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Documents", command=self.view_documents).pack(side="left", padx=4)

        columns = ("id", "name", "type", "license_no", "license_exp", "estcard_exp", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=20)
        headers = ["ID", "Company Name", "Legal Type", "Trade License No.", "License Expiry",
                   "Est. Card Expiry", "Status"]
        widths = [40, 260, 100, 150, 120, 120, 90]
        for c, h, w in zip(columns, headers, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")
        self.tree.column("id", width=40, stretch=False)
        self.tree.pack(fill="both", expand=True)
        configure_status_tags(self.tree)
        self.tree.bind("<Double-1>", lambda e: self.edit_company())

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        rows = db.list_companies(self.search_var.get())
        today = date.today()
        for c in rows:
            worst_status = utils.STATUS_OK
            for _, _, exp_field in utils.COMPANY_DOC_MAP:
                if c[exp_field]:
                    st, _ = utils.classify(c[exp_field], today)
                    if _rank(st) > _rank(worst_status):
                        worst_status = st
            self.tree.insert("", "end", iid=str(c["id"]),
                              values=(c["id"], c["company_name"], c["legal_type"] or "-",
                                      c["trade_license_no"] or "-",
                                      utils.fmt_date_display(c["trade_license_expiry"]),
                                      utils.fmt_date_display(c["establishment_card_expiry"]),
                                      c["status"]),
                              tags=(utils.STATUS_ROW_TAGS[worst_status],))

    def select_company(self, company_id):
        self.refresh()
        iid = str(company_id)
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def add_company(self):
        def save(data):
            if not data.get("company_name", "").strip():
                messagebox.showerror("Required", "Company name is required.")
                return False
            db.add_company(data)
            self.refresh()
            self.app.dashboard_tab.refresh()
        FormDialog(self, "Add Company", COMPANY_FORM_FIELDS, on_save=save)

    def edit_company(self):
        cid = self._selected_id()
        if not cid:
            messagebox.showinfo("Select", "Select a company first.")
            return
        row = db.get_company(cid)
        initial = {k: row[k] for k in row.keys()}

        def save(data):
            db.update_company(cid, data)
            self.refresh()
            self.app.dashboard_tab.refresh()
        FormDialog(self, f"Edit Company - {row['company_name']}", COMPANY_FORM_FIELDS, initial, save)

    def delete_company(self):
        cid = self._selected_id()
        if not cid:
            messagebox.showinfo("Select", "Select a company first.")
            return
        row = db.get_company(cid)
        emp_count = len(db.list_employees(company_id=cid))
        warn = f"Delete '{row['company_name']}'?"
        if emp_count:
            warn += f"\n\nThis company has {emp_count} linked employee record(s), which will also be removed."
        if messagebox.askyesno("Confirm delete", warn):
            db.delete_company(cid)
            self.refresh()
            self.app.refresh_all()

    def view_employees(self):
        cid = self._selected_id()
        if not cid:
            messagebox.showinfo("Select", "Select a company first.")
            return
        self.app.notebook.select(self.app.employees_tab)
        self.app.employees_tab.filter_to_company(cid)

    def view_documents(self):
        cid = self._selected_id()
        if not cid:
            messagebox.showinfo("Select", "Select a company first.")
            return
        self.app.notebook.select(self.app.documents_tab)
        self.app.documents_tab.filter_to_owner("company", cid)


def _rank(status):
    order = [utils.STATUS_OK, utils.STATUS_UNKNOWN, utils.STATUS_UPCOMING,
             utils.STATUS_WARNING, utils.STATUS_CRITICAL, utils.STATUS_EXPIRED]
    return order.index(status) if status in order else 0


# ============================================================== EMPLOYEES
EMPLOYEE_STATIC_FIELDS_1 = [
    ("employee_code", "Employee Code / ID", "text"),
    ("full_name", "Full Name *", "text"),
    ("nationality", "Nationality", "text"),
    ("gender", "Gender", "combo", ["Male", "Female"]),
    ("date_of_birth", "Date of Birth", "date"),
    ("job_title", "Job Title", "text"),
    ("date_of_joining", "Date of Joining", "date"),
    ("basic_salary", "Basic Salary (AED)", "text"),
    ("visa_sponsor", "Visa Sponsor", "text"),
    ("status", "Employment Status", "combo", ["Active", "On Leave", "Cancelled", "Absconded"]),
    ("cancellation_date", "Cancellation Date (if any)", "date"),
]
EMPLOYEE_DOC_FIELDS = [
    ("passport_no", "Passport No.", "text"),
    ("passport_expiry", "Passport Expiry", "date"),
    ("entry_permit_no", "Entry Permit No.", "text"),
    ("entry_permit_expiry", "Entry Permit Expiry", "date"),
    ("residence_visa_no", "Residence Visa No.", "text"),
    ("residence_visa_expiry", "Residence Visa Expiry", "date"),
    ("emirates_id_no", "Emirates ID No.", "text"),
    ("emirates_id_expiry", "Emirates ID Expiry", "date"),
    ("labour_card_no", "Labour Card / Work Permit No.", "text"),
    ("labour_card_expiry", "Labour Card / Work Permit Expiry", "date"),
    ("employment_contract_no", "Employment Contract No. (MOHRE)", "text"),
    ("employment_contract_expiry", "Employment Contract Expiry", "date"),
    ("medical_test_date", "Medical Fitness Test Date", "date"),
    ("medical_test_expiry", "Medical Fitness Test Expiry", "date"),
    ("insurance_policy_no", "Health Insurance Policy No.", "text"),
    ("insurance_expiry", "Health Insurance Expiry", "date"),
]
EMPLOYEE_CONTACT_FIELDS = [
    ("phone", "Phone", "text"),
    ("email", "Email", "text"),
    ("notes", "Notes", "textarea"),
]


class EmployeesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.search_var = tk.StringVar()
        self.company_filter_var = tk.StringVar(value="All Companies")
        self.status_filter_var = tk.StringVar(value="All")

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Label(toolbar, text="Search:", font=FONT_BOLD).pack(side="left")
        entry = ttk.Entry(toolbar, textvariable=self.search_var, width=22)
        entry.pack(side="left", padx=6)
        entry.bind("<KeyRelease>", lambda e: self.refresh())

        ttk.Label(toolbar, text="Company:", font=FONT_BOLD).pack(side="left", padx=(10, 0))
        self.company_combo = ttk.Combobox(toolbar, textvariable=self.company_filter_var,
                                           state="readonly", width=24)
        self.company_combo.pack(side="left", padx=6)
        self.company_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Label(toolbar, text="Status:", font=FONT_BOLD).pack(side="left", padx=(10, 0))
        status_combo = ttk.Combobox(toolbar, textvariable=self.status_filter_var, state="readonly",
                                     width=12, values=["All", "Active", "On Leave", "Cancelled", "Absconded"])
        status_combo.pack(side="left", padx=6)
        status_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(toolbar, text="+ Add Employee", command=self.add_employee).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Edit", command=self.edit_employee).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Delete", command=self.delete_employee).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Documents", command=self.view_documents).pack(side="left", padx=4)

        columns = ("id", "name", "company", "title", "visa_exp", "eid_exp", "labour_exp", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=20)
        headers = ["ID", "Full Name", "Company", "Job Title", "Visa Expiry", "Emirates ID Expiry",
                   "Labour Card Expiry", "Status"]
        widths = [40, 190, 190, 140, 110, 130, 130, 90]
        for c, h, w in zip(columns, headers, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")
        self.tree.column("id", width=40, stretch=False)
        self.tree.pack(fill="both", expand=True)
        configure_status_tags(self.tree)
        self.tree.bind("<Double-1>", lambda e: self.edit_employee())

    def _company_options(self):
        companies = db.list_companies()
        return {"All Companies": None, **{c["company_name"]: c["id"] for c in companies}}

    def refresh(self):
        opts = self._company_options()
        self.company_combo["values"] = list(opts.keys())
        if self.company_filter_var.get() not in opts:
            self.company_filter_var.set("All Companies")

        company_id = opts.get(self.company_filter_var.get())
        rows = db.list_employees(search=self.search_var.get(), company_id=company_id,
                                  status=self.status_filter_var.get())
        self.tree.delete(*self.tree.get_children())
        today = date.today()
        for e in rows:
            worst_status = utils.STATUS_OK
            for _, _, exp_field in utils.EMPLOYEE_DOC_MAP:
                if e[exp_field]:
                    st, _ = utils.classify(e[exp_field], today)
                    if _rank(st) > _rank(worst_status):
                        worst_status = st
            self.tree.insert("", "end", iid=str(e["id"]),
                              values=(e["id"], e["full_name"], e["company_name"] or "-",
                                      e["job_title"] or "-",
                                      utils.fmt_date_display(e["residence_visa_expiry"]),
                                      utils.fmt_date_display(e["emirates_id_expiry"]),
                                      utils.fmt_date_display(e["labour_card_expiry"]),
                                      e["status"]),
                              tags=(utils.STATUS_ROW_TAGS[worst_status],))

    def filter_to_company(self, company_id):
        opts = self._company_options()
        for name, cid in opts.items():
            if cid == company_id:
                self.company_filter_var.set(name)
                break
        self.refresh()

    def select_employee(self, employee_id):
        self.company_filter_var.set("All Companies")
        self.refresh()
        iid = str(employee_id)
        if self.tree.exists(iid):
            self.tree.selection_set(iid)
            self.tree.see(iid)

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def _company_field_spec(self, current_company_id=None):
        companies = db.list_companies()
        if not companies:
            messagebox.showwarning("No companies", "Please add a company first before adding employees.")
            return None
        options = [f"{c['id']} - {c['company_name']}" for c in companies]
        default = next((o for o in options if o.startswith(f"{current_company_id} -")), options[0])
        return options, default

    def add_employee(self):
        spec = self._company_field_spec()
        if not spec:
            return
        options, default = spec
        fields = ([("company_id", "Company *", "combo", options)] +
                  EMPLOYEE_STATIC_FIELDS_1 + EMPLOYEE_DOC_FIELDS + EMPLOYEE_CONTACT_FIELDS)

        def save(data):
            if not data.get("full_name", "").strip():
                messagebox.showerror("Required", "Full name is required.")
                return False
            data["company_id"] = int(data["company_id"].split(" - ")[0])
            db.add_employee(data)
            self.refresh()
            self.app.dashboard_tab.refresh()
        FormDialog(self, "Add Employee", fields, initial={"company_id": default}, on_save=save, width=600)

    def edit_employee(self):
        eid = self._selected_id()
        if not eid:
            messagebox.showinfo("Select", "Select an employee first.")
            return
        row = db.get_employee(eid)
        spec = self._company_field_spec(row["company_id"])
        if not spec:
            return
        options, _ = spec
        current = next((o for o in options if o.startswith(f"{row['company_id']} -")), options[0])
        fields = ([("company_id", "Company *", "combo", options)] +
                  EMPLOYEE_STATIC_FIELDS_1 + EMPLOYEE_DOC_FIELDS + EMPLOYEE_CONTACT_FIELDS)
        initial = {k: row[k] for k in row.keys()}
        initial["company_id"] = current

        def save(data):
            data["company_id"] = int(data["company_id"].split(" - ")[0])
            db.update_employee(eid, data)
            self.refresh()
            self.app.dashboard_tab.refresh()
        FormDialog(self, f"Edit Employee - {row['full_name']}", fields, initial, save, width=600)

    def delete_employee(self):
        eid = self._selected_id()
        if not eid:
            messagebox.showinfo("Select", "Select an employee first.")
            return
        row = db.get_employee(eid)
        if messagebox.askyesno("Confirm delete", f"Delete employee '{row['full_name']}'?"):
            db.delete_employee(eid)
            self.refresh()
            self.app.dashboard_tab.refresh()

    def view_documents(self):
        eid = self._selected_id()
        if not eid:
            messagebox.showinfo("Select", "Select an employee first.")
            return
        self.app.notebook.select(self.app.documents_tab)
        self.app.documents_tab.filter_to_owner("employee", eid)


# ============================================================== OTHER DOCS
class DocumentsTab(ttk.Frame):
    """Custom / ad-hoc documents linked to a company or an employee."""

    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.owner_type_var = tk.StringVar(value="company")
        self.owner_var = tk.StringVar()

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Label(toolbar, text="Link to:", font=FONT_BOLD).pack(side="left")
        ttk.Combobox(toolbar, textvariable=self.owner_type_var, state="readonly", width=10,
                     values=["company", "employee"]).pack(side="left", padx=4)
        self.owner_combo = ttk.Combobox(toolbar, textvariable=self.owner_var, state="readonly", width=30)
        self.owner_combo.pack(side="left", padx=4)
        self.owner_type_var.trace_add("write", lambda *a: self._refresh_owner_list())
        self.owner_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        ttk.Button(toolbar, text="+ Add Document", command=self.add_document).pack(side="left", padx=10)
        ttk.Button(toolbar, text="Edit", command=self.edit_document).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Delete", command=self.delete_document).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Show All", command=self.show_all).pack(side="left", padx=10)

        columns = ("id", "owner", "doc_name", "doc_no", "issue", "expiry", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=20)
        headers = ["ID", "Linked To", "Document Name", "Doc. No.", "Issue Date", "Expiry Date", "Status"]
        widths = [40, 220, 220, 130, 110, 110, 90]
        for c, h, w in zip(columns, headers, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")
        self.tree.column("id", width=40, stretch=False)
        self.tree.pack(fill="both", expand=True)
        configure_status_tags(self.tree)
        self.tree.bind("<Double-1>", lambda e: self.edit_document())

        self._owner_map = {}
        self._show_all = True
        self._refresh_owner_list()

    def _refresh_owner_list(self):
        if self.owner_type_var.get() == "company":
            rows = db.list_companies()
            self._owner_map = {c["company_name"]: c["id"] for c in rows}
        else:
            rows = db.list_employees()
            self._owner_map = {f"{e['full_name']} ({e['company_name'] or 'no company'})": e["id"] for e in rows}
        self.owner_combo["values"] = list(self._owner_map.keys())
        self.refresh()

    def filter_to_owner(self, owner_type, owner_id):
        self.owner_type_var.set(owner_type)
        self._refresh_owner_list()
        for label, oid in self._owner_map.items():
            if oid == owner_id:
                self.owner_var.set(label)
                break
        self._show_all = False
        self.refresh()

    def show_all(self):
        self._show_all = True
        self.owner_var.set("")
        self.refresh()

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        owner_type = self.owner_type_var.get()
        owner_id = self._owner_map.get(self.owner_var.get()) if not self._show_all else None
        rows = db.list_custom_documents(owner_type=None if self._show_all else owner_type,
                                         owner_id=owner_id)
        companies = {c["id"]: c["company_name"] for c in db.list_companies()}
        employees = {e["id"]: e["full_name"] for e in db.list_employees()}
        for d in rows:
            owner_label = (companies.get(d["owner_id"], "(deleted company)") if d["owner_type"] == "company"
                            else employees.get(d["owner_id"], "(deleted employee)"))
            status = utils.STATUS_UNKNOWN
            if d["expiry_date"]:
                status, _ = utils.classify(d["expiry_date"])
            self.tree.insert("", "end", iid=str(d["id"]),
                              values=(d["id"], f"[{d['owner_type']}] {owner_label}", d["document_name"],
                                      d["document_no"] or "-", utils.fmt_date_display(d["issue_date"]),
                                      utils.fmt_date_display(d["expiry_date"]), status),
                              tags=(utils.STATUS_ROW_TAGS[status],))

    def _selected_id(self):
        sel = self.tree.selection()
        return int(sel[0]) if sel else None

    def add_document(self):
        if not self._owner_map:
            messagebox.showwarning("Nothing to link", "Add a company or employee first.")
            return
        owner_type = self.owner_type_var.get()
        default_owner = self.owner_var.get() or list(self._owner_map.keys())[0]
        fields = [
            ("owner_type", "Linked To Type", "combo", ["company", "employee"]),
            ("owner_label", "Linked To *", "combo", list(self._owner_map.keys())),
            ("document_name", "Document Name *", "text"),
            ("document_no", "Document No.", "text"),
            ("issue_date", "Issue Date", "date"),
            ("expiry_date", "Expiry Date", "date"),
            ("status", "Status", "combo", ["Active", "Cancelled"]),
            ("notes", "Notes", "textarea"),
        ]

        def save(data):
            if not data.get("document_name", "").strip():
                messagebox.showerror("Required", "Document name is required.")
                return False
            owner_map = self._owner_map
            data["owner_id"] = owner_map.get(data.pop("owner_label"))
            if not data["owner_id"]:
                messagebox.showerror("Required", "Select who this document belongs to.")
                return False
            db.add_custom_document(data)
            self.refresh()
            self.app.dashboard_tab.refresh()
        FormDialog(self, "Add Other Document", fields,
                   initial={"owner_type": owner_type, "owner_label": default_owner}, on_save=save)

    def edit_document(self):
        did = self._selected_id()
        if not did:
            messagebox.showinfo("Select", "Select a document first.")
            return
        row = None
        for r in db.list_custom_documents():
            if r["id"] == did:
                row = r
                break
        if not row:
            return

        if row["owner_type"] == "company":
            owner_map = {c["company_name"]: c["id"] for c in db.list_companies()}
        else:
            owner_map = {f"{e['full_name']} ({e['company_name'] or 'no company'})": e["id"]
                         for e in db.list_employees()}
        current_label = next((k for k, v in owner_map.items() if v == row["owner_id"]), "")

        fields = [
            ("owner_type", "Linked To Type", "readonly"),
            ("owner_label", "Linked To *", "combo", list(owner_map.keys()) or [current_label]),
            ("document_name", "Document Name *", "text"),
            ("document_no", "Document No.", "text"),
            ("issue_date", "Issue Date", "date"),
            ("expiry_date", "Expiry Date", "date"),
            ("status", "Status", "combo", ["Active", "Cancelled"]),
            ("notes", "Notes", "textarea"),
        ]
        initial = {k: row[k] for k in row.keys()}
        initial["owner_label"] = current_label

        def save(data):
            data["owner_id"] = owner_map.get(data.pop("owner_label"), row["owner_id"])
            data["owner_type"] = row["owner_type"]
            db.update_custom_document(did, data)
            self.refresh()
            self.app.dashboard_tab.refresh()
        FormDialog(self, f"Edit Document - {row['document_name']}", fields, initial, save)

    def delete_document(self):
        did = self._selected_id()
        if not did:
            messagebox.showinfo("Select", "Select a document first.")
            return
        if messagebox.askyesno("Confirm delete", "Delete this document record?"):
            db.delete_custom_document(did)
            self.refresh()
            self.app.dashboard_tab.refresh()


# ============================================================== REPORTS
class ReportsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.status_var = tk.StringVar(value="All")
        self.include_cancelled_var = tk.BooleanVar(value=False)

        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", pady=(0, 6))
        ttk.Label(toolbar, text="Status filter:", font=FONT_BOLD).pack(side="left")
        ttk.Combobox(toolbar, textvariable=self.status_var, state="readonly", width=14,
                     values=["All", utils.STATUS_EXPIRED, utils.STATUS_CRITICAL, utils.STATUS_WARNING,
                             utils.STATUS_UPCOMING, utils.STATUS_OK]).pack(side="left", padx=6)
        ttk.Checkbutton(toolbar, text="Include cancelled records", variable=self.include_cancelled_var,
                         command=self.refresh).pack(side="left", padx=10)
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Export to CSV", command=self.export_csv).pack(side="right", padx=4)
        ttk.Button(toolbar, text="Export to Excel", command=self.export_excel).pack(side="right", padx=4)

        columns = ("category", "company", "name", "document", "number", "expiry", "status", "days")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=22)
        headers = ["Type", "Company", "Employee / Company", "Document", "No.", "Expiry", "Status", "Days Left"]
        widths = [70, 190, 190, 220, 130, 90, 90, 80]
        for c, h, w in zip(columns, headers, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True)
        configure_status_tags(self.tree)

        self._items_cache = []

    def refresh(self):
        items = utils.gather_all_tracked_documents(active_only=not self.include_cancelled_var.get())
        f = self.status_var.get()
        if f != "All":
            items = [it for it in items if it["status"] == f]
        self._items_cache = items
        self.tree.delete(*self.tree.get_children())
        for it in items:
            days = it["days_left"]
            days_txt = "-" if days is None else (f"{days}d overdue" if days < 0 else f"{days}")
            self.tree.insert("", "end",
                              values=(it["category"], it["company_name"], it["owner_name"],
                                      it["document"], it["number"], utils.fmt_date_display(it["expiry"]),
                                      it["status"], days_txt),
                              tags=(utils.STATUS_ROW_TAGS[it["status"]],))

    def export_csv(self):
        if not self._items_cache:
            self.refresh()
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                             filetypes=[("CSV file", "*.csv")],
                                             initialfile="document_expiry_report.csv")
        if not path:
            return
        exp.export_csv(self._items_cache, path)
        messagebox.showinfo("Exported", f"Report exported to:\n{path}")

    def export_excel(self):
        if not self._items_cache:
            self.refresh()
        if not exp.HAVE_OPENPYXL:
            messagebox.showwarning(
                "openpyxl not installed",
                "Excel export needs the 'openpyxl' package.\n\n"
                "Install it with:\n    pip install openpyxl\n\n"
                "Exporting to CSV instead is always available.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                             filetypes=[("Excel file", "*.xlsx")],
                                             initialfile="document_expiry_report.xlsx")
        if not path:
            return
        exp.export_excel(self._items_cache, path)
        messagebox.showinfo("Exported", f"Report exported to:\n{path}")


# ============================================================== SETTINGS
class SettingsTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=20)
        self.app = app

        ttk.Label(self, text="Alert Thresholds (days before expiry)", font=FONT_SUBHEADER).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        self.critical_var = tk.StringVar(value=db.get_setting("alert_critical_days", "15"))
        self.warning_var = tk.StringVar(value=db.get_setting("alert_warning_days", "30"))
        self.upcoming_var = tk.StringVar(value=db.get_setting("alert_upcoming_days", "60"))

        self._labeled_entry("Critical (red) if expiry within:", self.critical_var, 1)
        self._labeled_entry("Warning (orange) if expiry within:", self.warning_var, 2)
        self._labeled_entry("Upcoming (yellow) if expiry within:", self.upcoming_var, 3)

        ttk.Button(self, text="Save Settings", command=self.save_settings, style="Accent.TButton").grid(
            row=4, column=0, sticky="w", pady=16)

        ttk.Separator(self).grid(row=5, column=0, columnspan=2, sticky="ew", pady=16)

        ttk.Label(self, text="Database Location", font=FONT_SUBHEADER).grid(row=6, column=0, sticky="w")
        ttk.Label(self, text=db.DB_PATH, font=FONT_NORMAL, foreground="#555").grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(2, 12))

        ttk.Label(self, text="Recent Activity Log", font=FONT_SUBHEADER).grid(row=8, column=0, sticky="w")
        self.log_box = tk.Listbox(self, width=100, height=14, font=("Consolas", 9))
        self.log_box.grid(row=9, column=0, columnspan=2, sticky="w", pady=6)
        ttk.Button(self, text="Refresh Log", command=self.refresh_log).grid(row=10, column=0, sticky="w")

        self.refresh_log()

    def _labeled_entry(self, label, var, row):
        ttk.Label(self, text=label, width=32).grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(self, textvariable=var, width=8).grid(row=row, column=1, sticky="w")

    def save_settings(self):
        try:
            crit, warn, up = int(self.critical_var.get()), int(self.warning_var.get()), int(self.upcoming_var.get())
        except ValueError:
            messagebox.showerror("Invalid", "Thresholds must be whole numbers.")
            return
        if not (crit <= warn <= up):
            messagebox.showerror("Invalid", "Values must satisfy: Critical \u2264 Warning \u2264 Upcoming.")
            return
        db.set_setting("alert_critical_days", str(crit))
        db.set_setting("alert_warning_days", str(warn))
        db.set_setting("alert_upcoming_days", str(up))
        messagebox.showinfo("Saved", "Settings saved.")
        self.app.refresh_all()

    def refresh_log(self):
        self.log_box.delete(0, "end")
        for row in db.get_activity_log(200):
            self.log_box.insert("end", f"{row['ts']}  {row['action']:8}  {row['entity']:16}  "
                                        f"#{row['entity_id'] or '-':<5} {row['details']}")
