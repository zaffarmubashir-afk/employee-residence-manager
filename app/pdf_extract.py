"""
pdf_extract.py
---------------
Best-effort extraction of employee identity-document details from an
uploaded file: a text-based PDF, a scanned/photographed PDF, or a plain
photo (JPG/PNG/etc.) of a passport, Emirates ID, residence visa, or
labour card.

Pipeline
--------
1. Get raw text out of the file:
     - PDF with a text layer  -> read it directly (PyMuPDF, or pypdf).
     - PDF with no text layer (i.e. it's a scan) or an image file
       -> OCR it (PyMuPDF/pdf2image to rasterize the page, then
       pytesseract to read the pixels).
2. Look for a passport Machine-Readable Zone (MRZ) first - the two
   lines of <<<< text at the bottom of a passport bio page. It's far
   more reliable than free text because it's fixed-width and
   standardised worldwide (ICAO 9303).
3. Fall back to label-based regex matching for Emirates ID numbers,
   "Date of Birth", "Nationality", document expiry dates, etc.
4. Return a dict using the same field names as app.database.EMPLOYEE_FIELDS
   so a result can be dropped straight into an Add/Edit Employee form.

Nothing here is guaranteed to be perfect - OCR misreads characters and
document layouts vary between countries and issuers. The app always
shows extracted values in an editable review table before anything is
saved to the database (see app/import_dialog.py).

Every heavy dependency is optional and imported defensively. With
none of them installed, extract_text() simply returns "" and the UI
tells the user what to install for which capability.
"""
import io
import os
import re
from datetime import date

# ---------------------------------------------------------- optional deps
try:
    import fitz  # PyMuPDF - text extraction + page rasterizing, no external binary
    HAVE_FITZ = True
except ImportError:
    HAVE_FITZ = False

try:
    import pypdf  # pure-python text extraction fallback
    HAVE_PYPDF = True
except ImportError:
    HAVE_PYPDF = False

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

try:
    import pytesseract  # needs the separate Tesseract-OCR program installed too
    HAVE_TESSERACT = True
except ImportError:
    HAVE_TESSERACT = False

try:
    from pdf2image import convert_from_path  # needs the separate Poppler binaries
    HAVE_PDF2IMAGE = True
except ImportError:
    HAVE_PDF2IMAGE = False

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
PDF_EXT = ".pdf"

CAN_READ_TEXT_PDF = HAVE_FITZ or HAVE_PYPDF
CAN_RASTERIZE_PDF = HAVE_FITZ or HAVE_PDF2IMAGE
CAN_OCR = HAVE_TESSERACT and HAVE_PIL


def capability_report():
    """List of (label, ok, hint) tuples for display in Settings."""
    return [
        ("Read text-based PDFs (Passport/Visa PDFs saved from a computer)",
         CAN_READ_TEXT_PDF, "pip install pymupdf  (or: pip install pypdf)"),
        ("Read scanned PDFs and photos (OCR)",
         CAN_OCR and CAN_RASTERIZE_PDF, "pip install pymupdf pillow pytesseract, "
         "and install the Tesseract-OCR program itself (see README)."),
    ]


# ------------------------------------------------------------- text layer
def _ocr_image(img):
    if not HAVE_TESSERACT:
        return ""
    try:
        return pytesseract.image_to_string(img)
    except Exception:
        return ""


def _pdf_page_to_image(path, page_index, zoom=3.0):
    if HAVE_FITZ:
        try:
            doc = fitz.open(path)
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
            img = Image.open(io.BytesIO(pix.tobytes("png"))) if HAVE_PIL else None
            doc.close()
            return img
        except Exception:
            return None
    if HAVE_PDF2IMAGE:
        try:
            dpi = int(150 * zoom)
            pages = convert_from_path(path, dpi=dpi, first_page=page_index + 1, last_page=page_index + 1)
            return pages[0] if pages else None
        except Exception:
            return None
    return None


MAX_OCR_PAGES = 5  # keep bulk imports of thousands of files fast


