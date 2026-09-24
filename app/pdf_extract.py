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
    import pytesseract  # Python wrapper; the Tesseract engine is installed separately
    HAVE_TESSERACT = True
    # Common Windows installation locations. This lets OCR work without
    # requiring the user to edit PATH manually.
    if os.name == "nt":
        _tess_candidates = [
            os.environ.get("TESSERACT_CMD", ""),
            r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
            r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe",
        ]
        for _candidate in _tess_candidates:
            if _candidate and os.path.exists(_candidate):
                pytesseract.pytesseract.tesseract_cmd = _candidate
                break
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
        # Improve common phone scans/photos: grayscale, contrast and a
        # moderate upscale. Keep the original available as a fallback.
        work = img
        if HAVE_PIL:
            from PIL import ImageOps, ImageEnhance, ImageFilter
            if work.mode not in ("L", "RGB"):
                work = work.convert("RGB")
            gray = ImageOps.grayscale(work)
            gray = ImageEnhance.Contrast(gray).enhance(1.6)
            if gray.width < 1800:
                scale = min(2.0, 1800 / max(1, gray.width))
                gray = gray.resize((int(gray.width * scale), int(gray.height * scale)))
            work = gray.filter(ImageFilter.SHARPEN)
        langs = "eng"
        try:
            available = pytesseract.get_languages(config="")
            if "ara" in available:
                langs = "eng+ara"
        except Exception:
            pass
        text = pytesseract.image_to_string(work, lang=langs, config="--psm 6")
        if not text.strip() and work is not img:
            text = pytesseract.image_to_string(img, lang="eng", config="--psm 6")
        return text
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


def _find_labeled_value(text, labels, max_len=80):
    """Find a value following one of several labels on the same line."""
    label_re = "|".join(re.escape(x) for x in labels)
    m = re.search(rf"(?:{label_re})\\s*(?:NO\\.?|NUMBER|NUM|#)?\\s*[:\\-]?\\s*([A-Z0-9][A-Z0-9 ./\\-]{{2,{max_len}}})", text, re.I)
    return m.group(1).strip(" .:-") if m else ""

def _find_number_by_pattern(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1).strip()
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

    if "MEDICAL" in upper or "FITNESS" in upper:
        dt = _find_date_near(lines, "DATE OF TEST", "TEST DATE", "MEDICAL DATE")
        if dt:
            result.setdefault("medical_test_date", dt)
        exp = _find_date_near(lines, "EXPIRY", "VALID UNTIL")
        if exp:
            result.setdefault("medical_test_expiry", exp)

    if "INSURANCE" in upper or "POLICY" in upper:
        value = _find_labeled_value(joined, ["POLICY NO", "POLICY NUMBER", "POLICY"])
        if value:
            result.setdefault("insurance_policy_no", value[:80])
        exp = _find_date_near(lines, "EXPIRY", "VALID UNTIL", "POLICY EXPIRY")
        if exp:
            result.setdefault("insurance_expiry", exp)

    # Common UAE document numbers. These are deliberately conservative:
    # the import window remains editable so OCR mistakes can be corrected.
    value = _find_labeled_value(joined, ["RESIDENCE VISA", "RESIDENCY VISA", "VISA NO", "VISA NUMBER"])
    if value:
        result.setdefault("residence_visa_no", value[:80])

    value = _find_labeled_value(joined, ["ENTRY PERMIT", "ENTRY PERMIT NO", "PERMIT NUMBER"])
    if value:
        result.setdefault("entry_permit_no", value[:80])

    value = _find_labeled_value(joined, ["LABOUR CARD", "LABOR CARD", "WORK PERMIT", "WORK CARD"])
    if value:
        result.setdefault("labour_card_no", value[:80])

    value = _find_labeled_value(joined, ["EMPLOYMENT CONTRACT", "CONTRACT NO", "CONTRACT NUMBER"])
    if value:
        result.setdefault("employment_contract_no", value[:80])

    if "PHONE" in upper or "MOBILE" in upper or "TEL" in upper:
        value = _find_labeled_value(joined, ["PHONE", "MOBILE", "MOBILE NO", "TEL", "TELEPHONE"])
        if value:
            result.setdefault("phone", value[:40])

    if re.search(r'\bSEX\s*[:\-]?\s*M\b', upper) or re.search(r'\bMALE\b', upper):
        result.setdefault("gender", "Male")
    elif re.search(r'\bSEX\s*[:\-]?\s*F\b', upper) or re.search(r'\bFEMALE\b', upper):
        result.setdefault("gender", "Female")

    return result


def extract_employee_fields(path):
    """Top-level entry point used by the bulk-import UI.
    Returns (fields_dict, used_ocr: bool, raw_text_preview: str)."""
    text, used_ocr = extract_text(path)
    if not text.strip():
        return {}, used_ocr, ""

    fields = {}
    fields.update(parse_passport_mrz(text))
    for k, v in parse_labelled_fields(text).items():
        fields.setdefault(k, v)

    return fields, used_ocr, text[:2000]
