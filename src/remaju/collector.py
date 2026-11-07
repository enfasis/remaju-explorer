import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from selectolax.parser import HTMLParser

from .archive import utc_now, write_json
from .jsf import parse_partial_response
from .parser import RemajuParser


LIST_URL = "https://remaju.pj.gob.pe/remaju/pages/publico/remateExterno.xhtml"
LIST_ID = "formBuscarRemateExterno:listaRemate"


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


def initial_state(html: str) -> tuple[str, dict[str, str]]:
    tree = HTMLParser(html)
    form = tree.css_first('form[id="formBuscarRemateExterno"]')
    if form is None:
        raise ValueError("Expected source form not found")
    fields: dict[str, str] = {}
    for node in form.css("input[name]"):
        name = node.attributes.get("name", "")
        if name and node.attributes.get("type", "").lower() not in {"submit", "button", "image"}:
            fields[name] = node.attributes.get("value", "")
    state = fields.get("javax.faces.ViewState")
    if not state:
        raise ValueError("JSF ViewState missing")
    return state, fields


def collect_sample(output: Path) -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    trace = Trace(output / run_id)
    report: dict[str, Any] = {"run_id": run_id, "mode": "sample", "status": "failed", "publishable": False, "started_at": utc_now()}
    try:
        with requests.Session() as session:
            html = trace.request(session, "GET", LIST_URL, "list-init")
            state, fields = initial_state(html)
            fields.update({"javax.faces.partial.ajax": "true", "javax.faces.source": LIST_ID, "javax.faces.partial.execute": LIST_ID, "javax.faces.partial.render": LIST_ID, "javax.faces.behavior.event": "page", "javax.faces.partial.event": "page", f"{LIST_ID}_pagination": "true", f"{LIST_ID}_first": "0", f"{LIST_ID}_rows": "4", "javax.faces.ViewState": state})
            xml = trace.request(session, "POST", LIST_URL, "list-page", fields)
            partial = parse_partial_response(xml)
            if partial.error or LIST_ID not in partial.updates:
                raise ValueError("Invalid listing response")
            parser = RemajuParser()
            cards = parser.extract_card_info(xml)
            if not cards:
                raise ValueError("No recognizable auction cards")
            report.update({"status": "partial", "count": len(cards), "cards": cards, "warnings": ["Sample only; source scope and detail coverage are unverified."]})
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        report["finished_at"] = utc_now()
        write_json(trace.directory / "run.json", report)
    return report
