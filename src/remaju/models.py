"""Pydantic models for REMAJU auction data."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class Inmueble(BaseModel):
    """Property/Inmueble model."""

    partida_registral: str
    tipo_inmueble: str
    direccion: str
    carga_gravamen: Optional[str] = None
    porcentaje_a_remstar: str
    imagenes: int
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    area_m2: Optional[float] = None


class CronogramaFase(BaseModel):
    """Schedule phase model."""

    nro: int
    fase: str
    fecha_inicio: datetime
    fecha_fin: datetime


class RemateTab(BaseModel):
    """Remate tab data model."""

    expediente: str
    distrito_judicial: str
    organo_jurisdiccional: str
    instancia: str
    juez: str
    especialista: str
    materia: str
    resolucion: str
    fecha_resolucion: date
    archivo: Optional[str] = None
    convocatoria: str
    tasacion: str
    precio_base: str
    incremento_entre_ofertas: str
    arancel: str
    oblaje: str
    descripcion: str
    nro_inscritos: int
    # Computed values (both currencies for optimization)
    precio_base_pen: Optional[float] = None
    precio_base_usd: Optional[float] = None
    arancel_pen: Optional[float] = None
    arancel_usd: Optional[float] = None
    oblaje_pen: Optional[float] = None
    oblaje_usd: Optional[float] = None
    exchange_rate: Optional[float] = None  # Rate used for conversion
    exchange_rate_date: Optional[date] = None  # Date of exchange rate


class InmueblesTab(BaseModel):
    """Inmuebles tab data model."""

    distrito_judicial: str
    departamento: str
    provincia: str
    distrito: str
    inmuebles: List[Inmueble]


class CronogramaTab(BaseModel):
    """Cronograma tab data model."""

    fases: List[CronogramaFase]


class RemateDetail(BaseModel):
    """Complete detail model with all tabs."""

    numero_remate: str
    url: str
    tabs: List[str]
    remate_tab: RemateTab
    inmuebles_tab: InmueblesTab
    cronograma_tab: CronogramaTab


class Expediente(BaseModel):
    """Expediente model for seguimiento."""

    nro_expediente: str
    distrito_judicial: str
    especialidad: str
    instancia: str
    organo_jurisdiccional: str


class SeguimientoData(BaseModel):
    """Seguimiento data model."""

    nro_convocatoria: str
    fecha_registro: date
    procesado_por: str
    reanudado: str
    fase_convocatoria: str
    estado_convocatoria: str


class Seguimiento(BaseModel):
    """Complete seguimiento model."""

    url: str
    expediente: Expediente
    seguimiento: SeguimientoData


class RemateListItem(BaseModel):
    """Remate item from list page."""

    numero_remate: str
    convocatoria: str
    tipo: str
    distrito: str
    fecha_presentacion: date
    hora_presentacion: str
    fase: str
    estado: str
    precio_base: Optional[str] = None
    descripcion: str


class Auction(BaseModel):
    """Complete auction model combining list, detail and seguimiento."""

    numero_remate: str
    list_data: RemateListItem
    detail: RemateDetail
    seguimiento: Optional[Seguimiento] = None

    @property
    def has_inmuebles(self) -> bool:
        """Check if auction has properties."""
        return len(self.detail.inmuebles_tab.inmuebles) > 0

    @property
    def total_fases(self) -> int:
        """Get total number of phases."""
        return len(self.detail.cronograma_tab.fases)
