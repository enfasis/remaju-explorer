import json
import re
import time
from pathlib import Path
from typing import Any

import requests

from .archive import utc_now


def redact(text: str) -> str:
    text = re.sub(r"(?i);jsessionid=[^\s\"'<>?&;]+", ";jsessionid=[redacted]", text)
    text = re.sub(r'(?i)(name=["\']javax\.faces\.ViewState["\'][^>]*value=["\'])[^"\']+', r'\1[redacted]', text)
    text = re.sub(r'(?is)(<update[^>]*id=["\'][^"\']*ViewState[^"\']*["\'][^>]*>\s*<!\[CDATA\[).*?(\]\]>)', r'\1[redacted]\2', text)
    return text


def challenge(body: str) -> bool:
    lowered = body.lower()
    return "h-captcha" in lowered or "hcaptcha" in lowered or "radware" in lowered


class Trace:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=False)
        self.sequence = 0

    def event(self, action: str, state: str, **details: Any) -> None:
        entry = {"timestamp": utc_now(), "action": action, "state": state, **details}
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def request(self, session: requests.Session, method: str, url: str, action: str, data: dict[str, str] | None = None) -> str:
        self.sequence += 1
        sequence = self.sequence
        self.event(action, "start", sequence=sequence, method=method, url=redact(url), payload_keys=sorted(data or {}))
        started = time.monotonic()
        try:
            response = session.request(method, url, data=data, headers={"Faces-Request": "partial/ajax"} if method == "POST" else {}, timeout=(10, 30), allow_redirects=False)
            body = response.text
            (self.directory / f"{sequence:06d}-{action}.txt").write_text(redact(body), encoding="utf-8")
            self.event(action, "end", sequence=sequence, status=response.status_code, elapsed_ms=round((time.monotonic() - started) * 1000))
            response.raise_for_status()
            if 300 <= response.status_code < 400:
                raise ValueError("Unexpected redirect")
            if challenge(body):
                raise ValueError("Source challenge detected")
            return body
        except Exception as error:
            self.event(action, "failed", sequence=sequence, error=type(error).__name__, elapsed_ms=round((time.monotonic() - started) * 1000))
            raise
