from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Any

import requests

from models import Auction, Card, RemateDetail, Seguimiento
from utils import extract
from utils.archive import utc_now, write_json
from utils.debugger import Trace
from utils.jsf import parse_partial_response
from utils.site import CRONOGRAMA, INMUEBLES, ROWS, RemajuSite, polite_pause


class Parser:
    def __init__(self, site: RemajuSite, cache: Path, max_pages: int | None = None):
        self.site = site
        self.cache = cache
        self.max_pages = max_pages
        self.auctions: list[Auction] = []
        self.failures: list[dict[str, str]] = []
        self.pages_complete = False

    def process(self) -> list[Auction]:
        for first, cards in self.pages():
            for card in cards:
                self.collect(first, card)
        return self.auctions

    def pages(self) -> Iterator[tuple[int, list[Card]]]:
        for page in count():
            if self.max_pages is not None and page >= self.max_pages:
                return
            first = page * ROWS
            self.site.open_listing()
            cards = extract.cards(self.site.list_page(first))
            if not cards:
                self.pages_complete = True
                return
            fresh = [card for card in cards if not self.seen(card)]
            if not fresh:
                return
            yield first, fresh
            if self.site.total is not None and first + ROWS >= self.site.total:
                self.pages_complete = True
                return

    def collect(self, first: int, card: Card) -> None:
        try:
            auction = Auction(
                numero_remate=card.listing.numero_remate,
                list_data=card.listing,
                detail=self.detail(card),
                seguimiento=self.tracking(card),
            )
        except (ValueError, requests.RequestException) as error:
            self.failures.append({"numero_remate": card.listing.numero_remate, "type": type(error).__name__, "message": str(error)})
            self.recover(first)
            return
        self.auctions.append(auction)
        write_json(self.cache, [item.model_dump(mode="json") for item in self.auctions])

    def detail(self, card: Card) -> RemateDetail:
        html = self.site.open_detail(card)
        inmuebles = self.site.open_tab(INMUEBLES)
        cronograma = self.site.open_tab(CRONOGRAMA)
        self.site.leave()
        return extract.detail(card.listing.numero_remate, html, inmuebles, cronograma)

    def tracking(self, card: Card) -> Seguimiento | None:
        if not card.tracking_id:
            return None
        html = self.site.open_tracking(card)
        self.site.leave()
        return extract.seguimiento(html)

    def recover(self, first: int) -> None:
        self.site.open_listing()
        self.site.list_page(first)

    def seen(self, card: Card) -> bool:
        return any(auction.numero_remate == card.listing.numero_remate for auction in self.auctions)

    def report(self) -> dict[str, Any]:
        return {
            "advertised_total": self.site.total,
            "pages_complete": self.pages_complete,
            "details_complete": not self.failures,
            "count": len(self.auctions),
            "failures": self.failures,
        }


def collect(output: Path, mode: str, session: requests.Session | None = None, pause: Callable[[], None] = polite_pause, max_pages: int | None = None) -> dict[str, Any]:
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    trace = Trace(output / run_id)
    started = utc_now()
    limit = max_pages if mode == "live" else 1
    scope = "sample" if mode != "live" else "partial" if max_pages is not None else "all-phases"
    report: dict[str, Any] = {"run_id": run_id, "mode": mode, "scope": scope, "max_pages": limit, "status": "failed", "started_at": started, "observed_at": started}
    try:
        with session or requests.Session() as http:
            parser = Parser(RemajuSite(trace, http, pause), trace.directory / "auctions.json", limit)
            parser.process()
            report.update(parser.report())
            report["status"] = "complete" if scope == "all-phases" and report["pages_complete"] and report["details_complete"] else "partial"
    except (ValueError, OSError, requests.RequestException) as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        report["finished_at"] = utc_now()
        write_json(trace.directory / "run.json", report)
    return report


def replay(capture_dir: Path) -> dict[str, Any]:
    xml = (capture_dir / "page1_list.xml").read_text(encoding="utf-8")
    if extract.LIST_ID not in parse_partial_response(xml).updates:
        raise ValueError("Expected listing update is missing")
    auctions = extract.listing(xml)
    actions = extract.card_actions(xml)
    if len(auctions) != len(actions) or not auctions:
        raise ValueError("List items and card actions do not match")
    return {
        "mode": "replay", "status": "partial", "publishable": False,
        "warnings": ["Legacy parser may fabricate missing values; output is for characterization only."],
        "count": len(auctions), "auctions": [auction.model_dump(mode="json") for auction in auctions],
        "cards": actions,
    }
