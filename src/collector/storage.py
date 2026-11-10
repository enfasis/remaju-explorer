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


def restore(client: Any, public: str, site: Path) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("restore", "publish"))
    parser.add_argument("--site", type=Path)
    parser.add_argument("--public")
    args = parser.parse_args()
    client = boto3.client("s3", endpoint_url=os.environ["AWS_ENDPOINT_URL"], region_name="auto")
    if args.action == "restore":
        restore(client, args.public, args.site)
    else:
        publish(client, args.public, args.site)


if __name__ == "__main__":
    main()
