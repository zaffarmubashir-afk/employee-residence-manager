"""
database.py
------------
SQLite data layer for the UAE Employee Residence & Company Document
Management System.

All dates are stored as ISO strings 'YYYY-MM-DD' so they sort/compare
correctly as plain text.

Tables
------
companies         : one row per legal entity / trade license holder
employees         : one row per employee, linked to a company
custom_documents  : free-form extra documents linked to a company OR employee
                     (insurance, addendum, VAT cert, DED permits, etc.)
settings          : simple key/value app settings (alert thresholds etc.)
activity_log      : simple audit trail of add/edit/delete/renew actions
"""

import sqlite3
import os
import sys
import shutil
from datetime import date

APP_NAME = "EmployeeResidenceManager"


def _app_data_dir():
    """A per-user, per-machine folder that is NEVER inside the app/exe
    folder and NEVER inside a PyInstaller --onefile temp-extraction
    folder. This is the fix for "my data disappears when I close and
    reopen the app": a onefile .exe unpacks itself into a fresh temp
    directory (sys._MEIPASS) on every launch and deletes it on exit, so
    anything stored relative to the app's own path is wiped every time.
    Windows: %APPDATA%\\EmployeeResidenceManager
    macOS:   ~/Library/Application Support/EmployeeResidenceManager
    Linux:   $XDG_DATA_HOME/EmployeeResidenceManager (or ~/.local/share/...)
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


DATA_DIR = _app_data_dir()
DB_PATH = os.path.join(DATA_DIR, "erms.db")
LOGO_DIR = os.path.join(DATA_DIR, "branding")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")


def _legacy_db_candidates():
    """Where earlier versions of this app used to store erms.db, so we
    can migrate anyone's existing data into the new, safe location."""
    candidates = []
    try:
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            candidates.append(os.path.join(exe_dir, "data", "erms.db"))
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                candidates.append(os.path.join(meipass, "data", "erms.db"))
        else:
            src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates.append(os.path.join(src_dir, "data", "erms.db"))
    except Exception:
        pass
    return candidates


