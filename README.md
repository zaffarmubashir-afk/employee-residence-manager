# UAE Employee & Company Residence / Document Management System

A Windows desktop application (Python + Tkinter + SQLite — no external
services, no internet connection required, all data stays on your PC)
for tracking every official document a UAE company and its employees
need to keep alive, and warning you before anything expires.

---

## 1. Why these specific documents? (UAE regulatory background)

### Company-side documents (set up once you establish the business)
| Document | Issued by | Typical validity | Notes |
|---|---|---|---|
| **Trade License** | DED / Free Zone Authority | 1 year | Core license to operate; must stay valid or nothing else can renew |
| **Establishment / Immigration Card** | GDRFA (Dubai) or ICP (other Emirates) / Free zone | 1 year (some free zones: 2–3 yrs) | Required before the company can sponsor ANY employee visa. Trade license must be renewed first — the card renewal is blocked otherwise |
| **MOHRE Establishment File / Labour Card Company File** | Ministry of Human Resources & Emiratisation | Linked to license | Required for all work-permit and labour-contract transactions |
| **Chamber of Commerce Certificate** | Dubai/Emirate Chamber | 1 year | Often needed for trade/commercial transactions |
| **Tenancy Contract / Ejari** | Land Department / Municipality | 1 year | Office lease registration; needed for license & establishment card renewal |

### Employee-side documents (per employee, from hiring to exit)
| Document | Issued by | Typical validity | Notes |
|---|---|---|---|
| **Entry Permit** | GDRFA/ICP | ~60 days | Pre-arrival permit, converted to residence visa after entry |
| **Residence Visa** | GDRFA/ICP | 1–10 years (2–3 yrs typical for employment visas) | 30-day grace period after expiry, then AED 50/day fine |
| **Emirates ID** | ICP | Matches visa validity | Automatically expires when the residence visa expires; 30-day grace period, AED 20/day fine (capped) |
| **Labour Card / Work Permit** | MOHRE | 2 years (private sector) / 3 years (government) | Late renewal fine: AED 200/month, capped at AED 2,000 |
| **Employment Contract** | MOHRE (e-contract) | Must be filed within 60 days of joining | Late filing fine: AED 100/day, capped at AED 2,000 |
| **Medical Fitness Test** | Ministry of Health / DHA | Required at visa issuance/renewal | Screens for communicable diseases |
| **Passport** | Employee's home country | Varies | Must remain valid for visa processing |
| **Health Insurance** | Private insurer (mandatory) | Usually 1 year | Mandatory under UAE health insurance law |

This tool models all of the above as trackable "documents" with an
expiry date, automatically colour-codes them by urgency, and lets you
add any *other* document type you need (DED permits, VAT certificates,
bank guarantees, etc.) via the free-form "Other Documents" tab.

> Regulations and fees change. Always confirm current requirements with
> MOHRE (mohre.gov.ae), ICP/GDRFA (icp.gov.ae), and your Emirate's
> Department of Economy before relying on this tool for compliance
> deadlines — this app is an internal tracking aid, not legal advice.

---

## 2. What the application does

- **Dashboard** — live KPI cards (Expired / Critical / Warning /
  Upcoming / Valid) and a full colour-coded list of every tracked
  document across every company and employee. Click a card to filter;
  double-click a row to jump straight to that record.
- **Companies** — add/edit/delete companies with all license &
  immigration fields; one click to see that company's employees or
  extra documents.
- **Employees** — add/edit/delete employees, linked to a company, with
  every visa/labour/ID/contract field; filter by company or status.
- **Other Documents** — link any additional document (VAT cert, bank
  guarantee, DED permit, insurance addendum, etc.) to a company or an
  employee.
- **Reports / Export** — filter the master list by status, export to
  CSV (always available) or Excel (`pip install openpyxl` for
  colour-coded `.xlsx`).
- **Import from PDF / Scanned Documents / Photos** (Employees tab) —
  select any number of passport, Emirates ID, or visa PDFs/photos at
  once and the app reads names, numbers, and expiry dates out of them
  automatically, so you don't have to type in thousands of employees by
  hand. Every result is shown in an editable table for you to check and
  fix before anything is saved. See **section 4** below for what this
  needs installed.
