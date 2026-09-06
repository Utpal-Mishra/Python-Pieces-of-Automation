from __future__ import annotations

import argparse
import json
from pathlib import Path

from crm_store import add_event, get_engine, list_accounts, update_account


def main() -> None:
    parser = argparse.ArgumentParser(description="Log a generated monthly client report into the Agency Control Center timeline")
    parser.add_argument("--report", required=True)
    parser.add_argument("--account-id", default="")
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    engine = get_engine()
    account_id = args.account_id.strip()

    if not account_id:
        matches = [r for r in list_accounts(engine) if r.get("business_name") == report.get("client")]
        if len(matches) != 1:
            raise SystemExit("Provide --account-id when the report client name does not uniquely match one CRM account.")
        account_id = matches[0]["id"]

    actions = report.get("actions") or []
    top = actions[0] if actions else {}
    top_action = str(top.get("action") or "")
    top_why = str(top.get("why") or "")
    period = str(report.get("period") or "")
    plan_label = str(report.get("plan_label") or report.get("plan") or "")

    update_values = {}
    if top_action:
        update_values["next_action"] = top_action
    if plan_label:
        update_values["subscription_plan"] = plan_label

    if update_values:
        update_account(
            engine,
            account_id,
            update_values,
            actor="monthly_intelligence",
            note=f"Monthly intelligence updated for {period}." if period else "Monthly intelligence updated.",
        )

    add_event(
        engine,
        account_id,
        "MONTHLY_REPORT_GENERATED",
        actor="monthly_intelligence",
        source="subscription_pipeline",
        note=(f"{period}: {top_action}. {top_why}" if top_action else f"{period}: monthly client report generated."),
        metadata_payload={
            "period": period,
            "plan": report.get("plan"),
            "plan_label": plan_label,
            "recommended_actions": actions,
            "connected_sources": report.get("connected_sources", []),
        },
    )
    print(json.dumps({"account_id": account_id, "period": period, "top_action": top_action}, indent=2))


if __name__ == "__main__":
    main()
