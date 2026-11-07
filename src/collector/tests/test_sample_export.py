from utils.publication import summary
from utils.sample_export import current_status, public_detail


def auction() -> dict:
    return {
        "numero_remate": "123",
        "list_data": {},
        "detail": {
            "remate_tab": {"expediente": "case", "descripcion": "text", "precio_base": "$ 10", "archivo": "Inicio", "juez": "name", "exchange_rate": 0.3},
            "inmuebles_tab": {"departamento": "ICA", "provincia": "CHINCHA", "distrito": "", "inmuebles": [{"direccion": "address", "latitude": None}]},
            "cronograma_tab": {"fases": [{"fase": "Ofertas"}]},
        },
        "seguimiento": {"eventos": [
            {"fase_convocatoria": "Publicación", "estado_convocatoria": "Desierto"},
            {"fase_convocatoria": "Publicación e Inscripcion", "estado_convocatoria": "En proceso"},
        ]},
    }


def test_public_detail_preserves_curated_sections_without_session_fields() -> None:
    result = public_detail(auction())
    assert result["remate"]["precio_base"] == "$ 10"
    assert "archivo" not in result["remate"]
    assert "juez" not in result["remate"]
    assert "documents" not in result
    assert result["ubicacion"] == {"departamento": "ICA", "provincia": "CHINCHA", "distrito": None}
    assert result["inmuebles"][0]["direccion"] == "address"
    assert result["cronograma"][0]["fase"] == "Ofertas"


def test_status_comes_from_latest_tracking_event() -> None:
    assert current_status(auction()["seguimiento"]) == {"fase": "Publicación e Inscripcion", "estado": "En proceso"}
    assert current_status(None) == {"fase": None, "estado": None}
    assert public_detail(auction())["estado"]["estado"] == "En proceso"


def test_summary_falls_back_to_tracking_status() -> None:
    result = summary(auction())
    assert result["fase"] == "Publicación e Inscripcion"
    assert result["estado"] == "En proceso"


def test_summary_carries_schedule_for_current_phase() -> None:
    result = summary(auction())
    assert result["cronograma"] == [{"nro": None, "fase": "Ofertas", "fecha_inicio": None, "fecha_fin": None}]
