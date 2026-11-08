from functools import lru_cache
from math import isfinite
from pathlib import Path
from typing import Any

from .archive import read_json


@lru_cache(maxsize=1)
def polygons() -> list[Any]:
    return read_json(Path(__file__).resolve().parents[2] / "shared/peru.json")["coordinates"]


def in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    for a, b in zip(ring, [ring[-1], *ring[:-1]]):
        ax, ay = a[:2]
        bx, by = b[:2]
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if abs(cross) < 1e-10 and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by):
            return True
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


def in_peru(latitude: Any, longitude: Any) -> bool:
    if isinstance(latitude, bool) or isinstance(longitude, bool) or not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return False
    if not isfinite(latitude) or not isfinite(longitude) or not -19 <= latitude <= 1 or not -82 <= longitude <= -68:
        return False
    return any(in_ring(longitude, latitude, polygon[0]) and not any(in_ring(longitude, latitude, hole) for hole in polygon[1:]) for polygon in polygons())


def clean_coordinates(auction: dict[str, Any]) -> None:
    for item in (auction.get("detail", {}).get("inmuebles_tab", {}).get("inmuebles") or []):
        if not in_peru(item.get("latitude"), item.get("longitude")):
            item["latitude"] = None
            item["longitude"] = None