def _migrate_legacy_db():
    """One-time, best-effort migration. Runs only if the new location has
    no database yet, so it never overwrites newer data."""
    if os.path.exists(DB_PATH):
        return
    for legacy_path in _legacy_db_candidates():
        try:
            if os.path.exists(legacy_path) and os.path.getsize(legacy_path) > 0:
                shutil.copy2(legacy_path, DB_PATH)
                return
        except Exception:
            continue


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name        TEXT NOT NULL,
    legal_type           TEXT,              -- Mainland / Free Zone / Offshore
    free_zone_name        TEXT,
    trade_license_no      TEXT,
    trade_license_expiry  TEXT,
    establishment_card_no     TEXT,
    establishment_card_expiry TEXT,
    mohre_establishment_no    TEXT,
    immigration_file_no       TEXT,
    chamber_of_commerce_no    TEXT,
    chamber_of_commerce_expiry TEXT,
    tenancy_ejari_no          TEXT,
    tenancy_ejari_expiry      TEXT,
    vat_trn                   TEXT,
    address                TEXT,
    phone                  TEXT,
    email                  TEXT,
    status                 TEXT DEFAULT 'Active',   -- Active / Cancelled / Suspended
    notes                  TEXT,
    created_at             TEXT,
    updated_at              TEXT
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id          INTEGER NOT NULL,
    employee_code         TEXT,
    full_name             TEXT NOT NULL,
    nationality            TEXT,
    gender                 TEXT,
    date_of_birth          TEXT,
    job_title               TEXT,
    date_of_joining         TEXT,
    passport_no              TEXT,
    passport_expiry          TEXT,
    entry_permit_no          TEXT,
    entry_permit_expiry       TEXT,
    residence_visa_no         TEXT,
    residence_visa_expiry     TEXT,
    visa_sponsor              TEXT,     -- usually = company, or 'Own/Family'
    emirates_id_no             TEXT,
    emirates_id_expiry          TEXT,
    labour_card_no               TEXT,   -- MOHRE work permit
    labour_card_expiry            TEXT,
    employment_contract_no         TEXT,
    employment_contract_expiry      TEXT,
    medical_test_date                TEXT,
    medical_test_expiry               TEXT,
    insurance_policy_no                TEXT,
    insurance_expiry                    TEXT,
    basic_salary                          REAL,
    status                                 TEXT DEFAULT 'Active', -- Active/Cancelled/Absconded/On Leave
    cancellation_date                       TEXT,
    phone                                   TEXT,
    email                                   TEXT,
    notes                                   TEXT,
    created_at                              TEXT,
    updated_at                              TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS custom_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_type     TEXT NOT NULL,   -- 'company' or 'employee'
    owner_id        INTEGER NOT NULL,
    document_name     TEXT NOT NULL,
    document_no        TEXT,
    issue_date          TEXT,
    expiry_date          TEXT,
    status                TEXT DEFAULT 'Active',
    notes                 TEXT,
    created_at             TEXT,
    updated_at              TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT,
    action     TEXT,
    entity      TEXT,
    entity_id    INTEGER,
    details       TEXT
);
"""

DEFAULT_SETTINGS = {
    "alert_critical_days": "15",   # red   : expires within this many days (or already expired)
    "alert_warning_days": "30",    # orange: expires within this many days
    "alert_upcoming_days": "60",   # yellow: expires within this many days
    "company_name_header": "My Company Group",
    "reminder_email": "",
    "company_logo_path": "",
    "shortcut_offered": "0",
}


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(LOGO_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    _migrate_legacy_db()
    conn = get_connection()
    conn.executescript(SCHEMA)
    for k, v in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
    conn.commit()
    conn.close()


def now_str():
    return date.today().isoformat()


def log_activity(action, entity, entity_id, details=""):
    conn = get_connection()
    conn.execute(
        "INSERT INTO activity_log (ts, action, entity, entity_id, details) VALUES (?,?,?,?,?)",
        (now_str(), action, entity, entity_id, details),
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- settings
def get_setting(key, default=""):
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) "
                 "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- companies
COMPANY_FIELDS = [
    "company_name", "legal_type", "free_zone_name", "trade_license_no", "trade_license_expiry",
    "establishment_card_no", "establishment_card_expiry", "mohre_establishment_no",
    "immigration_file_no", "chamber_of_commerce_no", "chamber_of_commerce_expiry",
    "tenancy_ejari_no", "tenancy_ejari_expiry", "vat_trn", "address", "phone", "email",
    "status", "notes",
]


def add_company(data: dict):
    conn = get_connection()
    cols = COMPANY_FIELDS + ["created_at", "updated_at"]
    vals = [data.get(c, "") for c in COMPANY_FIELDS] + [now_str(), now_str()]
    placeholders = ",".join(["?"] * len(cols))
    cur = conn.execute(f"INSERT INTO companies ({','.join(cols)}) VALUES ({placeholders})", vals)
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    log_activity("CREATE", "company", new_id, data.get("company_name", ""))
    return new_id


def update_company(company_id, data: dict):
    conn = get_connection()
    sets = ",".join([f"{c}=?" for c in COMPANY_FIELDS])
    vals = [data.get(c, "") for c in COMPANY_FIELDS] + [now_str(), company_id]
    conn.execute(f"UPDATE companies SET {sets}, updated_at=? WHERE id=?", vals)
    conn.commit()
    conn.close()
    log_activity("UPDATE", "company", company_id, data.get("company_name", ""))


def delete_company(company_id):
    conn = get_connection()
    conn.execute("DELETE FROM companies WHERE id=?", (company_id,))
    conn.commit()
    conn.close()
    log_activity("DELETE", "company", company_id, "")


def get_company(company_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM companies WHERE id=?", (company_id,)).fetchone()
    conn.close()
    return row


def list_companies(search=""):
    conn = get_connection()
    if search:
        like = f"%{search}%"
        rows = conn.execute(
            "SELECT * FROM companies WHERE company_name LIKE ? OR trade_license_no LIKE ? "
            "ORDER BY company_name", (like, like)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM companies ORDER BY company_name").fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------------- employees
EMPLOYEE_FIELDS = [
    "company_id", "employee_code", "full_name", "nationality", "gender", "date_of_birth",
    "job_title", "date_of_joining", "passport_no", "passport_expiry",
    "entry_permit_no", "entry_permit_expiry", "residence_visa_no", "residence_visa_expiry",
    "visa_sponsor", "emirates_id_no", "emirates_id_expiry", "labour_card_no", "labour_card_expiry",
    "employment_contract_no", "employment_contract_expiry", "medical_test_date", "medical_test_expiry",
    "insurance_policy_no", "insurance_expiry", "basic_salary", "status", "cancellation_date",
    "phone", "email", "notes",
]


def add_employee(data: dict):
    conn = get_connection()
    cols = EMPLOYEE_FIELDS + ["created_at", "updated_at"]
    vals = [data.get(c, "") for c in EMPLOYEE_FIELDS] + [now_str(), now_str()]
    placeholders = ",".join(["?"] * len(cols))
    cur = conn.execute(f"INSERT INTO employees ({','.join(cols)}) VALUES ({placeholders})", vals)
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    log_activity("CREATE", "employee", new_id, data.get("full_name", ""))
    return new_id


def update_employee(employee_id, data: dict):
    conn = get_connection()
    sets = ",".join([f"{c}=?" for c in EMPLOYEE_FIELDS])
    vals = [data.get(c, "") for c in EMPLOYEE_FIELDS] + [now_str(), employee_id]
    conn.execute(f"UPDATE employees SET {sets}, updated_at=? WHERE id=?", vals)
    conn.commit()
    conn.close()
    log_activity("UPDATE", "employee", employee_id, data.get("full_name", ""))


def delete_employee(employee_id):
    conn = get_connection()
    conn.execute("DELETE FROM employees WHERE id=?", (employee_id,))
    conn.commit()
    conn.close()
    log_activity("DELETE", "employee", employee_id, "")


def get_employee(employee_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
    conn.close()
    return row


def list_employees(search="", company_id=None, status=None):
    conn = get_connection()
    q = "SELECT e.*, c.company_name FROM employees e LEFT JOIN companies c ON e.company_id = c.id WHERE 1=1"
    params = []
    if search:
        q += " AND (e.full_name LIKE ? OR e.employee_code LIKE ? OR e.passport_no LIKE ? OR e.emirates_id_no LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like, like]
    if company_id:
        q += " AND e.company_id = ?"
        params.append(company_id)
    if status and status != "All":
        q += " AND e.status = ?"
        params.append(status)
    q += " ORDER BY e.full_name"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


# ---------------------------------------------------------- custom documents
def add_custom_document(data: dict):
    conn = get_connection()
    cols = ["owner_type", "owner_id", "document_name", "document_no", "issue_date",
            "expiry_date", "status", "notes", "created_at", "updated_at"]
    vals = [data.get(c, "") for c in cols[:-2]] + [now_str(), now_str()]
    placeholders = ",".join(["?"] * len(cols))
    cur = conn.execute(f"INSERT INTO custom_documents ({','.join(cols)}) VALUES ({placeholders})", vals)
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    log_activity("CREATE", "custom_document", new_id, data.get("document_name", ""))
    return new_id


def update_custom_document(doc_id, data: dict):
    conn = get_connection()
    cols = ["owner_type", "owner_id", "document_name", "document_no", "issue_date",
            "expiry_date", "status", "notes"]
    sets = ",".join([f"{c}=?" for c in cols])
    vals = [data.get(c, "") for c in cols] + [now_str(), doc_id]
    conn.execute(f"UPDATE custom_documents SET {sets}, updated_at=? WHERE id=?", vals)
    conn.commit()
    conn.close()
    log_activity("UPDATE", "custom_document", doc_id, data.get("document_name", ""))


def delete_custom_document(doc_id):
    conn = get_connection()
    conn.execute("DELETE FROM custom_documents WHERE id=?", (doc_id,))
    conn.commit()
    conn.close()
    log_activity("DELETE", "custom_document", doc_id, "")


def list_custom_documents(owner_type=None, owner_id=None):
    conn = get_connection()
    q = "SELECT * FROM custom_documents WHERE 1=1"
    params = []
    if owner_type:
        q += " AND owner_type=?"
        params.append(owner_type)
    if owner_id:
        q += " AND owner_id=?"
        params.append(owner_id)
    q += " ORDER BY expiry_date"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def get_activity_log(limit=200):
    conn = get_connection()
    rows = conn.execute("SELECT * FROM activity_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows
