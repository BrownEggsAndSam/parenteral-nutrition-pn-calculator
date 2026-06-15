# Parenteral Nutrition (PN) Calculator

Mobile-first calculator for quick Parenteral Nutrition (PN/TPN) worksheet calculations, including Total Fluid Limit (TFL), IVFE, PN rate, protein intake, and glucose infusion rate (GIR).

This version is intentionally focused on quick bedside/mobile calculations for clinicians. The visible workflow excludes electrolyte/additive sections so the phone UI stays fast and compact.

## GitHub Pages version

This repo now includes a static GitHub Pages app in:

```text
site/index.html
```

The GitHub Pages version runs fully in the browser. It does not require Flask, Python, Gunicorn, Render, or a database server.

Important behavior difference:

- Saved sessions are stored in the user's browser using `localStorage`.
- Sessions are not shared across phones/computers.
- Clearing browser storage can delete saved sessions.
- Do not enter PHI, names, MRNs, or dates of birth in the public GitHub Pages version.

## Features

- Mobile-first compact calculator UI
- Public GitHub Pages deployment
- Required named calculation sessions
- Browser-local save, edit, duplicate, delete, print, import, and export
- Live worksheet math as values are entered
- TFL: mL/kg/day → mL/day → mL/hr
- IVFE: g/kg/day → g/day → mL/day → mL/hr
- PN volume: non-PN fluid aggregation → PN rate → PN order range
- Protein: g/kg/day → g/day → kcal/day
- GIR: TPN GIR, rider GIR, and total GIR

## Enable GitHub Pages

The repo includes this workflow:

```text
.github/workflows/deploy-pages.yml
```

It publishes the static site from:

```text
site/
```

In GitHub, go to:

```text
Settings → Pages → Source → GitHub Actions
```

Then go to:

```text
Actions → Deploy static PN Calculator to GitHub Pages → Run workflow
```

After it completes, the app should be available at:

```text
https://browneggsandsam.github.io/parenteral-nutrition-pn-calculator/
```

## Flask version

The repo also still contains the Flask version:

- `app.py`
- `deploy.py`
- `requirements.txt`
- `render.yaml`
- `Procfile`

Use the Flask/Render version only if you want a server-backed app with SQLite persistence beyond one user's browser.

## Local Flask quick start

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
copy .env.example .env     # Windows
# cp .env.example .env      # macOS/Linux
flask --app app run --debug
```

Open:

```text
http://127.0.0.1:5000
```

Default local password:

```text
changeme
```

Change `APP_ACCESS_PASSWORD` and `SECRET_KEY` in `.env` before sharing.

## Clinical disclaimer

This application is a calculation aid based on a worksheet workflow. It does not replace pharmacist, dietitian, physician, or institutional review. All PN orders, concentrations, compatibility, labs, and local protocols must be verified before clinical use.

Do not store real patient identifiers unless the app is deployed in an approved, secure, HIPAA-compliant environment.
