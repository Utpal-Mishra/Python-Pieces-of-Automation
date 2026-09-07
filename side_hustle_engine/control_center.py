from __future__ import annotations

import hmac
import os
from pathlib import Path

import pandas as pd
import streamlit as st

from crm_store import STAGES, get_engine, list_accounts, list_events, sync_outreach_queue, update_account

st.set_page_config(page_title="Agency Control Center", page_icon="📊", layout="wide")


def require_auth() -> None:
    expected = os.getenv("CONTROL_CENTER_PASSWORD", "").strip()
    required = os.getenv("REQUIRE_CONTROL_CENTER_AUTH", "false").lower() == "true"
    if not expected and not required:
        st.warning("Local/dev mode: dashboard authentication is not enabled.")
        return
    if not expected:
        st.error("CONTROL_CENTER_PASSWORD is required when REQUIRE_CONTROL_CENTER_AUTH=true.")
        st.stop()
    supplied = st.sidebar.text_input("Control Center password", type="password")
    if not supplied or not hmac.compare_digest(supplied, expected):
        st.info("Enter the private dashboard password to continue.")
        st.stop()


@st.cache_resource
def engine():
    return get_engine()


def euro(value: float | int | None) -> str:
    return "€0" if value in (None, "") else f"€{float(value):,.0f}"


def stage_rank(stage: str) -> int:
    try:
        return STAGES.index(stage)
    except ValueError:
        return 999


