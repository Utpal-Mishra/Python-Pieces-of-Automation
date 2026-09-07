from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
PLACE_DETAILS_URL = "https://places.googleapis.com/v1/places/{place_id}"

DISCOVERY_FIELDS = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.rating",
        "places.userRatingCount",
        "places.primaryType",
        "places.businessStatus",
        "nextPageToken",
    ]
)

DETAIL_FIELDS = ",".join(
    [
        "id",
        "displayName",
        "formattedAddress",
        "websiteUri",
        "googleMapsUri",
        "rating",
        "userRatingCount",
        "primaryType",
        "businessStatus",
        "nationalPhoneNumber",
        "regularOpeningHours",
        "reviews",
        "photos",
        "googleMapsLinks",
    ]
)

REVIEW_THEME_TERMS = {
    "friendly": ["friendly", "welcoming", "kind", "lovely", "warm"],
    "professional": ["professional", "expert", "knowledgeable", "competent"],
    "quality": ["excellent", "amazing", "great", "quality", "brilliant"],
    "trust": ["trust", "trusted", "honest", "reliable", "recommend"],
    "speed": ["quick", "fast", "efficient", "prompt", "on time"],
    "care": ["care", "caring", "gentle", "comfortable", "helpful"],
    "cleanliness": ["clean", "spotless", "hygienic", "tidy"],
    "value": ["value", "reasonable", "affordable", "worth"],
}


@dataclass
class Lead:
    place_id: str
    name: str
    category: str
    niche: str
    address: str
    website: str
    maps_uri: str
    rating: float | None
    review_count: int
    source_query: str
    business_status: str
    missing_website: bool
    score: int = 0
    agency_conversion_probability: float = 0.0
    phone: str = ""
    reviews_uri: str = ""
    photos_uri: str = ""
    opening_hours: str = ""
    review_themes: str = ""
    web_audit_score: int | None = None
    problem_summary: str = ""
    preview_file: str = ""
    audit_file: str = ""
    prompt_file: str = ""
    share_link: str = ""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def display_name(place: dict[str, Any]) -> str:
    raw = place.get("displayName") or {}
    return text(raw.get("text")) if isinstance(raw, dict) else text(raw)


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower().strip())
    return value.strip("-") or "business"


def stable_token(place_id: str, name: str) -> str:
    digest = hashlib.sha256(f"{place_id}|{name}".encode("utf-8")).hexdigest()
    return digest[:10]


def place_headers(api_key: str, field_mask: str) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": field_mask,
    }


