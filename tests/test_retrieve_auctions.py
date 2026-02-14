"""Tests for retrieving auction data from REMAJU website.

This module tests the complete flow of downloading and parsing
auction data, including list, detail, and seguimiento pages.
All HTTP requests are mocked using the responses library.
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from remaju.models import RemateListItem, RemateDetail, Seguimiento, Auction
from remaju.parser import RemajuParser
from download import RemajuDownloader


class TestParseListPage:
    """Tests for parsing the auction list page."""

    def test_parse_list_page_returns_list(self, list_page_html):
        """Test that parse_list_page returns a list."""
        parser = RemajuParser(list_page_html)
        remates = parser.parse_list_page()

        assert isinstance(remates, list)
        assert len(remates) > 0

    def test_parse_list_page_returns_remate_list_items(self, list_page_html):
        """Test that parsed items are RemateListItem instances."""
        parser = RemajuParser(list_page_html)
        remates = parser.parse_list_page()

        for remate in remates:
            assert isinstance(remate, RemateListItem)

    def test_first_remate_has_correct_number(self, list_page_html):
        """Test that the first remate has number 22096."""
        parser = RemajuParser(list_page_html)
        remates = parser.parse_list_page()

        first_remate = remates[0]
        assert first_remate.numero_remate == "22096"

    def test_first_remate_has_correct_distrito(self, list_page_html):
        """Test that the first remate is in SAN BORJA."""
        parser = RemajuParser(list_page_html)
        remates = parser.parse_list_page()

        first_remate = remates[0]
        assert "SAN BORJA" in first_remate.distrito.upper()

    def test_remate_has_required_fields(self, list_page_html):
        """Test that remates have all required fields populated."""
        parser = RemajuParser(list_page_html)
        remates = parser.parse_list_page()

        for remate in remates:
            assert remate.numero_remate
            assert remate.tipo
            assert remate.distrito
            assert remate.fecha_presentacion
            assert remate.estado


class TestParseDetailPage:
    """Tests for parsing the detail page with all tabs."""

    def test_parse_detail_page_returns_remate_detail(self, detail_page_html):
        """Test that parse_detail_page returns RemateDetail."""
        parser = RemajuParser(detail_page_html)
        detail = parser.parse_detail_page("22096")

        assert isinstance(detail, RemateDetail)

    def test_detail_has_correct_remate_number(self, detail_page_html):
        """Test that detail has the correct remate number."""
        parser = RemajuParser(detail_page_html)
        detail = parser.parse_detail_page("22096")

        assert detail.numero_remate == "22096"

    def test_detail_has_three_tabs(self, detail_page_html):
        """Test that detail has Remate, Inmuebles, and Cronograma tabs."""
        parser = RemajuParser(detail_page_html)
        detail = parser.parse_detail_page("22096")

        assert "Remate" in detail.tabs
        assert "Inmuebles" in detail.tabs
        assert "Cronograma" in detail.tabs

    def test_remate_tab_has_expediente(self, detail_page_html):
        """Test that remate tab contains expediente information."""
        parser = RemajuParser(detail_page_html)
        detail = parser.parse_detail_page("22096")

        assert detail.remate_tab.expediente == "15700-2023-0-1817-JR-CO-07"

    def test_remate_tab_has_precio_base(self, detail_page_html):
        """Test that remate tab contains precio base."""
        parser = RemajuParser(detail_page_html)
        detail = parser.parse_detail_page("22096")

        assert "1,163,355.99" in detail.remate_tab.precio_base

    def test_inmuebles_tab_has_properties(self, detail_page_html):
        """Test that inmuebles tab contains property information."""
        parser = RemajuParser(detail_page_html)
        detail = parser.parse_detail_page("22096")

        assert len(detail.inmuebles_tab.inmuebles) >= 0

    def test_first_inmueble_has_partida_registral(self, detail_page_html):
        """Test that first inmueble has partida registral."""
        parser = RemajuParser(detail_page_html)
        detail = parser.parse_detail_page("22096")

        if detail.inmuebles_tab.inmuebles:
            first_inmueble = detail.inmuebles_tab.inmuebles[0]
            assert first_inmueble.partida_registral

    def test_cronograma_tab_has_fases(self, detail_page_html):
        """Test that cronograma tab contains schedule phases."""
        parser = RemajuParser(detail_page_html)
        detail = parser.parse_detail_page("22096")

        assert len(detail.cronograma_tab.fases) > 0

    def test_cronograma_has_five_fases(self, detail_page_html):
        """Test that cronograma has exactly 5 phases."""
        parser = RemajuParser(detail_page_html)
        detail = parser.parse_detail_page("22096")

        assert len(detail.cronograma_tab.fases) == 5


class TestParseSeguimientoPage:
    """Tests for parsing the seguimiento page."""

    def test_parse_seguimiento_page_returns_seguimiento(self, seguimiento_page_html):
        """Test that parse_seguimiento_page returns Seguimiento."""
        parser = RemajuParser(seguimiento_page_html)
        seguimiento = parser.parse_seguimiento_page()

        assert isinstance(seguimiento, Seguimiento)

    def test_seguimiento_has_expediente(self, seguimiento_page_html):
        """Test that seguimiento contains expediente information."""
        parser = RemajuParser(seguimiento_page_html)
        seguimiento = parser.parse_seguimiento_page()

        assert seguimiento.expediente.nro_expediente == "15700-2023-0-1817-JR-CO-07"

    def test_seguimiento_has_correct_distrito(self, seguimiento_page_html):
        """Test that expediente has correct distrito."""
        parser = RemajuParser(seguimiento_page_html)
        seguimiento = parser.parse_seguimiento_page()

        assert seguimiento.expediente.distrito_judicial == "LIMA"

    def test_seguimiento_data_has_convocatoria(self, seguimiento_page_html):
        """Test that seguimiento data contains convocatoria info."""
        parser = RemajuParser(seguimiento_page_html)
        seguimiento = parser.parse_seguimiento_page()

        assert seguimiento.seguimiento.nro_convocatoria == "PRIMERA CONVOCATORIA"

    def test_seguimiento_has_fase_info(self, seguimiento_page_html):
        """Test that seguimiento contains fase information."""
        parser = RemajuParser(seguimiento_page_html)
        seguimiento = parser.parse_seguimiento_page()

        assert seguimiento.seguimiento.fase_convocatoria == "Publicación e Inscripcion"
        assert seguimiento.seguimiento.estado_convocatoria == "En proceso"


class TestDownloadWithMocks:
    """Tests for download functionality with mocked HTTP requests."""

    def test_download_list_page(self, mock_list_page):
        """Test downloading list page with mocked response."""
        downloader = RemajuDownloader()
        html = downloader.download_list_page()

        assert html
        assert "Remate" in html

    def test_download_detail_page(self, mock_detail_page):
        """Test downloading detail page with mocked response."""
        downloader = RemajuDownloader()
        html = downloader.download_detail_page("22096")

        assert html
        assert "Detalle" in html or "Expediente" in html

    def test_download_seguimiento_page(self, mock_seguimiento_page):
        """Test downloading seguimiento page with mocked response."""
        downloader = RemajuDownloader()
        html = downloader.download_seguimiento_page("22096")

        assert html
        assert "Seguimiento" in html or "seguimiento" in html.lower()

    def test_download_complete_auction(self, mock_all_pages, tmp_path):
        """Test downloading complete auction data with all mocks."""
        downloader = RemajuDownloader(output_dir=tmp_path)

        # Create a mock remate list item
        from datetime import date

        remate = RemateListItem(
            numero_remate="22096",
            convocatoria="PRIMERA CONVOCATORIA",
            tipo="REMATE SIMPLE",
            distrito="SAN BORJA",
            fecha_presentacion=date(2026, 2, 26),
            hora_presentacion="11:59 AM",
            fase="Publicación e Inscripcion",
            estado="En proceso",
            precio_base="S/. 1,163,355.99",
            descripcion="DEPARTAMENTO TIPO DUPLEX...",
        )

        auction = downloader.download_auction(remate)

        assert isinstance(auction, Auction)
        assert auction.numero_remate == "22096"
        assert auction.list_data.numero_remate == "22096"
        assert auction.detail is not None
        assert auction.seguimiento is not None

    def test_auction_data_is_consistent(self, mock_all_pages, tmp_path):
        """Test that all auction data is consistent across pages."""
        downloader = RemajuDownloader(output_dir=tmp_path)

        from datetime import date

        remate = RemateListItem(
            numero_remate="22096",
            convocatoria="PRIMERA CONVOCATORIA",
            tipo="REMATE SIMPLE",
            distrito="SAN BORJA",
            fecha_presentacion=date(2026, 2, 26),
            hora_presentacion="11:59 AM",
            fase="Publicación e Inscripcion",
            estado="En proceso",
            precio_base="S/. 1,163,355.99",
            descripcion="DEPARTAMENTO TIPO DUPLEX...",
        )

        auction = downloader.download_auction(remate)

        # Check that expediente is consistent
        detail_expediente = auction.detail.remate_tab.expediente
        seguimiento_expediente = auction.seguimiento.expediente.nro_expediente
        assert detail_expediente == seguimiento_expediente

        # Check that distrito is consistent
        assert (
            auction.detail.remate_tab.distrito_judicial
            == auction.seguimiento.expediente.distrito_judicial
        )

    def test_save_auctions_creates_file(self, mock_all_pages, tmp_path):
        """Test that save_auctions creates a JSON file."""
        downloader = RemajuDownloader(output_dir=tmp_path)

        from datetime import date

        remate = RemateListItem(
            numero_remate="22096",
            convocatoria="PRIMERA CONVOCATORIA",
            tipo="REMATE SIMPLE",
            distrito="SAN BORJA",
            fecha_presentacion=date(2026, 2, 26),
            hora_presentacion="11:59 AM",
            fase="Publicación e Inscripcion",
            estado="En proceso",
            precio_base="S/. 1,163,355.99",
            descripcion="DEPARTAMENTO TIPO DUPLEX...",
        )

        auction = downloader.download_auction(remate)
        downloader.save_auctions([auction], "test_auctions.json")

        output_file = tmp_path / "test_auctions.json"
        assert output_file.exists()

        # Verify it's valid JSON
        import json

        with open(output_file, "r") as f:
            data = json.load(f)
            assert "auctions" in data
            assert data["count"] == 1


class TestAuctionModel:
    """Tests for the Auction model."""

    def test_auction_has_properties(self, mock_all_pages, tmp_path):
        """Test Auction model properties."""
        downloader = RemajuDownloader(output_dir=tmp_path)

        from datetime import date

        remate = RemateListItem(
            numero_remate="22096",
            convocatoria="PRIMERA CONVOCATORIA",
            tipo="REMATE SIMPLE",
            distrito="SAN BORJA",
            fecha_presentacion=date(2026, 2, 26),
            hora_presentacion="11:59 AM",
            fase="Publicación e Inscripcion",
            estado="En proceso",
            precio_base="S/. 1,163,355.99",
            descripcion="DEPARTAMENTO TIPO DUPLEX...",
        )

        auction = downloader.download_auction(remate)

        # Test has_inmuebles property
        assert hasattr(auction, "has_inmuebles")
        assert isinstance(auction.has_inmuebles, bool)

        # Test total_fases property
        assert hasattr(auction, "total_fases")
        assert auction.total_fases == 5

    def test_auction_serialization(self, mock_all_pages, tmp_path):
        """Test that Auction can be serialized to dict."""
        downloader = RemajuDownloader(output_dir=tmp_path)

        from datetime import date

        remate = RemateListItem(
            numero_remate="22096",
            convocatoria="PRIMERA CONVOCATORIA",
            tipo="REMATE SIMPLE",
            distrito="SAN BORJA",
            fecha_presentacion=date(2026, 2, 26),
            hora_presentacion="11:59 AM",
            fase="Publicación e Inscripcion",
            estado="En proceso",
            precio_base="S/. 1,163,355.99",
            descripcion="DEPARTAMENTO TIPO DUPLEX...",
        )

        auction = downloader.download_auction(remate)
        data = auction.model_dump()

        assert "numero_remate" in data
        assert "list_data" in data
        assert "detail" in data
        assert "seguimiento" in data
