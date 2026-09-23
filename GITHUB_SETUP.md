# Putting this project on GitHub

Everything below is written for **Git Bash / Command Prompt / PowerShell
on Windows** (or macOS/Linux Terminal — the commands are the same). You
only need to do the one-time setup once.

## 0. One-time setup (skip if already done)

1. Install Git: https://git-scm.com/downloads
2. Create a free GitHub account: https://github.com/join
3. Tell Git who you are (once per computer):
   ```
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```

## 1. Create the repository on GitHub

1. Go to https://github.com/new
2. Repository name: `employee-residence-manager` (or anything you like)
3. Leave it **empty** — do NOT tick "Add a README" or "Add .gitignore"
   (this project already has both).
4. Choose Private if this will contain real employee data, Public if not.
5. Click **Create repository** and keep that page open — it shows the
   commands from step 3 below with your exact repo URL already filled in.

## 2. Open a terminal inside the project folder

```
cd path\to\EmployeeResidenceManager
```

## 3. Initialize git and push

```
git init
git add .
git commit -m "Initial commit: UAE Employee & Company Document Management System"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/employee-residence-manager.git
git push -u origin main
```

Replace `YOUR-USERNAME` (and the repo name, if you changed it) with your
own — GitHub shows you the exact command on the page from step 1.

That's it — refresh the GitHub page and your code is there.

## 4. What NOT to commit

The included `.gitignore` already keeps these out automatically, but
worth knowing:
- `data/*.db` — your actual company/employee database (real personal
  data should not go into a git repo, especially a public one)
- `dist/`, `build/`, `*.spec` — PyInstaller build output
- exported `.csv` / `.xlsx` reports

If you ever need to share a **copy of your data** with a teammate, send
the `data/erms.db` file directly (email/USB/shared drive) rather than
committing it.

## 5. Making changes later

Every time you edit the code and want to save a new version to GitHub:

```
git add .
git commit -m "Describe what you changed"
git push
```

## 6. Automatic .exe builds (already set up for you)

This repo includes `.github/workflows/build-exe.yml`. Once pushed to
GitHub, it automatically:
- Builds `EmployeeResidenceManager.exe` on a real Windows machine every
  time you push to `main`
- Lets you download that `.exe` from the **Actions** tab of your repo
  (click the latest run → scroll to **Artifacts**)
- If you push a version tag (see below), it also attaches the `.exe`
  directly to a GitHub **Release** so others can download it with one
  click, with no need to install Python at all.

To cut a release with an attached `.exe`:
```
git tag v1.0.0
git push origin v1.0.0
```
Then check the **Releases** section of your GitHub repo a minute or two
later — the `.exe` will be attached automatically.

You can also trigger a build manually any time from the **Actions** tab
→ "Build Windows EXE" → **Run workflow**, without needing to push or tag
anything.

## 7. Inviting collaborators (optional)

Repo page → **Settings** → **Collaborators** → **Add people**, then
they can:
```
git clone https://github.com/YOUR-USERNAME/employee-residence-manager.git
```
and run it exactly as described in the main `README.md`.

## 8. Cloning it back down on a new machine

```
git clone https://github.com/YOUR-USERNAME/employee-residence-manager.git
cd employee-residence-manager
python main.py
```
