from dataclasses import dataclass
from xml.etree import ElementTree


@dataclass(frozen=True)
class PartialResponse:
    updates: dict[str, str]
    redirect: str | None
    error: str | None


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
