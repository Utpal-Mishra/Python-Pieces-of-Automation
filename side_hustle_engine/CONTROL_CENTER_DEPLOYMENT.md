# Control Center Deployment

## Recommended topology

- **GitHub** — source code, CI/CD and infrastructure definition only.
- **Render Web Service** — hosts the private Streamlit Control Center.
- **Postgres** — persistent CRM/event-log database.
- **Local mode** — development/emergency fallback only.

GitHub Pages cannot host this application because the Control Center is a stateful Python/Streamlit service rather than a static website.

## One-click Render Blueprint

The repository root contains `render.yaml`. Creating a Render Blueprint from this branch provisions:

- `agency-control-center` — Streamlit web service in Frankfurt;
- `agency-control-db` — PostgreSQL database in Frankfurt;
- private internal database networking;
- password-required Control Center access;
- health monitoring at `/_stcore/health`;
- deployment only after linked CI checks pass.

During the first Blueprint creation Render prompts for:

`CONTROL_CENTER_PASSWORD`

Use a unique strong password and store it in a password manager. Do not commit it to GitHub.

## Current pilot branch

The Blueprint currently deploys:

`feature/side-hustle-engine-v1`

After the pull request is merged and validated, change the Render service branch to `main` and update `render.yaml` accordingly.

## Access

After the first successful deployment Render assigns an HTTPS address similar to:

`https://agency-control-center.onrender.com`

Open that URL from your laptop or phone and enter the Control Center password in the sidebar.

The application is intentionally single-operator during the pilot. Before adding staff or client access, replace the shared password gate with identity-based authentication and roles.

## Free pilot limitations

The current Blueprint intentionally uses the Render free plans to avoid creating paid infrastructure without explicit approval.

Important: Render Free Postgres expires 30 days after creation. It is suitable only for the pilot. Before storing valuable live-client history, choose one of these durable options:

1. Upgrade the Render Postgres instance.
2. Replace `CRM_DATABASE_URL` with a persistent managed Postgres connection such as Neon/Supabase.

The application is portable because all persistence goes through `CRM_DATABASE_URL`.

## Local fallback

```bash
cd side_hustle_engine
pip install -r requirements.txt
export REQUIRE_CONTROL_CENTER_AUTH=false
streamlit run control_center.py
```

Local mode defaults to SQLite at:

`side_hustle_engine/runtime/agency_control.db`

Local mode is useful for development but should not be the main operating system because it is unavailable when your computer is off and is not automatically shared with GitHub Actions.

## Data boundaries

Never store the following in the Git repository:

- owner/client private contact data;
- CRM notes;
- credentials or OAuth tokens;
- subscription commercial terms that are meant to be private;
- the SQLite database;
- raw client analytics exports.

Those belong in Postgres/secret storage. GitHub contains the application and audit-able code only.
