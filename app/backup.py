"""
backup.py
---------
Backup / restore for the database (and the uploaded company logo).

Two layers of protection:
  1. AUTOMATIC: a timestamped copy of the database is saved every time
     the app closes normally (rotated, keeping the most recent copies).
     This is a safety net against accidental deletion/corruption - it is
     NOT a substitute for keeping your own copy somewhere safe.
  2. MANUAL: "Backup Now" lets the user save a full .zip snapshot
     (database + logo) anywhere they like - a USB drive, a shared/cloud
     folder, etc. - and "Restore" can load it back.
"""
import os
import shutil
import zipfile
import tempfile
from datetime import datetime

from app import database as db

MAX_AUTO_BACKUPS = 20


def _ensure_dirs():
    os.makedirs(db.BACKUP_DIR, exist_ok=True)


def auto_backup():
    """Cheap timestamped copy of just the .db file. Called on app close
    and is safe to call any time; failures are swallowed (a failed
    backup should never stop the user from closing the app)."""
    _ensure_dirs()
    if not os.path.exists(db.DB_PATH):
        return None
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(db.BACKUP_DIR, f"auto_{ts}.db")
    try:
        shutil.copy2(db.DB_PATH, dest)
    except Exception:
        return None
    _rotate()
    return dest


def _rotate():
    try:
        files = sorted(f for f in os.listdir(db.BACKUP_DIR)
                        if f.startswith("auto_") and f.endswith(".db"))
        while len(files) > MAX_AUTO_BACKUPS:
            oldest = files.pop(0)
            os.remove(os.path.join(db.BACKUP_DIR, oldest))
    except OSError:
        pass


def list_auto_backups():
    """Newest first: list of (path, display_label)."""
    _ensure_dirs()
    files = [f for f in os.listdir(db.BACKUP_DIR) if f.startswith("auto_") and f.endswith(".db")]
    files.sort(reverse=True)
    out = []
    for f in files:
        ts = f[len("auto_"):-len(".db")]
        try:
            label = datetime.strptime(ts, "%Y%m%d_%H%M%S").strftime("%d %b %Y, %I:%M %p")
        except ValueError:
            label = f
        out.append((os.path.join(db.BACKUP_DIR, f), label))
    return out


def export_backup_zip(dest_path):
    """Manual full backup: database + logo folder, zipped to dest_path."""
    with zipfile.ZipFile(dest_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(db.DB_PATH):
            zf.write(db.DB_PATH, arcname="erms.db")
        if os.path.isdir(db.LOGO_DIR):
            for fname in os.listdir(db.LOGO_DIR):
                full = os.path.join(db.LOGO_DIR, fname)
                if os.path.isfile(full):
                    zf.write(full, arcname=os.path.join("branding", fname))
    return dest_path


def restore_from_zip(zip_path):
    """Restore database (+ logo) from a manual backup .zip."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
        if "erms.db" not in names:
            raise ValueError("This doesn't look like a valid backup file (no erms.db inside).")
        with tempfile.TemporaryDirectory() as tmp:
            zf.extractall(tmp)
            shutil.copy2(os.path.join(tmp, "erms.db"), db.DB_PATH)
            branding_src = os.path.join(tmp, "branding")
            if os.path.isdir(branding_src):
                os.makedirs(db.LOGO_DIR, exist_ok=True)
                for fname in os.listdir(branding_src):
                    shutil.copy2(os.path.join(branding_src, fname), os.path.join(db.LOGO_DIR, fname))


def restore_from_db_file(src_db_path):
    """Restore directly from a raw .db file (e.g. one of the automatic
    backups)."""
    shutil.copy2(src_db_path, db.DB_PATH)


def open_backups_folder():
    _ensure_dirs()
    import sys
    import subprocess
    try:
        if sys.platform == "win32":
            os.startfile(db.BACKUP_DIR)  # noqa
        elif sys.platform == "darwin":
            subprocess.run(["open", db.BACKUP_DIR])
        else:
            subprocess.run(["xdg-open", db.BACKUP_DIR])
        return True
    except Exception:
        return False
