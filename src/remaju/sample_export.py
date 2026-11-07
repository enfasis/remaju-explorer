import argparse
import json
from pathlib import Path
from typing import Any


def public_detail(auction: dict[str, Any]) -> dict[str, Any]:
    detail = auction.get("detail") or {}
    remate = detail.get("remate_tab") or {}
    keys = ("expediente", "distrito_judicial", "organo_jurisdiccional", "instancia", "materia", "resolucion", "fecha_resolucion", "convocatoria", "tasacion", "precio_base", "incremento_entre_ofertas", "arancel", "oblaje", "descripcion", "nro_inscritos")
    return {
        "numero_remate": auction["numero_remate"],
        "remate": {key: remate.get(key) for key in keys},
        "inmuebles": (detail.get("inmuebles_tab") or {}).get("inmuebles", []),
        "cronograma": (detail.get("cronograma_tab") or {}).get("fases", []),
        "seguimiento": auction.get("seguimiento"),
        "documents": [],
        "source_url": "https://remaju.pj.gob.pe/remaju/pages/publico/remateExterno.xhtml",
    }


def export_sample(source: Path, output: Path) -> int:
    auctions = json.loads(source.read_text())["auctions"]
    snapshot_path = output / "availability.json"
    snapshot = json.loads(snapshot_path.read_text())
    by_id = {str(a["numero_remate"]): a for a in auctions}
    for summary in snapshot["auctions"]:
        auction = by_id[summary["numero_remate"]]
        detail = public_detail(auction)
        summary["descripcion"] = detail["remate"].get("descripcion") or summary["descripcion"]
        properties = detail["inmuebles"]
        summary["coordinates"] = [{"latitude": p["latitude"], "longitude": p["longitude"]} for p in properties if p.get("latitude") is not None and p.get("longitude") is not None]
        summary["thumbnail_path"] = None
        (output / Path(summary["detail_path"]).name).write_text(json.dumps(detail, ensure_ascii=False, indent=2) + "\n")
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n")
    return len(snapshot["auctions"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update an existing partial sample from saved extraction; never publishes a current dataset")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(export_sample(args.source, args.output))
