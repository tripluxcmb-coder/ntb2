# Deploy from GitHub to Vercel

This repository is ready for Vercel's native Flask runtime. Vercel imports the
top-level `app` object from `app.py`; it does not run Waitress, `run.py`, or
`launcher.py` in the cloud.

## 1. Create a private GitHub repository

1. Create a new **private** repository in GitHub. Do not add a README or
   `.gitignore` because both are already included here.
2. Extract this ZIP and open a terminal in the extracted project folder.
3. Upload the project using GitHub Desktop, the GitHub web uploader, or Git:

```bash
git init
git add .
git commit -m "Initial Vercel-ready relationship dashboard"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-PRIVATE-REPOSITORY.git
git push -u origin main
```

Before committing, confirm that `.env` and `.venv` are absent from `git status`.
Never commit the OpenRouter key or an access password.

## 2. Import the repository in Vercel

1. In Vercel, choose **Add New → Project** and import the private GitHub repository.
2. Leave **Root Directory** as the repository root.
3. Vercel should detect **Flask**. Do not set a build command or output directory.
4. Add the environment variables below for Production, Preview and Development.
5. Select **Deploy**.

Required access protection:

```text
REQUIRE_ACCESS_AUTH=true
APP_ACCESS_USERNAME=choose-a-nonpublic-username
APP_ACCESS_PASSWORD=choose-a-long-random-password
```

Optional OpenRouter recommendations:

```text
OPENROUTER_API_KEY=your-secret-key
OPENROUTER_MODEL=openai/gpt-4.1-mini
OPENROUTER_REQUIRE_ZDR=true
```

Optional display settings:

```text
BANK_NAME=Nations Trust Bank
SOURCE_CURRENCY=LKR
```

Do not set `HOST`, `PORT`, `OPEN_BROWSER`, or local file-system paths in Vercel.

## 3. Verify the deployment

Open `https://YOUR-PROJECT.vercel.app/health`; it should return:

```json
{"status":"ok"}
```

Then open the root URL. The browser should request the username and password
configured above. Verify the company dropdown, CIF filter, charts, product
priorities and visit-brief download.

If the root page returns HTTP 503, `APP_ACCESS_PASSWORD` is missing. Add it in
Vercel **Project Settings → Environment Variables**, then redeploy. If AI
priorities are unavailable, confirm `OPENROUTER_API_KEY` is configured for the
current Vercel environment and inspect the Function logs without copying
customer data or secrets into a support ticket.

## Data updates in this GitHub version

The included CSV/JSON files are bundled read-only into each deployment. To
publish a new balance snapshot, replace the files under `data/`, commit and push
to `main`; Vercel will build a new immutable production deployment.

Vercel Functions do not provide persistent writable application storage. For
automatic backend updates without a Git push, replace the file adapter with a
private bank-approved object store or database such as AWS S3/RDS. Do not try to
run `backend_update.py` inside Vercel.

## Security boundary

The included HTTP password is a minimum accidental-exposure safeguard, not
bank-grade identity or authorization. Before using real customer information,
obtain the bank's cloud/security approval and integrate SSO, per-user CIF
entitlements, audit logging, retention controls and an approved data source.
Keep the GitHub repository private and review whether the included balance file
is permitted to leave the bank-controlled environment.
