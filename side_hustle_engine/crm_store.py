from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Column, Float, Integer, MetaData, String, Table, Text, create_engine, delete, insert, select, update
from sqlalchemy.engine import Engine

STAGES = [
    "DISCOVERED",
    "QUALIFIED",
    "PREVIEW_READY",
    "APPROVED_FOR_CONTACT",
    "CONTACTED",
    "REPLIED",
    "MEETING",
    "PROPOSAL",
    "WON",
    "ONBOARDING",
    "LIVE",
    "RETAINER",
    "LOST",
    "PAUSED",
]

metadata = MetaData()

accounts = Table(
    "accounts",
    metadata,
    Column("id", String(64), primary_key=True),
    Column("business_name", String(300), nullable=False),
    Column("niche", String(100), default=""),
    Column("location", Text, default=""),
    Column("stage", String(40), nullable=False, default="DISCOVERED"),
    Column("lead_score", Integer),
    Column("conversion_probability", Float),
    Column("problem_summary", Text, default=""),
    Column("preview_url", Text, default=""),
    Column("website_url", Text, default=""),
    Column("source", String(100), default="agency_pipeline"),
    Column("estimated_monthly_value_base_eur", Float),
    Column("owner_name", String(200), default=""),
    Column("contact_channel", String(80), default=""),
    Column("contact_handle", String(300), default=""),
    Column("subscription_plan", String(80), default=""),
    Column("monthly_fee_eur", Float),
    Column("next_action", Text, default=""),
    Column("next_action_due", String(40), default=""),
    Column("created_at", String(40), nullable=False),
    Column("updated_at", String(40), nullable=False),
)

events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("account_id", String(64), nullable=False, index=True),
    Column("event_type", String(80), nullable=False),
    Column("from_stage", String(40), default=""),
    Column("to_stage", String(40), default=""),
    Column("note", Text, default=""),
    Column("actor", String(100), default="system"),
    Column("source", String(100), default="control_center"),
    Column("metadata_json", Text, default="{}"),
    Column("event_at", String(40), nullable=False),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_database_url() -> str:
    runtime = Path(__file__).resolve().parent / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{runtime / 'agency_control.db'}"


def get_engine(database_url: str | None = None) -> Engine:
    url = (database_url or os.getenv("CRM_DATABASE_URL") or default_database_url()).strip()
    kwargs: dict[str, Any] = {"future": True, "pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    metadata.create_all(engine)
    return engine


def stable_account_id(name: str, location: str = "") -> str:
    return hashlib.sha256(f"{name.strip().lower()}|{location.strip().lower()}".encode("utf-8")).hexdigest()[:20]


def _row_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping)


def list_accounts(engine: Engine) -> list[dict[str, Any]]:
    with engine.begin() as conn:
        rows = conn.execute(select(accounts).order_by(accounts.c.updated_at.desc())).fetchall()
    return [_row_dict(row) for row in rows]