def extract_text(path):
    """Return (text, used_ocr: bool)."""
    ext = os.path.splitext(path)[1].lower()

    if ext in IMAGE_EXTS:
        if not (HAVE_PIL and HAVE_TESSERACT):
            return "", False
        try:
            img = Image.open(path)
        except Exception:
            return "", False
        return _ocr_image(img), True

    if ext == PDF_EXT:
        text, n_pages = "", 0
        if HAVE_FITZ:
            try:
                doc = fitz.open(path)
                text = "\n".join(p.get_text() for p in doc)
                n_pages = len(doc)
                doc.close()
            except Exception:
                text, n_pages = "", 0
        elif HAVE_PYPDF:
            try:
                reader = pypdf.PdfReader(path)
                text = "\n".join((p.extract_text() or "") for p in reader.pages)
                n_pages = len(reader.pages)
            except Exception:
                text, n_pages = "", 0

        if text.strip():
            return text, False

        # No text layer found -> treat it as a scan and OCR each page.
        if CAN_OCR and CAN_RASTERIZE_PDF:
            chunks = []
            for i in range(min(n_pages or 1, MAX_OCR_PAGES)):
                img = _pdf_page_to_image(path, i)
                if img is not None:
                    chunks.append(_ocr_image(img))
            return "\n".join(chunks), True
        return "", False

    return "", False


# --------------------------------------------------------- MRZ (passport)
_MRZ_LINE_RE = re.compile(r'^[A-Z0-9<]{28,44}$')


def _find_mrz_lines(text):
    lines = [re.sub(r'\s+', '', l.strip().upper()) for l in text.splitlines()]
    return [l for l in lines if len(l) >= 28 and l.count("<") >= 2 and _MRZ_LINE_RE.match(l)]


def _mrz_date(yy_mm_dd):
    if not yy_mm_dd or len(yy_mm_dd) != 6 or not yy_mm_dd.isdigit():
        return ""
    yy, mm, dd = int(yy_mm_dd[0:2]), yy_mm_dd[2:4], yy_mm_dd[4:6]
    # MRZ years have no century digit. Heuristic: 00-30 => 2000s, else
    # 1900s - reasonable for a working-age population; the review step
    # lets the user fix the rare edge case.
    century = 2000 if yy <= 30 else 1900
    try:
        return date(century + yy, int(mm), int(dd)).isoformat()
    except ValueError:
        return ""


def parse_passport_mrz(text):
    """Parse a TD3 (2-line x 44-char) passport MRZ if one is present."""
    result = {}
    lines = _find_mrz_lines(text)
    for i, l in enumerate(lines):
        if l.startswith("P<") and i + 1 < len(lines):
            line1 = (l + "<" * 44)[:44]
            line2 = (lines[i + 1] + "<" * 44)[:44]

            nationality1 = line1[2:5].rstrip("<")
            name_field = line1[5:]
            parts = name_field.split("<<", 1)
            surname = parts[0].replace("<", " ").strip() if parts else ""
            given = parts[1].replace("<", " ").strip() if len(parts) > 1 else ""
            full_name = " ".join(p for p in (given, surname) if p).strip()

            passport_no = line2[0:9].replace("<", "").strip()
            nationality2 = line2[10:13].rstrip("<")
            dob = _mrz_date(line2[13:19])
            sex_code = line2[20:21]
            expiry = _mrz_date(line2[21:27])

            if full_name:
                result["full_name"] = full_name
            if passport_no:
                result["passport_no"] = passport_no
            nat = nationality2 or nationality1
            if nat:
                result["nationality"] = nat
            if dob:
                result["date_of_birth"] = dob
            if expiry:
                result["passport_expiry"] = expiry
            if sex_code in ("M", "F"):
                result["gender"] = "Male" if sex_code == "M" else "Female"
            break
    return result


# ------------------------------------------------------- label-based text
EID_RE = re.compile(r'784[\s\-]?\d{4}[\s\-]?\d{7}[\s\-]?\d{1}')
_DATE_RE = r'(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2})'


def _norm_date(s):
    s = s.strip()
    m = re.match(r'^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})$', s)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return ""
    m = re.match(r'^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$', s)
    if m:
        y, mo, d = (int(x) for x in m.groups())
        try:
            return date(y, mo, d).isoformat()
        except ValueError:
            return ""
    return ""


def _find_date_near(lines, *keywords):
    for l in lines:
        lu = l.upper()
        if any(k in lu for k in keywords):
            m = re.search(_DATE_RE, l)
            if m:
                nd = _norm_date(m.group(1))
                if nd:
                    return nd
    return ""


