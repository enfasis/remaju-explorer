from pathlib import Path
from typing import Any

from .jsf import parse_partial_response
from .parser import RemajuParser


def replay(capture_dir: Path) -> dict[str, Any]:
    parser = RemajuParser()
    list_file = capture_dir / "page1_list.xml"
    xml = list_file.read_text(encoding="utf-8")
    response = parse_partial_response(xml)
    component = "formBuscarRemateExterno:listaRemate"
    if component not in response.updates:
        raise ValueError("Expected listing update is missing")
    auctions = parser.parse_list_xml(xml)
    cards = parser.extract_card_info(xml)
    if len(auctions) != len(cards) or not auctions:
        raise ValueError("List items and card actions do not match")
    return {
        "mode": "replay", "status": "partial", "publishable": False,
        "warnings": ["Legacy parser may fabricate missing values; output is for characterization only."],
        "count": len(auctions), "auctions": [auction.model_dump(mode="json") for auction in auctions],
        "cards": cards,
    }
