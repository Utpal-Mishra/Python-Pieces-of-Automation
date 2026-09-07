# Live Integrations

This folder connects the agency/client-retention system to authorised live data sources. No client credentials are committed to the repository.

## 1. Prospect preview deployment — Netlify

The acquisition workflow can deploy only `output/previews/` to Netlify as an unlisted draft deploy. Internal files such as `audits/`, `prompts/`, lead scoring and commercial assumptions are never published.

Required GitHub configuration:

- Secret: `NETLIFY_AUTH_TOKEN`
- Secret: `NETLIFY_SITE_ID`
- Variable: `PREVIEW_DEPLOY_ENABLED=true`

Netlify draft deploys produce a unique URL. `finalize_share_links.py` then inserts that deployed base URL into `outreach_queue.csv` for every prospect.

For stronger confidentiality, configure project-level access controls on the Netlify project. The generated pages already contain `noindex,nofollow`, but an unlisted URL alone is not authentication.

## 2. Google Analytics 4

`live_metrics.py` uses the Google Analytics Data API and `runReport`.

Authorisation uses Google Application Default Credentials. The authenticated identity must have access to the client's GA4 property.

Set the client configuration:

```json
"ga4": {"enabled": true, "property_id": "123456789"}
```

The adapter currently normalises sessions, session key-event rate, product views, cart-to-view rate, checkout activity, purchases, purchase revenue and average purchase revenue.

## 3. Google Search Console

The adapter queries Search Analytics using the read-only Search Console scope. The authenticated identity must have access to the configured property.

```json
"search_console": {"enabled": true, "site_url": "sc-domain:example.ie"}
```

Normalised metrics include clicks, impressions, CTR and average position.

## 4. Google Business Profile Performance

The adapter uses the Business Profile Performance API with the `business.manage` OAuth scope.

```json
"business_profile": {"enabled": true, "location_id": "12345678901234567890"}
```

Normalised signals include Search/Maps impressions, direction requests, call clicks, website clicks and bookings.

Google may require Business Profile API access approval for the project. A configured API with zero quota must be approved before this connector can run.

## 5. Shopify

Shopify analytics uses `shopifyqlQuery` through the GraphQL Admin API. The merchant app/token must grant the required `read_reports` scope and any required protected-customer-data access.

Client config references an environment variable instead of storing the token:

```json
"shopify": {
  "enabled": true,
  "store_domain": "example-store.myshopify.com",
  "access_token_env": "EXAMPLE_SHOPIFY_ACCESS_TOKEN"
}
```

The adapter retrieves sales, orders, average order value, returning-customer rate, sessions, conversion rate and top-product signals.

## 6. Generate a live monthly report

First collect and normalise data:

```bash
python side_hustle_engine/integrations/live_metrics.py \
  --client clients/example.json \
  --output runtime/example-metrics.json
```

Then pass the generated payload to the existing subscription engine:

```bash
python side_hustle_engine/subscription_pipeline.py \
  --profiles side_hustle_engine/subscription_profiles.json \
  --client runtime/example-metrics.json \
  --plan commerce \
  --output runtime/example-report
```

If no explicit dates are supplied, the collector defaults to the last two complete calendar months so scheduled reports avoid comparing partial months.

## Credential model

For a real agency, credentials must be isolated per client. Recommended progression:

1. Pilot: repository/environment secrets with one test client.
2. Early clients: separate secret names per client and private client config files.
3. Scale: encrypted secret manager + OAuth token storage + tenant/client IDs in a database.

Never commit OAuth refresh tokens, Shopify access tokens, service-account JSON files or client secrets.
