import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError

from utils.archive import read_json
from utils.publication import checksum, document_path, load_history


def download(client: Any, bucket: str, key: str, target: Path, optional: bool = False) -> bool:
    try:
        data = client.get_object(Bucket=bucket, Key=key)["Body"].read()
    except ClientError as error:
        if optional and error.response["Error"]["Code"] in {"NoSuchKey", "404"}:
            return False
        raise
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return True


def restore(client: Any, public: str, private: str, site: Path, cache: Path) -> None:
    cache.mkdir(parents=True, exist_ok=True)
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=private, Prefix="cache/"):
        for item in page.get("Contents", []):
            relative = item["Key"].removeprefix("cache/")
            if relative and not item["Key"].endswith("/"):
                download(client, private, item["Key"], document_path(cache, relative))
    if download(client, public, "manifest.json", site / "manifest.json", optional=True):
        manifest = read_json(site / "manifest.json")
        if manifest.get("schema_version") != 2 or manifest["history"]["path"] != "history.json" or manifest["ids"]["path"] != "ids.txt":
            raise ValueError("Unsupported storage manifest")
        download(client, public, "history.json", site / "history.json")
        download(client, public, "ids.txt", site / "ids.txt")
        load_history(site, manifest)
        if checksum(site / "ids.txt") != manifest["ids"]["sha256"]:
            raise ValueError("Restored IDs checksum mismatch")
    elif download(client, public, "data/manifest.json", site / "data/manifest.json", optional=True):
        manifest = read_json(site / "data/manifest.json")
        key = manifest["state"]["path"].lstrip("/")
        if not re.fullmatch(r"data/releases/[A-Za-z0-9_-]+/state.json", key):
            raise ValueError("Invalid legacy state path")
        download(client, public, key, document_path(site, key))
        load_history(site, manifest)


def publish(client: Any, bucket: str, site: Path) -> None:
    manifest = read_json(site / "manifest.json")
    for field, name in (("available", "available.json"), ("history", "history.json"), ("ids", "ids.txt")):
        if manifest[field]["path"] != name or checksum(site / name) != manifest[field]["sha256"]:
            raise ValueError("Local publication checksum mismatch")
        if name.endswith(".json") and read_json(site / name)["dataset_version"] != manifest["dataset_version"]:
            raise ValueError("Local publication version mismatch")
    for name in ("available.json", "history.json", "ids.txt"):
        data = (site / name).read_bytes()
        client.put_object(Bucket=bucket, Key=name, Body=data, ContentType="text/plain; charset=utf-8" if name.endswith(".txt") else "application/json", CacheControl="public, max-age=0, must-revalidate")
        if hashlib.sha256(client.get_object(Bucket=bucket, Key=name)["Body"].read()).hexdigest() != hashlib.sha256(data).hexdigest():
            raise ValueError("Uploaded publication checksum mismatch")
    client.put_object(Bucket=bucket, Key="manifest.json", Body=(site / "manifest.json").read_bytes(), ContentType="application/json", CacheControl="public, max-age=0, must-revalidate")
    print(json.dumps({key: manifest[key] for key in ("dataset_version", "count", "history_count")}))


def save(client: Any, bucket: str, cache: Path, run: Path) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run.name):
        raise ValueError("Invalid run ID")
    for directory, prefix in ((cache, "cache"), (run, f"runs/{run.name}")):
        for path in sorted(directory.rglob("*")):
            if path.is_file() and not path.is_symlink():
                client.put_object(Bucket=bucket, Key=f"{prefix}/{path.relative_to(directory).as_posix()}", Body=path.read_bytes())


def fetch(client: Any, bucket: str, run_id: str, target: Path) -> int:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", run_id):
        raise ValueError("Invalid run ID")
    prefix = f"runs/{run_id}/"
    destination = target / run_id
    count = 0
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for item in page.get("Contents", []):
            relative = item["Key"].removeprefix(prefix)
            if relative and not item["Key"].endswith("/"):
                download(client, bucket, item["Key"], document_path(destination, relative))
                count += 1
    if not count:
        raise FileNotFoundError(f"No trace found at {prefix}")
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("restore", "publish", "save", "fetch"))
    parser.add_argument("--site", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--public")
    parser.add_argument("--private")
    parser.add_argument("--run-id")
    parser.add_argument("--target", type=Path)
    args = parser.parse_args()
    client = boto3.client("s3", endpoint_url=os.environ["AWS_ENDPOINT_URL"], region_name="auto")
    if args.action == "restore":
        restore(client, args.public, args.private, args.site, args.cache)
    elif args.action == "publish":
        publish(client, args.public, args.site)
    elif args.action == "fetch":
        count = fetch(client, args.private, args.run_id, args.target)
        print(json.dumps({"run_id": args.run_id, "files": count, "path": str(args.target / args.run_id)}))
    else:
        save(client, args.private, args.cache, args.run)


if __name__ == "__main__":
    main()
