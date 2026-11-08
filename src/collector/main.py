import json
import sys
from pathlib import Path
from typing import Any, Literal, override

from clypi import ClypiConfig, Command, arg, configure

from config import Settings
from parser import collect, replay
from processing import Processing
from utils.archive import export_csv, identifier, read_json, utc_now, write_json
from utils.exchange import ExchangeRateClient
from utils.geocode import GeocodingClient
from utils.publication import publish_run, validate_run

class CommandFailed(Exception):
    def __init__(self, result: Any, code: int):
        super().__init__(code)
        self.result = result
        self.code = code


def load_auctions(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    auctions = data if isinstance(data, list) else data.get("auctions") if isinstance(data, dict) else None
    if not isinstance(auctions, list) or not all(isinstance(item, dict) for item in auctions):
        raise ValueError("Expected an array of auction objects or an object with an auctions array")
    ids = [identifier(item) for item in auctions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate auction identifiers")
    return auctions


def new_output(output: Path, source: Path | None = None) -> None:
    if output.exists() or (source is not None and output.resolve() == source.resolve()):
        raise ValueError("Output must be a new file distinct from the input")


class Action(Command):
    def execute(self) -> Any:
        raise NotImplementedError

    @override
    async def run(self) -> None:
        try:
            result = self.execute()
        except CommandFailed as failure:
            print(json.dumps(failure.result, ensure_ascii=False, default=str))
            raise SystemExit(failure.code)
        except (OSError, ValueError, TypeError) as error:
            print(json.dumps({"error": {"code": "INVALID_INPUT", "message": str(error)}}, ensure_ascii=False), file=sys.stderr)
            raise SystemExit(5)
        print(json.dumps(result, ensure_ascii=False, default=str))


class Collect(Action):
    """Collect auctions from REMAJU into a cached run"""

    mode: Literal["sample", "live"] = arg("sample", help="sample walks one listing page; live walks every page")
    output: Path = arg(Path("var/private/runs"), help="Directory for run caches and traces")
    max_pages: int | None = arg(None, help="Stop a live run after this many listing pages; the run stays partial")
    page_size: int = arg(12, help="Auctions per listing page: 4 or 12")
    cache_dir: Path | None = arg(None, help="Persistent collector cache and ordered ids.txt")
    cache_max_age_hours: int = arg(168, help="Refresh unchanged details after this many hours; 0 forces fresh details")
    baseline_dir: Path | None = arg(None, help="Restore the baseline from verified manifest.json, ids.txt and history.json")
    stop_window: int | None = arg(None, help="Experimental: stop at this many unchanged consecutive historical IDs; output cannot be published")

    @override
    def execute(self) -> Any:
        result = collect(self.output, self.mode, max_pages=self.max_pages, page_size=self.page_size, cache_dir=self.cache_dir, cache_max_age_hours=self.cache_max_age_hours, stop_window=self.stop_window, baseline_dir=self.baseline_dir)
        if result["status"] == "failed":
            raise CommandFailed(result, 4)
        return result


class Process(Action):
    """Geocode, convert, consolidate and optionally publish a cached run"""

    run_dir: Path = arg(help="Run directory containing auctions.json and run.json")
    geocode: bool = arg(False, help="Geocode properties with the paid Google API")
    exchange: bool = arg(False, help="Convert prices with the external exchange-rate API")
    target: Path | None = arg(None, help="Publish the consolidated run into this site root")
    allow_partial: bool = arg(False, help="Publish a partial live run, such as one limited with --max-pages")

    @override
    def execute(self) -> Any:
        settings = Settings()
        processing = Processing(
            self.run_dir,
            GeocodingClient(settings.geocoding_key(), settings.geocoding_cache) if self.geocode else None,
            ExchangeRateClient(settings.exchange_rate_cache) if self.exchange else None,
            self.target,
            allow_partial=self.allow_partial,
        )
        result = processing.process()
        if self.target is not None:
            return result
        return {"output": str(self.run_dir / "consolidated.json"), "count": len(result["auctions"])}


class Publish(Action):
    """Publish a consolidated run into a site root"""

    run_file: Path = arg(help="Consolidated run document")
    target: Path = arg(help="Site root")
    allow_partial: bool = arg(False, help="Publish a partial live run, such as one limited with --max-pages")

    @override
    def execute(self) -> Any:
        return publish_run(read_json(self.run_file), self.target, self.allow_partial)


class ValidateRun(Action):
    """Check whether a consolidated run may be published"""

    run_file: Path = arg(help="Consolidated run document")

    @override
    def execute(self) -> Any:
        validate_run(read_json(self.run_file))
        return {"valid": True}


class Replay(Action):
    """Parse a captured listing page for characterization"""

    capture_dir: Path = arg(help="Directory containing page1_list.xml")
    output: Path = arg(help="New file for the replay result")

    @override
    def execute(self) -> Any:
        new_output(self.output)
        result = replay(self.capture_dir)
        write_json(self.output, result)
        return {"output": str(self.output), "count": result["count"], "publishable": False}


class Query(Action):
    """List auctions from a document"""

    input: Path = arg(help="Auction document")
    department: str | None = arg(None, help="Only auctions in this department")
    limit: int = arg(100, help="Maximum auctions to return (1-10000)")

    @override
    def execute(self) -> Any:
        if self.limit < 1 or self.limit > 10000:
            raise ValueError("limit must be between 1 and 10000")
        auctions = load_auctions(self.input)
        if self.department:
            auctions = [a for a in auctions if (a.get("detail", {}).get("inmuebles_tab", {}).get("departamento") or "").casefold() == self.department.casefold()]
        return {"count": len(auctions), "auctions": auctions[:self.limit]}


class Show(Action):
    """Show one auction from a document"""

    input: Path = arg(help="Auction document")
    auction_id: str = arg(help="Identifier such as remaju:22096")

    @override
    def execute(self) -> Any:
        result = next((a for a in load_auctions(self.input) if identifier(a) == self.auction_id), None)
        if result is None:
            raise ValueError("Auction not found")
        return result


class Validate(Action):
    """Check the structure and identifiers of an auction document"""

    input: Path = arg(help="Auction document")

    @override
    def execute(self) -> Any:
        auctions = load_auctions(self.input)
        return {"valid": True, "count": len(auctions), "note": "Structure and identifiers only; completeness is not established"}


class ImportLegacy(Action):
    """Wrap a legacy auction export as a non-current document"""

    input: Path = arg(help="Legacy auction document")
    output: Path = arg(help="New file for the imported document")

    @override
    def execute(self) -> Any:
        auctions = load_auctions(self.input)
        new_output(self.output, self.input)
        write_json(self.output, {"schema_version": 1, "scope": "legacy-import", "imported_at": utc_now(), "observation_time": None, "current": False, "count": len(auctions), "auctions": auctions})
        return {"output": str(self.output), "count": len(auctions), "current": False}


class ExportCsv(Action):
    """Export auctions as CSV"""

    input: Path = arg(help="Auction document")
    output: Path = arg(help="New CSV file")

    @override
    def execute(self) -> Any:
        auctions = load_auctions(self.input)
        new_output(self.output, self.input)
        export_csv(auctions, self.output)
        return {"output": str(self.output), "count": len(auctions)}


class Remaju(Command):
    """REMAJU auction collector"""

    subcommand: Collect | Process | Publish | ValidateRun | Replay | Query | Show | Validate | ImportLegacy | ExportCsv

    @override
    @classmethod
    def prog(cls) -> str:
        return "remaju"


def main(args: list[str] | None = None) -> None:
    configure(ClypiConfig(disable_colors=not sys.stdout.isatty()))
    Remaju.parse(args).start()


if __name__ == "__main__":
    main()