def parse_labelled_fields(text):
    """Heuristic, label-driven extraction used for everything that isn't
    a passport MRZ: Emirates ID, residence visa, labour card, and as a
    passport fallback when no MRZ was found (e.g. a cropped photo)."""
    result = {}
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    joined = "\n".join(lines)
    upper = joined.upper()

    m = EID_RE.search(joined)
    if m:
        digits = re.sub(r'[^0-9]', '', m.group(0))
        if len(digits) == 15:
            result["emirates_id_no"] = f"{digits[0:3]}-{digits[3:7]}-{digits[7:14]}-{digits[14:15]}"

    m = re.search(r'PASSPORT\s*(?:NO\.?|NUMBER)?\s*[:\-]?\s*([A-Z][A-Z0-9]{5,8})', upper)
    if m:
        result.setdefault("passport_no", m.group(1))

    m = re.search(r'(?:FULL\s*NAME|NAME)\s*[:\-]\s*([A-Z][A-Z .\'\-]{2,60})', upper)
    if m:
        result.setdefault("full_name", m.group(1).strip().title())

    m = re.search(r'NATIONALITY\s*[:\-]?\s*([A-Za-z .\'\-]{2,30})', joined, re.IGNORECASE)
    if m:
        result.setdefault("nationality", m.group(1).strip().title())

    dob = _find_date_near(lines, "DATE OF BIRTH", "DOB", "BIRTH")
    if dob:
        result.setdefault("date_of_birth", dob)

    if "EMIRATES ID" in upper or "IDENTITY CARD" in upper or "RESIDENT IDENTITY" in upper:
        exp = _find_date_near(lines, "EXPIRY", "DATE OF EXPIRY", "VALID UNTIL")
        if exp:
            result.setdefault("emirates_id_expiry", exp)

    if "PASSPORT" in upper:
        exp = _find_date_near(lines, "DATE OF EXPIRY", "EXPIRY")
        if exp:
            result.setdefault("passport_expiry", exp)

    if ("RESIDENCE" in upper and "VISA" in upper) or "UNIFIED NUMBER" in upper or "PERMIT" in upper:
        exp = _find_date_near(lines, "EXPIRY", "VALID UNTIL", "DATE OF EXPIRY")
        if exp:
            result.setdefault("residence_visa_expiry", exp)

    if "LABOUR" in upper or "LABOR" in upper or "WORK PERMIT" in upper:
        exp = _find_date_near(lines, "EXPIRY", "VALID UNTIL")
        if exp:
            result.setdefault("labour_card_expiry", exp)

    if re.search(r'\bSEX\s*[:\-]?\s*M\b', upper) or re.search(r'\bMALE\b', upper):
        result.setdefault("gender", "Male")
    elif re.search(r'\bSEX\s*[:\-]?\s*F\b', upper) or re.search(r'\bFEMALE\b', upper):
        result.setdefault("gender", "Female")

    return result


def extract_employee_fields(path):
    """Top-level entry point for a file expected to hold ONE employee's
    documents (passport/EID/visa). Returns
    (fields_dict, used_ocr: bool, raw_text_preview: str)."""
    text, used_ocr = extract_text(path)
    if not text.strip():
        return {}, used_ocr, ""

    fields = {}
    fields.update(parse_passport_mrz(text))
    for k, v in parse_labelled_fields(text).items():
        fields.setdefault(k, v)

    return fields, used_ocr, text[:2000]


# --------------------------------------------------- multi-employee rosters
# Some UAE government portals (MOHRE "List of Employees by Establishment",
# GDRFA visa-status lists, etc.) export a single PDF containing a TABLE of
# many employees at once - passport no., name, job, nationality, permit/
# card number, expiry, contract type. One uploaded file should then become
# several employee rows, not one.

NATIONALITY_WORDS = [
    "PHILIPPINES", "SYRIA", "PAKISTAN", "INDIA", "BANGLADESH", "EGYPT", "JORDAN",
    "LEBANON", "SUDAN", "NEPAL", "SRI LANKA", "NIGERIA", "KENYA", "ETHIOPIA",
    "MOROCCO", "TUNISIA", "ALGERIA", "YEMEN", "IRAQ", "AFGHANISTAN", "INDONESIA",
    "CHINA", "UNITED KINGDOM", "SOUTH AFRICA", "UNITED ARAB EMIRATES", "JAMAICA",
    "GHANA", "UGANDA", "CAMEROON", "TURKEY", "IRAN", "RUSSIA", "UKRAINE",
    "USA", "UNITED STATES", "CANADA", "AUSTRALIA", "FRANCE", "GERMANY",
    "THAILAND", "VIETNAM", "MYANMAR", "MALAYSIA", "SINGAPORE",
]
_NAT_ALT = "|".join(sorted(NATIONALITY_WORDS, key=len, reverse=True))

