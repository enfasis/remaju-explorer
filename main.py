"""Streamlit app for visualizing REMAJU auction data with map and currency support."""

import json
from datetime import datetime
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

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
        if fecha_inicio.date() <= now.date() <= fecha_fin.date():
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


def get_price_for_display(row, use_usd, field_prefix="precio_base"):
    """Get formatted price for display."""
    if use_usd:
        price = row.get(f"{field_prefix}_usd")
        if price:
            return f"${price:,.2f}"
    else:
        price = row.get(f"{field_prefix}_pen")
        if price:
            return f"S/. {price:,.2f}"

    # Fallback to original text
    price = row.get(field_prefix, "N/A")
    if price and price != "N/A":
        return price
    return "N/A"


def get_price_value(row, field_prefix="precio_base"):
    """Get numeric price value in PEN."""
    return row.get(f"{field_prefix}_pen") or 0


def compute_color(price):
    if price >= PRICE_THRESHOLD_RED:
        return [255, 0, 0]
    ratio = price / PRICE_THRESHOLD_RED if price > 0 else 0
    red = int(255 * ratio)
    green = int(255 * (1 - ratio))
    return [red, green, 0]


def get_location_info(auction):
    """Extract location info from auction data with fallbacks."""
    detail = auction.get("detail", {})
    inmuebles_tab = detail.get("inmuebles_tab", {})
    list_data = auction.get("list_data", {})

    # Priority: inmuebles_tab > inmueble > list_data
    departamento = inmuebles_tab.get("departamento", "")
    provincia = inmuebles_tab.get("provincia", "")
    distrito = inmuebles_tab.get("distrito", "")

    # Try to get from first inmueble if tab is empty
    inmuebles = inmuebles_tab.get("inmuebles", [])
    if inmuebles:
        inmueble = inmuebles[0]
        if not departamento:
            departamento = inmueble.get("departamento", "")
        if not provincia:
            provincia = inmueble.get("provincia", "")
        if not distrito:
            distrito = inmueble.get("distrito", "")

    # Fallback to list_data distrito
    if not distrito:
        distrito = list_data.get("distrito", "")

    return departamento, provincia, distrito


def prepare_data(auctions):
    """Prepare data for display."""
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

        # Get location info with fallbacks
        depto, prov, dist = get_location_info(auction)

        if inmuebles:
            # Create a row for each inmueble
            for inmueble in inmuebles:
                # Use inmueble-specific location if available, otherwise use auction-level
                row_depto = inmueble.get("departamento") or depto
                row_prov = inmueble.get("provincia") or prov
                row_dist = inmueble.get("distrito") or dist

                row = {
                    "numero_remate": auction.get("numero_remate"),
                    "expediente": remate_tab.get("expediente", ""),
                    "precio_base": remate_tab.get("precio_base", ""),
                    "precio_base_pen": remate_tab.get("precio_base_pen"),
                    "precio_base_usd": remate_tab.get("precio_base_usd"),
                    "arancel": remate_tab.get("arancel", ""),
                    "arancel_pen": remate_tab.get("arancel_pen"),
                    "arancel_usd": remate_tab.get("arancel_usd"),
                    "oblaje": remate_tab.get("oblaje", ""),
                    "oblaje_pen": remate_tab.get("oblaje_pen"),
                    "oblaje_usd": remate_tab.get("oblaje_usd"),
                    "descripcion": remate_tab.get("descripcion", ""),
                    "nro_inscritos": remate_tab.get("nro_inscritos", 0),
                    "departamento": row_depto,
                    "provincia": row_prov,
                    "distrito": row_dist,
                    "direccion": inmueble.get("direccion", ""),
                    "tipo_inmueble": inmueble.get("tipo_inmueble", ""),
                    "partida_registral": inmueble.get("partida_registral", ""),
                    "latitude": inmueble.get("latitude"),
                    "longitude": inmueble.get("longitude"),
                    "area_m2": inmueble.get("area_m2"),
                    "fase_actual": current_fase,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    # Keep reference to full auction data
                    "_auction": auction,
                }
                row["price_value"] = get_price_value(row)
                row["color"] = compute_color(row["price_value"])
                rows.append(row)
        else:
            # Create a row for auctions without inmuebles (empty data)
            row = {
                "numero_remate": auction.get("numero_remate"),
                "expediente": remate_tab.get("expediente", ""),
                "precio_base": remate_tab.get("precio_base", ""),
                "precio_base_pen": remate_tab.get("precio_base_pen"),
                "precio_base_usd": remate_tab.get("precio_base_usd"),
                "arancel": remate_tab.get("arancel", ""),
                "arancel_pen": remate_tab.get("arancel_pen"),
                "arancel_usd": remate_tab.get("arancel_usd"),
                "oblaje": remate_tab.get("oblaje", ""),
                "oblaje_pen": remate_tab.get("oblaje_pen"),
                "oblaje_usd": remate_tab.get("oblaje_usd"),
                "descripcion": remate_tab.get("descripcion", ""),
                "nro_inscritos": remate_tab.get("nro_inscritos", 0),
                "departamento": depto,
                "provincia": prov,
                "distrito": dist,
                "direccion": "",
                "tipo_inmueble": "",
                "partida_registral": "",
                "latitude": None,
                "longitude": None,
                "area_m2": None,
                "fase_actual": current_fase,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                # Keep reference to full auction data
                "_auction": auction,
            }
            row["price_value"] = get_price_value(row)
            row["color"] = compute_color(row["price_value"])
            rows.append(row)
    return pd.DataFrame(rows)


