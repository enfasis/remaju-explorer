import fcntl
import hashlib
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

from .archive import canonical_bytes, export_csv, identifier, read_json, reconcile, utc_now, write_events, write_json


PHASES = {"publicación e inscripcion", "publicación e inscripción", "validación de inscripción", "presentación de ofertas"}
MAX_SUMMARY_SIZE = 1024 * 1024


def validate_run(run: dict[str, Any], previous_count: int | None = None) -> None:
    if run.get("mode") != "live" or run.get("status") != "complete" or run.get("scope") != "all-phases":
        raise ValueError("Only complete all-phase live runs may be published")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", str(run.get("run_id", ""))):
        raise ValueError("Invalid run identifier")
    auctions = run.get("auctions")
    if not isinstance(auctions, list) or not auctions:
        raise ValueError("Empty or missing auction list requires manual review")
    if run.get("advertised_total") != len(auctions):
        raise ValueError("Advertised total does not match observed records")
    if run.get("pages_complete") is not True or run.get("details_complete") is not True:
        raise ValueError("Incomplete pagination or details")
    if previous_count and len(auctions) < previous_count * 0.7:
        raise ValueError("Suspicious drop requires manual review")
    seen = set()
    for auction in auctions:
        if not isinstance(auction, dict):
            raise ValueError("Invalid auction")
        key = identifier(auction)
        if key in seen:
            raise ValueError("Duplicate auction identifier")
        seen.add(key)
        detail = auction.get("detail")
        if not isinstance(detail, dict) or not all(isinstance(detail.get(key), dict) for key in ("remate_tab", "inmuebles_tab", "cronograma_tab")):
            raise ValueError(f"Incomplete detail for {key}")


def money(value: str | None) -> dict[str, str | None] | None:
    if not value:
        return None
    raw = str(value).strip()
    currency = "PEN" if raw.startswith(("S/.", "S/")) else "USD" if raw.startswith("$") else None
    if not currency:
        return {"raw": raw, "amount": None, "currency": None}
    text = re.sub(r"^(S/\.?|\$)\s*", "", raw).replace(",", "")
    try:
        amount = Decimal(text)
        if not amount.is_finite() or amount < 0:
            raise InvalidOperation
    except InvalidOperation:
        return {"raw": raw, "amount": None, "currency": currency}
    return {"raw": raw, "amount": format(amount, "f"), "currency": currency}


def summary(auction: dict[str, Any]) -> dict[str, Any]:
    listing = auction.get("list_data") or {}
    detail = auction.get("detail") or {}
    property_tab = detail.get("inmuebles_tab") or {}
    remate = detail.get("remate_tab") or {}
    properties = property_tab.get("inmuebles") or []
    raw_date = listing.get("fecha_presentacion")
    try:
        offer_date = date.fromisoformat(raw_date).isoformat() if raw_date else None
    except (ValueError, TypeError):
        offer_date = None
    return {
        "auction_id": identifier(auction), "numero_remate": str(auction["numero_remate"]),
        "descripcion": remate.get("descripcion") or listing.get("descripcion") or None,
        "departamento": property_tab.get("departamento") or None,
        "provincia": property_tab.get("provincia") or None,
        "distrito": property_tab.get("distrito") or None,
        "tipo_inmueble": properties[0].get("tipo_inmueble") if properties else None,
        "fase": listing.get("fase") or None, "estado": listing.get("estado") or None,
        "offer_date": offer_date, "offer_at": None,
        "precio_base": money(remate.get("precio_base") or listing.get("precio_base")),
        "detail_path": f"auctions/{auction['numero_remate']}.json",
    }


def eligible(auction: dict[str, Any]) -> bool:
    listing = auction.get("list_data") or {}
    phase = str(listing.get("fase") or "").strip().casefold()
    status = str(listing.get("estado") or "").strip().casefold()
    return phase in PHASES and status in {"en proceso", "activo", "activa"}


@contextmanager
def exclusive_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def publish_run(run: dict[str, Any], root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(root / ".lock"):
        manifest_path = root / "data/manifest.json"
        old_manifest = read_json(manifest_path) if manifest_path.exists() else None
        old_state = read_json(root / old_manifest["state"]["path"].lstrip("/")) if old_manifest else {}
        if old_manifest and checksum(root / old_manifest["state"]["path"].lstrip("/")) != old_manifest["state"]["sha256"]:
            raise ValueError("Previous state checksum mismatch")
        if old_state.get("last_run_id") == run.get("run_id"):
            raise ValueError("Run already accepted")
        previous_count = sum(record["present"] for record in old_state.get("records", {}).values()) if old_state else None
        validate_run(run, previous_count)
        run_id = run["run_id"]
        release_relative = Path("data/releases") / run_id
        final = root / release_relative
        if final.exists():
            raise ValueError("Release already exists")
        state, events = reconcile(old_state, run["auctions"], run_id, run["observed_at"], run["scope"])
        temporary = Path(tempfile.mkdtemp(prefix=".release-", dir=root))
        try:
            available = []
            for auction in run["auctions"]:
                if eligible(auction):
                    item = summary(auction)
                    item["detail_path"] = f"/{release_relative}/auctions/{auction['numero_remate']}.json"
                    available.append(item)
                    write_json(temporary / "auctions" / f"{auction['numero_remate']}.json", auction)
            available.sort(key=lambda item: item["auction_id"])
            snapshot = {"schema_version": 1, "dataset_version": run_id, "auctions": available}
            if len(canonical_bytes(snapshot)) > MAX_SUMMARY_SIZE:
                raise ValueError("Availability exceeds size budget")
            write_json(temporary / "availability.json", snapshot)
            export_csv([auction for auction in run["auctions"] if eligible(auction)], temporary / "available.csv")
            write_json(temporary / "state.json", state)
            write_json(temporary / "members.json", [{"auction_id": identifier(a), "revision": state["records"][identifier(a)]["revision"]} for a in run["auctions"]])
            write_events(temporary / "events.jsonl.gz", events)
            latest = [{"auction_id": key, **record} for key, record in sorted(state["records"].items())]
            write_json(temporary / "archive/latest.json", {"schema_version": 1, "auctions": latest})
            write_json(temporary / "archive/manifest.json", {"schema_version": 1, "latest": f"/{release_relative}/archive/latest.json", "history": [*(old_manifest.get("history", []) if old_manifest else []), f"/{release_relative}/events.jsonl.gz"]})
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(temporary, final)
            manifest = {"schema_version": 1, "dataset_version": run_id, "run_id": run_id, "generated_at": utc_now(), "observed_at": run["observed_at"], "scope": run["scope"], "count": len(available), "availability": {"path": f"/{release_relative}/availability.json", "sha256": checksum(final / "availability.json")}, "state": {"path": f"/{release_relative}/state.json", "sha256": checksum(final / "state.json")}, "archive": {"path": f"/{release_relative}/archive/manifest.json"}, "history": [*(old_manifest.get("history", []) if old_manifest else []), f"/{release_relative}/events.jsonl.gz"]}
            write_json(manifest_path, manifest)
            return manifest
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
