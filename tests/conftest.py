"""Test fixtures for REMAJU scraper."""

import json
from pathlib import Path

import pytest
import responses

# Add src to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from remaju.models import RemateListItem, RemateDetail, Seguimiento, Auction
from remaju.parser import RemajuParser


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def list_page_html(fixtures_dir) -> str:
    """Load list page HTML fixture."""
    with open(
        fixtures_dir / "remate_externo_list_page1.html", "r", encoding="utf-8"
    ) as f:
        return f.read()


@pytest.fixture
def detail_page_html(fixtures_dir) -> str:
    """Load detail page HTML fixture."""
    with open(
        fixtures_dir / "detalle_remate_22096_full.html", "r", encoding="utf-8"
    ) as f:
        return f.read()


@pytest.fixture
def seguimiento_page_html(fixtures_dir) -> str:
    """Load seguimiento page HTML fixture."""
    with open(
        fixtures_dir / "seguimiento_remate_22096.html", "r", encoding="utf-8"
    ) as f:
        return f.read()


@pytest.fixture
def mock_responses():
    """Provide responses mock context."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_list_page(mock_responses, list_page_html):
    """Mock the list page URL."""
    mock_responses.add(
        responses.GET,
        "https://remaju.pj.gob.pe/remaju/pages/publico/remateExterno.xhtml",
        body=list_page_html,
        status=200,
        content_type="text/html",
    )
    return mock_responses


@pytest.fixture
def mock_detail_page(mock_responses, detail_page_html):
    """Mock the detail page URL."""
    mock_responses.add(
        responses.GET,
        "https://remaju.pj.gob.pe/remaju/pages/publico/mostrarDetalleRemate.xhtml",
        body=detail_page_html,
        status=200,
        content_type="text/html",
    )
    return mock_responses


@pytest.fixture
def mock_seguimiento_page(mock_responses, seguimiento_page_html):
    """Mock the seguimiento page URL."""
    mock_responses.add(
        responses.GET,
        "https://remaju.pj.gob.pe/remaju/pages/publico/mostrarSeguimientoRemate.xhtml",
        body=seguimiento_page_html,
        status=200,
        content_type="text/html",
    )
    return mock_responses


@pytest.fixture
def mock_all_pages(mock_list_page, mock_detail_page, mock_seguimiento_page):
    """Mock all pages at once."""
    return mock_list_page


@pytest.fixture
def expected_list_data() -> list:
    """Expected list data based on scraped_data.json."""
    return [
        {
            "numero_remate": "22096",
            "convocatoria": "PRIMERA CONVOCATORIA",
            "tipo": "REMATE SIMPLE",
            "distrito": "SAN BORJA",
            "fecha_presentacion": "2026-02-26",
            "hora_presentacion": "11:59 AM",
            "fase": "Publicación e Inscripcion",
            "estado": "En proceso",
            "precio_base": "S/. 1,163,355.99",
            "descripcion": "DEPARTAMENTO TIPO DUPLEX UBICADO EN EL OCTAVO PISO Y AZOTEA DE UN EDIFICIO DE OCHO PISOS CON AZOTEA Y SEMISÓTANO",
        }
    ]


@pytest.fixture
def expected_detail_data() -> dict:
    """Expected detail data based on scraped_data.json."""
    return {
        "numero_remate": "22096",
        "expediente": "15700-2023-0-1817-JR-CO-07",
        "distrito_judicial": "LIMA",
        "organo_jurisdiccional": "7°JUZGADO CIVIL-COMERCIAL",
        "instancia": "JUZGADO ESPECIALIZADO",
        "juez": "VARILLAS SOLANO, JUAN GUSTAVO",
        "especialista": "CACERES CASTILLO EDWARD JESUS",
        "materia": "EJECUCION DE GARANTIAS",
        "resolucion": "6",
        "tasacion": "S/. 1,745,033.98",
        "precio_base": "S/. 1,163,355.99",
        "nro_inscritos": 0,
    }


@pytest.fixture
def expected_seguimiento_data() -> dict:
    """Expected seguimiento data based on scraped_data.json."""
    return {
        "nro_expediente": "15700-2023-0-1817-JR-CO-07",
        "distrito_judicial": "LIMA",
        "especialidad": "COMERCIAL",
        "nro_convocatoria": "PRIMERA CONVOCATORIA",
        "procesado_por": "ORDEN JUDICIAL",
        "reanudado": "NO",
        "fase_convocatoria": "Publicación e Inscripcion",
        "estado_convocatoria": "En proceso",
    }