def list_events(engine: Engine, account_id: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    statement = select(events)
    if account_id:
        statement = statement.where(events.c.account_id == account_id)
    statement = statement.order_by(events.c.id.desc()).limit(limit)
    with engine.begin() as conn:
        rows = conn.execute(statement).fetchall()
    return [_row_dict(row) for row in rows]


def add_event(
    engine: Engine,
    account_id: str,
    event_type: str,
    note: str = "",
    *,
    from_stage: str = "",
    to_stage: str = "",
    actor: str = "system",
    source: str = "control_center",
    metadata_payload: dict[str, Any] | None = None,
) -> None:
    payload = {
        "account_id": account_id,
        "event_type": event_type,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "note": note,
        "actor": actor,
        "source": source,
        "metadata_json": json.dumps(metadata_payload or {}, ensure_ascii=False),
        "event_at": utc_now(),
    }
    with engine.begin() as conn:
        conn.execute(insert(events).values(**payload))


def get_account(engine: Engine, account_id: str) -> dict[str, Any] | None:
    with engine.begin() as conn:
        row = conn.execute(select(accounts).where(accounts.c.id == account_id)).first()
    return _row_dict(row) if row else None


def update_account(
    engine: Engine,
    account_id: str,
    values: dict[str, Any],
    *,
    actor: str = "Utpal",
    note: str = "",
) -> None:
    current = get_account(engine, account_id)
    if not current:
        raise KeyError(f"Unknown account: {account_id}")

    cleaned = {key: value for key, value in values.items() if key in accounts.c and key not in {"id", "created_at"}}
    old_stage = str(current.get("stage") or "")
    new_stage = str(cleaned.get("stage") or old_stage)
    cleaned["updated_at"] = utc_now()

    with engine.begin() as conn:
        conn.execute(update(accounts).where(accounts.c.id == account_id).values(**cleaned))

    changed = {key: {"from": current.get(key), "to": value} for key, value in cleaned.items() if key != "updated_at" and current.get(key) != value}
    if old_stage != new_stage:
        add_event(
            engine,
            account_id,
            "STAGE_CHANGED",
            note=note,
            from_stage=old_stage,
            to_stage=new_stage,
            actor=actor,
            metadata_payload={"changes": changed},
        )
    elif changed or note:
        add_event(engine, account_id, "ACCOUNT_UPDATED", note=note, actor=actor, metadata_payload={"changes": changed})


def sync_outreach_queue(engine: Engine, queue_path: Path, *, actor: str = "agency_pipeline") -> dict[str, int]:
    if not queue_path.exists():
        raise FileNotFoundError(queue_path)

    created = 0
    refreshed = 0
    with queue_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        name = (row.get("name") or "Unnamed business").strip()
        location = (row.get("address") or "").strip()
        account_id = stable_account_id(name, location)
        current = get_account(engine, account_id)
        now = utc_now()
        preview_url = (row.get("share_link") or "").strip()
        stage = "PREVIEW_READY" if preview_url or row.get("preview_file") else "QUALIFIED"
        payload = {
            "business_name": name,
            "niche": (row.get("niche") or "").strip(),
            "location": location,
            "lead_score": int(float(row.get("lead_score") or 0)) if row.get("lead_score") else None,
            "conversion_probability": float(row.get("agency_conversion_probability") or 0) if row.get("agency_conversion_probability") else None,
            "problem_summary": (row.get("problem_summary") or "").strip(),
            "preview_url": preview_url,
            "website_url": (row.get("website") or "").strip(),
            "estimated_monthly_value_base_eur": float(row.get("estimated_monthly_value_base_eur") or 0) if row.get("estimated_monthly_value_base_eur") else None,
            "updated_at": now,
        }

        if current:
            # Never move a human-progressed account backwards when a new discovery run refreshes it.
            if STAGES.index(current["stage"]) <= STAGES.index("PREVIEW_READY"):
                payload["stage"] = stage
            with engine.begin() as conn:
                conn.execute(update(accounts).where(accounts.c.id == account_id).values(**payload))
            add_event(engine, account_id, "PIPELINE_REFRESHED", actor=actor, source="agency_pipeline", metadata_payload={"queue": str(queue_path)})
            refreshed += 1
        else:
            payload.update({
                "id": account_id,
                "stage": stage,
                "source": "agency_pipeline",
                "created_at": now,
            })
            with engine.begin() as conn:
                conn.execute(insert(accounts).values(**payload))
            add_event(engine, account_id, "LEAD_CREATED", to_stage=stage, actor=actor, source="agency_pipeline", metadata_payload={"queue": str(queue_path)})
            created += 1

    return {"created": created, "refreshed": refreshed, "total": len(rows)}


def delete_account(engine: Engine, account_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(delete(events).where(events.c.account_id == account_id))
        conn.execute(delete(accounts).where(accounts.c.id == account_id))
