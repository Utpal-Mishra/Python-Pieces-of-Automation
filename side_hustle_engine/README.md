# Side Hustle Engine v1

A small, auditable pipeline for turning public local-business data into **qualified website-service opportunities** with minimal repetitive work.

The goal is not spam or fake passive-income claims. The engine automates the repetitive parts:

1. Search configured local-business categories with Google Places Text Search (New).
2. Prioritise businesses with no website listed and useful demand signals.
3. Generate a clearly-labelled concept preview for each qualified lead.
4. Produce a review queue with a personalised outreach draft.
5. Leave the final contact decision to a human.

## Why the final outreach is manual

Electronic direct marketing is regulated. This project intentionally does **not** scrape personal email addresses or automatically send cold email/SMS/WhatsApp messages. Review the applicable rules and choose a lawful outreach route before contacting any lead.

## What you need

- Python 3.11+
- A Google Places API key with Places API (New) enabled
- `pip install -r requirements.txt`

## Quick start

```bash
cd side_hustle_engine
cp config.example.json config.json
export GOOGLE_PLACES_API_KEY="your-key"
python main.py --config config.json --output output
```

To test the full scoring / preview / queue flow without making an API call:

```bash
python main.py --sample --output output-sample
```

## Outputs

- `leads.csv` — all discovered candidates and scores
- `outreach_queue.csv` — shortlisted leads, concept-preview path, and draft message
- `previews/*.html` — unofficial concept landing pages for your review
- `run_summary.json` — counts and pipeline metadata

## Scoring

The default scoring deliberately favours a measurable digital gap:

- no website listed: strongest signal
- existing Google rating/review activity: evidence of real demand
- complete location / Maps information: easier to verify

Tune weights in `config.json` once you have real conversion data.

## Automation

The repository workflow `.github/workflows/side-hustle-engine.yml` can run weekly. It is disabled by default through the repository variable `SIDE_HUSTLE_AUTOMATION_ENABLED`.

To enable it:

1. Add the Actions secret `GOOGLE_PLACES_API_KEY`.
2. Add repository variable `SIDE_HUSTLE_AUTOMATION_ENABLED=true`.
3. Edit `config.example.json` or replace it with your own checked-in configuration.
4. Run the workflow manually once before relying on the schedule.

The workflow uploads the generated lead package as an Actions artifact. It does not contact anyone.

## Commercial model this supports

Use the engine as the top of a productised service funnel:

**discover -> verify -> concept preview -> human-approved outreach -> paid setup -> recurring hosting/maintenance**

The software can automate discovery, qualification, preview generation, onboarding, deployment, reporting and maintenance. The parts that should remain human are trust-building, approval of claims/content, pricing exceptions and client relationship decisions.
