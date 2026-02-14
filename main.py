"""Streamlit app for visualizing REMAJU auction data with map and currency support."""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="REMAJU - Mapa de Remates", page_icon="🏛️", layout="wide")

PRICE_THRESHOLD_RED = 1500000


def load_auctions():
    data_file = Path("data/auctions.json")
    if not data_file.exists():
        return []
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("auctions", [])


def get_current_fase(fases):
    now = datetime.now()
    for fase in fases:
        fecha_inicio = datetime.fromisoformat(
            fase["fecha_inicio"].replace("Z", "").replace("+00:00", "")
        )
        fecha_fin = datetime.fromisoformat(
            fase["fecha_fin"].replace("Z", "").replace("+00:00", "")
        )
        if fecha_inicio <= now <= fecha_fin:
            return fase["fase"]
    return "Finalizado"


def get_fase_dates(fases):
    if not fases:
        return None, None
    fecha_inicio = datetime.fromisoformat(
        fases[0]["fecha_inicio"].replace("Z", "").replace("+00:00", "")
    )
    fecha_fin = datetime.fromisoformat(
        fases[-1]["fecha_fin"].replace("Z", "").replace("+00:00", "")
    )
    return fecha_inicio, fecha_fin


def parse_hour(hour_str):
    if not hour_str:
        return None
    try:
        hour_str = hour_str.replace("AM", "").replace("PM", "").strip()
        parts = hour_str.split(":")
        return int(parts[0])
    except:
        return None


def get_price_for_display(row, use_usd):
    if use_usd:
        price = row.get("precio_base_usd")
        if price:
            return f"${price:,.2f}"
    else:
        price = row.get("precio_base_pen")
        if price:
            return f"S/. {price:,.2f}"
    return row.get("precio_base", "N/A")


def get_price_value(row):
    return row.get("precio_base_pen") or 0


def compute_color(price):
    if price >= PRICE_THRESHOLD_RED:
        return [255, 0, 0]
    ratio = price / PRICE_THRESHOLD_RED if price > 0 else 0
    red = int(255 * ratio)
    green = int(255 * (1 - ratio))
    return [red, green, 0]


