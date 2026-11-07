from remaju.sample_export import public_detail


def test_public_detail_preserves_tabs_without_session_fields() -> None:
    auction = {
        "numero_remate": "123",
        "detail": {
            "remate_tab": {"expediente": "case", "descripcion": "text", "precio_base": "$ 10", "archivo": "Inicio", "juez": "name", "exchange_rate": 0.3},
            "inmuebles_tab": {"inmuebles": [{"direccion": "address", "latitude": None}]},
            "cronograma_tab": {"fases": [{"fase": "Ofertas"}]},
        },
        "seguimiento": {"eventos": []},
    }
    result = public_detail(auction)
    assert result["remate"]["precio_base"] == "$ 10"
    assert "archivo" not in result["remate"]
    assert "juez" not in result["remate"]
    assert result["inmuebles"][0]["direccion"] == "address"
    assert result["cronograma"][0]["fase"] == "Ofertas"
    assert result["documents"] == []
