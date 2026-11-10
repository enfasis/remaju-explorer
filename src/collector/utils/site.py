import random
import time
from collections.abc import Callable
from dataclasses import dataclass

import requests

from models import Card

from .debugger import Trace
from .extract import LIST_ID, TABS_ID, advertised_total, button_id, cards
from .jsf import AjaxInteraction, JsfSession, form_session

BASE_URL = "https://remaju.pj.gob.pe/remaju/pages/publico"
LIST_URL = f"{BASE_URL}/remateExterno.xhtml"
DETAIL_URL = f"{BASE_URL}/mostrarDetalleRemate.xhtml"
TRACKING_URL = f"{BASE_URL}/mostrarSeguimientoRemate.xhtml"
LIST_FORM = "formBuscarRemateExterno"
DETAIL_FORM = "formDetalleRemate"
TRACKING_FORM = "formSeguimiento"
ROWS = 4


@dataclass(frozen=True)
class Tab:
    name: str
    panel: str
    index: str


INMUEBLES = Tab("inmuebles", "tbInmuebles", "1")
CRONOGRAMA = Tab("cronograma", "tbCronograma", "2")


def list_page(first: int, rows: int = ROWS) -> AjaxInteraction:
    return AjaxInteraction(
        name="list-page",
        source=LIST_ID,
        execute=LIST_ID,
        render=LIST_ID,
        event="page",
        parameters=((f"{LIST_ID}_pagination", "true"), (f"{LIST_ID}_first", str(first)), (f"{LIST_ID}_rows", str(rows))),
    )


def tab_change(tab: Tab) -> AjaxInteraction:
    panels = ("pgResumenRemate", "pgResumenInmueble", "pgResumenParte", "pgResumenCronograma")
    return AjaxInteraction(
        name=f"detail-{tab.name}",
        source=TABS_ID,
        execute=TABS_ID,
        render=" ".join([*(f"{TABS_ID}:{panel}" for panel in panels), TABS_ID]),
        event="tabChange",
        parameters=(
            (f"{TABS_ID}_contentLoad", "true"),
            (f"{TABS_ID}_newTab", f"{TABS_ID}:{tab.panel}"),
            (f"{TABS_ID}_tabindex", tab.index),
            (f"{TABS_ID}_activeIndex", tab.index),
        ),
    )


def click(name: str, button: str, destination: str, parameters: tuple[tuple[str, str], ...] = ()) -> AjaxInteraction:
    return AjaxInteraction(name=name, source=button, execute="@all", parameters=((button, button), *parameters), destination=destination)


def home_page(html: str) -> bool:
    return "BIENVENIDOS A REM@JU" in html or "formInicio" in html


def detail_page(html: str) -> bool:
    return DETAIL_FORM in html and not home_page(html) and any(label in html for label in ("Expediente", "Distrito Judicial", "Tasaci", "Precio Base"))


def tracking_page(html: str) -> bool:
    return "Detalle de seguimiento" in html and not home_page(html)


def polite_pause() -> None:
    time.sleep(1 + random.uniform(0, 1))


class RemajuSite:
    def __init__(self, trace: Trace, session: requests.Session, pause: Callable[[], None] = polite_pause, rows: int = ROWS):
        self.trace = trace
        self.session = session
        self.pause = pause
        self.rows = rows
        self.first = 0
        self.cards: dict[str, Card] = {}
        self.view = JsfSession({}, "")
        self.exit: tuple[str, AjaxInteraction] | None = None
        self.total: int | None = None

    def open_listing(self) -> None:
        html = self.get(LIST_URL, "list-init")
        self.view = form_session(html, LIST_FORM)
        self.cards = {}
        self.total = advertised_total(html) or self.total

    def list_page(self, first: int) -> str:
        xml = self.post(LIST_URL, list_page(first, self.rows))
        self.first = first
        self.cards = {card.listing.numero_remate: card for card in cards(xml)}
        return xml

    def current_card(self, card: Card) -> Card:
        current = self.cards.get(card.listing.numero_remate)
        if current is None or current.listing != card.listing:
            raise ValueError(f"Listing changed for auction {card.listing.numero_remate}")
        return current

    def open_detail(self, card: Card) -> str:
        current = self.current_card(card)
        self.post(LIST_URL, click("detail-click", current.detail_id, DETAIL_URL))
        html = self.get(DETAIL_URL, "detail-page")
        if not detail_page(html):
            raise ValueError(f"Invalid detail page for auction {card.listing.numero_remate}")
        self.enter(html, DETAIL_FORM, DETAIL_URL, "detail-close")
        return html

    def open_tab(self, tab: Tab) -> str:
        xml = self.post(DETAIL_URL, tab_change(tab))
        self.view.fields[f"{TABS_ID}_activeIndex"] = tab.index
        return xml

    def open_tracking(self, card: Card) -> str:
        current = self.current_card(card)
        if not current.tracking_id:
            raise ValueError(f"Tracking action missing for auction {card.listing.numero_remate}")
        self.post(LIST_URL, click("tracking-click", current.tracking_id, TRACKING_URL))
        html = self.get(TRACKING_URL, "tracking-page")
        if not tracking_page(html):
            raise ValueError(f"Invalid tracking page for auction {card.listing.numero_remate}")
        self.enter(html, TRACKING_FORM, TRACKING_URL, "tracking-close", ((f"{TRACKING_FORM}:dgListaConvocatoria_rppDD", "4"),))
        return html

    def leave(self) -> None:
        if self.exit is None:
            raise ValueError("No page to leave")
        url, interaction = self.exit
        self.post(url, interaction)
        self.exit = None
        self.open_listing()
        self.list_page(self.first)

    def enter(self, html: str, form: str, url: str, name: str, parameters: tuple[tuple[str, str], ...] = ()) -> None:
        button = button_id(html, form, "Regresar")
        if button is None:
            raise ValueError(f"Return button missing in {form}")
        self.view = form_session(html, form)
        self.exit = (url, click(name, button, LIST_URL, parameters))

    def get(self, url: str, action: str) -> str:
        self.pause()
        return self.trace.request(self.session, "GET", url, action)

    def post(self, url: str, interaction: AjaxInteraction) -> str:
        self.pause()
        xml, _ = self.view.perform(interaction, lambda action, data: self.trace.request(self.session, "POST", url, action, data))
        return xml