def apply_filters(
    df,
    depto_filter,
    prov_filter,
    dist_filter,
    fase_filter,
    price_range,
    date_range,
):
    """Apply all filters to dataframe."""
    filtered_df = df.copy()

    if depto_filter and depto_filter != "Todos":
        filtered_df = filtered_df[filtered_df["departamento"] == depto_filter]

    if prov_filter and prov_filter != "Todos":
        filtered_df = filtered_df[filtered_df["provincia"] == prov_filter]

    if dist_filter and dist_filter != "Todos":
        filtered_df = filtered_df[filtered_df["distrito"] == dist_filter]

    if fase_filter and fase_filter != "Todas":
        filtered_df = filtered_df[filtered_df["fase_actual"] == fase_filter]

    if price_range:
        filtered_df = filtered_df[
            (filtered_df["price_value"] >= price_range[0])
            & (filtered_df["price_value"] <= price_range[1])
        ]

    if date_range and len(date_range) == 2:
        # Handle None values in fecha_inicio/fecha_fin
        mask = pd.Series([True] * len(filtered_df), index=filtered_df.index)

        # Get valid date ranges
        valid_dates = (
            filtered_df["fecha_inicio"].notna() & filtered_df["fecha_fin"].notna()
        )

        # Apply date filter only to rows with valid dates
        if valid_dates.any():
            date_mask = (
                filtered_df.loc[valid_dates, "fecha_inicio"].dt.date <= date_range[1]
            ) & (filtered_df.loc[valid_dates, "fecha_fin"].dt.date >= date_range[0])
            # Keep rows without dates (they pass the filter) or rows that match the date filter
            mask = ~valid_dates | date_mask.reindex(filtered_df.index, fill_value=False)

        filtered_df = filtered_df[mask]

    return filtered_df


