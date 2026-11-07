from dataclasses import dataclass
from datetime import date, datetime

from pydantic import BaseModel


class Inmueble(BaseModel):
    partida_registral: str
    tipo_inmueble: str
    direccion: str
    carga_gravamen: str | None = None
    porcentaje_a_remstar: str
    imagenes: int
    latitude: float | None = None
    longitude: float | None = None
    area_m2: float | None = None


class CronogramaFase(BaseModel):
    nro: int
    fase: str
    fecha_inicio: datetime
    fecha_fin: datetime


class RemateTab(BaseModel):
    expediente: str
    distrito_judicial: str
    organo_jurisdiccional: str
    instancia: str
    juez: str
    especialista: str
    materia: str
    resolucion: str
    fecha_resolucion: date
    archivo: str | None = None
    convocatoria: str
    tasacion: str
    precio_base: str
    incremento_entre_ofertas: str
    arancel: str
    oblaje: str
    descripcion: str
    nro_inscritos: int
    precio_base_pen: float | None = None
    precio_base_usd: float | None = None
    arancel_pen: float | None = None
    arancel_usd: float | None = None
    oblaje_pen: float | None = None
    oblaje_usd: float | None = None
    exchange_rate: float | None = None
    exchange_rate_date: date | None = None


class InmueblesTab(BaseModel):
    distrito_judicial: str
    departamento: str
    provincia: str
    distrito: str
    inmuebles: list[Inmueble]


class CronogramaTab(BaseModel):
    fases: list[CronogramaFase]


class RemateDetail(BaseModel):
    numero_remate: str
    url: str
    tabs: list[str]
    remate_tab: RemateTab
    inmuebles_tab: InmueblesTab
    cronograma_tab: CronogramaTab


class Expediente(BaseModel):
    nro_expediente: str
    distrito_judicial: str
    especialidad: str
    instancia: str
    organo_jurisdiccional: str


class SeguimientoEvento(BaseModel):
    nro_convocatoria: str
    fecha_registro: date
    procesado_por: str
    reanudado: str
    fase_convocatoria: str
    estado_convocatoria: str
    fecha_desierto: date | None = None


class Seguimiento(BaseModel):
    expediente: Expediente
    eventos: list[SeguimientoEvento]


class RemateListItem(BaseModel):
    numero_remate: str
    convocatoria: str
    tipo: str
    distrito: str
    fecha_presentacion: date
    hora_presentacion: str
    fase: str
    estado: str
    precio_base: str | None = None
    descripcion: str


class Auction(BaseModel):
    numero_remate: str
    list_data: RemateListItem
    detail: RemateDetail
    seguimiento: Seguimiento | None = None


@dataclass(frozen=True)
class Card:
    listing: RemateListItem
    detail_id: str
    tracking_id: str | None
