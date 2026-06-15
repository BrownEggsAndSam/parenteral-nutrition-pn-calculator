# Parenteral Nutrition (PN) Calculator

Mobile-first Flask app for quick Parenteral Nutrition (PN/TPN) worksheet calculations, including Total Fluid Limit (TFL), IVFE, PN rate, protein intake, and glucose infusion rate (GIR).

This version is intentionally focused on quick bedside/mobile calculations for clinicians. The visible workflow excludes electrolyte/additive sections so the phone UI stays fast and compact.

## Features

- Password-protected blurred login page
- Mobile-first compact calculator UI
- Required named calculation sessions
- Save, edit, duplicate, delete, and print sessions
- Live worksheet math as values are entered
- TFL: mL/kg/day → mL/day → mL/hr
- IVFE: g/kg/day → g/day → mL/day → mL/hr
- PN volume: non-PN fluid aggregation → PN rate → PN order range
- Protein: g/kg/day → g/day → kcal/day
- GIR: TPN GIR, rider GIR, and total GIR
- SQLite persistence

## Quick start

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

## Deployment note

For production, run behind HTTPS and set environment variables securely:

```env
APP_ACCESS_PASSWORD=<strong password>
SECRET_KEY=<long random secret>
DATABASE_PATH=instance/pn_calculator.sqlite3
```

Example Gunicorn command:

```bash
gunicorn app:app
```
