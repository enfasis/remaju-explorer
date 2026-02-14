"""Test fixtures for REMAJU scraper."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from remaju.parser import RemajuParser


@pytest.fixture
def parser() -> RemajuParser:
    """Create a parser instance."""
    return NewRemajuParser()


@pytest.fixture
def list_xml(sample_data_dir) -> str:
    """Load list page XML."""
    with open(sample_data_dir / "page1_list.xml", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def detail_html(sample_data_dir) -> str:
    """Load detail base HTML."""
    with open(sample_data_dir / "detail_base.html", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def inmuebles_xml(sample_data_dir) -> str:
    """Load inmuebles XML."""
    with open(sample_data_dir / "detail_inmuebles.xml", "r", encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def cronograma_xml(sample_data_dir) -> str:
    """Load cronograma XML."""
    with open(sample_data_dir / "detail_cronograma.xml", "r", encoding="utf-8") as f:
        return f.read()
