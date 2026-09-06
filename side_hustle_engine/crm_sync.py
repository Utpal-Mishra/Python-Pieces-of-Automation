from __future__ import annotations

import argparse
import json
from pathlib import Path

from crm_store import get_engine, sync_outreach_queue


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync agency outreach queue into the persistent CRM store")
    parser.add_argument("--queue", default="output/outreach_queue.csv")
    args = parser.parse_args()

    engine = get_engine()
    result = sync_outreach_queue(engine, Path(args.queue))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
