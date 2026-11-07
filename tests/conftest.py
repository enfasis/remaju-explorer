from pathlib import Path

import pytest

from remaju.parser import RemajuParser


@pytest.fixture
def sample_data_dir() -> Path:
    return Path(__file__).parent.parent / "test_data"


@pytest.fixture
def parser() -> RemajuParser:
    return RemajuParser()


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
