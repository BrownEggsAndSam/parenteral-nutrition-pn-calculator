# Deployment Guide

This app is prepared for Render deployment so it can be accessed from a public URL.

## Recommended deployment: Render Web Service

The repo includes `render.yaml`, which defines a Render web service with:

- Python runtime
- `pip install -r requirements.txt` build command
- `gunicorn deploy:app` start command
- `PUBLIC_ACCESS=true` so anyone with the URL can open the calculator
- persistent SQLite storage at `/var/data/pn_calculator.sqlite3`
- a persistent disk mounted at `/var/data`

## Steps

1. Sign in to Render.
2. Choose **New +**.
3. Choose **Blueprint**.
4. Connect this GitHub repository:

   ```text
   BrownEggsAndSam/parenteral-nutrition-pn-calculator
   ```

5. Render should detect `render.yaml`.
6. During setup, Render may prompt for `APP_ACCESS_PASSWORD`. You can enter any strong value. Public mode is on by default, so the password is not used unless `PUBLIC_ACCESS` is changed to `false`.
7. Deploy the service.
8. After deployment finishes, Render will provide an `onrender.com` URL.

## Public vs password-protected mode

The Render blueprint currently sets:

```env
PUBLIC_ACCESS=true
```

This means anyone with the URL can use the app.

To require the blurred password screen again, change the Render environment variable to:

```env
PUBLIC_ACCESS=false
```

Then set:

```env
APP_ACCESS_PASSWORD=<your shared password>
```

## Important clinical/privacy warning

Public mode means anyone with the URL can access the dashboard and saved sessions. Do not enter names, MRNs, dates of birth, or any PHI unless the deployment environment is formally approved for that use.

For real hospital use, the safer configuration is:

```env
PUBLIC_ACCESS=false
```

and a shared password or individual user accounts.

## Always-on note

The blueprint uses Render's paid `starter` plan because free web services can spin down on inactivity and lose local SQLite file changes. The persistent disk keeps the SQLite database under `/var/data` across deploys and restarts.

If you change the plan to `free`, the app can still run, but it is not truly always-on and saved SQLite sessions can be lost.
