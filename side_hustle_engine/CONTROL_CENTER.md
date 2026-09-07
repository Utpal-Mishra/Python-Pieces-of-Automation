# Agency Control Center

The Control Center is the private operating layer for the Side Hustle Engine. Pipeline CSVs and GitHub artifacts remain evidence/output files; the CRM database is the system of record for prospect/client progress.

## What it tracks

Each business has one account record containing:

- business name, niche and location;
- lead score and opportunity summary;
- website/concept preview link;
- current pipeline stage;
- owner/contact name and preferred contact channel;
- next action and due date;
- subscription plan and actual monthly fee;
- created/updated timestamps.

Every meaningful change also creates an append-only event. Old history is never replaced when the current account status changes.

## Pipeline stages

`DISCOVERED -> QUALIFIED -> PREVIEW_READY -> APPROVED_FOR_CONTACT -> CONTACTED -> REPLIED -> MEETING -> PROPOSAL -> WON -> ONBOARDING -> LIVE -> RETAINER`

Side states: `LOST`, `PAUSED`.

The discovery pipeline is prevented from moving a prospect backwards after a human has advanced it.

## Automatic logging

### Acquisition runs

When `CRM_AUTO_SYNC_ENABLED=true`, the weekly/live agency workflow writes the generated `outreach_queue.csv` into the private CRM using `crm_sync.py`.

New businesses create `LEAD_CREATED` events. Repeated discovery runs create `PIPELINE_REFRESHED` events without erasing the sales history.

### Human updates

`control_center.py` writes changes such as contact status, sales stage, owner details, next action, plan and fee directly to the CRM and records an event with the note supplied by the operator.

### Monthly client intelligence

The monthly reporting workflow can call `crm_log_report.py`. This records `MONTHLY_REPORT_GENERATED`, stores the report period/plan/actions in event metadata and promotes the report's top recommendation to the account's next action.

## Dashboard views

The Streamlit Control Center provides:

1. **Pipeline** — stage board plus all prospect/client records.
2. **Account Detail** — one business, editable progress and full timeline.
3. **Clients** — won/onboarding/live/retainer accounts.
4. **Activity Log** — append-only chronological operational history.
5. **Revenue** — retainer count, MRR, annualised recurring revenue and client plan table.

## Persistence

Local development defaults to:

`sqlite:///side_hustle_engine/runtime/agency_control.db`

For a hosted dashboard use a private persistent Postgres-compatible database and set:

`CRM_DATABASE_URL=postgresql+psycopg://...`

This can point to a managed Postgres provider such as Supabase, Neon, Railway or another private PostgreSQL service. Do not use a temporary filesystem database for a production dashboard.

## Authentication

For any hosted instance set:

- `REQUIRE_CONTROL_CENTER_AUTH=true`
- `CONTROL_CENTER_PASSWORD=<strong secret>`

The current password gate is suitable for a single-operator pilot. Before adding employees or clients, replace it with provider authentication/SSO and role-based access.

## Run locally

```bash
cd side_hustle_engine
pip install -r requirements.txt
streamlit run control_center.py
```

Optional first sync:

```bash
python crm_sync.py --queue output/outreach_queue.csv
```

## GitHub Actions integration

To allow automated lead ingestion after each live agency run configure:

- repository variable: `CRM_AUTO_SYNC_ENABLED=true`
- repository secret: `CRM_DATABASE_URL`

The monthly client workflow uses the same CRM connection. A client config may include `crm_account_id` so the generated report is always attached to the correct business.

## Important data rule

Do not commit owner contact details, client credentials, private notes or the CRM database to the public repository. The repository contains application code; private operational/client data belongs in the configured database/secrets layer.
