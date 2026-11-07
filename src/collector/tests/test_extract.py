from datetime import date, datetime

from models import CronogramaFase, Inmueble, RemateListItem
from utils import extract


def test_listing_fixture_known_identifiers_and_prices(list_xml):
    auctions = extract.listing(list_xml)
    assert [item.numero_remate for item in auctions] == ["22096", "22095", "22094", "22093"]
    assert all(isinstance(item, RemateListItem) and item.tipo and item.estado for item in auctions)
    assert auctions[0].precio_base == "S/. 1,163,355.99"
    assert auctions[0].fecha_presentacion == date(2026, 2, 26)
    assert auctions[0].hora_presentacion == "11:59 AM"


def test_card_actions_capture_dynamic_button_ids(list_xml):
    actions = extract.card_actions(list_xml)
    assert len(actions) == 4
    for action in actions:
        assert action["remate_index"] is not None
        assert action["numero_remate"].isdigit()
        assert "j_idt169" in action["detalle_id"]
        assert "j_idt168" in action["seguimiento_id"]


def test_cards_join_listing_with_actions(list_xml):
    cards = extract.cards(list_xml)
    assert [card.listing.numero_remate for card in cards] == ["22096", "22095", "22094", "22093"]
    assert cards[0].detail_id == "formBuscarRemateExterno:listaRemate:0:j_idt169"
    assert cards[0].tracking_id == "formBuscarRemateExterno:listaRemate:0:j_idt168"


def test_advertised_total_and_return_button(list_html, detail_html):
    assert extract.advertised_total(list_html) == 197
    assert extract.button_id(detail_html, "formDetalleRemate", "Regresar") == "formDetalleRemate:j_idt171"


def test_remate_tab_fixture_known_values(detail_html):
    tab = extract.remate_tab(detail_html)
    assert tab.expediente == "15700-2023-0-1817-JR-CO-07"
    assert tab.fecha_resolucion == date(2025, 4, 21)
    assert tab.precio_base == "S/. 1,163,355.99"
    assert tab.tasacion == "S/. 1,745,033.98"


def test_property_and_schedule_fixtures(inmuebles_xml, cronograma_xml):
    properties = extract.inmuebles_tab(inmuebles_xml)
    schedule = extract.cronograma_tab(cronograma_xml)
    assert len(properties.inmuebles) == 1
    assert isinstance(properties.inmuebles[0], Inmueble)
    assert properties.inmuebles[0].partida_registral == "12714204"
    assert properties.inmuebles[0].tipo_inmueble == "DEPARTAMENTO"
    assert properties.inmuebles[0].direccion
    assert len(schedule.fases) == 5
    assert all(isinstance(fase, CronogramaFase) and fase.nro > 0 for fase in schedule.fases)
    assert schedule.fases[2].fase == "Presentación de Ofertas"
    assert schedule.fases[2].fecha_fin == datetime(2026, 2, 27, 11, 59, 59)


def test_detail_combines_all_tabs(detail_html, inmuebles_xml, cronograma_xml):
    detail = extract.detail("22096", detail_html, inmuebles_xml, cronograma_xml)
    assert detail.numero_remate == "22096"
    assert detail.tabs == ["Remate", "Inmuebles", "Cronograma"]
    assert detail.remate_tab == extract.remate_tab(detail_html)
    assert detail.inmuebles_tab == extract.inmuebles_tab(inmuebles_xml)
    assert detail.cronograma_tab == extract.cronograma_tab(cronograma_xml)


def test_area_converts_hectares():
    assert extract.parse_area("TERRENO DE 1,250.50 M2") == 1250.5
    assert extract.parse_area("FUNDO DE 2 HA") == 20000
    assert extract.parse_area("SIN AREA") is None