def render_filters(df):
    """Render filter controls and return filter values."""
    st.sidebar.header("🔍 Filtros")

    # Currency toggle
    use_usd = st.sidebar.toggle("💵 Mostrar en USD", value=False)

    # Department filter
    deptos = ["Todos"] + sorted(
        [d for d in df["departamento"].dropna().unique().tolist() if d]
    )
    depto_filter = st.sidebar.selectbox("Departamento", deptos)

    # Province filter (depends on department)
    if depto_filter != "Todos":
        provs = ["Todos"] + sorted(
            df[df["departamento"] == depto_filter]["provincia"]
            .dropna()
            .unique()
            .tolist()
        )
    else:
        provs = ["Todos"] + sorted(
            [p for p in df["provincia"].dropna().unique().tolist() if p]
        )
    prov_filter = st.sidebar.selectbox("Provincia", provs)

    # District filter (depends on province)
    if prov_filter != "Todos":
        dists = ["Todos"] + sorted(
            df[df["provincia"] == prov_filter]["distrito"].dropna().unique().tolist()
        )
    elif depto_filter != "Todos":
        dists = ["Todos"] + sorted(
            df[df["departamento"] == depto_filter]["distrito"]
            .dropna()
            .unique()
            .tolist()
        )
    else:
        dists = ["Todos"] + sorted(
            [d for d in df["distrito"].dropna().unique().tolist() if d]
        )
    dist_filter = st.sidebar.selectbox("Distrito", dists)

    # Phase filter
    fases = ["Todas"] + sorted(df["fase_actual"].dropna().unique().tolist())
    fase_filter = st.sidebar.selectbox("Fase", fases)

    # Price range
    min_price = int(df["price_value"].min()) if not df.empty else 0
    max_price = int(df["price_value"].max()) if not df.empty else 2000000
    if max_price <= min_price:
        max_price = min_price + 100000
    price_range = st.sidebar.slider(
        "Rango de precio (PEN)",
        min_price,
        max_price,
        (min_price, max_price),
        step=50000,
    )

    # Date range
    if df["fecha_inicio"].notna().any():
        min_date = df["fecha_inicio"].min().date()
        max_date = df["fecha_fin"].max().date()
        date_range = st.sidebar.date_input("Rango de fechas", [min_date, max_date])
    else:
        date_range = None

    return (
        use_usd,
        depto_filter,
        prov_filter,
        dist_filter,
        fase_filter,
        price_range,
        date_range,
    )


def make_map_link(row):
    """Create Google Maps link for coordinates."""
    if pd.notna(row["latitude"]) and pd.notna(row["longitude"]):
        lat, lon = row["latitude"], row["longitude"]
        url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        return f"[🗺️]({url})"
    return ""


def render_table_view(filtered_df, use_usd):
    """Render full table view with all columns."""
    st.subheader("📋 Lista Completa de Inmuebles")

    if filtered_df.empty:
        st.info("No hay inmuebles que coincidan con los filtros")
        return

    # Prepare display columns
    display_df = filtered_df.copy()
    display_df["mapa"] = display_df.apply(make_map_link, axis=1)
    display_df["precio"] = display_df.apply(
        lambda row: get_price_for_display(row, use_usd), axis=1
    )
    display_df["arancel_fmt"] = display_df.apply(
        lambda row: get_price_for_display(row, use_usd, "arancel"), axis=1
    )
    display_df["oblaje_fmt"] = display_df.apply(
        lambda row: get_price_for_display(row, use_usd, "oblaje"), axis=1
    )

    # Select columns for display
    cols = [
        "mapa",
        "numero_remate",
        "expediente",
        "tipo_inmueble",
        "departamento",
        "provincia",
        "distrito",
        "direccion",
        "precio",
        "arancel_fmt",
        "oblaje_fmt",
        "area_m2",
        "fase_actual",
        "nro_inscritos",
    ]

    # Only include columns that exist
    available_cols = [c for c in cols if c in display_df.columns]

    st.write(f"Mostrando {len(display_df)} inmueble(s)")
    st.dataframe(
        display_df[available_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "mapa": st.column_config.LinkColumn("Mapa", width="small"),
            "numero_remate": st.column_config.TextColumn("Remate", width="small"),
            "expediente": st.column_config.TextColumn("Expediente", width="medium"),
            "tipo_inmueble": st.column_config.TextColumn("Tipo", width="small"),
            "departamento": st.column_config.TextColumn("Departamento", width="small"),
            "provincia": st.column_config.TextColumn("Provincia", width="small"),
            "distrito": st.column_config.TextColumn("Distrito", width="small"),
            "direccion": st.column_config.TextColumn("Dirección", width="large"),
            "precio": st.column_config.TextColumn("Precio Base", width="small"),
            "arancel_fmt": st.column_config.TextColumn("Arancel", width="small"),
            "oblaje_fmt": st.column_config.TextColumn("Oblaje", width="small"),
            "area_m2": st.column_config.NumberColumn("Área m²", width="small"),
            "fase_actual": st.column_config.TextColumn("Fase", width="medium"),
            "nro_inscritos": st.column_config.NumberColumn("Inscritos", width="small"),
        },
    )


