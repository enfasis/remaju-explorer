import csv
import gzip
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, mode="wb", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(canonical_bytes(value))
            stream.flush()
            os.fsync(stream.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def identifier(auction: dict[str, Any]) -> str:
    number = str(auction.get("numero_remate") or "")
    if not re.fullmatch(r"[0-9]+", number):
        raise ValueError("Auction numero_remate must contain only digits")
    return f"remaju:{number}"


def reconcile(previous: dict[str, Any], auctions: list[dict[str, Any]], run_id: str, observed_at: str, scope: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if previous and previous.get("scope") != scope:
        raise ValueError("Cannot reconcile observations from different scopes")
    records = {key: dict(value) for key, value in previous.get("records", {}).items()}
    current: dict[str, dict[str, Any]] = {}
    for auction in auctions:
        key = identifier(auction)
        if key in current:
            raise ValueError(f"Duplicate auction identifier: {key}")
        current[key] = auction
    events = []
    for key, auction in sorted(current.items()):
        revision = digest(auction)
        old = records.get(key)
        event_types = []
        if old is None or old["revision"] != revision:
            event_types.append("auction.observed")
        if old is not None and not old["present"]:
            event_types.append("auction.reappeared")
        for event_type in event_types:
            event = {"run_id": run_id, "observed_at": observed_at, "auction_id": key, "type": event_type, "revision": revision}
            event["event_id"] = digest(event)
            if event_type == "auction.observed":
                event["document"] = auction
            events.append(event)
        records[key] = {"document": auction, "revision": revision, "present": True, "first_seen_at": old["first_seen_at"] if old else observed_at, "last_seen_at": observed_at, "last_changed_at": observed_at if old is None or old["revision"] != revision else old["last_changed_at"]}
    for key in sorted(records.keys() - current.keys()):
        record = records[key]
        if record["present"]:
            event = {"run_id": run_id, "observed_at": observed_at, "auction_id": key, "type": "auction.absent", "revision": record["revision"]}
            event["event_id"] = digest(event)
            events.append(event)
            record["present"] = False
    return {"schema_version": 1, "scope": scope, "last_run_id": run_id, "records": records}, events


def export_csv(records: list[dict[str, Any]], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["auction_id", "numero_remate", "descripcion", "fecha_presentacion", "precio_base", "fase", "estado"])
        writer.writeheader()
        for record in records:
            listing = record.get("list_data") or {}
            row = {"auction_id": identifier(record), "numero_remate": str(record["numero_remate"]), **{key: listing.get(key) for key in ("descripcion", "fecha_presentacion", "precio_base", "fase", "estado")}}
            writer.writerow({key: safe_csv(value) for key, value in row.items()})


def safe_csv(value: Any) -> str:
    text = "" if value is None else str(value)
    if text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def write_events(path: Path, events: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as stream:
            for event in events:
                stream.write(canonical_bytes(event) + b"\n")
