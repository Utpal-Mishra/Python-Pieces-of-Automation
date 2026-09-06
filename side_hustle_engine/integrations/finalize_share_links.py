from __future__ import annotations

import argparse
import csv
from pathlib import Path


def public_preview_path(preview_file: str) -> str:
    value = preview_file.replace("\\", "/").lstrip("/")
    if value.startswith("previews/"):
        value = value[len("previews/"):]
    if value.endswith("/index.html"):
        value = value[: -len("index.html")]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Attach a deployed preview base URL to the outreach queue")
    parser.add_argument("--queue", required=True)
    parser.add_argument("--base-url", required=True)
    args = parser.parse_args()

    queue_path = Path(args.queue)
    with queue_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    base = args.base_url.rstrip("/")
    for row in rows:
        relative = public_preview_path(row.get("preview_file", ""))
        row["share_link"] = f"{base}/{relative}" if relative else base

    with queue_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {len(rows)} share links using {base}")


if __name__ == "__main__":
    main()
