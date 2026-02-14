"""REMAJU auction scraper package."""

from .models import (
    Auction,
    RemateListItem,
    RemateDetail,
    Seguimiento,
    Inmueble,
    CronogramaFase,
    RemateTab,
    InmueblesTab,
    CronogramaTab,
    Expediente,
    SeguimientoData,
)
from .parser import RemajuParser

__all__ = [
    "Auction",
    "RemateListItem",
    "RemateDetail",
    "Seguimiento",
    "Inmueble",
    "CronogramaFase",
    "RemateTab",
    "InmueblesTab",
    "CronogramaTab",
    "Expediente",
    "SeguimientoData",
    "RemajuParser",
]
