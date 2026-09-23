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
- **Settings** — adjust the Critical / Warning / Upcoming day
  thresholds to match your own renewal lead-time policy, and review a
  full activity log (who/what/when was added, edited, or deleted).

All data is stored locally in a single SQLite file at
`data/erms.db` — easy to back up (just copy the file) or move between
machines.

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
5. (Optional, for the Excel export button) Install the one optional
   dependency:
   ```
   pip install openpyxl
   ```

---

## 4. Turning it into a double-click Windows `.exe`

PyInstaller must be run **on a Windows machine** (it builds for the OS
it's run on), so do this step on your own PC:

```
pip install pyinstaller
pyinstaller --onefile --windowed --name "EmployeeResidenceManager" ^
    --add-data "data;data" main.py
```

This produces `dist\EmployeeResidenceManager.exe` — a single file you
can copy anywhere and double-click, no Python installation needed on
the target machine. A ready-made `build_exe.bat` script that runs this
for you is included in this folder — just double-click it on Windows.

> Tip: the packaged `.exe` will create its `data\erms.db` file next to
> wherever it's run from the first time you launch it.

---

## 5. Project structure

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
├── data/                    # SQLite database lives here (auto-created)
└── app/
    ├── database.py          # schema + all CRUD operations
    ├── utils.py              # date math, expiry classification, report builder
    ├── export.py              # CSV / Excel export
    ├── widgets.py               # date picker, generic form dialog, dashboard cards
    └── main_window.py            # all six tabs (UI)
```

---

## 6. Customizing further

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

## 7. Putting this on GitHub

See **[GITHUB_SETUP.md](GITHUB_SETUP.md)** for copy-paste commands to
push this project to a new GitHub repo, plus a ready-made GitHub Actions
workflow (`.github/workflows/build-exe.yml`) that automatically builds
`EmployeeResidenceManager.exe` on every push and attaches it to
Releases — so teammates can download a working `.exe` without installing
Python at all.

