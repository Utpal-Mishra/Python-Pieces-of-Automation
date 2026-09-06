# Side Hustle Engine — Agency Factory

An auditable pipeline for turning public local-business information into **qualified website-agency opportunities, personalised research packs, website concepts, outreach-ready links and recurring analytics services** with minimal repetitive work.

The aim is not spam or fake passive-income claims. The engine automates the research and production work while leaving trust-sensitive contact, factual approval and commercial decisions with a human.

## Agency acquisition pipeline

1. **Find leads** — search selected locations and business categories with Google Places Text Search (New).
2. **Understand the niche** — map dentists, physiotherapists, clinics, beauty, restaurants, home services and retail businesses to different website structures, trust signals and CTAs.
3. **Audit the business** — enrich shortlisted leads with Place Details, public reputation themes, Maps review/photo links, phone/hours and, where a website exists, a lightweight conversion/technical audit.
4. **Model commercial value** — generate a transparent low/base/high website-value scenario and a heuristic agency-conversion probability. These are assumptions for prioritisation, never claims about the business's actual revenue.
5. **Build the concept** — generate an unofficial personalised HTML preview plus a structured website-generation prompt and audit JSON for deeper automated iteration.
6. **Prepare outreach** — produce channel-specific email, LinkedIn, Instagram and WhatsApp drafts and, once a preview host is connected, a shareable link for each prospect.
7. **Sell and onboard** — use `SALES_PLAYBOOK.md` for qualification, discovery, offer structure and closing principles.

## Recurring subscription pipeline

After the website is live, `subscription_pipeline.py` turns connected/client-approved performance data into a monthly report and prioritised action list.

Configured plans in `subscription_profiles.json`:

- **Website Care** — site health + basic KPI snapshot.
- **Growth Intelligence** — website/search/local/review performance + monthly opportunity ranking.
- **Commerce Intelligence** — store funnel, product/category performance, traffic-to-revenue, customer review analysis and commercial recommendations.

The pipeline is source-agnostic. In production, adapters can feed it data from services such as GA4, Search Console, Google Business Profile and Shopify once the client authorises the relevant connections.

## Retail niche

Retail is now a dedicated strategy rather than falling into the generic local-business profile. The engine can target boutiques, gift shops, fashion/accessory stores, home-goods stores and similar retailers with a structure focused on:

- new/featured products;
- collections;
- gifts/local makers;
- customer reputation;
- location/hours;
- enquiry or item-reservation path;
- optional commerce integration after client discovery.

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

- `agency_pipeline.py` — agency research, audit, commercial model, concept generation and outreach queue.
- `niche_profiles.json` — niche matching, information architecture, CTAs and editable commercial assumptions.
- `subscription_pipeline.py` — recurring client performance analysis and owner-facing monthly report generation.
- `subscription_profiles.json` — subscription tiers, KPI groups and editable price hypotheses.
- `SALES_PLAYBOOK.md` — prospect qualification, outreach, discovery and selling structure.
- `config.example.json` — categories, locations, scoring weights and pipeline limits.
- `main.py` — original V1 website-gap prototype retained for reference.

## What you need

- Python 3.11+
- Google Places API (New)
- `pip install -r requirements.txt`

## Test the agency pipeline with no API spend

```bash
cd side_hustle_engine
python agency_pipeline.py \
  --config config.example.json \
  --profiles niche_profiles.json \
  --sample \
  --output output-sample
```

## Test the subscription pipeline

```bash
python subscription_pipeline.py \
  --profiles subscription_profiles.json \
  --plan commerce \
  --sample \
  --output subscription-output-sample
```

## Live acquisition run

```bash
export GOOGLE_PLACES_API_KEY="your-key"
python agency_pipeline.py \
  --config config.example.json \
  --profiles niche_profiles.json \
  --output output
```

## Acquisition outputs

- `leads.csv` — discovered prospects, scores and niche assignment.
- `outreach_queue.csv` — shortlisted businesses, problem summary, value scenarios, conversion heuristic, channel drafts and shareable URL when configured.
- `audits/*.json` — structured business research, website audit and strategy evidence.
- `prompts/*.md` — business-specific website-generation/refinement brief.
- `previews/<business>/index.html` — personalised unofficial concept page.
- `run_summary.json` — batch-level forecast and pipeline metadata.

## Subscription outputs

- `monthly_report.json` — structured KPI movement and recommended actions.
- `monthly_report.md` — client/owner-facing monthly summary.

The current subscription engine accepts a normalised client-data JSON. Live provider adapters are the next integration layer; the analysis/reporting logic is deliberately kept independent from any one analytics provider.

## Website audit

If a prospect already has a website, the acquisition pipeline can check basic signals such as reachability/HTTPS, page title/meta description, mobile viewport, contact links, booking/appointment language and form presence.

This makes the agency target both **no-website businesses** and **weak-website businesses** rather than treating every prospect identically.

## Commercial model

`niche_profiles.json` contains editable assumptions such as customer value and low/base/high incremental-customer scenarios. These exist to rank opportunities and frame a business case; they are never presented as factual revenue without real client data.

`agency_conversion_probability` is also a starting heuristic. Once actual outreach outcomes are logged, it should be calibrated using the real conversion dataset.

## Shareable links

Set `PREVIEW_BASE_URL` after connecting a preview host. The generated outreach queue will then contain a link for every preview.

Suitable architecture:

**generated static preview → private/unlisted preview host → unique prospect URL → human-approved outreach**

Do not publicly index prospect concepts as though they were official sites.

## GitHub Actions automation

`.github/workflows/side-hustle-engine.yml`:

- compiles V1, agency V2 and the subscription pipeline;
- executes zero-cost fictitious acquisition and subscription smoke tests on the PR;
- can run the live agency acquisition pipeline weekly;
- uploads the full lead package as a GitHub Actions artifact;
- never sends outreach automatically.

The scheduled acquisition run remains gated by `SIDE_HUSTLE_AUTOMATION_ENABLED=true` plus the Places API key. Recurring client reports should be scheduled only after a client exists and its data-source permissions are configured.

## Mature operating model

**discover → niche → research → audit → prioritise → generate → refine → publish preview → review outreach → sell → onboard → deploy production → measure → analyse → recommend → retain**

The machine should do almost all repeated data gathering, audit generation, concept creation, deployment preparation and reporting. Human involvement remains where it adds the most value: quality control, sales conversation, factual approval and client relationship management.
