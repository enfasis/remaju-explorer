from collections.abc import Callable, Mapping
from dataclasses import dataclass
from urllib.parse import urljoin
from xml.etree import ElementTree

from selectolax.parser import HTMLParser

from .debugger import diagnostic_url

VIEW_STATE = "javax.faces.ViewState"


@dataclass(frozen=True)
class PartialResponse:
    updates: dict[str, str]
    redirect: str | None
    error: str | None

    @property
    def state(self) -> str | None:
        return next((value for key, value in self.updates.items() if VIEW_STATE in key), None)


@dataclass(frozen=True)
class AjaxInteraction:
    name: str
    source: str
    execute: str
    render: str = ""
    event: str = ""
    parameters: tuple[tuple[str, str], ...] = ()
    destination: str = ""

    def payload(self, fields: Mapping[str, str], state: str) -> dict[str, str]:
        if not state or not all((self.name, self.source, self.execute)) or not (self.render or self.destination):
            raise ValueError("Incomplete JSF interaction")
        payload = dict(fields)
        payload.update({
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": self.source,
            "javax.faces.partial.execute": self.execute,
        })
        if self.render:
            payload["javax.faces.partial.render"] = self.render
        if self.event:
            payload["javax.faces.behavior.event"] = self.event
            payload["javax.faces.partial.event"] = self.event
        payload.update(self.parameters)
        payload[VIEW_STATE] = state
        return payload

    def response(self, xml: str) -> PartialResponse:
        result = parse_partial_response(xml)
        if result.error:
            raise ValueError(f"Invalid {self.name} response")
        if self.destination:
            if not result.redirect or urljoin(self.destination, result.redirect) != self.destination:
                target = diagnostic_url(result.redirect) if result.redirect else "(missing)"
                raise ValueError(f"Unexpected {self.name} redirect: {target}")
        elif result.redirect is not None or not any(key in result.updates for key in self.render.split()):
            raise ValueError(f"Invalid {self.name} response")
        return result


@dataclass
class JsfSession:
    fields: dict[str, str]
    state: str

    def perform(self, interaction: AjaxInteraction, send: Callable[[str, dict[str, str]], str]) -> tuple[str, PartialResponse]:
        xml = send(interaction.name, interaction.payload(self.fields, self.state))
        result = interaction.response(xml)
        state = result.state
        if state is not None:
            if not state:
                raise ValueError("JSF ViewState missing")
            self.state = state
        return xml, result


def form_session(html: str, form_id: str) -> JsfSession:
    form = HTMLParser(html).css_first(f'form[id="{form_id}"]')
    if form is None:
        raise ValueError(f"Expected form {form_id} not found")
    fields: dict[str, str] = {}
    for node in form.css("input[name]"):
        name = node.attributes.get("name") or ""
        if name and (node.attributes.get("type") or "").lower() not in {"submit", "button", "image"}:
            fields[name] = node.attributes.get("value") or ""
    state = fields.get(VIEW_STATE)
    if not state:
        raise ValueError("JSF ViewState missing")
    return JsfSession(fields, state)


def parse_partial_response(xml: str) -> PartialResponse:
    if len(xml.encode("utf-8")) > 10 * 1024 * 1024:
        raise ValueError("JSF response exceeds size limit")
    if "<!DOCTYPE" in xml.upper() or "<!ENTITY" in xml.upper():
        raise ValueError("DTD and entity declarations are not allowed")
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as error:
        raise ValueError("Invalid JSF partial response") from error
    if root.tag.rsplit("}", 1)[-1] != "partial-response":
        raise ValueError("Expected JSF partial-response")
    updates = {}
    redirect = None
    error_message = None
    for node in root.iter():
        name = node.tag.rsplit("}", 1)[-1]
        if name == "update":
            key = node.get("id")
            if not key or key in updates:
                raise ValueError("Missing or duplicate update identifier")
            updates[key] = "".join(node.itertext())
        elif name == "redirect":
            redirect = node.get("url")
        elif name == "error":
            error_message = " ".join(text.strip() for text in node.itertext() if text.strip())
    return PartialResponse(updates, redirect, error_message)
