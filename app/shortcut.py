"""
shortcut.py
-----------
Create a Desktop shortcut to launch the app, with no third-party
dependency required.

Windows: writes a tiny throwaway VBScript and runs it with the built-in
         `cscript` interpreter (present on every Windows machine) to
         create a proper .lnk file - this is the standard dependency-free
         trick for making Windows shortcuts from Python.
Linux:   writes a standard .desktop launcher file.
macOS:   not automated (no single standard "Desktop shortcut" mechanism
         without extra tooling); the user gets a clear message instead.
"""
import os
import sys
import subprocess
import tempfile


def _prepare_icon(icon_path):
    """Return a Windows-friendly .ico path when a raster logo is supplied."""
    if not icon_path or not os.path.exists(icon_path):
        return None
    if icon_path.lower().endswith(".ico"):
        return icon_path
    try:
        from PIL import Image
        ico_path = os.path.join(os.path.dirname(icon_path), "company_logo.ico")
        img = Image.open(icon_path).convert("RGBA")
        img.thumbnail((256, 256))
        img.save(ico_path, format="ICO", sizes=[(256,256), (128,128), (64,64), (32,32), (16,16)])
        return ico_path
    except Exception:
        return icon_path

APP_TITLE = "EmployeeResidenceManager"
APP_DESCRIPTION = "UAE Employee & Company Residence / Document Management System"


def _launch_target():
    """Return (target_exe, args_string, working_dir) to point the
    shortcut at - the built .exe if this is a frozen build, otherwise
    the Python interpreter + main.py."""
    if getattr(sys, "frozen", False):
        target = sys.executable
        return target, "", os.path.dirname(target)

    py = sys.executable
    pythonw = py
    candidate = py.replace("python.exe", "pythonw.exe")
    if os.path.exists(candidate):
        pythonw = candidate  # avoids a console window popping up
    main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
    return pythonw, f'"{main_py}"', os.path.dirname(main_py)


def create_desktop_shortcut(icon_path=None):
    """Returns (ok: bool, message: str)."""
    if sys.platform == "win32":
        return _create_windows_shortcut(icon_path)
    if sys.platform.startswith("linux"):
        return _create_linux_shortcut(icon_path)
    return False, ("Automatic Desktop shortcuts aren't set up for macOS yet. "
                    "You can drag the app into your Dock or Applications folder instead.")


def _windows_desktop_dir():
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        candidate = os.path.join(userprofile, "Desktop")
        if os.path.isdir(candidate):
            return candidate
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            return winreg.QueryValueEx(key, "Desktop")[0]
    except Exception:
        return None


def _create_windows_shortcut(icon_path=None):
    desktop = _windows_desktop_dir()
    if not desktop or not os.path.isdir(desktop):
        return False, "Couldn't locate your Windows Desktop folder."

    shortcut_path = os.path.join(desktop, f"{APP_TITLE}.lnk")
    target, args, workdir = _launch_target()
    icon = _prepare_icon(icon_path) or target

    vbs = (
        'Set oWS = WScript.CreateObject("WScript.Shell")\n'
        f'sLinkFile = "{shortcut_path}"\n'
        'Set oLink = oWS.CreateShortcut(sLinkFile)\n'
        f'oLink.TargetPath = "{target}"\n'
        f'oLink.Arguments = "{args}"\n'
        f'oLink.WorkingDirectory = "{workdir}"\n'
        f'oLink.IconLocation = "{icon}"\n'
        f'oLink.Description = "{APP_DESCRIPTION}"\n'
        'oLink.Save\n'
    )
    vbs_path = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".vbs", delete=False) as f:
            f.write(vbs)
            vbs_path = f.name
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        subprocess.run(["cscript", "//nologo", vbs_path], check=True, creationflags=creationflags)
        return True, f"Shortcut created on your Desktop:\n{shortcut_path}"
    except Exception as e:
        return False, f"Couldn't create the shortcut automatically ({e})."
    finally:
        if vbs_path and os.path.exists(vbs_path):
            try:
                os.remove(vbs_path)
            except OSError:
                pass


def _create_linux_shortcut(icon_path=None):
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(desktop):
        return False, "No Desktop folder found in your home directory."
    target, args, workdir = _launch_target()
    exec_line = f'"{target}" {args}'.strip()
    entry = (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={APP_TITLE}\n"
        f"Comment={APP_DESCRIPTION}\n"
        f"Exec={exec_line}\n"
        f"Path={workdir}\n"
        f"Icon={icon_path or ''}\n"
        "Terminal=false\n"
    )
    path = os.path.join(desktop, f"{APP_TITLE}.desktop")
    try:
        with open(path, "w") as f:
            f.write(entry)
        os.chmod(path, 0o755)
        return True, f"Shortcut created:\n{path}"
    except Exception as e:
        return False, f"Couldn't create the shortcut ({e})."
