import json
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import requests

from .archive import utc_now


def redact(text: str) -> str:
    text = re.sub(r"(?i);jsessionid=[^\s\"'<>?&;]+", ";jsessionid=[redacted]", text)
    text = re.sub(r'(?i)(name=["\']javax\.faces\.ViewState["\'][^>]*value=["\'])[^"\']+', r'\1[redacted]', text)
    text = re.sub(r'(?is)(<update[^>]*id=["\'][^"\']*ViewState[^"\']*["\'][^>]*>\s*<!\[CDATA\[).*?(\]\]>)', r'\1[redacted]\2', text)
    return text


def challenge(body: str) -> bool:
    lowered = body.lower()
    return any(marker in lowered for marker in ("h-captcha", "hcaptcha", "radware", "g-recaptcha", "cf-turnstile", "/cdn-cgi/challenge-platform/"))


def diagnostic_url(url: str) -> str:
    parts = urlsplit(url)
    return redact(urlunsplit((parts.scheme, parts.netloc.rsplit("@", 1)[-1], parts.path, "[redacted]" if parts.query else "", "")))


def diagnostic_error(error: Exception) -> str:
    return redact(re.sub(r'https?://[^\s"\'<>]+', lambda match: diagnostic_url(match.group()), str(error)))


class Trace:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=False)
        self.sequence = 0
        self.last_response: dict[str, Any] | None = None

    def event(self, action: str, state: str, **details: Any) -> None:
        entry = {"timestamp": utc_now(), "action": action, "state": state, **details}
        with (self.directory / "events.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def request(self, session: requests.Session, method: str, url: str, action: str, data: dict[str, str] | None = None) -> str:
        self.sequence += 1
        sequence = self.sequence
        self.last_response = None
        self.event(action, "start", sequence=sequence, method=method, url=diagnostic_url(url), payload_keys=sorted(data or {}))
        started = time.monotonic()
        try:
            response = session.request(method, url, data=data, headers={"Faces-Request": "partial/ajax"} if method == "POST" else {}, timeout=(10, 30), allow_redirects=False)
            body = response.text
            body_file = f"{sequence:06d}-{action}.txt"
            (self.directory / body_file).write_text(redact(body), encoding="utf-8")
            headers = getattr(response, "headers", {})
            self.last_response = {
                "sequence": sequence, "action": action, "method": method,
                "url": diagnostic_url(url), "status": response.status_code,
                "location": diagnostic_url(headers.get("Location", "")),
                "content_type": headers.get("Content-Type", ""),
                "challenge_detected": challenge(body), "body_file": body_file,
            }
            self.event(action, "end", **{key: value for key, value in self.last_response.items() if key != "action"}, elapsed_ms=round((time.monotonic() - started) * 1000))
            response.raise_for_status()
            if 300 <= response.status_code < 400:
                raise ValueError("Unexpected redirect")
            if challenge(body):
                raise ValueError("Source challenge detected")
            return body
        except Exception as error:
            self.event(action, "failed", sequence=sequence, error=type(error).__name__, message=diagnostic_error(error), response=self.last_response, elapsed_ms=round((time.monotonic() - started) * 1000))
            raise
