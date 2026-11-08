import fcntl
import hashlib
import os
import re
import shutil
import tempfile
from copy import deepcopy
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from .archive import identifier, read_json, reconcile, utc_now, write_json
from .geography import clean_coordinates, in_peru
from .sample_export import current_status, schedule


LIMA = ZoneInfo("America/Lima")


def validate_run(run: dict[str, Any], previous_count: int | None = None, allow_partial: bool = False) -> None:
    if run.get("stop_reason") == "known-consecutive-window":
        raise ValueError("Early-stop runs are experimental and cannot replace published data")
    if allow_partial:
        if run.get("mode") != "live" or run.get("status") not in {"complete", "partial"} or run.get("scope") not in {"all-phases", "partial"}:
            raise ValueError("Only live runs may be published")
    elif run.get("mode") != "live" or run.get("status") != "complete" or run.get("scope") != "all-phases":
        raise ValueError("Only complete all-phase live runs may be published")
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", str(run.get("run_id", ""))):
        raise ValueError("Invalid run identifier")
    auctions = run.get("auctions")
    if not isinstance(auctions, list) or not auctions:
        raise ValueError("Empty or missing auction list requires manual review")
    if not allow_partial:
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
    status = current_status(auction.get("seguimiento"))
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
        "fase": listing.get("fase") or status["fase"], "estado": listing.get("estado") or status["estado"],
        "offer_date": offer_date, "offer_at": None,
        "precio_base": money(remate.get("precio_base") or listing.get("precio_base")),
        "cronograma": schedule(detail),
        "coordinates": [{"latitude": item["latitude"], "longitude": item["longitude"]} for item in properties if in_peru(item.get("latitude"), item.get("longitude"))],
        "thumbnail_path": None,
    }


def eligible(auction: dict[str, Any], now: datetime | None = None) -> bool:
    listing = auction.get("list_data") or {}
    status = str(listing.get("estado") or "").strip().casefold()
    if any(word in status for word in ("desiert", "suspend", "cancel", "nul", "conclu", "finaliz", "adjudic")):
        return False
    phase = next((item for item in schedule(auction.get("detail") or {}) if str(item.get("nro")) == "3"), None)
    if phase is None:
        return False
    try:
        deadline = datetime.fromisoformat(phase["fecha_fin"])
    except (TypeError, ValueError):
        return False
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=LIMA)
    current = now or datetime.now(LIMA)
    if current.tzinfo is None:
        current = current.replace(tzinfo=LIMA)
    return deadline >= current


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


def document_path(root: Path, path: str) -> Path:
    result = (root / path.lstrip("/")).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError("Invalid manifest file path")
    return result


def load_history(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    reference = manifest["history"] if manifest.get("schema_version") == 2 else manifest["state"]
    path = document_path(root, reference["path"])
    if checksum(path) != reference["sha256"]:
        raise ValueError("Previous history checksum mismatch")
    return read_json(path)


def publish_run(run: dict[str, Any], root: Path, allow_partial: bool = False, now: datetime | None = None) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)
    with exclusive_lock(root / ".lock"):
        manifest_path = root / "manifest.json"
        previous_path = manifest_path if manifest_path.exists() else root / "data/manifest.json"
        old_manifest = read_json(previous_path) if previous_path.exists() else None
        old_state = load_history(root, old_manifest) if old_manifest else {}
        if old_state.get("last_run_id") == run.get("run_id"):
            raise ValueError("Run already accepted")
        if old_manifest and old_manifest.get("scope") == "all-phases" and run.get("scope") != "all-phases":
            raise ValueError("A partial run cannot replace a complete published dataset")
        previous_count = sum(record["present"] for record in old_state.get("records", {}).values()) if old_state.get("scope") == "all-phases" else None
        validate_run(run, previous_count, allow_partial)
        if old_state and old_state.get("scope") != run.get("scope"):
            old_state["scope"] = run["scope"]
        run = deepcopy(run)
        for auction in run["auctions"]:
            clean_coordinates(auction)
        for record in old_state.get("records", {}).values():
            clean_coordinates(record["document"])
        run_id = run["run_id"]
        state, _ = reconcile(old_state, run["auctions"], run_id, run["observed_at"], run["scope"])
        observed = {identifier(auction) for auction in run["auctions"]}
        for key, record in state["records"].items():
            if key in observed:
                record["detail_checked_at"] = run.get("detail_checked_at", {}).get(key.split(":", 1)[1], run["observed_at"])
            else:
                record["detail_checked_at"] = old_state.get("records", {}).get(key, {}).get("detail_checked_at", record["last_seen_at"])
        state["dataset_version"] = run_id
        state["schema_version"] = 2
        temporary = Path(tempfile.mkdtemp(prefix=".publication-", dir=root))
        try:
            available = []
            for auction in run["auctions"]:
                if eligible(auction, now):
                    item = deepcopy(auction)
                    item["auction_id"] = identifier(auction)
                    item["detail_checked_at"] = run.get("detail_checked_at", {}).get(str(auction["numero_remate"]))
                    available.append(item)
            available.sort(key=lambda item: item["auction_id"])
            snapshot = {"schema_version": 2, "dataset_version": run_id, "auctions": available}
            write_json(temporary / "available.json", snapshot)
            write_json(temporary / "history.json", state)
            (temporary / "ids.txt").write_text("".join(f"{auction['numero_remate']}\n" for auction in run["auctions"]), encoding="utf-8")
            manifest = {"schema_version": 2, "dataset_version": run_id, "run_id": run_id, "generated_at": utc_now(), "observed_at": run["observed_at"], "scope": run["scope"], "count": len(available), "history_count": len(state["records"]), "available": {"path": "available.json", "sha256": checksum(temporary / "available.json")}, "history": {"path": "history.json", "sha256": checksum(temporary / "history.json")}, "ids": {"path": "ids.txt", "sha256": checksum(temporary / "ids.txt")}}
            manifest["collection"] = {key: run.get(key) for key in ("details_fetched", "details_reused", "detail_cache_max_age_hours")}
            for name in ("available.json", "history.json", "ids.txt"):
                os.replace(temporary / name, root / name)
            write_json(manifest_path, manifest)
            return manifest
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)