def account_dataframe(records: list[dict]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    preferred = [
        "business_name", "niche", "location", "stage", "lead_score", "conversion_probability",
        "preview_url", "owner_name", "contact_channel", "subscription_plan", "monthly_fee_eur",
        "next_action", "next_action_due", "updated_at", "id",
    ]
    existing = [col for col in preferred if col in df.columns]
    return df[existing].sort_values(by="stage", key=lambda s: s.map(stage_rank))


require_auth()
db = engine()
records = list_accounts(db)
events = list_events(db, limit=1000)

st.title("Agency Control Center")
st.caption("Private operating dashboard for prospects, sales progress, clients, recurring revenue and the complete activity trail.")

with st.sidebar:
    st.subheader("Pipeline sync")
    default_queue = Path(os.getenv("AGENCY_OUTPUT_DIR", "side_hustle_engine/output")) / "outreach_queue.csv"
    queue_path = st.text_input("Outreach queue", value=str(default_queue))
    if st.button("Import / refresh pipeline"):
        try:
            result = sync_outreach_queue(db, Path(queue_path))
            st.success(f"Synced {result['total']} leads: {result['created']} new, {result['refreshed']} refreshed.")
            st.cache_resource.clear()
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

active_pipeline = [r for r in records if r.get("stage") not in {"WON", "LIVE", "RETAINER", "LOST", "PAUSED"}]
won = [r for r in records if r.get("stage") in {"WON", "ONBOARDING", "LIVE", "RETAINER"}]
retainers = [r for r in records if r.get("stage") == "RETAINER"]
mrr = sum(float(r.get("monthly_fee_eur") or 0) for r in retainers)
weighted_pipeline = sum(
    float(r.get("estimated_monthly_value_base_eur") or 0) * float(r.get("conversion_probability") or 0)
    for r in active_pipeline
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total prospects / clients", len(records))
c2.metric("Active sales pipeline", len(active_pipeline))
c3.metric("Won / active clients", len(won))
c4.metric("Monthly recurring revenue", euro(mrr))
c5.metric("Weighted opportunity", euro(weighted_pipeline))

pipeline_tab, account_tab, clients_tab, activity_tab, revenue_tab = st.tabs(
    ["Pipeline", "Account Detail", "Clients", "Activity Log", "Revenue"]
)

with pipeline_tab:
    st.subheader("Pipeline board")
    display_stages = ["QUALIFIED", "PREVIEW_READY", "APPROVED_FOR_CONTACT", "CONTACTED", "REPLIED", "MEETING", "PROPOSAL"]
    cols = st.columns(len(display_stages))
    for col, stage in zip(cols, display_stages):
        stage_records = [r for r in records if r.get("stage") == stage]
        with col:
            st.markdown(f"**{stage.replace('_', ' ').title()} · {len(stage_records)}**")
            for item in stage_records[:12]:
                st.caption(item["business_name"])
                if item.get("lead_score") is not None:
                    st.write(f"Score {item['lead_score']}")
                if item.get("next_action"):
                    st.write(f"Next: {item['next_action']}")
                if item.get("preview_url"):
                    st.link_button("Preview", item["preview_url"], use_container_width=True)
                st.divider()

    st.subheader("All records")
    df = account_dataframe(records)
    if df.empty:
        st.info("No CRM records yet. Import the latest outreach queue from the sidebar.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

with account_tab:
    if not records:
        st.info("Import leads first.")
    else:
        label_to_id = {f"{r['business_name']} · {r['stage']} · {r['location']}": r["id"] for r in records}
        selected_label = st.selectbox("Select prospect/client", list(label_to_id.keys()))
        account_id = label_to_id[selected_label]
        account = next(r for r in records if r["id"] == account_id)

        left, right = st.columns([1.1, 1])
        with left:
            st.markdown(f"### {account['business_name']}")
            st.write(account.get("problem_summary") or "No problem summary yet.")
            if account.get("preview_url"):
                st.link_button("Open private prospect preview", account["preview_url"])
            st.write(f"**Niche:** {account.get('niche') or '—'}")
            st.write(f"**Lead score:** {account.get('lead_score') if account.get('lead_score') is not None else '—'}")
            st.write(f"**Location:** {account.get('location') or '—'}")

        with right:
            new_stage = st.selectbox("Stage", STAGES, index=STAGES.index(account.get("stage") or "DISCOVERED"))
            owner_name = st.text_input("Owner/contact name", value=account.get("owner_name") or "")
            contact_channel = st.selectbox(
                "Preferred channel",
                ["", "In person", "Email", "LinkedIn", "Instagram", "Phone", "WhatsApp"],
                index=(["", "In person", "Email", "LinkedIn", "Instagram", "Phone", "WhatsApp"].index(account.get("contact_channel") or "")
                       if (account.get("contact_channel") or "") in ["", "In person", "Email", "LinkedIn", "Instagram", "Phone", "WhatsApp"] else 0),
            )
            contact_handle = st.text_input("Contact detail / handle", value=account.get("contact_handle") or "")
            subscription_plan = st.selectbox(
                "Subscription",
                ["", "Website Care", "Growth Intelligence", "Commerce Intelligence"],
                index=(["", "Website Care", "Growth Intelligence", "Commerce Intelligence"].index(account.get("subscription_plan") or "")
                       if (account.get("subscription_plan") or "") in ["", "Website Care", "Growth Intelligence", "Commerce Intelligence"] else 0),
            )
            monthly_fee = st.number_input("Monthly fee (€)", min_value=0.0, value=float(account.get("monthly_fee_eur") or 0), step=10.0)
            next_action = st.text_input("Next action", value=account.get("next_action") or "")
            next_due = st.text_input("Next action due", value=account.get("next_action_due") or "", placeholder="YYYY-MM-DD")
            note = st.text_area("Progress note", placeholder="What happened, what was agreed, objection, next step...")

            if st.button("Save progress", type="primary"):
                update_account(
                    db,
                    account_id,
                    {
                        "stage": new_stage,
                        "owner_name": owner_name,
                        "contact_channel": contact_channel,
                        "contact_handle": contact_handle,
                        "subscription_plan": subscription_plan,
                        "monthly_fee_eur": monthly_fee or None,
                        "next_action": next_action,
                        "next_action_due": next_due,
                    },
                    note=note,
                )
                st.success("Progress saved and added to the activity log.")
                st.rerun()

        st.markdown("### Complete account timeline")
        timeline = list_events(db, account_id=account_id, limit=200)
        if timeline:
            for event in timeline:
                stage_text = ""
                if event.get("from_stage") or event.get("to_stage"):
                    stage_text = f" · {event.get('from_stage') or '—'} → {event.get('to_stage') or '—'}"
                st.markdown(f"**{event['event_type']}**{stage_text}  \n{event['event_at']} · {event.get('actor') or 'system'}")
                if event.get("note"):
                    st.write(event["note"])
                st.divider()
        else:
            st.info("No events recorded yet.")

with clients_tab:
    client_records = [r for r in records if r.get("stage") in {"WON", "ONBOARDING", "LIVE", "RETAINER"}]
    if not client_records:
        st.info("Won and active clients will appear here automatically as their stage changes.")
    else:
        st.dataframe(account_dataframe(client_records), use_container_width=True, hide_index=True)

with activity_tab:
    st.subheader("Append-only activity log")
    st.caption("Pipeline imports, stage changes and manual progress updates are recorded here instead of overwriting history.")
    if events:
        event_df = pd.DataFrame(events)
        event_df["business_name"] = event_df["account_id"].map({r["id"]: r["business_name"] for r in records})
        columns = ["event_at", "business_name", "event_type", "from_stage", "to_stage", "actor", "note", "source"]
        st.dataframe(event_df[[c for c in columns if c in event_df.columns]], use_container_width=True, hide_index=True)
    else:
        st.info("No activity recorded yet.")

with revenue_tab:
    st.subheader("Commercial overview")
    r1, r2, r3 = st.columns(3)
    r1.metric("Retainer clients", len(retainers))
    r2.metric("MRR", euro(mrr))
    r3.metric("Annualised recurring revenue", euro(mrr * 12))

    commercial = [r for r in records if float(r.get("monthly_fee_eur") or 0) > 0]
    if commercial:
        revenue_df = pd.DataFrame(commercial)[["business_name", "stage", "subscription_plan", "monthly_fee_eur", "updated_at"]]
        st.dataframe(revenue_df, use_container_width=True, hide_index=True)
    else:
        st.info("Subscription clients and recurring revenue will appear here after a plan and monthly fee are recorded.")
