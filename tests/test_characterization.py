from datetime import date, datetime


def test_list_fixture_known_identifiers_and_prices(parser, list_xml):
    auctions = parser.parse_list_xml(list_xml)
    assert [item.numero_remate for item in auctions] == ["22096", "22095", "22094", "22093"]
    assert auctions[0].precio_base == "S/. 1,163,355.99"
    assert auctions[0].fecha_presentacion == date(2026, 2, 26)
    assert auctions[0].hora_presentacion == "11:59 AM"


def test_detail_fixture_known_auction_values(parser, detail_html):
    detail = parser.parse_detail_html(detail_html, "22096")
    assert detail.remate_tab.expediente == "15700-2023-0-1817-JR-CO-07"
    assert detail.remate_tab.fecha_resolucion == date(2025, 4, 21)
    assert detail.remate_tab.precio_base == "S/. 1,163,355.99"
    assert detail.remate_tab.tasacion == "S/. 1,745,033.98"


def test_property_and_schedule_fixtures(parser, inmuebles_xml, cronograma_xml):
    properties = parser.parse_inmuebles_xml(inmuebles_xml)
    schedule = parser.parse_cronograma_xml(cronograma_xml)
    assert len(properties.inmuebles) == 1
    assert properties.inmuebles[0].partida_registral == "12714204"
    assert properties.inmuebles[0].tipo_inmueble == "DEPARTAMENTO"
    assert len(schedule.fases) == 5
    assert schedule.fases[2].fase == "Presentación de Ofertas"
    assert schedule.fases[2].fecha_fin == datetime(2026, 2, 27, 11, 59, 59)