def render_folium_map(map_df):
    """Render map using folium with color-coded markers."""
    if map_df.empty:
        return

    # Calculate center
    center_lat = map_df["latitude"].mean()
    center_lon = map_df["longitude"].mean()

    # Create map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=5)

    # Convert RGB list to hex color
    def rgb_to_hex(color_list):
        if isinstance(color_list, list) and len(color_list) == 3:
            return "#{:02x}{:02x}{:02x}".format(*color_list)
        return "#ff0000"

    # Add markers
    for _, row in map_df.iterrows():
        color_hex = rgb_to_hex(row.get("color", [255, 0, 0]))
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=8,
            popup=folium.Popup(
                f"<b>Remate:</b> {row['numero_remate']}<br>"
                f"<b>Precio:</b> S/. {row['price_value']:,.0f}",
                max_width=200,
            ),
            color=color_hex,
            fill=True,
            fillColor=color_hex,
            fillOpacity=0.7,
        ).add_to(m)

    # Fit bounds to show all markers
    if len(map_df) > 1:
        sw = map_df[["latitude", "longitude"]].min().values.tolist()
        ne = map_df[["latitude", "longitude"]].max().values.tolist()
        m.fit_bounds([sw, ne])

    st_folium(m, width="100%", height=500)


def render_map_table_view(filtered_df, use_usd):
    """Render map + table view (side by side)."""
    col_map, col_table = st.columns([1, 1])

    with col_map:
        st.subheader("📍 Mapa")
        map_df = filtered_df.dropna(subset=["latitude", "longitude"])

        if not map_df.empty:
            render_folium_map(map_df)
            st.write(f"{len(map_df)} propiedades con coordenadas")
        else:
            st.info("No hay coordenadas disponibles")

    with col_table:
        st.subheader("📋 Inmuebles")

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
                "provincia",
                "distrito",
                "precio",
                "fase_actual",
            ]
            available_cols = [c for c in display_cols if c in display_df.columns]

            st.dataframe(
                display_df[available_cols],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "mapa": st.column_config.LinkColumn("Mapa", width="small"),
                    "numero_remate": st.column_config.TextColumn(
                        "Remate", width="small"
                    ),
                    "tipo_inmueble": st.column_config.TextColumn("Tipo", width="small"),
                    "departamento": st.column_config.TextColumn(
                        "Departamento", width="small"
                    ),
                    "provincia": st.column_config.TextColumn(
                        "Provincia", width="small"
                    ),
                    "distrito": st.column_config.TextColumn("Distrito", width="small"),
                    "precio": st.column_config.TextColumn("Precio", width="small"),
                    "fase_actual": st.column_config.TextColumn("Fase", width="medium"),
                },
            )
        else:
            st.info("No hay inmuebles")


