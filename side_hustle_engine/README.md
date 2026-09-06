# Side Hustle Engine — Agency Factory

An auditable pipeline for turning public local-business information into **qualified website-agency opportunities, personalised research packs, website concepts and outreach-ready links** with minimal repetitive work.

The aim is not spam or fake passive-income claims. The engine automates the research and production work while leaving the trust-sensitive decision to contact a business with a human.

## Reel-inspired pipeline

1. **Find leads** — search selected locations and business categories with Google Places Text Search (New).
2. **Understand the niche** — map dentists, physiotherapists, clinics, beauty, restaurants and local services to different website structures, trust signals and CTAs.
3. **Audit the business** — enrich shortlisted leads with Place Details, public reputation themes, Maps review/photo links, phone/hours and, where a website exists, a lightweight conversion/technical audit.
4. **Model commercial value** — generate a transparent low/base/high website-value scenario and a heuristic agency-conversion probability. These are assumptions for prioritisation, never claims about the business's actual revenue.
5. **Build the concept** — generate an unofficial personalised HTML preview plus a structured website-generation prompt and audit JSON for deeper automated iteration.
6. **Prepare outreach** — produce channel-specific email, LinkedIn, Instagram and WhatsApp drafts and, once a preview host is connected, a shareable link for each prospect.

## Research and content guardrails

Google review/photo information is used as **research evidence**. The concept may infer non-quoted themes such as "professional" or "friendly", but production sites should use business-approved facts, assets and claims.

The pipeline does not:

- claim affiliation with the prospect;
- copy third-party photographs into a production website;
- turn review text into unattributed testimonials;
- invent treatments, qualifications, prices, awards or medical outcomes;
- claim to know a business's current website revenue without analytics;
- automatically send cold email, SMS, WhatsApp or social DMs.

Preview pages include `noindex,nofollow` and an explicit unofficial-concept notice.

## Files

- `agency_pipeline.py` — V2 agency research, audit, commercial model, concept generation and outreach queue.
- `niche_profiles.json` — niche matching, suggested information architecture, CTAs and editable commercial assumptions.
- `config.example.json` — categories, locations, scoring weights and pipeline limits.
- `main.py` — original V1 website-gap prototype retained for reference.

## What you need

- Python 3.11+
- Google Places API (New)
- `pip install -r requirements.txt`

## Test with no API spend

```bash
cd side_hustle_engine
python agency_pipeline.py \
  --config config.example.json \
  --profiles niche_profiles.json \
  --sample \
  --output output-sample
```

The sample uses fictitious businesses but runs the full research → niche → value model → preview → prompt → outreach-queue flow.

## Live run

```bash
export GOOGLE_PLACES_API_KEY="your-key"
python agency_pipeline.py \
  --config config.example.json \
  --profiles niche_profiles.json \
  --output output
```

## Outputs

- `leads.csv` — discovered prospects, scores and niche assignment.
- `outreach_queue.csv` — shortlisted businesses, problem summary, estimated value scenarios, conversion heuristic, channel drafts and shareable URL when configured.
- `audits/*.json` — structured business research, website audit and strategy evidence.
- `prompts/*.md` — business-specific website-generation / refinement brief.
- `previews/<business>/index.html` — personalised unofficial concept page.
- `run_summary.json` — batch-level forecast and pipeline metadata.

## Website audit

If a prospect already has a website, V2 can check basic signals such as:

- reachability and HTTPS;
- page title / meta-description presence;
- mobile viewport;
- contact links;
- booking / appointment language;
- presence of a form.

This makes the agency target both **no-website businesses** and **weak-website businesses** rather than treating every prospect identically.

## Commercial model

`niche_profiles.json` contains editable assumptions such as customer value and low/base/high incremental-customer scenarios. These exist to rank opportunities and frame a business case.

For example, the engine can say:

> Under the configured base scenario, three incremental customers at an assumed €250 value would represent €750/month.

It must **not** say:

> This clinic is losing €750/month.

until there is real analytics or client-supplied evidence.

The `agency_conversion_probability` is also only a starting heuristic. Once we record actual outreach outcomes, it should be replaced or calibrated using the real conversion dataset.

## Shareable links

Set `PREVIEW_BASE_URL` after connecting a preview host. The generated outreach queue will then contain a link for every preview.

Suitable architecture:

**generated static preview → private/unlisted preview host → unique prospect URL → human-approved outreach**

Netlify Deploy Previews or Cloudflare Pages preview deployments are good candidates because they provide unique preview URLs. Do not publicly index prospect concepts as though they were official sites.

## GitHub Actions automation

`.github/workflows/side-hustle-engine.yml`:

- compiles both V1 and V2;
- executes a zero-cost fictitious V2 smoke test on the PR;
- can run the live agency pipeline weekly;
- uploads the full lead package as a GitHub Actions artifact;
- never sends outreach automatically.

The scheduled run is gated. To activate it:

1. Add Actions secret `GOOGLE_PLACES_API_KEY`.
2. Add repository variable `SIDE_HUSTLE_AUTOMATION_ENABLED=true`.
3. Optionally add repository variable `PREVIEW_BASE_URL` after preview hosting is connected.
4. Run once manually and review the results before relying on the schedule.

## Operating model

The desired mature workflow is:

**discover → niche → research → audit → prioritise → generate → refine → publish preview → review outreach → sell → onboard → deploy production → recurring maintenance**

The machine should eventually do almost all repeated data gathering, audit generation, concept creation, deployment preparation and reporting. Human involvement remains where it adds the most value: quality control, sales conversation, factual approval and client relationship management.
