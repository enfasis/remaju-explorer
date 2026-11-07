from dataclasses import dataclass
from collections.abc import Callable, Mapping
from xml.etree import ElementTree


@dataclass(frozen=True)
class PartialResponse:
    updates: dict[str, str]
    redirect: str | None
    error: str | None


@dataclass(frozen=True)
class AjaxInteraction:
    name: str
    source: str
    execute: str
    render: str
    event: str
    parameters: tuple[tuple[str, str], ...] = ()

    def payload(self, fields: Mapping[str, str], state: str) -> dict[str, str]:
        if not state or not all((self.name, self.source, self.execute, self.render, self.event)):
            raise ValueError("Incomplete JSF interaction")
        payload = dict(fields)
        payload.update({
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": self.source,
            "javax.faces.partial.execute": self.execute,
            "javax.faces.partial.render": self.render,
            "javax.faces.behavior.event": self.event,
            "javax.faces.partial.event": self.event,
        })
        payload.update(self.parameters)
        payload["javax.faces.ViewState"] = state
        return payload

    def response(self, xml: str) -> PartialResponse:
        result = parse_partial_response(xml)
        if result.error or result.redirect is not None or self.render not in result.updates:
            raise ValueError(f"Invalid {self.name} response")
        return result


@dataclass
class JsfSession:
    fields: dict[str, str]
    state: str

    def perform(self, interaction: AjaxInteraction, send: Callable[[str, dict[str, str]], str]) -> tuple[str, PartialResponse]:
        xml = send(interaction.name, interaction.payload(self.fields, self.state))
        result = interaction.response(xml)
        state = result.updates.get("javax.faces.ViewState")
        if state is not None:
            if not state:
                raise ValueError("JSF ViewState missing")
            self.state = state
        return xml, result


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
