from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pct_change(current: float | int | None, previous: float | int | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round((float(current) - float(previous)) / float(previous) * 100, 1)


def metric_row(name: str, current: Any, previous: Any) -> dict[str, Any]:
    return {
        "metric": name,
        "current": current,
        "previous": previous,
        "change_pct": pct_change(current, previous),
    }


def recommendations(metrics: dict[str, Any], previous: dict[str, Any], plan: str) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []

    sessions = pct_change(metrics.get("website_sessions"), previous.get("website_sessions"))
    conversion = pct_change(metrics.get("conversion_rate"), previous.get("conversion_rate"))
    search = pct_change(metrics.get("search_clicks"), previous.get("search_clicks"))
    rating_now = metrics.get("average_rating")
    rating_prev = previous.get("average_rating")

    if sessions is not None and sessions < -10:
        actions.append({"priority": "high", "action": "Investigate traffic decline", "why": f"Website sessions changed {sessions}%. Check search visibility, referral sources and campaign activity."})
    if sessions is not None and sessions > 10 and conversion is not None and conversion < -10:
        actions.append({"priority": "high", "action": "Run a conversion-path review", "why": "Traffic increased while conversion efficiency fell. Review landing-page intent, CTA visibility and mobile flow."})
    if conversion is not None and conversion < -10:
        actions.append({"priority": "high", "action": "Test one focused CTA improvement", "why": f"Conversion rate changed {conversion}%. Test a single measurable change rather than redesigning blindly."})
    if search is not None and search < -10:
        actions.append({"priority": "medium", "action": "Review search demand and page coverage", "why": f"Search clicks changed {search}%. Check which queries/pages lost visibility before changing content."})
    if rating_now is not None and rating_prev is not None and float(rating_now) < float(rating_prev) - 0.1:
        actions.append({"priority": "medium", "action": "Review recent customer feedback themes", "why": "Average rating softened. Group recent feedback by theme and address repeated operational issues before promoting reviews."})
    if metrics.get("new_reviews", 0) and not actions:
        actions.append({"priority": "low", "action": "Turn positive reputation into conversion support", "why": "New review activity is healthy. Summarise recurring themes and use only client-approved, rights-cleared proof points on the website."})

    if plan == "commerce":
        revenue = pct_change(metrics.get("revenue"), previous.get("revenue"))
        orders = pct_change(metrics.get("orders"), previous.get("orders"))
        add_to_cart = pct_change(metrics.get("add_to_cart_rate"), previous.get("add_to_cart_rate"))
        if revenue is not None and revenue < -10:
            actions.append({"priority": "high", "action": "Decompose the revenue decline", "why": f"Revenue changed {revenue}%. Separate traffic, conversion, order volume and average-order-value effects before taking action."})
        if add_to_cart is not None and add_to_cart < -10:
            actions.append({"priority": "high", "action": "Audit product-page merchandising", "why": f"Add-to-cart rate changed {add_to_cart}%. Review product imagery, pricing clarity, stock status, delivery messaging and product-page friction."})
        if orders is not None and orders > 10 and revenue is not None and revenue <= 0:
            actions.append({"priority": "medium", "action": "Improve basket value", "why": "Orders grew without comparable revenue growth. Review average order value, bundles and cross-sell opportunities."})

    if not actions:
        actions.append({"priority": "low", "action": "Maintain and test", "why": "No material negative movement detected. Preserve the current experience and run one controlled improvement test."})
    return actions[:5]


def build_report(client: dict[str, Any], profiles: dict[str, Any], plan: str) -> dict[str, Any]:
    if plan not in profiles:
        raise ValueError(f"Unknown plan: {plan}")

    current = client.get("current_period", {})
    previous = client.get("previous_period", {})
    tracked = profiles[plan].get("metrics", [])
    rows = [metric_row(metric, current.get(metric), previous.get(metric)) for metric in tracked if metric in current or metric in previous]

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "client": client.get("client", "Unnamed client"),
        "plan": plan,
        "plan_label": profiles[plan].get("label"),
        "price_hypothesis_eur_month": profiles[plan].get("price_hypothesis_eur_month"),
        "period": client.get("period", ""),
        "connected_sources": client.get("connected_sources", []),
        "metrics": rows,
        "review_theme_summary": client.get("review_theme_summary", []),
        "top_products": client.get("top_products", []),
        "actions": recommendations(current, previous, plan),
        "guardrail": "Recommendations are generated from connected/client-approved data. Validate commercial decisions with the client before changing live pricing, inventory, claims or campaigns.",
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Monthly Performance Report — {report['client']}",
        "",
        f"**Period:** {report.get('period') or 'Not supplied'}  ",
        f"**Plan:** {report['plan_label']}  ",
        f"**Connected data:** {', '.join(report.get('connected_sources') or ['No live source connected'])}",
        "",
        "## KPI movement",
        "",
        "| Metric | Current | Previous | Change |",
        "|---|---:|---:|---:|",
    ]
    for row in report["metrics"]:
        change = "—" if row["change_pct"] is None else f"{row['change_pct']:+.1f}%"
        lines.append(f"| {row['metric'].replace('_', ' ').title()} | {row['current']} | {row['previous']} | {change} |")

    if report.get("review_theme_summary"):
        lines += ["", "## Customer review themes", ""]
        lines.extend(f"- {theme}" for theme in report["review_theme_summary"])

    if report.get("top_products"):
        lines += ["", "## Product signals", ""]
        lines.extend(f"- {item}" for item in report["top_products"])

    lines += ["", "## Recommended actions", ""]
    for action in report["actions"]:
        lines.append(f"- **{action['priority'].upper()} — {action['action']}**: {action['why']}")

    lines += ["", "## Guardrail", "", report["guardrail"], ""]
    return "\n".join(lines)


