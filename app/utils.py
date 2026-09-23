"""
utils.py
--------
Shared helpers: date parsing, days-to-expiry, status/color classification,
and the master routine that collects EVERY trackable document (company +
employee + custom) into one flat list for the Dashboard / Reports screens.
"""

from datetime import datetime, date
from app import database as db

DATE_FMT = "%Y-%m-%d"

STATUS_EXPIRED = "Expired"
STATUS_CRITICAL = "Critical"     # e.g. <= 15 days
STATUS_WARNING = "Warning"       # e.g. <= 30 days
STATUS_UPCOMING = "Upcoming"     # e.g. <= 60 days
STATUS_OK = "Valid"
STATUS_UNKNOWN = "No Date"

STATUS_COLORS = {
    STATUS_EXPIRED: "#c0392b",
    STATUS_CRITICAL: "#e74c3c",
    STATUS_WARNING: "#e67e22",
    STATUS_UPCOMING: "#f1c40f",
    STATUS_OK: "#27ae60",
    STATUS_UNKNOWN: "#95a5a6",
}

STATUS_ROW_TAGS = {
    STATUS_EXPIRED: "row_expired",
    STATUS_CRITICAL: "row_critical",
    STATUS_WARNING: "row_warning",
    STATUS_UPCOMING: "row_upcoming",
    STATUS_OK: "row_ok",
    STATUS_UNKNOWN: "row_unknown",
}


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), DATE_FMT).date()
    except (ValueError, AttributeError):
        return None


def days_until(expiry_str, today=None):
    d = parse_date(expiry_str)
    if d is None:
        return None
    today = today or date.today()
    return (d - today).days


def classify(expiry_str, today=None):
    """Return (status_label, days_left_or_None)."""
    days = days_until(expiry_str, today)
    if days is None:
        return STATUS_UNKNOWN, None

    crit = int(db.get_setting("alert_critical_days", "15"))
    warn = int(db.get_setting("alert_warning_days", "30"))
    up = int(db.get_setting("alert_upcoming_days", "60"))

    if days < 0:
        return STATUS_EXPIRED, days
    if days <= crit:
        return STATUS_CRITICAL, days
    if days <= warn:
        return STATUS_WARNING, days
    if days <= up:
        return STATUS_UPCOMING, days
    return STATUS_OK, days


def fmt_date_display(s):
    d = parse_date(s)
    return d.strftime("%d-%b-%Y") if d else "-"


# --------------------------------------------------------------------------
# The "tracked document" model used across Dashboard / Reports:
#   dict(category, owner_type, owner_id, owner_name, company_name,
#        document, number, expiry, status, days_left)
# --------------------------------------------------------------------------

COMPANY_DOC_MAP = [
    ("Trade License", "trade_license_no", "trade_license_expiry"),
    ("Establishment / Immigration Card", "establishment_card_no", "establishment_card_expiry"),
    ("Chamber of Commerce Certificate", "chamber_of_commerce_no", "chamber_of_commerce_expiry"),
    ("Tenancy Contract (Ejari)", "tenancy_ejari_no", "tenancy_ejari_expiry"),
]

EMPLOYEE_DOC_MAP = [
    ("Passport", "passport_no", "passport_expiry"),
    ("Entry Permit", "entry_permit_no", "entry_permit_expiry"),
    ("Residence Visa", "residence_visa_no", "residence_visa_expiry"),
    ("Emirates ID", "emirates_id_no", "emirates_id_expiry"),
    ("Labour Card / Work Permit", "labour_card_no", "labour_card_expiry"),
    ("Employment Contract (MOHRE)", "employment_contract_no", "employment_contract_expiry"),
    ("Medical Fitness Test", None, "medical_test_expiry"),
    ("Health Insurance", "insurance_policy_no", "insurance_expiry"),
]


def gather_all_tracked_documents(active_only=True):
    items = []
    today = date.today()

    companies = db.list_companies()
    comp_by_id = {c["id"]: c for c in companies}
    for c in companies:
        if active_only and c["status"] == "Cancelled":
            continue
        for doc_name, num_field, exp_field in COMPANY_DOC_MAP:
            expiry = c[exp_field]
            if not expiry:
                continue
            status, days = classify(expiry, today)
            items.append({
                "category": "Company",
                "owner_type": "company",
                "owner_id": c["id"],
                "owner_name": c["company_name"],
                "company_name": c["company_name"],
                "document": doc_name,
                "number": c[num_field] if num_field else "",
                "expiry": expiry,
                "status": status,
                "days_left": days,
            })

    employees = db.list_employees()
    for e in employees:
        if active_only and e["status"] in ("Cancelled",):
            continue
        company_name = e["company_name"]
        if not company_name:
            comp = comp_by_id.get(e["company_id"])
            company_name = comp["company_name"] if comp else ""
        for doc_name, num_field, exp_field in EMPLOYEE_DOC_MAP:
            expiry = e[exp_field]
            if not expiry:
                continue
            status, days = classify(expiry, today)
            items.append({
                "category": "Employee",
                "owner_type": "employee",
                "owner_id": e["id"],
                "owner_name": e["full_name"],
                "company_name": company_name,
                "document": doc_name,
                "number": e[num_field] if num_field else "",
                "expiry": expiry,
                "status": status,
                "days_left": days,
            })

    custom_docs = db.list_custom_documents()
    for d in custom_docs:
        if active_only and d["status"] == "Cancelled":
            continue
        if not d["expiry_date"]:
            continue
        if d["owner_type"] == "company":
            owner = comp_by_id.get(d["owner_id"])
            owner_name = owner["company_name"] if owner else "(deleted company)"
            company_name = owner_name
            category = "Company"
        else:
            emp = db.get_employee(d["owner_id"])
            owner_name = emp["full_name"] if emp else "(deleted employee)"
            company_name = ""
            if emp:
                comp = comp_by_id.get(emp["company_id"])
                company_name = comp["company_name"] if comp else ""
            category = "Employee"
        status, days = classify(d["expiry_date"], today)
        items.append({
            "category": category,
            "owner_type": d["owner_type"],
            "owner_id": d["owner_id"],
            "owner_name": owner_name,
            "company_name": company_name,
            "document": d["document_name"] + " (Other)",
            "number": d["document_no"] or "",
            "expiry": d["expiry_date"],
            "status": status,
            "days_left": days,
        })

    # soonest-expiring first, unknown/valid pushed to the end
    def sort_key(item):
        d = item["days_left"]
        return (d is None, d if d is not None else 0)

    items.sort(key=sort_key)
    return items


def summary_counts(items):
    counts = {STATUS_EXPIRED: 0, STATUS_CRITICAL: 0, STATUS_WARNING: 0,
              STATUS_UPCOMING: 0, STATUS_OK: 0}
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
    return counts
