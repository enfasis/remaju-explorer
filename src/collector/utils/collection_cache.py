from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from models import Auction, Card

from .archive import read_json, utc_now, write_json
from .publication import checksum, document_path, load_history


class ConsecutiveWindow:
    def __init__(self, history: list[str], size: int):
        if size < 2:
            raise ValueError("Stop window must contain at least two auctions")
        if len(history) != len(set(history)):
            raise ValueError("History contains duplicate auction numbers")
        self.positions = {number: position for position, number in enumerate(history)}
        self.size = size
        self.matched: deque[str] = deque(maxlen=size)
        self.previous: int | None = None

    def observe(self, number: str, unchanged: bool = True) -> bool:
        position = self.positions.get(number) if unchanged else None
        if position is None or self.previous is None or position != self.previous + 1:
            self.matched.clear()
        if position is not None:
            self.matched.append(number)
        self.previous = position
        return len(self.matched) == self.size


class CollectionCache:
    def __init__(self, directory: Path | None, max_age_hours: int = 168):
        if max_age_hours < 0:
            raise ValueError("Cache max age cannot be negative")
        self.directory = directory
        self.max_age = timedelta(hours=max_age_hours)
        self.records: dict[str, Any] = {}
        self.order: list[str] = []
        self.checked_at: dict[str, str] = {}
        self.positions: dict[str, int] = {}
        self.visited: set[int] = set()
        self.next_position = 0
        if directory is None:
            return
        snapshot = directory / "auctions.json"
        numbers = directory / "ids.txt"
        if not numbers.exists():
            numbers = directory / "auction-numbers.txt"
        if snapshot.exists() and numbers.exists():
            cached = read_json(snapshot)
            order = numbers.read_text(encoding="utf-8").splitlines()
            if cached.get("schema_version") == 1 and cached.get("order") == order and len(order) == len(set(order)) and all(number.isdigit() for number in order):
                self.records = cached["records"]
                self.order = order
                self.positions = {number: position for position, number in enumerate(order)}

    def use_published(self, root: Path | None) -> None:
        if root is None or not (root / "manifest.json").exists():
            return
        manifest = read_json(root / "manifest.json")
        if manifest.get("schema_version") != 2 or manifest.get("scope") != "all-phases":
            return
        history = load_history(root, manifest)
        path = document_path(root, manifest["ids"]["path"])
        if checksum(path) != manifest["ids"]["sha256"]:
            raise ValueError("Previous ID list checksum mismatch")
        order = path.read_text(encoding="utf-8").splitlines()
        records = {record["document"]["numero_remate"]: {"checked_at": record.get("detail_checked_at", record["last_seen_at"]), "auction": record["document"]} for record in history["records"].values() if record["present"]}
        if len(order) != len(set(order)) or set(order) != set(records):
            raise ValueError("Published IDs do not match history")
        self.records, self.order = records, order
        self.positions = {number: position for position, number in enumerate(order)}

    def reuse(self, card: Card) -> Auction | None:
        position = self.positions.get(card.listing.numero_remate)
        if position is not None:
            in_order = position == self.next_position
            self.visited.add(position)
            while self.next_position in self.visited:
                self.next_position += 1
            if not in_order:
                return None
        record = self.records.get(card.listing.numero_remate)
        if record is None:
            return None
        auction = Auction.model_validate(record["auction"])
        checked = datetime.fromisoformat(record["checked_at"].replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - checked
        if not timedelta(0) <= age < self.max_age or auction.list_data != card.listing:
            return None
        self.checked_at[auction.numero_remate] = record["checked_at"]
        return auction.model_copy(deep=True)

    def fetched(self, auction: Auction) -> None:
        self.checked_at[auction.numero_remate] = utc_now()

    def save(self, auctions: list[Auction]) -> None:
        if self.directory is None:
            return
        order = [auction.numero_remate for auction in auctions]
        records = {auction.numero_remate: {"checked_at": self.checked_at[auction.numero_remate], "auction": auction.model_dump(mode="json")} for auction in auctions}
        write_json(self.directory / "auctions.json", {"schema_version": 1, "order": order, "records": records})
        temporary = self.directory / "ids.txt.tmp"
        temporary.write_text("".join(f"{number}\n" for number in order), encoding="utf-8")
        temporary.replace(self.directory / "ids.txt")
