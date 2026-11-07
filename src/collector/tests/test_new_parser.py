"""Tests for the new REMAJU parser using downloaded sample data."""

from remaju.parser import RemajuParser
from remaju.models import (
    RemateListItem,
    RemateDetail,
    RemateTab,
    InmueblesTab,
    CronogramaTab,
    Inmueble,
    CronogramaFase,
)


class TestParseListXML:
    """Tests for parsing list page XML."""

    def test_parse_list_returns_list(self, parser, list_xml):
        """Test that parse_list_xml returns a list."""
        remates = parser.parse_list_xml(list_xml)
        assert isinstance(remates, list)
        assert len(remates) > 0

    def test_parse_list_returns_remate_items(self, parser, list_xml):
        """Test that parsed items are RemateListItem instances."""
        remates = parser.parse_list_xml(list_xml)
        for remate in remates:
            assert isinstance(remate, RemateListItem)

    def test_first_remate_has_number(self, parser, list_xml):
        """Test that the first remate has a number."""
        remates = parser.parse_list_xml(list_xml)
        first_remate = remates[0]
        assert first_remate.numero_remate
        assert first_remate.numero_remate.isdigit()

    def test_remate_has_required_fields(self, parser, list_xml):
        """Test that remates have all required fields."""
        remates = parser.parse_list_xml(list_xml)
        for remate in remates:
            assert remate.numero_remate
            assert remate.tipo
            assert remate.fecha_presentacion
            assert remate.estado


class TestExtractCardInfo:
    """Tests for extracting card info with button IDs."""

    def test_extract_card_info_returns_list(self, parser, list_xml):
        """Test that extract_card_info returns a list."""
        cards = parser.extract_card_info(list_xml)
        assert isinstance(cards, list)
        assert len(cards) > 0

    def test_card_has_remate_index(self, parser, list_xml):
        """Test that cards have remate index."""
        cards = parser.extract_card_info(list_xml)
        for card in cards:
            assert card["remate_index"] is not None

    def test_card_has_button_ids(self, parser, list_xml):
        """Test that cards have button IDs."""
        cards = parser.extract_card_info(list_xml)
        for card in cards:
            assert card["detalle_id"]
            assert card["seguimiento_id"]
            assert "j_idt168" in card["seguimiento_id"]
            assert "j_idt169" in card["detalle_id"]

    def test_card_has_remate_number(self, parser, list_xml):
        """Test that cards have remate number."""
        cards = parser.extract_card_info(list_xml)
        for card in cards:
            assert card["numero_remate"]
            assert card["numero_remate"].isdigit()


class TestParseDetailHTML:
    """Tests for parsing detail base HTML."""

    def test_parse_detail_returns_remate_detail(self, parser, detail_html):
        """Test that parse_detail_html returns RemateDetail."""
        detail = parser.parse_detail_html(detail_html, "22096")
        assert isinstance(detail, RemateDetail)

    def test_detail_has_correct_remate_number(self, parser, detail_html):
        """Test that detail has the correct remate number."""
        detail = parser.parse_detail_html(detail_html, "22096")
        assert detail.numero_remate == "22096"

    def test_detail_has_three_tabs(self, parser, detail_html):
        """Test that detail has three tabs."""
        detail = parser.parse_detail_html(detail_html, "22096")
        assert len(detail.tabs) == 3
        assert "Remate" in detail.tabs
        assert "Inmuebles" in detail.tabs
        assert "Cronograma" in detail.tabs

    def test_remate_tab_has_expediente(self, parser, detail_html):
        """Test that remate tab contains expediente."""
        detail = parser.parse_detail_html(detail_html, "22096")
        assert detail.remate_tab.expediente

    def test_remate_tab_has_precio_base(self, parser, detail_html):
        """Test that remate tab contains precio base."""
        detail = parser.parse_detail_html(detail_html, "22096")
        assert detail.remate_tab.precio_base
        assert "S/." in detail.remate_tab.precio_base


class TestParseInmueblesXML:
    """Tests for parsing inmuebles tab XML."""

    def test_parse_inmuebles_returns_inmuebles_tab(self, parser, inmuebles_xml):
        """Test that parse_inmuebles_xml returns InmueblesTab."""
        tab = parser.parse_inmuebles_xml(inmuebles_xml)
        assert isinstance(tab, InmueblesTab)

    def test_inmuebles_tab_has_list(self, parser, inmuebles_xml):
        """Test that inmuebles tab has inmuebles list."""
        tab = parser.parse_inmuebles_xml(inmuebles_xml)
        assert isinstance(tab.inmuebles, list)

    def test_inmueble_has_required_fields(self, parser, inmuebles_xml):
        """Test that inmuebles have required fields."""
        tab = parser.parse_inmuebles_xml(inmuebles_xml)
        for inmueble in tab.inmuebles:
            assert isinstance(inmueble, Inmueble)
            assert inmueble.partida_registral
            assert inmueble.tipo_inmueble
            assert inmueble.direccion


class TestParseCronogramaXML:
    """Tests for parsing cronograma tab XML."""

    def test_parse_cronograma_returns_cronograma_tab(self, parser, cronograma_xml):
        """Test that parse_cronograma_xml returns CronogramaTab."""
        tab = parser.parse_cronograma_xml(cronograma_xml)
        assert isinstance(tab, CronogramaTab)

    def test_cronograma_has_fases(self, parser, cronograma_xml):
        """Test that cronograma tab has fases."""
        tab = parser.parse_cronograma_xml(cronograma_xml)
        assert isinstance(tab.fases, list)

    def test_fase_has_required_fields(self, parser, cronograma_xml):
        """Test that fases have required fields."""
        tab = parser.parse_cronograma_xml(cronograma_xml)
        for fase in tab.fases:
            assert isinstance(fase, CronogramaFase)
            assert fase.nro > 0
            assert fase.fase
            assert fase.fecha_inicio
            assert fase.fecha_fin


class TestMergeDetailData:
    """Tests for merging detail data from different tabs."""

    def test_merge_combines_all_tabs(
        self, parser, detail_html, inmuebles_xml, cronograma_xml
    ):
        """Test that merge combines all tab data."""
        base_detail = parser.parse_detail_html(detail_html, "22096")
        inmuebles_tab = parser.parse_inmuebles_xml(inmuebles_xml)
        cronograma_tab = parser.parse_cronograma_xml(cronograma_xml)

        merged = parser.merge_detail_data(base_detail, inmuebles_tab, cronograma_tab)

        assert merged.remate_tab == base_detail.remate_tab
        assert merged.inmuebles_tab == inmuebles_tab
        assert merged.cronograma_tab == cronograma_tab