- **Settings** — adjust the Critical / Warning / Upcoming day
  thresholds to match your own renewal lead-time policy; upload your
  company logo (shown at the top of the app); create a Desktop
  shortcut; back up or restore your data; and review a full activity
  log (who/what/when was added, edited, or deleted).

All data is stored locally in a single SQLite file in your Windows
user profile at `%APPDATA%\EmployeeResidenceManager\erms.db` — **not**
inside the app/install folder. This matters: it's what makes your data
survive closing and reopening the app (including the packaged `.exe`),
moving/reinstalling the app, and Windows updates. It's also
automatically backed up every time you close the app (see section 5).

---

## 3. Running it (no installation needed beyond Python)

1. Install **Python 3.10+** for Windows from https://python.org
   (during setup, tick **"Add Python to PATH"**). Tkinter and SQLite
   are already bundled with the standard Windows installer — nothing
   else is required.
2. Unzip this project anywhere, e.g. `C:\Apps\EmployeeResidenceManager`.
3. Open a Command Prompt in that folder and run:
   ```
   python main.py
   ```
4. (Optional) Load a few sample records to explore the app:
   ```
   python seed_sample_data.py
   python main.py
   ```
5. (Optional extras) Install any of these as needed:
   ```
   pip install openpyxl                       # Excel export button
   pip install pymupdf pillow                 # read text-based PDFs
   pip install pymupdf pillow pytesseract      # + OCR scanned PDFs/photos
   ```
   See **section 4** for the full picture on the PDF/photo import
   feature, including the one piece (Tesseract-OCR) that isn't a `pip
   install`.

---

## 4. Setting up "Import from PDF / Scanned Documents / Photos"

The Employees tab has an **Import from PDF/Photos** button that reads
passport, Emirates ID, and visa documents automatically instead of you
typing every employee in by hand. It has two tiers of capability,
each needing different optional packages — the app tells you in
**Settings** which of these you currently have:

| Capability | What it reads | Needs |
|---|---|---|
| **Text-based PDFs** | A PDF that was generated/printed from a computer (has selectable text) | `pip install pymupdf` (or `pip install pypdf` as a lighter fallback) |
| **Scanned PDFs & photos (OCR)** | A scanned page or a phone photo of a document, where the "text" is really just pixels | The above, **plus** `pip install pillow pytesseract`, **plus** the free Tesseract-OCR program itself (this is a separate program, not a Python package — pytesseract is just a wrapper around it) |

**Installing Tesseract-OCR (one-time, only needed for scans/photos):**
1. Download the Windows installer from the UB-Mannheim build:
   https://github.com/UB-Mannheim/tesseract/wiki
2. Run it (default install location is fine).
3. Restart the app. Check **Settings → Employee Import from PDF /
   Photos** — it should now show a green checkmark for OCR.

Without Tesseract, the import tool still works fully for text-based
PDFs; scanned/photographed documents will just come back empty and
need to be filled in by hand, with a clear warning shown in the import
window.

**Passport reading** uses the machine-readable zone (MRZ) — the two
lines of `<<<<` text at the bottom of the passport photo page — which
is far more reliable than reading the printed text, when it's visible
in the scan/photo. Emirates ID, visa, and labour card documents are
read by looking for their labelled fields (ID number, "Date of
Expiry", etc.).

**Because OCR is never 100% accurate**, nothing is saved automatically
— every import shows an editable table first so you (or whoever is
onboarding the batch) can fix anything before it's added as an
employee record. For very large batches (hundreds/thousands of files),
processing runs in the background so the app stays responsive, with a
live progress count and a Cancel button.

---

## 5. Turning it into a double-click Windows `.exe`

PyInstaller must be run **on a Windows machine** (it builds for the OS
it's run on), so do this step on your own PC:

```
pip install pyinstaller
pyinstaller --onefile --windowed --name "EmployeeResidenceManager" main.py
```

This produces `dist\EmployeeResidenceManager.exe` — a single file you
can copy anywhere and double-click, no Python installation needed on
the target machine. A ready-made `build_exe.bat` script that runs this
for you is included in this folder — just double-click it on Windows.

If you want the PDF/photo import feature to work in the `.exe` too,
install the packages from section 4 *before* running PyInstaller so
they get bundled in.

> Your data is **not** stored next to the `.exe` — it lives in
> `%APPDATA%\EmployeeResidenceManager\` (see section 2), so it
> survives across app restarts, reinstalls, and rebuilding the `.exe`.

---

## 6. Desktop Shortcut & Backups

- **Desktop shortcut**: Settings → **Create Desktop Shortcut** adds an
  icon on your Windows Desktop that launches the app directly (it uses
  your uploaded company logo as the icon if you've set one).
- **Automatic backups**: every time you close the app, a timestamped
  copy of the database is saved to
  `%APPDATA%\EmployeeResidenceManager\backups\` (the most recent 20
  copies are kept). Settings → **Automatic backups** lists them, with a
  one-click **Restore Selected**.
- **Manual backup/restore**: Settings → **Backup Now** saves a `.zip`
  (database + your logo) anywhere you choose — a USB drive, a synced
  cloud folder, etc. **Restore from Backup File** loads one back in
  (it safety-backs-up your current data first, just in case).

---

## 7. Project structure

```
EmployeeResidenceManager/
├── main.py                  # entry point — run this
├── seed_sample_data.py      # optional demo data
├── build_exe.bat            # optional: builds a Windows .exe (run on Windows)
├── requirements-optional.txt
├── .gitignore
├── LICENSE
├── GITHUB_SETUP.md          # step-by-step guide to push this to GitHub
├── .github/workflows/build-exe.yml   # auto-builds the .exe via GitHub Actions
├── data/                    # legacy location, kept only for one-time migration
└── app/
    ├── database.py          # schema + all CRUD operations + app-data-folder logic
    ├── utils.py              # date math, expiry classification, report builder
    ├── export.py              # CSV / Excel export
    ├── backup.py               # automatic + manual backup/restore
    ├── shortcut.py              # Desktop shortcut creation
    ├── pdf_extract.py            # PDF/photo text extraction + field parsing (MRZ, OCR)
    ├── import_dialog.py           # bulk "Import from PDF/Photos" review table
    ├── widgets.py                  # date picker, generic form dialog, dashboard cards, logo loader
    └── main_window.py                # all six tabs (UI)
