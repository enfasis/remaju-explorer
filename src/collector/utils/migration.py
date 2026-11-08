from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .archive import read_json, write_json
from .publication import checksum, load_history, publish_run


def migrate_bucket(source: Path, output: Path, ids_file: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("Migration output must be a new directory")
    manifest_path = source / "manifest.json"
    if not manifest_path.exists():
        manifest_path = source / "data/manifest.json"
    latest = read_json(manifest_path)
    if latest.get("scope") != "all-phases":
        raise ValueError("Migration requires a complete published baseline")
    current = load_history(source, latest)
    present = {key for key, record in current["records"].items() if record["present"]}
    order = ids_file.read_text(encoding="utf-8").splitlines()
    if len(order) != len(set(order)) or any(not number.isdigit() for number in order) or {f"remaju:{number}" for number in order} != present:
        raise ValueError("Ordered IDs must exactly match the latest complete baseline")
    merged: dict[str, Any] = {}
    first_seen: dict[str, str] = {}
    states = sorted(source.glob("data/releases/*/state.json"))
    if (source / "history.json").exists():
        states.append(source / "history.json")
    for path in states:
        for key, record in read_json(path)["records"].items():
            first_seen[key] = min(first_seen.get(key, record["first_seen_at"]), record["first_seen_at"])
            if key not in merged or record["last_seen_at"] >= merged[key]["last_seen_at"]:
                merged[key] = deepcopy(record)
    for key, record in current["records"].items():
        first_seen[key] = min(first_seen.get(key, record["first_seen_at"]), record["first_seen_at"])
        merged[key] = deepcopy(record)
    detail_ids = {f"remaju:{path.stem}" for path in source.glob("data/releases/*/auctions/*.json")}
    if not detail_ids.issubset(merged):
        raise ValueError("Individual detail objects contain auctions missing from the state snapshots")
    for key, record in merged.items():
        record["present"] = key in present
        record["first_seen_at"] = first_seen[key]
    history = {**current, "records": merged}
    run_id = f"migration-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
    run = {"run_id": run_id, "mode": "live", "status": "complete", "scope": "all-phases", "observed_at": latest["observed_at"], "pages_complete": True, "details_complete": True, "advertised_total": len(order), "auctions": [merged[f"remaju:{number}"]["document"] for number in order], "detail_checked_at": {number: merged[f"remaju:{number}"].get("detail_checked_at", merged[f"remaju:{number}"]["last_seen_at"]) for number in order}}
    output.mkdir(parents=True)
    temporary_state = output / ".migration-state.json"
    write_json(temporary_state, history)
    write_json(output / "data/manifest.json", {"schema_version": 1, "scope": "all-phases", "state": {"path": temporary_state.name, "sha256": checksum(temporary_state)}})
    manifest = publish_run(run, output)
    temporary_state.unlink()
    (output / "data/manifest.json").unlink()
    (output / "data").rmdir()
    if manifest["history_count"] != len(merged):
        raise ValueError("Migration lost historical records")
    return {"manifest": manifest, "source_snapshots": len(states), "historical_auctions": len(merged), "current_auctions": len(order), "individual_detail_ids": len(detail_ids)}
