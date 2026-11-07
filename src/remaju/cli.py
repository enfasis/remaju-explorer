import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .archive import export_csv, identifier, read_json, utc_now, write_json
from .publication import publish_run, validate_run


def load_auctions(path: Path) -> list[dict[str, Any]]:
    data = read_json(path)
    auctions = data if isinstance(data, list) else data.get("auctions") if isinstance(data, dict) else None
    if not isinstance(auctions, list) or not all(isinstance(item, dict) for item in auctions):
        raise ValueError("Expected an array of auction objects or an object with an auctions array")
    ids = [identifier(item) for item in auctions]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate auction identifiers")
    return auctions


def main() -> int:
    parser = argparse.ArgumentParser(prog="remaju", description="Offline tools for REMAJU auction documents")
    parser.add_argument("--version", action="version", version="remaju 0.1.0")
    commands = parser.add_subparsers(dest="command", required=True)
    query = commands.add_parser("query")
    query.add_argument("--input", type=Path, required=True)
    query.add_argument("--department")
    query.add_argument("--limit", type=int, default=100)
    show = commands.add_parser("show")
    show.add_argument("--input", type=Path, required=True)
    show.add_argument("--auction-id", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--input", type=Path, required=True)
    legacy = commands.add_parser("import-legacy")
    legacy.add_argument("--input", type=Path, required=True)
    legacy.add_argument("--output", type=Path, required=True)
    csv_command = commands.add_parser("export-csv")
    csv_command.add_argument("--input", type=Path, required=True)
    csv_command.add_argument("--output", type=Path, required=True)
    publish = commands.add_parser("publish")
    publish.add_argument("--run", type=Path, required=True)
    publish.add_argument("--target", type=Path, required=True)
    publish.add_argument("--fixture-only", action="store_true")
    check_run = commands.add_parser("validate-run")
    check_run.add_argument("--run", type=Path, required=True)
    replay = commands.add_parser("replay")
    replay.add_argument("--capture-dir", type=Path, required=True)
    replay.add_argument("--output", type=Path, required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("--mode", choices=["sample"], default="sample")
    collect.add_argument("--output", type=Path, default=Path("var/private/runs"))
    args = parser.parse_args()
    try:
        if args.command == "collect":
            from .collector import collect_sample
            result = collect_sample(args.output)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result["status"] == "partial" else 4
        if args.command == "replay":
            from .replay import replay as replay_capture
            if args.output.exists():
                raise ValueError("Output must be a new file")
            result = replay_capture(args.capture_dir)
            write_json(args.output, result)
            print(json.dumps({"output": str(args.output), "count": result["count"], "publishable": False}))
            return 0
        if args.command == "validate-run":
            validate_run(read_json(args.run))
            print(json.dumps({"valid": True}))
            return 0
        if args.command == "publish":
            if not args.fixture_only:
                raise ValueError("Production publication is disabled; only synthetic fixture releases are supported")
            print(json.dumps(publish_run(read_json(args.run), args.target)))
            return 0
        auctions = load_auctions(args.input)
        if args.command == "query":
            if args.limit < 1 or args.limit > 10000:
                raise ValueError("limit must be between 1 and 10000")
            if args.department:
                auctions = [a for a in auctions if (a.get("detail", {}).get("inmuebles_tab", {}).get("departamento") or "").casefold() == args.department.casefold()]
            result: Any = {"count": len(auctions), "auctions": auctions[:args.limit]}
        elif args.command == "show":
            result = next((a for a in auctions if identifier(a) == args.auction_id), None)
            if result is None:
                raise ValueError("Auction not found")
        elif args.command == "validate":
            result = {"valid": True, "count": len(auctions), "note": "Structure and identifiers only; completeness is not established"}
        elif args.command == "import-legacy":
            if args.output.resolve() == args.input.resolve() or args.output.exists():
                raise ValueError("Output must be a new file distinct from the input")
            result = {"schema_version": 1, "scope": "legacy-import", "imported_at": utc_now(), "observation_time": None, "current": False, "count": len(auctions), "auctions": auctions}
            write_json(args.output, result)
            result = {"output": str(args.output), "count": len(auctions), "current": False}
        else:
            if args.output.resolve() == args.input.resolve() or args.output.exists():
                raise ValueError("Output must be a new file distinct from the input")
            export_csv(auctions, args.output)
            result = {"output": str(args.output), "count": len(auctions)}
        print(json.dumps(result, ensure_ascii=False, default=str))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        print(json.dumps({"error": {"code": "INVALID_INPUT", "message": str(error)}}, ensure_ascii=False), file=sys.stderr)
        return 5


if __name__ == "__main__":
    sys.exit(main())
