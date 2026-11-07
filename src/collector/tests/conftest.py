from pathlib import Path

import pytest


@pytest.fixture
def sample_data_dir() -> Path:
    return Path(__file__).parent / "test_data"


@pytest.fixture
def list_html(sample_data_dir: Path) -> str:
    return (sample_data_dir / "list_page.html").read_text(encoding="utf-8")


@pytest.fixture
def list_xml(sample_data_dir: Path) -> str:
    return (sample_data_dir / "page1_list.xml").read_text(encoding="utf-8")


@pytest.fixture
def detail_html(sample_data_dir: Path) -> str:
    return (sample_data_dir / "detail_base.html").read_text(encoding="utf-8")


@pytest.fixture
def inmuebles_xml(sample_data_dir: Path) -> str:
    return (sample_data_dir / "detail_inmuebles.xml").read_text(encoding="utf-8")


@pytest.fixture
def cronograma_xml(sample_data_dir: Path) -> str:
    return (sample_data_dir / "detail_cronograma.xml").read_text(encoding="utf-8")
