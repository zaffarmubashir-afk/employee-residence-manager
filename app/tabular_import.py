"""
tabular_import.py
------------------
Import employees from a CSV or Excel spreadsheet - a completely
reliable alternative to PDF/photo OCR for bulk data entry. Useful when:
  - you (or an assistant) have already transcribed/typed the employee
    list into a spreadsheet, or
  - a scanned/photographed document is too low-quality for OCR to read
    (small text, low resolution, coloured/light text) and retyping the
    handful of unreadable rows into a spreadsheet is faster than fixing
    every cell by hand in the review table.

Column headers are matched flexibly (case-insensitive, common
synonyms) so the file doesn't need to use our exact field names.
"""
import csv
import os

from app.pdf_extract import _norm_date

try:
    import openpyxl
    HAVE_OPENPYXL = True
except ImportError:
    HAVE_OPENPYXL = False

# our field key -> list of header names/synonyms that map to it
HEADER_ALIASES = {
    "full_name": ["full name", "name", "person name", "employee name"],
    "employee_code": ["employee code", "emp code", "staff no", "staff number"],
    "nationality": ["nationality"],
    "gender": ["gender", "sex"],
    "date_of_birth": ["date of birth", "dob", "birth date"],
    "job_title": ["job name", "job title", "designation", "position"],
    "date_of_joining": ["date of joining", "doj", "joining date"],
    "passport_no": ["passport number", "passport no", "passport"],
    "passport_expiry": ["passport expiry", "passport exp"],
    "entry_permit_no": ["entry permit no", "entry permit number"],
    "entry_permit_expiry": ["entry permit expiry"],
    "residence_visa_no": ["residence visa no", "visa number", "visa no"],
    "residence_visa_expiry": ["visa expiry", "residence visa expiry"],
    "visa_sponsor": ["visa sponsor", "sponsor"],
    "emirates_id_no": ["emirates id no", "emirates id number", "eid", "id number"],
    "emirates_id_expiry": ["emirates id expiry", "eid expiry"],
    "labour_card_no": ["labour card no", "labour card number", "card number", "labor card no"],
    "labour_card_expiry": ["labour card expiry", "card expiry", "labor card expiry"],
    "employment_contract_no": ["contract no", "contract number", "employment contract no"],
    "employment_contract_expiry": ["contract expiry", "employment contract expiry"],
    "medical_test_date": ["medical test date", "medical date"],
    "medical_test_expiry": ["medical test expiry", "medical expiry"],
    "insurance_policy_no": ["insurance policy no", "insurance no"],
    "insurance_expiry": ["insurance expiry"],
    "basic_salary": ["basic salary", "salary"],
    "status": ["status"],
    "cancellation_date": ["cancellation date"],
    "phone": ["phone", "mobile", "phone number", "mobile number"],
    "email": ["email", "email address"],
    "notes": ["notes", "remarks", "card type", "contract type"],
}


DATE_FIELDS = {
    "date_of_birth", "date_of_joining", "passport_expiry", "entry_permit_expiry",
    "residence_visa_expiry", "emirates_id_expiry", "labour_card_expiry",
    "employment_contract_expiry", "medical_test_date", "medical_test_expiry",
    "insurance_expiry", "cancellation_date",
}


def _normalize_row_dates(row):
    """The database stores dates as YYYY-MM-DD. Spreadsheets are usually
    DD/MM/YYYY (or already YYYY-MM-DD) - convert in place, leaving a
    value that doesn't parse as-is so it's visible/fixable on review
    rather than silently dropped."""
    for k in DATE_FIELDS:
        if k in row and row[k]:
            normalized = _norm_date(row[k])
            if normalized:
                row[k] = normalized
    return row


def _normalize_header(h):
    return (h or "").strip().lower().replace("_", " ").replace("-", " ")


def _build_header_map(headers):
    """Return {column_index: field_key} for the headers that match a
    known alias. Unmatched columns are ignored."""
    lookup = {}
    for field_key, aliases in HEADER_ALIASES.items():
        for a in aliases:
            lookup[a] = field_key

    mapping = {}
    for i, h in enumerate(headers):
        norm = _normalize_header(h)
        if norm in lookup:
            mapping[i] = lookup[norm]
    return mapping


def read_tabular_file(path):
    """Return (rows, unmatched_headers) where rows is a list of dicts
    using our field keys, and unmatched_headers lists any column titles
    that couldn't be matched (so the UI can warn about them)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return _read_csv(path)
    if ext in (".xlsx", ".xlsm"):
        return _read_xlsx(path)
    raise ValueError(f"Unsupported spreadsheet format: {ext}")


def _read_csv(path):
    with open(path, "r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows_raw = list(reader)
    if not rows_raw:
        return [], []
    headers = rows_raw[0]
    col_map = _build_header_map(headers)
    unmatched = [h for i, h in enumerate(headers) if i not in col_map and h.strip()]

    out = []
    for raw_row in rows_raw[1:]:
        if not any(c.strip() for c in raw_row):
            continue
        row = {}
        for i, val in enumerate(raw_row):
            key = col_map.get(i)
            if key:
                _set_field(row, key, val.strip())
        if row:
            out.append(_normalize_row_dates(row))
    return out, unmatched


def _set_field(row, key, value):
    """Two source columns (e.g. 'Card Type' and 'Contract Type') can both
    map to the same field (notes) - combine rather than overwrite."""
    if not value:
        return
    if key in row and row[key] and row[key] != value:
        row[key] = f"{row[key]} | {value}"
    else:
        row[key] = value


def _read_xlsx(path):
    if not HAVE_OPENPYXL:
        raise RuntimeError("Reading .xlsx files needs the openpyxl package: pip install openpyxl "
                            "(or save your spreadsheet as .csv instead, which always works).")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        headers = [str(h) if h is not None else "" for h in next(rows_iter)]
    except StopIteration:
        return [], []
    col_map = _build_header_map(headers)
    unmatched = [h for i, h in enumerate(headers) if i not in col_map and h.strip()]

    out = []
    for raw_row in rows_iter:
        if raw_row is None or not any(c not in (None, "") for c in raw_row):
            continue
        row = {}
        for i, val in enumerate(raw_row):
            key = col_map.get(i)
            if key and val is not None:
                _set_field(row, key, str(val).strip())
        if row:
            out.append(_normalize_row_dates(row))
    wb.close()
    return out, unmatched