def fetch_places(api_key: str, query: str, limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    token: str | None = None
    page_size = min(max(limit, 1), 20)

    while len(results) < limit:
        body: dict[str, Any] = {"textQuery": query, "pageSize": page_size}
        if token:
            body["pageToken"] = token

        response = requests.post(
            TEXT_SEARCH_URL,
            headers=place_headers(api_key, DISCOVERY_FIELDS),
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        results.extend(payload.get("places", []))
        token = payload.get("nextPageToken")
        if not token:
            break

    return results[:limit]


def fetch_place_details(api_key: str, place_id: str) -> dict[str, Any]:
    response = requests.get(
        PLACE_DETAILS_URL.format(place_id=place_id),
        headers=place_headers(api_key, DETAIL_FIELDS),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def match_niche(primary_type: str, source_query: str, profiles: dict[str, Any]) -> str:
    haystack = f"{primary_type} {source_query}".lower()
    for niche, profile in profiles.items():
        if niche == "default":
            continue
        keywords = [str(x).lower() for x in profile.get("match_keywords", [])]
        if any(keyword in haystack for keyword in keywords):
            return niche
    return "default"


def to_lead(place: dict[str, Any], query: str, profiles: dict[str, Any]) -> Lead:
    website = text(place.get("websiteUri"))
    raw_rating = place.get("rating")
    try:
        rating = float(raw_rating) if raw_rating is not None else None
    except (TypeError, ValueError):
        rating = None

    try:
        review_count = int(place.get("userRatingCount") or 0)
    except (TypeError, ValueError):
        review_count = 0

    category = text(place.get("primaryType")) or "local_business"
    niche = match_niche(category, query, profiles)
    return Lead(
        place_id=text(place.get("id")),
        name=display_name(place) or "Unnamed business",
        category=category,
        niche=niche,
        address=text(place.get("formattedAddress")),
        website=website,
        maps_uri=text(place.get("googleMapsUri")),
        rating=rating,
        review_count=review_count,
        source_query=query,
        business_status=text(place.get("businessStatus")),
        missing_website=not bool(website),
    )


def score_lead(lead: Lead, weights: dict[str, int]) -> int:
    score = 0
    if lead.missing_website:
        score += weights.get("missing_website", 45)
    else:
        score += weights.get("website_present_audit_opportunity", 5)
    if lead.rating is not None:
        score += weights.get("rating_present", 8)
    if lead.review_count >= 10:
        score += weights.get("reviews_10_plus", 8)
    if lead.review_count >= 50:
        score += weights.get("reviews_50_plus", 10)
    if lead.review_count >= 150:
        score += weights.get("reviews_150_plus", 8)
    if lead.address:
        score += weights.get("address_present", 4)
    if lead.maps_uri:
        score += weights.get("maps_uri_present", 4)
    if lead.rating is not None and lead.rating >= 4.0:
        score += weights.get("rating_4_plus", 6)
    if lead.business_status and "OPERATIONAL" in lead.business_status.upper():
        score += weights.get("operational", 7)
    return min(score, 100)


def conversion_probability(score: int, missing_website: bool) -> float:
    """Prioritisation heuristic, not a promise of actual agency conversion."""
    probability = 0.02 + max(score - 50, 0) * 0.002
    if missing_website:
        probability += 0.015
    return round(min(max(probability, 0.01), 0.18), 3)


def review_text(review: dict[str, Any]) -> str:
    raw = review.get("text") or {}
    return text(raw.get("text")) if isinstance(raw, dict) else text(raw)


def infer_review_themes(reviews: list[dict[str, Any]]) -> list[str]:
    corpus = " ".join(review_text(review).lower() for review in reviews)
    scored: list[tuple[int, str]] = []
    for theme, terms in REVIEW_THEME_TERMS.items():
        hits = sum(corpus.count(term) for term in terms)
        if hits:
            scored.append((hits, theme))
    scored.sort(reverse=True)
    return [theme for _, theme in scored[:4]]


def opening_hours_text(details: dict[str, Any]) -> str:
    hours = details.get("regularOpeningHours") or {}
    descriptions = hours.get("weekdayDescriptions") or []
    return " | ".join(text(item) for item in descriptions if text(item))


def enrich_lead(lead: Lead, details: dict[str, Any]) -> None:
    lead.phone = text(details.get("nationalPhoneNumber"))
    lead.opening_hours = opening_hours_text(details)
    links = details.get("googleMapsLinks") or {}
    lead.reviews_uri = text(links.get("reviewsUri"))
    lead.photos_uri = text(links.get("photosUri"))
    reviews = details.get("reviews") or []
    lead.review_themes = ", ".join(infer_review_themes(reviews))


def audit_existing_website(url: str, timeout: int = 12) -> dict[str, Any]:
    audit: dict[str, Any] = {
        "url": url,
        "reachable": False,
        "https": url.lower().startswith("https://"),
        "status_code": None,
        "has_title": False,
        "has_meta_description": False,
        "mobile_viewport": False,
        "has_contact_link": False,
        "has_booking_signal": False,
        "has_form": False,
        "score": 0,
        "issues": [],
    }
    try:
        response = requests.get(
            url,
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; SideHustleAudit/1.0)"},
        )
        audit["status_code"] = response.status_code
        audit["reachable"] = response.ok
        body = response.text[:1_000_000].lower()
        audit["https"] = response.url.lower().startswith("https://")
        audit["has_title"] = bool(re.search(r"<title[^>]*>\s*[^<]{3,}", body, re.I))
        audit["has_meta_description"] = "name=\"description\"" in body or "name='description'" in body
        audit["mobile_viewport"] = "name=\"viewport\"" in body or "name='viewport'" in body
        audit["has_contact_link"] = "mailto:" in body or "tel:" in body or "contact" in body
        audit["has_booking_signal"] = any(
            signal in body for signal in ["book now", "book online", "appointment", "reserve", "schedule"]
        )
        audit["has_form"] = "<form" in body
    except requests.RequestException as exc:
        audit["error"] = str(exc)

    checks = [
        ("reachable", 25, "Website is not reliably reachable."),
        ("https", 15, "Website does not resolve over HTTPS."),
        ("has_title", 10, "Page title is missing or weak."),
        ("has_meta_description", 10, "Meta description appears to be missing."),
        ("mobile_viewport", 15, "Mobile viewport configuration was not detected."),
        ("has_contact_link", 10, "Clear contact action was not detected."),
        ("has_booking_signal", 10, "Booking/appointment CTA was not detected."),
        ("has_form", 5, "Lead/contact form was not detected."),
    ]
    score = 0
    for key, points, issue in checks:
        if audit.get(key):
            score += points
        else:
            audit["issues"].append(issue)
    audit["score"] = score
    return audit


def website_value_scenarios(profile: dict[str, Any]) -> dict[str, Any]:
    value = float(profile.get("assumed_customer_value_eur", 150))
    scenarios = profile.get("incremental_customers_per_month", [1, 3, 6])
    low, base, high = [float(x) for x in scenarios[:3]]
    return {
        "assumed_customer_value_eur": value,
        "incremental_customers_per_month": {"low": low, "base": base, "high": high},
        "estimated_monthly_value_eur": {
            "low": round(low * value, 2),
            "base": round(base * value, 2),
            "high": round(high * value, 2),
        },
        "warning": (
            "Scenario model only. This is not the business's current website revenue and must not "
            "be presented as factual without analytics or client-supplied conversion data."
        ),
    }


def problem_summary(lead: Lead, website_audit: dict[str, Any] | None) -> str:
    if lead.missing_website:
        if lead.review_count >= 50:
            return "Strong public demand signal but no website returned: likely discoverability-to-conversion gap."
        return "No website returned: opportunity to create an owned conversion destination beyond directory listings."
    if website_audit and int(website_audit.get("score") or 0) < 70:
        issues = website_audit.get("issues") or []
        return "Existing website has improvement opportunities: " + "; ".join(issues[:3])
    return "Existing website present: lead requires a design/conversion review before outreach."


def concept_html(lead: Lead, profile: dict[str, Any], commercial: dict[str, Any]) -> str:
    name = html.escape(lead.name)
    address = html.escape(lead.address or "Local service area")
    niche_label = html.escape(text(profile.get("label")) or lead.niche.replace("_", " ").title())
    maps_link = html.escape(lead.maps_uri or "#", quote=True)
    cta = html.escape(text(profile.get("primary_cta")) or "Contact the business")
    themes = [x.strip() for x in lead.review_themes.split(",") if x.strip()]
    theme_html = "".join(f"<span class='chip'>{html.escape(x.title())}</span>" for x in themes)
    if not theme_html:
        theme_html = "<span class='chip'>Public reputation to verify</span>"

    sections = profile.get("suggested_sections", ["Services", "About", "Reviews", "Contact"])
    section_cards = "".join(
        f"<article class='card'><div class='kicker'>Suggested section</div><h3>{html.escape(str(section))}</h3>"
        "<p>Structure to confirm with the business before production.</p></article>"
        for section in sections[:6]
    )
    base_value = commercial["estimated_monthly_value_eur"]["base"]

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{name} — Unofficial agency concept</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:#0a0b0d; color:#f6f7f8; }}
.wrap {{ width:min(1120px,92vw); margin:0 auto; }}
.notice {{ margin:18px 0; padding:10px 14px; border:1px solid #343842; border-radius:999px; display:inline-block; color:#b9bec8; font-size:12px; }}
.hero {{ min-height:68vh; display:grid; align-content:center; gap:18px; }}
.kicker {{ color:#9ba2ad; text-transform:uppercase; letter-spacing:.12em; font-size:12px; }}
h1 {{ font-size:clamp(48px,9vw,104px); line-height:.94; margin:0; max-width:950px; }}
h2 {{ font-size:clamp(28px,4vw,48px); }} h3 {{ margin:8px 0; }}
.lead {{ max-width:760px; color:#c7cbd2; font-size:clamp(18px,2.3vw,24px); line-height:1.5; }}
.actions,.chips {{ display:flex; flex-wrap:wrap; gap:10px; }}
.btn,.chip {{ display:inline-block; padding:12px 16px; border-radius:999px; text-decoration:none; }}
.btn {{ background:#f4f5f6; color:#0a0b0d; font-weight:700; }}
.chip {{ border:1px solid #343842; color:#d1d4da; font-size:13px; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; margin:24px 0 70px; }}
.card {{ border:1px solid #272b33; background:#111319; border-radius:20px; padding:22px; }}
.meta {{ color:#aeb3bd; }} footer {{ border-top:1px solid #272b33; padding:24px 0 40px; color:#8d949f; font-size:12px; line-height:1.5; }}
</style>
</head>
<body><main class="wrap">
<div class="notice">UNOFFICIAL CONCEPT · NOT AFFILIATED WITH OR ENDORSED BY {name}</div>
<section class="hero"><div class="kicker">{niche_label} · {address}</div><h1>{name}</h1>
<p class="lead">A personalised website direction based on verified public business information and a niche-specific conversion structure. Final claims, services, photos and branding require business approval.</p>
<div class="actions"><a class="btn" href="#" onclick="return false">{cta}</a><a class="chip" href="{maps_link}" target="_blank" rel="noreferrer">Verify Google listing</a></div></section>
<section><div class="kicker">Public reputation themes</div><h2>What customers appear to value</h2><div class="chips">{theme_html}</div>
<p class="meta">Themes are inferred from available public review text and are research signals, not approved marketing claims.</p></section>
<section><div class="kicker">Proposed information architecture</div><h2>Built around the niche, not a generic template</h2><div class="grid">{section_cards}</div></section>
<section class="card"><div class="kicker">Commercial scenario</div><h2>Base scenario: €{base_value:,.0f}/month of potential incremental customer value</h2>
<p class="meta">Illustrative scenario only. It is not an estimate of this business's current website revenue.</p></section>
<footer>Agency research preview. Revalidate public facts before outreach. Do not reuse third-party photos or review quotations in production without appropriate rights, attribution and client approval.</footer>
</main></body></html>"""


def build_audit(
    lead: Lead,
    profile: dict[str, Any],
    website_audit: dict[str, Any] | None,
    commercial: dict[str, Any],
) -> dict[str, Any]:
    return {
        "business": {
            "name": lead.name,
            "category": lead.category,
            "niche": lead.niche,
            "address": lead.address,
            "website": lead.website,
            "phone": lead.phone,
            "rating": lead.rating,
            "review_count": lead.review_count,
            "maps_uri": lead.maps_uri,
            "reviews_uri": lead.reviews_uri,
            "photos_uri": lead.photos_uri,
            "opening_hours": lead.opening_hours,
            "review_themes": [x.strip() for x in lead.review_themes.split(",") if x.strip()],
        },
        "agency": {
            "lead_score": lead.score,
            "heuristic_conversion_probability": lead.agency_conversion_probability,
            "problem_summary": lead.problem_summary,
        },
        "website_audit": website_audit,
        "commercial_scenarios": commercial,
        "niche_strategy": {
            "label": profile.get("label", lead.niche),
            "primary_cta": profile.get("primary_cta", "Contact"),
            "suggested_sections": profile.get("suggested_sections", []),
            "trust_elements": profile.get("trust_elements", []),
        },
        "research_guardrails": [
            "Verify facts before outreach.",
            "Treat review themes as research signals, not approved testimonials.",
            "Do not present scenario values as the business's actual revenue.",
            "Use business-owned or properly licensed images in the final production site.",
        ],
    }


def website_prompt(lead: Lead, profile: dict[str, Any], audit: dict[str, Any]) -> str:
    payload = json.dumps(audit, indent=2, ensure_ascii=False)
    return f"""# Website Generation Brief — {lead.name}

You are building an UNOFFICIAL agency concept for outreach, not a production website.

## Objective
Create a polished, mobile-first {profile.get('label', lead.niche)} website concept that addresses the business problem in the audit.

## Rules
- Use only facts in the research payload as facts.
- Do not invent treatments, qualifications, prices, awards, medical outcomes, opening hours or staff names.
- Treat suggested service sections as structure to confirm unless verified.
- Do not copy review quotations or third-party photos into production without rights/approval.
- Keep an "Unofficial concept — not affiliated or endorsed" notice on outreach previews.
- Add noindex,nofollow to preview pages.
- Optimise for the primary CTA: {profile.get('primary_cta', 'Contact')}.
- Make the visual direction specific to the niche rather than generic SaaS styling.
- Produce an accessible responsive page with trust, service, location and conversion sections.

## Research payload
```json
{payload}
```

## Automated iteration checklist
1. Validate that every factual claim appears in the payload.
2. Check mobile layout and CTA visibility.
3. Make the first screen explain the business and the desired customer action.
4. Surface genuine trust signals without fabricating testimonials.
5. Ensure the concept can be converted to production quickly after client approval.
"""


def channel_messages(lead: Lead) -> dict[str, str]:
    common = (
        f"I put together an unofficial website concept for {lead.name} after reviewing its public listing. "
        f"The main opportunity I noticed: {lead.problem_summary}"
    )
    return {
        "email_subject": f"Website concept for {lead.name}",
        "email": (
            f"Hi {lead.name} team,\n\n{common}\n\n"
            "I have a private concept link I can share. If improving the site is already on your radar, "
            "I can turn it into a production version using your approved content, branding and images.\n\n"
            "Regards,\nUtpal"
        ),
        "linkedin_dm": (
            f"Hi — I created a small unofficial website concept for {lead.name}. "
            f"{lead.problem_summary} If useful, I can share the preview link here."
        ),
        "instagram_dm": (
            f"Hi! I came across {lead.name} while researching local businesses and built a small unofficial "
            "website concept around the public information available. Happy to send the preview if useful."
        ),
        "whatsapp": (
            f"Hi, I built an unofficial website concept for {lead.name} based on its public business listing. "
            "If you are considering a website/update, I can share the preview link. No obligation."
        ),
    }


def build_share_link(base_url: str, relative_preview: str) -> str:
    if not base_url:
        return ""
    return f"{base_url.rstrip('/')}/{relative_preview.replace(os.sep, '/')}"


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def sample_places() -> list[tuple[dict[str, Any], str]]:
    return [
        (
            {
                "id": "sample-dental",
                "displayName": {"text": "River Lee Dental"},
                "formattedAddress": "Sample Street, Cork, Ireland",
                "googleMapsUri": "#",
                "rating": 4.8,
                "userRatingCount": 118,
                "primaryType": "dentist",
                "businessStatus": "OPERATIONAL",
            },
            "dentists in Cork, Ireland",
        ),
        (
            {
                "id": "sample-physio",
                "displayName": {"text": "Cork Motion Physio"},
                "formattedAddress": "Sample Quay, Cork, Ireland",
                "googleMapsUri": "#",
                "rating": 4.6,
                "userRatingCount": 52,
                "primaryType": "physiotherapist",
                "businessStatus": "OPERATIONAL",
            },
            "physiotherapists in Cork, Ireland",
        ),
    ]


def sample_details(place_id: str) -> dict[str, Any]:
    return {
        "id": place_id,
        "nationalPhoneNumber": "+353 21 000 0000",
        "regularOpeningHours": {"weekdayDescriptions": ["Monday: 09:00–17:00", "Tuesday: 09:00–17:00"]},
        "reviews": [
            {"text": {"text": "Very professional and friendly team. Excellent care and easy to recommend."}},
            {"text": {"text": "Clean, welcoming and efficient service."}},
        ],
        "googleMapsLinks": {"reviewsUri": "#", "photosUri": "#"},
    }


def run(config: dict[str, Any], profiles: dict[str, Any], output_dir: Path, use_sample: bool = False) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir = output_dir / "previews"
    audit_dir = output_dir / "audits"
    prompt_dir = output_dir / "prompts"
    preview_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
    if not use_sample and not api_key:
        raise SystemExit("GOOGLE_PLACES_API_KEY is required unless --sample is used.")

    if use_sample:
        raw_items = sample_places()
    else:
        raw_items: list[tuple[dict[str, Any], str]] = []
        for query in config.get("queries", []):
            places = fetch_places(api_key, query, int(config.get("max_leads_per_query", 10)))
            raw_items.extend((place, query) for place in places)

    discovered: list[Lead] = []
    seen: set[str] = set()
    for place, query in raw_items:
        lead = to_lead(place, query, profiles)
        key = lead.place_id or f"{lead.name}|{lead.address}".lower()
        if key in seen:
            continue
        seen.add(key)
        lead.score = score_lead(lead, config.get("weights", {}))
        lead.agency_conversion_probability = conversion_probability(lead.score, lead.missing_website)
        discovered.append(lead)

    discovered.sort(key=lambda item: (item.score, item.review_count), reverse=True)

    min_score = int(config.get("min_score", 60))
    enrich_top_n = int(config.get("enrich_top_n", 20))
    include_existing = bool(config.get("include_existing_websites", True))
    shortlisted = [
        lead for lead in discovered if lead.score >= min_score and (include_existing or lead.missing_website)
    ][:enrich_top_n]

    preview_base_url = text(os.getenv("PREVIEW_BASE_URL") or config.get("preview_base_url"))
    queue_rows: list[dict[str, Any]] = []

    for index, lead in enumerate(shortlisted, start=1):
        details = sample_details(lead.place_id) if use_sample else fetch_place_details(api_key, lead.place_id)
        enrich_lead(lead, details)

        profile = profiles.get(lead.niche) or profiles["default"]
        website_audit = None
        if lead.website and bool(config.get("audit_existing_websites", True)):
            website_audit = audit_existing_website(lead.website)
            lead.web_audit_score = int(website_audit.get("score") or 0)

        lead.problem_summary = problem_summary(lead, website_audit)
        commercial = website_value_scenarios(profile)
        audit = build_audit(lead, profile, website_audit, commercial)

        token = stable_token(lead.place_id, lead.name)
        folder = f"{index:03d}-{slugify(lead.name)}-{token}"
        target_dir = preview_dir / folder
        target_dir.mkdir(parents=True, exist_ok=True)
        relative_preview = str(Path("previews") / folder / "index.html")
        (target_dir / "index.html").write_text(concept_html(lead, profile, commercial), encoding="utf-8")
        lead.preview_file = relative_preview
        lead.share_link = build_share_link(preview_base_url, relative_preview)

        audit_path = audit_dir / f"{folder}.json"
        audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
        lead.audit_file = str(Path("audits") / audit_path.name)

        prompt_path = prompt_dir / f"{folder}.md"
        prompt_path.write_text(website_prompt(lead, profile, audit), encoding="utf-8")
        lead.prompt_file = str(Path("prompts") / prompt_path.name)

        messages = channel_messages(lead)
        queue_rows.append(
            {
                "name": lead.name,
                "niche": lead.niche,
                "address": lead.address,
                "website": lead.website,
                "rating": "" if lead.rating is None else lead.rating,
                "review_count": lead.review_count,
                "lead_score": lead.score,
                "agency_conversion_probability": lead.agency_conversion_probability,
                "problem_summary": lead.problem_summary,
                "estimated_monthly_value_low_eur": commercial["estimated_monthly_value_eur"]["low"],
                "estimated_monthly_value_base_eur": commercial["estimated_monthly_value_eur"]["base"],
                "estimated_monthly_value_high_eur": commercial["estimated_monthly_value_eur"]["high"],
                "preview_file": lead.preview_file,
                "share_link": lead.share_link,
                "audit_file": lead.audit_file,
                "prompt_file": lead.prompt_file,
                "reviews_uri": lead.reviews_uri,
                "photos_uri": lead.photos_uri,
                "status": "REVIEW_REQUIRED",
                "email_subject": messages["email_subject"],
                "email": messages["email"],
                "linkedin_dm": messages["linkedin_dm"],
                "instagram_dm": messages["instagram_dm"],
                "whatsapp": messages["whatsapp"],
                "automatic_send": "NO",
            }
        )

    lead_fields = list(asdict(discovered[0]).keys()) if discovered else list(Lead.__dataclass_fields__.keys())
    write_csv(output_dir / "leads.csv", (asdict(lead) for lead in discovered), lead_fields)

    queue_fields = [
        "name", "niche", "address", "website", "rating", "review_count", "lead_score",
        "agency_conversion_probability", "problem_summary", "estimated_monthly_value_low_eur",
        "estimated_monthly_value_base_eur", "estimated_monthly_value_high_eur", "preview_file",
        "share_link", "audit_file", "prompt_file", "reviews_uri", "photos_uri", "status",
        "email_subject", "email", "linkedin_dm", "instagram_dm", "whatsapp", "automatic_send",
    ]
    write_csv(output_dir / "outreach_queue.csv", queue_rows, queue_fields)

    expected_conversions = round(sum(float(row["agency_conversion_probability"]) for row in queue_rows), 2)
    aggregate_base_value = round(sum(float(row["estimated_monthly_value_base_eur"]) for row in queue_rows), 2)
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "sample" if use_sample else "google_places",
        "discovered": len(discovered),
        "shortlisted_and_enriched": len(shortlisted),
        "expected_agency_conversions_from_batch": expected_conversions,
        "aggregate_base_monthly_value_scenario_eur": aggregate_base_value,
        "preview_base_url_configured": bool(preview_base_url),
        "automatic_outreach": False,
        "notes": [
            "Agency conversion is a heuristic until calibrated with real outreach outcomes.",
            "Commercial values are scenarios, not claims about a business's existing website revenue.",
        ],
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI-assisted local business website agency pipeline")
    parser.add_argument("--config", default="config.example.json")
    parser.add_argument("--profiles", default="niche_profiles.json")
    parser.add_argument("--output", default="output")
    parser.add_argument("--sample", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_json(Path(args.config))
    profiles = load_json(Path(args.profiles))
    summary = run(config, profiles, Path(args.output), use_sample=args.sample)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