def render_detail_section(filtered_df, use_usd):
    """Render detail section for selected remate."""
    st.divider()

    remate_options = (
        filtered_df["numero_remate"].unique() if not filtered_df.empty else []
    )
    selected_remate = st.selectbox(
        "Selecciona un remate",
        options=remate_options,
        format_func=lambda x: f"Remate N° {x}",
    )

    if not selected_remate:
        return

    st.subheader(f"📄 Detalle del Remate - {selected_remate}")

    remate_data = filtered_df[filtered_df["numero_remate"] == selected_remate].iloc[0]
    auction = remate_data["_auction"]
    detail = auction.get("detail", {})
    remate_tab = detail.get("remate_tab", {})

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Información General**")
        st.write(f"**Remate:** {remate_data['numero_remate']}")
        st.write(f"**Expediente:** {remate_data['expediente']}")
        st.write(f"**Fase:** {remate_data['fase_actual']}")
        st.write(f"**Inscritos:** {remate_data['nro_inscritos']}")
        if remate_tab.get("convocatoria"):
            st.write(f"**Convocatoria:** {remate_tab['convocatoria']}")
        if remate_tab.get("materia"):
            st.write(f"**Materia:** {remate_tab['materia']}")

    with col2:
        st.markdown("**Ubicación**")
        st.write(f"**Dpto:** {remate_data['departamento'] or 'N/A'}")
        st.write(f"**Prov:** {remate_data['provincia'] or 'N/A'}")
        st.write(f"**Dist:** {remate_data['distrito'] or 'N/A'}")
        st.write(f"**Dir:** {remate_data['direccion'][:60]}...")
        st.write(f"**Tipo:** {remate_data['tipo_inmueble']}")

        if remate_data["latitude"] and remate_data["longitude"]:
            lat, lon = remate_data["latitude"], remate_data["longitude"]
            maps_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            streetview_url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"
            st.markdown(f"[🗺️ Google Maps]({maps_url})")
            st.markdown(f"[🚶 Street View]({streetview_url})")

    with col3:
        st.markdown("**Precios**")
        st.write(f"**Base:** {get_price_for_display(remate_data, use_usd)}")
        st.write(
            f"**Arancel:** {get_price_for_display(remate_data, use_usd, 'arancel')}"
        )
        st.write(f"**Oblaje:** {get_price_for_display(remate_data, use_usd, 'oblaje')}")
        st.write(f"**Partida:** {remate_data['partida_registral']}")
        if remate_data.get("area_m2"):
            st.write(f"**Área:** {remate_data['area_m2']:,.2f} m²")

    # Description
    if remate_data["descripcion"]:
        st.markdown("**Descripción**")
        st.write(remate_data["descripcion"])

    # Schedule
    if remate_data["fecha_inicio"] and remate_data["fecha_fin"]:
        st.markdown("**Cronograma**")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.write(
                f"**Inicio:** {remate_data['fecha_inicio'].strftime('%d/%m/%Y %H:%M')}"
            )
        with col_f2:
            st.write(f"**Fin:** {remate_data['fecha_fin'].strftime('%d/%m/%Y %H:%M')}")

    # Detail Map - Show only this auction's location
    if remate_data["latitude"] and remate_data["longitude"]:
        st.divider()
        st.subheader(f"📍 Ubicación del Inmueble - {selected_remate}")

        lat, lon = remate_data["latitude"], remate_data["longitude"]
        m = folium.Map(location=[lat, lon], zoom_start=16)

        # Convert RGB list to hex color
        color_list = remate_data.get("color", [255, 0, 0])
        color_hex = "#{:02x}{:02x}{:02x}".format(*color_list)

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(
                f"<b>Remate:</b> {remate_data['numero_remate']}<br>"
                f"<b>Dirección:</b> {remate_data['direccion'][:80]}...<br>"
                f"<b>Precio:</b> S/. {remate_data['price_value']:,.0f}",
                max_width=250,
            ),
            tooltip="Ver detalles",
            icon=folium.Icon(color="red", icon="home", prefix="fa"),
        ).add_to(m)

        # Add a circle around the marker
        folium.Circle(
            location=[lat, lon],
            radius=100,
            popup="Área aproximada",
            color=color_hex,
            fill=True,
            fill_color=color_hex,
            fill_opacity=0.2,
        ).add_to(m)

        st_folium(m, width="100%", height=400)


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

    # Render filters in sidebar
    filters = render_filters(df)
    use_usd = filters[0]

    # Apply filters
    filtered_df = apply_filters(
        df, filters[1], filters[2], filters[3], filters[4], filters[5], filters[6]
    )

    # View selector
    st.sidebar.divider()
    view_mode = st.sidebar.radio(
        "Vista", ["📋 Tabla completa", "🗺️ Mapa + Tabla"], index=0
    )

    # Legend for colors
    st.sidebar.divider()
    st.sidebar.markdown("**🎨 Leyenda de precios:**")
    st.sidebar.markdown(
        "<span style='color: #00ff00'>■</span> Precio bajo", unsafe_allow_html=True
    )
    st.sidebar.markdown(
        "<span style='color: #ffff00'>■</span> Precio medio", unsafe_allow_html=True
    )
    st.sidebar.markdown(
        f"<span style='color: #ff0000'>■</span> Precio alto (> S/. {PRICE_THRESHOLD_RED:,.0f})",
        unsafe_allow_html=True,
    )

    # Main content
    if view_mode == "📋 Tabla completa":
        render_table_view(filtered_df, use_usd)
    else:
        render_map_table_view(filtered_df, use_usd)

    # Detail section
    render_detail_section(filtered_df, use_usd)


if __name__ == "__main__":
    main()