def prepare_data(auctions):
    rows = []
    for auction in auctions:
        detail = auction.get("detail", {})
        inmuebles_tab = detail.get("inmuebles_tab", {})
        cronograma_tab = detail.get("cronograma_tab", {})
        remate_tab = detail.get("remate_tab", {})
        inmuebles = inmuebles_tab.get("inmuebles", [])
        fases = cronograma_tab.get("fases", [])
        current_fase = get_current_fase(fases)
        fecha_inicio, fecha_fin = get_fase_dates(fases)

        for inmueble in inmuebles:
            row = {
                "numero_remate": auction.get("numero_remate"),
                "expediente": remate_tab.get("expediente", ""),
                "precio_base": remate_tab.get("precio_base", ""),
                "precio_base_pen": remate_tab.get("precio_base_pen"),
                "precio_base_usd": remate_tab.get("precio_base_usd"),
                "arancel": remate_tab.get("arancel", ""),
                "oblaje": remate_tab.get("oblaje", ""),
                "descripcion": remate_tab.get("descripcion", ""),
                "nro_inscritos": remate_tab.get("nro_inscritos", 0),
                "departamento": inmuebles_tab.get("departamento", ""),
                "provincia": inmuebles_tab.get("provincia", ""),
                "distrito": inmuebles_tab.get("distrito", ""),
                "direccion": inmueble.get("direccion", ""),
                "tipo_inmueble": inmueble.get("tipo_inmueble", ""),
                "partida_registral": inmueble.get("partida_registral", ""),
                "latitude": inmueble.get("latitude"),
                "longitude": inmueble.get("longitude"),
                "fase_actual": current_fase,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "hora_inicio": fecha_inicio.hour if fecha_inicio else 0,
                "hora_fin": fecha_fin.hour if fecha_fin else 23,
            }
            row["price_value"] = get_price_value(row)
            row["color"] = compute_color(row["price_value"])
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    st.title("🏛️ REMAJU - Mapa de Remates Judiciales")

    auctions = load_auctions()
    if not auctions:
        st.error("No hay datos de remates. Ejecuta: make download")
        return

    df = prepare_data(auctions)
    if df.empty:
        st.error("No hay inmuebles con datos")
        return

    # Currency toggle at top
    col_title, col_toggle = st.columns([4, 1])
    with col_toggle:
        use_usd = st.toggle("💵 Mostrar en USD", value=False)
        if use_usd:
            st.caption("Precios en dólares")
        else:
            st.caption("Precios en soles")

    # Filters row 1
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        deptos = ["Todos"] + sorted(df["departamento"].dropna().unique().tolist())
        depto_filter = st.selectbox("Departamento", deptos)

    with col2:
        if depto_filter != "Todos":
            provs = ["Todos"] + sorted(
                df[df["departamento"] == depto_filter]["provincia"]
                .dropna()
                .unique()
                .tolist()
            )
        else:
            provs = ["Todos"] + sorted(df["provincia"].dropna().unique().tolist())
        prov_filter = st.selectbox("Provincia", provs)

    with col3:
        fases = ["Todas"] + sorted(df["fase_actual"].dropna().unique().tolist())
        fase_filter = st.selectbox("Fase", fases)

    with col4:
        min_price = int(df["price_value"].min()) if not df.empty else 0
        max_price = int(df["price_value"].max()) if not df.empty else 2000000
        if max_price <= min_price:
            max_price = min_price + 100000
        price_range = st.slider(
            "Rango de precio (PEN)",
            min_price,
            max_price,
            (min_price, max_price),
            step=50000,
        )

    # Filters row 2
    col5, col6, col7, col8 = st.columns(4)

    with col5:
        if df["fecha_inicio"].notna().any():
            min_date = df["fecha_inicio"].min().date()
            max_date = df["fecha_fin"].max().date()
            date_range = st.date_input("Rango de fechas", [min_date, max_date])
        else:
            date_range = None

    with col6:
        min_hour = int(df["hora_inicio"].min()) if not df.empty else 0
        max_hour = int(df["hora_fin"].max()) if not df.empty else 23
        hour_range = st.slider(
            "Rango de hora", min_hour, max_hour, (min_hour, max_hour)
        )

    # Apply filters
    filtered_df = df.copy()

    if depto_filter != "Todos":
        filtered_df = filtered_df[filtered_df["departamento"] == depto_filter]

    if prov_filter != "Todos":
        filtered_df = filtered_df[filtered_df["provincia"] == prov_filter]

    if fase_filter != "Todas":
        filtered_df = filtered_df[filtered_df["fase_actual"] == fase_filter]

    if price_range:
        filtered_df = filtered_df[
            (filtered_df["price_value"] >= price_range[0])
            & (filtered_df["price_value"] <= price_range[1])
        ]

    if date_range and len(date_range) == 2:
        filtered_df = filtered_df[
            (filtered_df["fecha_inicio"].dt.date <= date_range[1])
            & (filtered_df["fecha_fin"].dt.date >= date_range[0])
        ]

    if hour_range:
        filtered_df = filtered_df[
            (filtered_df["hora_inicio"] >= hour_range[0])
            & (filtered_df["hora_fin"] <= hour_range[1])
        ]

    st.write(f"Mostrando {len(filtered_df)} inmueble(s)")

    # Legend for colors
    st.markdown("**🎨 Leyenda de precios:**")
    col_green, col_yellow, col_red = st.columns(3)
    with col_green:
        st.markdown(
            "<span style='color: #00ff00'>■</span> Precio bajo", unsafe_allow_html=True
        )
    with col_yellow:
        st.markdown(
            "<span style='color: #ffff00'>■</span> Precio medio", unsafe_allow_html=True
        )
    with col_red:
        st.markdown(
            "<span style='color: #ff0000'>■</span> Precio alto (>",
            unsafe_allow_html=True,
        )
        st.markdown(f"S/. {PRICE_THRESHOLD_RED:,.0f})")

    # Layout: Map and Table
    col_map, col_table = st.columns([1, 1])

    with col_map:
        st.subheader("📍 Mapa")
        map_df = filtered_df.dropna(subset=["latitude", "longitude"])

        if not map_df.empty:
            st.map(map_df[["latitude", "longitude", "color"]])
        else:
            st.info("No hay coordenadas disponibles")

    with col_table:
        st.subheader("📋 Inmuebles")

        def make_map_link(row):
            if pd.notna(row["latitude"]) and pd.notna(row["longitude"]):
                lat, lon = row["latitude"], row["longitude"]
                url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                return f"[🗺️]({url})"
            return ""

        if not filtered_df.empty:
            display_df = filtered_df.copy()
            display_df["mapa"] = display_df.apply(make_map_link, axis=1)
            display_df["precio"] = display_df.apply(
                lambda row: get_price_for_display(row, use_usd), axis=1
            )

            display_cols = [
                "mapa",
                "numero_remate",
                "tipo_inmueble",
                "departamento",
                "distrito",
                "precio",
                "fase_actual",
            ]
            available_cols = [c for c in display_cols if c in display_df.columns]

            st.markdown(
                display_df[available_cols].to_markdown(index=False),
                unsafe_allow_html=True,
            )
        else:
            st.info("No hay inmuebles")

    # Detail section
    st.divider()
    st.subheader("📄 Detalle del Remate")

    selected_remate = st.selectbox(
        "Selecciona un remate",
        options=filtered_df["numero_remate"].unique() if not filtered_df.empty else [],
        format_func=lambda x: f"Remate N° {x}",
    )

    if selected_remate:
        remate_data = filtered_df[filtered_df["numero_remate"] == selected_remate].iloc[
            0
        ]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Información General**")
            st.write(f"**Remate:** {remate_data['numero_remate']}")
            st.write(f"**Expediente:** {remate_data['expediente']}")
            st.write(f"**Fase:** {remate_data['fase_actual']}")
            st.write(f"**Inscritos:** {remate_data['nro_inscritos']}")

        with col2:
            st.markdown("**Ubicación**")
            st.write(f"**Dpto:** {remate_data['departamento']}")
            st.write(f"**Prov:** {remate_data['provincia']}")
            st.write(f"**Dist:** {remate_data['distrito']}")
            st.write(f"**Dir:** {remate_data['direccion'][:50]}...")
            st.write(f"**Tipo:** {remate_data['tipo_inmueble']}")

            if remate_data["latitude"] and remate_data["longitude"]:
                lat, lon = remate_data["latitude"], remate_data["longitude"]
                maps_url = (
                    f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
                )
                streetview_url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"
                st.markdown(f"[🗺️ Google Maps]({maps_url})")
                st.markdown(f"[🚶 Street View]({streetview_url})")

        with col3:
            st.markdown("**Precios**")
            st.write(f"**Base:** {get_price_for_display(remate_data, use_usd)}")
            st.write(
                f"**Arancel:** {get_price_for_display({'precio_base': remate_data['arancel'], 'precio_base_pen': remate_data.get('arancel_pen'), 'precio_base_usd': remate_data.get('arancel_usd')}, use_usd)}"
            )
            st.write(
                f"**Oblaje:** {get_price_for_display({'precio_base': remate_data['oblaje'], 'precio_base_pen': remate_data.get('oblaje_pen'), 'precio_base_usd': remate_data.get('oblaje_usd')}, use_usd)}"
            )
            st.write(f"**Partida:** {remate_data['partida_registral']}")

        if remate_data["descripcion"]:
            st.markdown("**Descripción**")
            st.write(remate_data["descripcion"])

        if remate_data["fecha_inicio"] and remate_data["fecha_fin"]:
            st.markdown("**Cronograma**")
            st.write(
                f"**Inicio:** {remate_data['fecha_inicio'].strftime('%d/%m/%Y %H:%M')}"
            )
            st.write(f"**Fin:** {remate_data['fecha_fin'].strftime('%d/%m/%Y %H:%M')}")


if __name__ == "__main__":
    main()
