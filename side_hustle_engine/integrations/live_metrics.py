from __future__ import annotations

import argparse
import json
import os
from calendar import monthrange
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

GOOGLE_ANALYTICS_SCOPE = "https://www.googleapis.com/auth/analytics.readonly"
GOOGLE_SEARCH_CONSOLE_SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"
GOOGLE_BUSINESS_SCOPE = "https://www.googleapis.com/auth/business.manage"
SHOPIFY_API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-07")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def previous_full_months(reference: date | None = None) -> dict[str, str]:
    today = reference or date.today()
    first_this_month = date(today.year, today.month, 1)
    previous_end = first_this_month.fromordinal(first_this_month.toordinal() - 1)
    previous_start = date(previous_end.year, previous_end.month, 1)
    prior_end = previous_start.fromordinal(previous_start.toordinal() - 1)
    prior_start = date(prior_end.year, prior_end.month, 1)
    return {
        "current_start": previous_start.isoformat(),
        "current_end": previous_end.isoformat(),
        "previous_start": prior_start.isoformat(),
        "previous_end": prior_end.isoformat(),
        "label": previous_start.strftime("%B %Y"),
    }


def resolve_period(config: dict[str, Any]) -> dict[str, str]:
    supplied = config.get("period") or {}
    required = ["current_start", "current_end", "previous_start", "previous_end"]
    if all(supplied.get(key) for key in required):
        resolved = {key: str(supplied[key]) for key in required}
        resolved["label"] = str(supplied.get("label") or resolved["current_start"])
        return resolved
    return previous_full_months()


def as_number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def clean_number(value: float) -> int | float:
    return int(value) if float(value).is_integer() else round(float(value), 4)


def google_credentials(scope: str):
    import google.auth

    credentials, _ = google.auth.default(scopes=[scope])
    return credentials


def fetch_ga4(property_id: str, start_date: str, end_date: str) -> dict[str, Any]:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Metric, RunReportRequest

    client = BetaAnalyticsDataClient()
    metric_names = [
        "sessions",
        "sessionKeyEventRate",
        "itemsViewed",
        "cartToViewRate",
        "checkouts",
        "addToCarts",
        "ecommercePurchases",
        "purchaseRevenue",
        "averagePurchaseRevenue",
    ]
    request = RunReportRequest(
        property=f"properties/{property_id}",
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        metrics=[Metric(name=name) for name in metric_names],
    )
    response = client.run_report(request)
    values = {name: 0.0 for name in metric_names}
    if response.rows:
        row = response.rows[0]
        for idx, name in enumerate(metric_names):
            values[name] = as_number(row.metric_values[idx].value)

    carts = values["addToCarts"]
    checkouts = values["checkouts"]
    return {
        "website_sessions": clean_number(values["sessions"]),
        "conversion_rate": round(values["sessionKeyEventRate"], 4),
        "product_views": clean_number(values["itemsViewed"]),
        "add_to_cart_rate": round(values["cartToViewRate"], 4),
        "checkout_rate": round(checkouts / carts, 4) if carts else 0.0,
        "orders": clean_number(values["ecommercePurchases"]),
        "revenue": round(values["purchaseRevenue"], 2),
        "average_order_value": round(values["averagePurchaseRevenue"], 2),
    }


def fetch_search_console(site_url: str, start_date: str, end_date: str) -> dict[str, Any]:
    from googleapiclient.discovery import build

    credentials = google_credentials(GOOGLE_SEARCH_CONSOLE_SCOPE)
    service = build("searchconsole", "v1", credentials=credentials, cache_discovery=False)
    payload = {
        "startDate": start_date,
        "endDate": end_date,
        "dataState": "final",
    }
    result = service.searchanalytics().query(siteUrl=site_url, body=payload).execute()
    rows = result.get("rows") or []
    if not rows:
        return {"search_clicks": 0, "search_impressions": 0, "search_ctr": 0.0, "search_position": 0.0}
    row = rows[0]
    return {
        "search_clicks": clean_number(as_number(row.get("clicks"))),
        "search_impressions": clean_number(as_number(row.get("impressions"))),
        "search_ctr": round(as_number(row.get("ctr")), 4),
        "search_position": round(as_number(row.get("position")), 2),
    }


