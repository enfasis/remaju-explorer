from io import BytesIO

import pytest
from botocore.exceptions import ClientError

from storage import download, fetch, publish, restore
from utils.archive import write_json
from utils.publication import checksum


class Client:
    def __init__(self):
        self.objects = {}
        self.uploaded = []
        self.fail_key = None

    def get_object(self, Bucket, Key):
        if (Bucket, Key) not in self.objects:
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        return {"Body": BytesIO(self.objects[Bucket, Key])}

    def put_object(self, Bucket, Key, Body, **kwargs):
        if Key == self.fail_key:
            raise OSError("upload failed")
        self.objects[Bucket, Key] = Body
        self.uploaded.append(Key)

    def get_paginator(self, name):
        return self

    def paginate(self, Bucket, Prefix):
        return [{"Contents": [{"Key": key} for bucket, key in self.objects if bucket == Bucket and key.startswith(Prefix)]}]


def publication(root):
    root.mkdir()
    write_json(root / "available.json", {"dataset_version": "v1", "auctions": []})
    write_json(root / "history.json", {"dataset_version": "v1", "records": {}})
    (root / "ids.txt").write_text("")
    manifest = {"schema_version": 2, "dataset_version": "v1", "count": 0, "history_count": 0}
    for field, filename in (("available", "available.json"), ("history", "history.json"), ("ids", "ids.txt")):
        manifest[field] = {"path": filename, "sha256": checksum(root / filename)}
    write_json(root / "manifest.json", manifest)


def test_manifest_is_uploaded_last_and_restored_with_checksums(tmp_path):
    source = tmp_path / "source"
    publication(source)
    client = Client()
    publish(client, "public", source)
    assert client.uploaded == ["available.json", "history.json", "ids.txt", "manifest.json"]
    restore(client, "public", "private", tmp_path / "site", tmp_path / "cache")
    assert (tmp_path / "site/history.json").read_bytes() == (source / "history.json").read_bytes()


def test_upload_failure_does_not_advance_manifest(tmp_path):
    source = tmp_path / "source"
    publication(source)
    client = Client()
    client.objects["public", "manifest.json"] = b"previous"
    client.fail_key = "history.json"
    with pytest.raises(OSError):
        publish(client, "public", source)
    assert client.objects["public", "manifest.json"] == b"previous"


def test_optional_download_does_not_hide_permission_errors(tmp_path):
    class Denied(Client):
        def get_object(self, **kwargs):
            raise ClientError({"Error": {"Code": "AccessDenied"}}, "GetObject")
    with pytest.raises(ClientError):
        download(Denied(), "public", "manifest.json", tmp_path / "manifest.json", optional=True)


def test_restore_rejects_cache_path_traversal(tmp_path):
    client = Client()
    client.objects["private", "cache/../../escape"] = b"data"
    with pytest.raises(ValueError, match="Invalid manifest file path"):
        restore(client, "public", "private", tmp_path / "site", tmp_path / "cache")


def test_fetch_downloads_a_run_trace(tmp_path):
    client = Client()
    client.objects["private", "runs/20261110T1/events.jsonl"] = b"{}"
    client.objects["private", "runs/20261110T1/responses/000008.txt"] = b"body"
    client.objects["private", "runs/20261110T10/run.json"] = b"other"
    assert fetch(client, "private", "20261110T1", tmp_path) == 2
    assert (tmp_path / "20261110T1/responses/000008.txt").read_bytes() == b"body"
    assert not (tmp_path / "20261110T10").exists()


def test_fetch_rejects_invalid_run_ids_and_traversal(tmp_path):
    client = Client()
    with pytest.raises(ValueError, match="Invalid run ID"):
        fetch(client, "private", "../cache", tmp_path)
    client.objects["private", "runs/x/../../../escape"] = b"data"
    with pytest.raises(ValueError, match="Invalid manifest file path"):
        fetch(client, "private", "x", tmp_path)


def test_fetch_fails_when_the_run_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        fetch(Client(), "private", "missing", tmp_path)