```

> **Note on `%APPDATA%`**: earlier versions of this app stored
> `erms.db` in the `data/` folder next to the app itself. That's fixed
> now — the database lives in your Windows user profile instead, which
> is what actually solves the "my data disappears when I reopen the
> app" problem (packaged `.exe` files run from a temporary folder that
> Windows deletes on exit, which is what was wiping the old location
> every time). If you have existing data in the old `data/erms.db`,
> the app copies it across automatically, once, the first time you run
> this version.

---

## 8. Customizing further

- **Add a new document type** to the Companies or Employees form: add a
  column in `app/database.py` (`COMPANY_FIELDS`/`EMPLOYEE_FIELDS` +
  `SCHEMA`), add a field to the form spec in `app/main_window.py`, and
  add it to `COMPANY_DOC_MAP`/`EMPLOYEE_DOC_MAP` in `app/utils.py` so
  it shows up on the Dashboard automatically. Delete `data/erms.db` to
  pick up the schema change (or write a small `ALTER TABLE` migration
  if you have existing data to keep).
- **Email/WhatsApp reminders**: not built in (this app has no internet
  access by design), but the `Settings` tab's `reminder_email` setting
  and the `utils.gather_all_tracked_documents()` function are the
  natural hook point if you want to add a scheduled emailer later.

---

## 9. Putting this on GitHub

See **[GITHUB_SETUP.md](GITHUB_SETUP.md)** for copy-paste commands to
push this project to a new GitHub repo, plus a ready-made GitHub Actions
workflow (`.github/workflows/build-exe.yml`) that automatically builds
`EmployeeResidenceManager.exe` on every push and attaches it to
Releases — so teammates can download a working `.exe` without installing
Python at all.