def sample_client() -> dict[str, Any]:
    return {
        "client": "Sample Independent Boutique",
        "period": "August 2026",
        "connected_sources": ["GA4", "Search Console", "Google Business Profile", "Shopify"],
        "previous_period": {
            "website_sessions": 980,
            "search_clicks": 330,
            "conversion_rate": 0.032,
            "new_reviews": 7,
            "average_rating": 4.8,
            "product_views": 2100,
            "add_to_cart_rate": 0.091,
            "checkout_rate": 0.54,
            "orders": 34,
            "revenue": 2140,
            "average_order_value": 62.94,
            "repeat_customer_rate": 0.21
        },
        "current_period": {
            "website_sessions": 1210,
            "search_clicks": 405,
            "conversion_rate": 0.026,
            "new_reviews": 11,
            "average_rating": 4.8,
            "product_views": 2600,
            "add_to_cart_rate": 0.072,
            "checkout_rate": 0.53,
            "orders": 31,
            "revenue": 2015,
            "average_order_value": 65.0,
            "repeat_customer_rate": 0.23
        },
        "review_theme_summary": ["Customers repeatedly value friendly service", "Gift selection is a recurring positive theme", "Stock availability is occasionally mentioned as a friction point"],
        "top_products": ["Gift items generated the strongest product engagement", "A small set of clothing products received high views but weak add-to-cart activity"]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Recurring client analytics/subscription report pipeline")
    parser.add_argument("--profiles", default="subscription_profiles.json")
    parser.add_argument("--client", default="")
    parser.add_argument("--plan", choices=["care", "growth", "commerce"], default="growth")
    parser.add_argument("--output", default="subscription-output")
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()

    profiles = load_json(Path(args.profiles))
    if args.sample:
        client = sample_client()
    elif args.client:
        client = load_json(Path(args.client))
    else:
        raise SystemExit("Provide --client or use --sample")

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report = build_report(client, profiles, args.plan)
    (output / "monthly_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / "monthly_report.md").write_text(markdown_report(report), encoding="utf-8")
    print(json.dumps({"client": report["client"], "plan": report["plan"], "actions": len(report["actions"])}, indent=2))


if __name__ == "__main__":
    main()
