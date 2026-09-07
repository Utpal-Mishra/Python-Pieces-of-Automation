from __future__ import annotations

import argparse
import csv
import html
import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests

PLACES_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.websiteUri",
        "places.googleMapsUri",
        "places.rating",
        "places.userRatingCount",
        "places.primaryType",
        "nextPageToken",
    ]
)


@dataclass
class Lead:
    place_id: str
    name: str
    category: str
    address: str
    website: str
    maps_uri: str
    rating: float | None
    review_count: int
    source_query: str
    missing_website: bool
    score: int = 0
    preview_file: str = ""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def display_name(place: dict[str, Any]) -> str:
    raw = place.get("displayName") or {}
    if isinstance(raw, dict):
        return text(raw.get("text"))
    return text(raw)


def fetch_places(api_key: str, query: str, limit: int) -> list[dict[str, Any]]:
    """Fetch up to `limit` places using Google Places Text Search (New)."""
    results: list[dict[str, Any]] = []
    token: str | None = None
    page_size = min(max(limit, 1), 20)

    while len(results) < limit:
        body: dict[str, Any] = {"textQuery": query, "pageSize": page_size}
        if token:
            body["pageToken"] = token

        response = requests.post(
            PLACES_URL,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
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


def to_lead(place: dict[str, Any], query: str) -> Lead:
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

    return Lead(
        place_id=text(place.get("id")),
        name=display_name(place) or "Unnamed business",
        category=text(place.get("primaryType")) or "local_business",
        address=text(place.get("formattedAddress")),
        website=website,
        maps_uri=text(place.get("googleMapsUri")),
        rating=rating,
        review_count=review_count,
        source_query=query,
        missing_website=not bool(website),
    )


def score_lead(lead: Lead, weights: dict[str, int]) -> int:
    score = 0
    if lead.missing_website:
        score += weights.get("missing_website", 55)
    if lead.rating is not None:
        score += weights.get("rating_present", 10)
    if lead.review_count >= 10:
        score += weights.get("reviews_10_plus", 10)
    if lead.review_count >= 50:
        score += weights.get("reviews_50_plus", 10)
    if lead.address:
        score += weights.get("address_present", 5)
    if lead.maps_uri:
        score += weights.get("maps_uri_present", 5)
    if lead.rating is not None and lead.rating >= 4.0:
        score += weights.get("rating_4_plus", 5)
    return score


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "business"


def concept_html(lead: Lead) -> str:
    name = html.escape(lead.name)
    address = html.escape(lead.address or "Local service area")
    category = html.escape(lead.category.replace("_", " ").title())
    maps_link = html.escape(lead.maps_uri or "#", quote=True)
    rating_line = (
        f"{lead.rating:.1f} rating · {lead.review_count} Google reviews"
        if lead.rating is not None
        else "Local business concept"
    )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>{name} — Unofficial concept preview</title>
  <style>
    :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #0c0d10; color: #f5f5f5; }}
    .wrap {{ width: min(1080px, 92vw); margin: 0 auto; }}
    .notice {{ margin: 18px 0; padding: 10px 14px; border: 1px solid #3a3d46; border-radius: 999px; display: inline-block; color: #c9ccd5; font-size: 13px; }}
    .hero {{ min-height: 72vh; display: grid; align-content: center; gap: 20px; }}
    .eyebrow {{ text-transform: uppercase; letter-spacing: .14em; color: #b5b8c2; font-size: 13px; }}
    h1 {{ font-size: clamp(48px, 9vw, 104px); line-height: .92; margin: 0; max-width: 900px; }}
    .lead {{ max-width: 700px; color: #c9ccd5; font-size: clamp(18px, 2.5vw, 25px); line-height: 1.45; }}
    .actions {{ display: flex; flex-wrap: wrap; gap: 12px; }}
    .btn {{ display: inline-block; padding: 13px 18px; border-radius: 999px; text-decoration: none; font-weight: 700; }}
    .primary {{ background: #f5f5f5; color: #0c0d10; }}
    .secondary {{ border: 1px solid #3a3d46; color: #f5f5f5; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap: 14px; padding-bottom: 70px; }}
    .card {{ border: 1px solid #252832; border-radius: 20px; padding: 22px; background: #12141a; }}
    .label {{ color: #8f94a3; font-size: 13px; text-transform: uppercase; letter-spacing: .08em; }}
    .value {{ margin-top: 8px; font-size: 18px; line-height: 1.4; }}
    footer {{ border-top: 1px solid #252832; padding: 25px 0 40px; color: #8f94a3; font-size: 13px; }}
  </style>
</head>
<body>
  <main class=\"wrap\">
    <div class=\"notice\">UNOFFICIAL CONCEPT PREVIEW · NOT AFFILIATED WITH {name}</div>
    <section class=\"hero\">
      <div class=\"eyebrow\">{category} · {address}</div>
      <h1>{name}</h1>
      <div class=\"lead\">A clean, mobile-first website concept designed to help local customers quickly understand the service, build trust and take the next step.</div>
      <div class=\"actions\">
        <a class=\"btn primary\" href=\"#\" onclick=\"return false\">Enquire</a>
        <a class=\"btn secondary\" href=\"{maps_link}\" target=\"_blank\" rel=\"noreferrer\">View Google listing</a>
      </div>
    </section>
    <section class=\"grid\">
      <div class=\"card\"><div class=\"label\">Trust signal</div><div class=\"value\">{html.escape(rating_line)}</div></div>
      <div class=\"card\"><div class=\"label\">Location</div><div class=\"value\">{address}</div></div>
      <div class=\"card\"><div class=\"label\">Website objective</div><div class=\"value\">Turn local discovery into enquiries, calls or bookings.</div></div>
    </section>
    <footer>This page is a speculative design concept generated from public business-listing information. It is not a live website and does not claim endorsement by the business.</footer>
  </main>
</body>
</html>
"""


def outreach_draft(lead: Lead) -> tuple[str, str]:
    subject = f"Website concept for {lead.name}"
    message = (
        f"Hi {lead.name} team,\n\n"
        "I was reviewing local businesses and your Google listing did not return a website in my check. "
        "I put together a small, unofficial concept page to show what a simple mobile-first site could look like.\n\n"
        "If a website is something you are already considering, I can turn the concept into a proper site using your approved content, branding and contact details. "
        "No obligation — the preview is simply a starting point for a conversation.\n\n"
        "Regards,\nUtpal"
    )
    return subject, message


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
                "id": "sample-001",
                "displayName": {"text": "Harbour & Pine Barbers"},
                "formattedAddress": "Sample Street, Cork, Ireland",
                "googleMapsUri": "#",
                "rating": 4.7,
                "userRatingCount": 86,
                "primaryType": "barber_shop",
            },
            "barbers in Cork, Ireland",
        ),
        (
            {
                "id": "sample-002",
                "displayName": {"text": "Lee Valley Home Services"},
                "formattedAddress": "Sample Road, Cork, Ireland",
                "googleMapsUri": "#",
                "rating": 4.5,
                "userRatingCount": 24,
                "primaryType": "plumber",
            },
            "plumbers in Cork, Ireland",
        ),
        (
            {
                "id": "sample-003",
                "displayName": {"text": "Example Cafe With Website"},
                "formattedAddress": "Sample Quay, Cork, Ireland",
                "websiteUri": "https://example.com",
                "googleMapsUri": "#",
                "rating": 4.2,
                "userRatingCount": 120,
                "primaryType": "cafe",
            },
            "cafes in Cork, Ireland",
        ),
    ]


def run(config: dict[str, Any], output_dir: Path, use_sample: bool = False) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir = output_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)

    discovered: list[Lead] = []
    if use_sample:
        raw_items = sample_places()
    else:
        api_key = os.getenv("GOOGLE_PLACES_API_KEY", "").strip()
        if not api_key:
            raise SystemExit("GOOGLE_PLACES_API_KEY is required unless --sample is used.")
        raw_items: list[tuple[dict[str, Any], str]] = []
        for query in config.get("queries", []):
            places = fetch_places(api_key, query, int(config.get("max_leads_per_query", 10)))
            raw_items.extend((place, query) for place in places)

    seen: set[str] = set()
    for place, query in raw_items:
        lead = to_lead(place, query)
        dedupe_key = lead.place_id or f"{lead.name}|{lead.address}".lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        lead.score = score_lead(lead, config.get("weights", {}))
        discovered.append(lead)

    discovered.sort(key=lambda item: (item.score, item.review_count), reverse=True)

    only_missing = bool(config.get("only_missing_website", True))
    min_score = int(config.get("min_score", 70))
    shortlisted = [
        lead
        for lead in discovered
        if lead.score >= min_score and (lead.missing_website or not only_missing)
    ]

    for index, lead in enumerate(shortlisted, start=1):
        filename = f"{index:03d}-{slugify(lead.name)}.html"
        target = preview_dir / filename
        target.write_text(concept_html(lead), encoding="utf-8")
        lead.preview_file = str(Path("previews") / filename)

    lead_fields = list(asdict(discovered[0]).keys()) if discovered else list(Lead.__dataclass_fields__.keys())
    write_csv(output_dir / "leads.csv", (asdict(lead) for lead in discovered), lead_fields)

    queue_rows: list[dict[str, Any]] = []
    for lead in shortlisted:
        subject, message = outreach_draft(lead)
        queue_rows.append(
            {
                "name": lead.name,
                "category": lead.category,
                "address": lead.address,
                "maps_uri": lead.maps_uri,
                "rating": "" if lead.rating is None else lead.rating,
                "review_count": lead.review_count,
                "score": lead.score,
                "preview_file": lead.preview_file,
                "status": "REVIEW_REQUIRED",
                "suggested_subject": subject,
                "suggested_message": message,
                "automatic_send": "NO",
            }
        )

    queue_fields = [
        "name",
        "category",
        "address",
        "maps_uri",
        "rating",
        "review_count",
        "score",
        "preview_file",
        "status",
        "suggested_subject",
        "suggested_message",
        "automatic_send",
    ]
    write_csv(output_dir / "outreach_queue.csv", queue_rows, queue_fields)

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "sample" if use_sample else "google_places",
        "discovered": len(discovered),
        "shortlisted": len(shortlisted),
        "min_score": min_score,
        "only_missing_website": only_missing,
        "automatic_outreach": False,
    }
    (output_dir / "run_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local-business opportunity discovery and concept-preview pipeline")
    parser.add_argument("--config", default="config.example.json", help="Path to JSON configuration")
    parser.add_argument("--output", default="output", help="Output directory")
    parser.add_argument("--sample", action="store_true", help="Run with fictitious sample businesses and no API key")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = Path(args.config)
    config = load_json(config_path)
    summary = run(config, Path(args.output), use_sample=args.sample)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
