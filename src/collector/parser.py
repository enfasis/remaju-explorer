import json
import sys
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Any

import requests

from models import Auction, Card, RemateDetail, Seguimiento
from utils import extract
from utils.archive import utc_now, write_json
from utils.collection_cache import CollectionCache, ConsecutiveWindow
from utils.debugger import Trace, diagnostic_error
from utils.jsf import parse_partial_response
from utils.site import CRONOGRAMA, INMUEBLES, ROWS, RemajuSite, polite_pause


class Parser:
    def __init__(self, site: RemajuSite, cache: Path, max_pages: int | None = None, baseline: CollectionCache | None = None, stop_window: int | None = None):
        self.site = site
        self.cache = cache
        self.max_pages = max_pages
        self.auctions: list[Auction] = []
        self.failures: list[dict[str, str]] = []
        self.pages_complete = False
        self.baseline = baseline or CollectionCache(None)
        self.window = ConsecutiveWindow(self.baseline.order, stop_window) if stop_window is not None else None
        self.stop_reason: str | None = None
        self.reused = 0
        self.fetched = 0
        self.order: list[str] = []

    def process(self) -> list[Auction]:
        for _, cards in self.pages():
            for card in cards:
                self.order.append(card.listing.numero_remate)
                reused = self.baseline.reuse(card)
                if reused is not None:
                    self.auctions.append(reused)
                    self.reused += 1
                    self.save()
                else:
                    self.collect(card)
                if self.window and self.window.observe(card.listing.numero_remate, reused is not None):
                    self.stop_reason = "known-consecutive-window"
                    return self.auctions
        return self.auctions

    def pages(self) -> Iterator[tuple[int, list[Card]]]:
        position = 0
        for page in count():
            if self.max_pages is not None and page >= self.max_pages:
                return
            first = position - position % self.site.rows
            self.site.open_listing()
            cards = extract.cards(self.site.list_page(first))
            if not cards:
                self.pages_complete = True
                return
            if self.site.total is not None and first + len(cards) < self.site.total and len(cards) != self.site.rows:
                raise ValueError("Source returned an unexpected page size; refusing to skip records")
            fresh = [card for card in cards if not self.seen(card)]
            if not fresh:
                self.pages_complete = self.site.total is not None and len(self.auctions) >= self.site.total
                return
            shift = self.site.shift
            yield first, fresh
            position = first + len(cards) + self.site.shift - shift
            if self.site.total is not None and position >= self.site.total:
                if len(self.auctions) >= self.site.total:
                    self.pages_complete = True
                    return
                position = 0

    def collect(self, card: Card) -> None:
        try:
            auction = Auction(
                numero_remate=card.listing.numero_remate,
                list_data=card.listing,
                detail=self.detail(card),
                seguimiento=self.tracking(card),
            )
        except (ValueError, requests.RequestException) as error:
            self.failures.append({"numero_remate": card.listing.numero_remate, "type": type(error).__name__, "message": diagnostic_error(error)})
            raise
        self.auctions.append(auction)
        self.fetched += 1
        self.baseline.fetched(auction)
        self.save()

    def save(self) -> None:
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

    def seen(self, card: Card) -> bool:
        return any(auction.numero_remate == card.listing.numero_remate for auction in self.auctions)

    def report(self) -> dict[str, Any]:
        return {
            "advertised_total": self.site.total,
            "pages_complete": self.pages_complete,
            "details_complete": not self.failures,
            "count": len(self.auctions),
            "failures": self.failures,
            "details_fetched": self.fetched,
            "details_reused": self.reused,
            "detail_checked_at": self.baseline.checked_at,
            "stop_reason": self.stop_reason,
            "matched_window": list(self.window.matched) if self.window and self.stop_reason == "known-consecutive-window" else [],
            "page_size": self.site.rows,
        }


def collect(output: Path, mode: str, session: requests.Session | None = None, pause: Callable[[], None] = polite_pause, max_pages: int | None = None, page_size: int = ROWS, cache_dir: Path | None = None, cache_max_age_hours: int = 168, stop_window: int | None = None, baseline_dir: Path | None = None) -> dict[str, Any]:
    if max_pages is not None and max_pages < 1:
        raise ValueError("max_pages must be at least 1")
    if page_size not in {4, 12}:
        raise ValueError("page_size must be 4 or 12")
    if stop_window is not None and (stop_window < 2 or cache_dir is None):
        raise ValueError("stop_window requires a cache directory and at least two auctions")
    baseline = CollectionCache(cache_dir, cache_max_age_hours)
    baseline.use_published(baseline_dir)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    trace = Trace(output / run_id)
    started = utc_now()
    limit = max_pages if mode == "live" else 1
    scope = "sample" if mode != "live" else "partial" if max_pages is not None else "all-phases"
    report: dict[str, Any] = {"run_id": run_id, "mode": mode, "scope": scope, "max_pages": limit, "status": "failed", "started_at": started, "observed_at": started, "detail_cache_max_age_hours": cache_max_age_hours}
    parser: Parser | None = None
    try:
        with session or requests.Session() as http:
            parser = Parser(RemajuSite(trace, http, pause, page_size), trace.directory / "auctions.json", limit, baseline, stop_window)
            parser.process()
            report.update(parser.report())
            if parser.stop_reason:
                report["scope"] = "partial"
            complete = scope == "all-phases" and report["pages_complete"] and report["details_complete"] and report["count"] > 0 and report["count"] == report["advertised_total"]
            report["status"] = "complete" if complete else "partial"
            if complete:
                baseline.save(parser.auctions)
    except (ValueError, OSError, requests.RequestException) as error:
        if parser is not None:
            parser.stop_reason = "collection-error"
            report.update(parser.report())
        report["status"] = "failed"
        report["error"] = {"type": type(error).__name__, "message": diagnostic_error(error), "response": trace.last_response}
        trace.event("collection", "failed", error=report["error"], failures=report.get("failures", []))
        print(json.dumps({"run_id": run_id, "status": "failed", "error": report["error"], "failures": report.get("failures", [])}, ensure_ascii=False), file=sys.stderr)
    finally:
        if parser is not None:
            (trace.directory / "ids.txt").write_text("".join(f"{number}\n" for number in parser.order), encoding="utf-8")
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