def _date_params(prefix: str, iso_date: str) -> dict[str, int]:
    parsed = date.fromisoformat(iso_date)
    return {
        f"{prefix}.year": parsed.year,
        f"{prefix}.month": parsed.month,
        f"{prefix}.day": parsed.day,
    }


def fetch_business_profile(location_id: str, start_date: str, end_date: str) -> dict[str, Any]:
    from google.auth.transport.requests import AuthorizedSession

    credentials = google_credentials(GOOGLE_BUSINESS_SCOPE)
    session = AuthorizedSession(credentials)
    metrics = [
        "BUSINESS_IMPRESSIONS_DESKTOP_MAPS",
        "BUSINESS_IMPRESSIONS_DESKTOP_SEARCH",
        "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
        "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
        "BUSINESS_DIRECTION_REQUESTS",
        "CALL_CLICKS",
        "WEBSITE_CLICKS",
        "BUSINESS_BOOKINGS",
    ]
    params: list[tuple[str, Any]] = [("dailyMetrics", metric) for metric in metrics]
    params.extend(_date_params("dailyRange.start_date", start_date).items())
    params.extend(_date_params("dailyRange.end_date", end_date).items())
    url = (
        "https://businessprofileperformance.googleapis.com/v1/"
        f"locations/{location_id}:fetchMultiDailyMetricsTimeSeries"
    )
    response = session.get(url, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()

    totals: dict[str, float] = {metric: 0.0 for metric in metrics}
    for group in payload.get("multiDailyMetricTimeSeries") or []:
        for series in group.get("dailyMetricTimeSeries") or []:
            metric = series.get("dailyMetric")
            total = sum(as_number(point.get("value")) for point in (series.get("timeSeries") or {}).get("datedValues") or [])
            if metric:
                totals[metric] = totals.get(metric, 0.0) + total

    impressions = sum(
        totals.get(metric, 0.0)
        for metric in metrics
        if metric.startswith("BUSINESS_IMPRESSIONS_")
    )
    return {
        "business_profile_impressions": clean_number(impressions),
        "direction_or_store_intent": clean_number(totals.get("BUSINESS_DIRECTION_REQUESTS", 0.0)),
        "business_profile_call_clicks": clean_number(totals.get("CALL_CLICKS", 0.0)),
        "business_profile_website_clicks": clean_number(totals.get("WEBSITE_CLICKS", 0.0)),
        "business_profile_bookings": clean_number(totals.get("BUSINESS_BOOKINGS", 0.0)),
    }


def shopify_graphql(store_domain: str, access_token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    endpoint = f"https://{store_domain}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
    response = requests.post(
        endpoint,
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        },
        json={"query": query, "variables": variables},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError(f"Shopify GraphQL error: {payload['errors']}")
    return payload.get("data") or {}


def run_shopifyql(store_domain: str, access_token: str, shopifyql: str) -> list[dict[str, Any]]:
    query = """
    query RunShopifyQL($query: String!) {
      shopifyqlQuery(query: $query) {
        tableData { columns { name dataType displayName } rows }
        parseErrors
      }
    }
    """
    data = shopify_graphql(store_domain, access_token, query, {"query": shopifyql})
    result = data.get("shopifyqlQuery") or {}
    if result.get("parseErrors"):
        raise RuntimeError(f"ShopifyQL parse error: {result['parseErrors']}")
    table = result.get("tableData") or {}
    return table.get("rows") or []


def fetch_shopify(store_domain: str, access_token: str, start_date: str, end_date: str) -> tuple[dict[str, Any], list[str]]:
    sales_query = (
        "FROM sales SHOW total_sales, orders, average_order_value, returning_customer_rate "
        f"SINCE {start_date} UNTIL {end_date}"
    )
    sessions_query = (
        "FROM sessions SHOW sessions, conversion_rate "
        f"SINCE {start_date} UNTIL {end_date}"
    )
    top_products_query = (
        "FROM sales SHOW net_sales, orders GROUP BY product_title "
        f"SINCE {start_date} UNTIL {end_date} ORDER BY net_sales DESC LIMIT 5"
    )
    sales_rows = run_shopifyql(store_domain, access_token, sales_query)
    session_rows = run_shopifyql(store_domain, access_token, sessions_query)
    product_rows = run_shopifyql(store_domain, access_token, top_products_query)

    sales = sales_rows[0] if sales_rows else {}
    sessions = session_rows[0] if session_rows else {}
    metrics = {
        "website_sessions": clean_number(as_number(sessions.get("sessions"))),
        "conversion_rate": round(as_number(sessions.get("conversion_rate")), 4),
        "orders": clean_number(as_number(sales.get("orders"))),
        "revenue": round(as_number(sales.get("total_sales")), 2),
        "average_order_value": round(as_number(sales.get("average_order_value")), 2),
        "repeat_customer_rate": round(as_number(sales.get("returning_customer_rate")), 4),
    }
    top_products = [
        f"{row.get('product_title', 'Unnamed product')}: €{as_number(row.get('net_sales')):,.2f} net sales across {clean_number(as_number(row.get('orders')))} orders"
        for row in product_rows
    ]
    return metrics, top_products


def collect_period(client: dict[str, Any], start_date: str, end_date: str) -> tuple[dict[str, Any], list[str]]:
    metrics: dict[str, Any] = {}
    product_signals: list[str] = []
    integrations = client.get("integrations") or {}

    ga4 = integrations.get("ga4") or {}
    if ga4.get("enabled") and ga4.get("property_id"):
        metrics.update(fetch_ga4(str(ga4["property_id"]), start_date, end_date))

    gsc = integrations.get("search_console") or {}
    if gsc.get("enabled") and gsc.get("site_url"):
        metrics.update(fetch_search_console(str(gsc["site_url"]), start_date, end_date))

    gbp = integrations.get("business_profile") or {}
    if gbp.get("enabled") and gbp.get("location_id"):
        metrics.update(fetch_business_profile(str(gbp["location_id"]), start_date, end_date))

    shopify = integrations.get("shopify") or {}
    if shopify.get("enabled") and shopify.get("store_domain"):
        token_env = str(shopify.get("access_token_env") or "SHOPIFY_ACCESS_TOKEN")
        access_token = os.getenv(token_env, "").strip()
        if not access_token:
            raise RuntimeError(f"Missing Shopify access token environment variable: {token_env}")
        shop_metrics, product_signals = fetch_shopify(str(shopify["store_domain"]), access_token, start_date, end_date)
        metrics.update(shop_metrics)

    return metrics, product_signals


def build_client_payload(client: dict[str, Any]) -> dict[str, Any]:
    period = resolve_period(client)
    current, top_products = collect_period(client, period["current_start"], period["current_end"])
    previous, _ = collect_period(client, period["previous_start"], period["previous_end"])
    sources = [name for name, cfg in (client.get("integrations") or {}).items() if (cfg or {}).get("enabled")]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "client": client.get("client", "Unnamed client"),
        "period": period["label"],
        "connected_sources": sources,
        "previous_period": previous,
        "current_period": current,
        "review_theme_summary": client.get("review_theme_summary", []),
        "top_products": top_products,
    }


def sample_payload() -> dict[str, Any]:
    return {
        "client": "Sample Integrated Boutique",
        "period": "August 2026",
        "connected_sources": ["ga4", "search_console", "business_profile", "shopify"],
        "previous_period": {
            "website_sessions": 980,
            "conversion_rate": 0.032,
            "search_clicks": 330,
            "business_profile_impressions": 4200,
            "direction_or_store_intent": 81,
            "business_profile_call_clicks": 24,
            "business_profile_website_clicks": 145,
            "orders": 34,
            "revenue": 2140,
            "average_order_value": 62.94,
            "repeat_customer_rate": 0.21,
        },
        "current_period": {
            "website_sessions": 1210,
            "conversion_rate": 0.026,
            "search_clicks": 405,
            "business_profile_impressions": 4810,
            "direction_or_store_intent": 94,
            "business_profile_call_clicks": 28,
            "business_profile_website_clicks": 177,
            "orders": 31,
            "revenue": 2015,
            "average_order_value": 65.0,
            "repeat_customer_rate": 0.23,
        },
        "review_theme_summary": ["Friendly service remains the strongest positive theme"],
        "top_products": ["Gift collection: €740.00 net sales across 11 orders"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect authorised live client metrics for the subscription reporting pipeline")
    parser.add_argument("--client", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()

    payload = sample_payload() if args.sample else build_client_payload(load_json(Path(args.client)))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"client": payload["client"], "sources": payload["connected_sources"]}, indent=2))


if __name__ == "__main__":
    main()