_ROSTER_ROW_RICH_RE = re.compile(
    r'(?P<passport>[A-Z]{1,2}\d{6,9}[A-Z]?)\s*\n'
    r'(?P<name>[A-Z][A-Za-z .\'\-]{2,58})\s*\n'
    r'[\s\S]*?'
    r'(?P<card_type>[A-Za-z][A-Za-z/ ]{5,55}?(?:PERMIT|SPONSORSHIP))\s*\n'
    r'[\s\S]*?'
    r'(?P<job>[A-Za-z][A-Za-z /]{2,40})\s*\n'
    r'(?P<nationality>' + _NAT_ALT + r')\s*\n'
    r'(?P<card_no>\d{8,9})\s*\n'
    r'(?P<expiry>\d{2}/\d{2}/\d{4})\s*\n?'
    r'(?P<contract>Limited|Unlimited)',
    re.IGNORECASE,
)

_ROSTER_ROW_SIMPLE_RE = re.compile(
    r'(?P<passport>[A-Z]{1,2}\d{6,9}[A-Z]?)\s*\n'
    r'(?P<name>[A-Z][A-Za-z .\'\-]{2,58})\s*\n'
    r'[\s\S]*?'
    r'(?P<nationality>' + _NAT_ALT + r')\s*\n'
    r'(?P<card_no>\d{8,9})\s*\n'
    r'(?P<expiry>\d{2}/\d{2}/\d{4})\s*\n?'
    r'(?P<contract>Limited|Unlimited)',
    re.IGNORECASE,
)


def looks_like_roster(text):
    upper = text.upper()
    return ("LIST OF EMPLOYEES" in upper or "TOTAL NUMBER OF EMPLOYEES" in upper
            or len(_ROSTER_ROW_SIMPLE_RE.findall(text)) >= 2)


def parse_employee_roster(text):
    """Return a list of employee field-dicts extracted from a multi-employee
    roster/table document. Empty list if the text doesn't look like one."""
    rows = []
    matches = list(_ROSTER_ROW_RICH_RE.finditer(text))
    use_rich = len(matches) >= 2
    if not use_rich:
        matches = list(_ROSTER_ROW_SIMPLE_RE.finditer(text))
    if len(matches) < 2:
        return []

    for m in matches:
        gd = m.groupdict()
        fields = {
            "passport_no": gd["passport"].strip(),
            "full_name": re.sub(r'\s+', ' ', gd["name"]).strip().title(),
            "nationality": gd["nationality"].strip().title(),
            "labour_card_no": gd["card_no"].strip(),
            "labour_card_expiry": _norm_date(gd["expiry"].strip()),
        }
        job = gd.get("job")
        if job:
            job_clean = re.sub(r'\s+', ' ', job).strip()
            if 2 <= len(job_clean) <= 40:
                fields["job_title"] = job_clean.title()
        card_type = gd.get("card_type")
        note_bits = []
        if card_type:
            note_bits.append(re.sub(r'\s+', ' ', card_type).strip().title())
        if gd.get("contract"):
            note_bits.append(f"{gd['contract'].title()} contract")
        if note_bits:
            fields["notes"] = " - ".join(note_bits)
        rows.append(fields)
    return rows


def extract_employee_records(path):
    """Top-level entry point used by the bulk-import UI. Handles BOTH a
    single ID document and a multi-employee roster/table file.
    Returns a list of (fields_dict, used_ocr: bool, note: str) - one item
    for a normal document, several for a roster."""
    text, used_ocr = extract_text(path)
    if not text.strip():
        return [({}, used_ocr, "")]

    if looks_like_roster(text):
        roster_rows = parse_employee_roster(text)
        if roster_rows:
            return [(fields, used_ocr, f"Row {i + 1} of {len(roster_rows)} in an employee list/roster file")
                    for i, fields in enumerate(roster_rows)]
        # Looked like a roster (has the header text) but rows didn't parse -
        # most likely the table cells themselves are too small/low-quality
        # for OCR to read, even though the page headers/footers came through.
        return [({}, used_ocr, "This looks like an employee list/roster, but the row "
                                "data couldn't be read clearly (image too small/low-res "
                                "for the table text). Try the original PDF instead of a "
                                "screenshot, or a higher-resolution scan.")]

    fields = {}
    fields.update(parse_passport_mrz(text))
    for k, v in parse_labelled_fields(text).items():
        fields.setdefault(k, v)
    if not fields:
        return [({}, used_ocr, "")]
    return [(fields, used_ocr, "")]
