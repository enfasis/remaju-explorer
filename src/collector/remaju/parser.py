"""New parser for REMAJU data downloaded via AJAX requests."""

import re
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from selectolax.parser import HTMLParser

from .models import (
    RemateListItem,
    RemateDetail,
    RemateTab,
    InmueblesTab,
    CronogramaTab,
    Inmueble,
    CronogramaFase,
    Seguimiento,
)


class RemajuParser:
    """Parser for REMAJU AJAX responses and HTML content."""

    BASE_URL = "https://remaju.pj.gob.pe"
    LIST_URL = f"{BASE_URL}/remaju/pages/publico/remateExterno.xhtml"
    DETAIL_URL = f"{BASE_URL}/remaju/pages/publico/mostrarDetalleRemate.xhtml"

    def __init__(self):
        """Initialize parser."""
        pass

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        return " ".join(text.split())

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string in format DD/MM/YYYY."""
        try:
            return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
        except ValueError, AttributeError:
            return None

    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string."""
        try:
            return datetime.strptime(datetime_str.strip(), "%d/%m/%Y %H:%M:%S %p")
        except ValueError, AttributeError:
            try:
                return datetime.strptime(datetime_str.strip(), "%d/%m/%Y %I:%M:%S %p")
            except ValueError, AttributeError:
                return None

    def _parse_money(self, money_str: str) -> str:
        """Parse and clean money string."""
        if not money_str:
            return ""
        match = re.search(r"S/\.\s*([\d,\.]+)", money_str)
        if match:
            return f"S/. {match.group(1)}"
        return self._clean_text(money_str)

    def _extract_cdata(self, xml: str, element_id: str) -> Optional[str]:
        """Extract CDATA content from XML response."""
        pattern = (
            rf'<update[^>]*id="{re.escape(element_id)}"[^>]*>\s*<!\[CDATA\[(.*?)\]\]>'
        )
        match = re.search(pattern, xml, re.DOTALL)
        if match:
            return match.group(1)
        return None

    def parse_list_xml(self, xml: str) -> List[RemateListItem]:
        """Parse list page XML and extract remate items."""
        remates = []
        seen_remates = set()

        cdata = self._extract_cdata(xml, "formBuscarRemateExterno:listaRemate")
        if not cdata:
            return remates

        tree = HTMLParser(cdata)
        cards = tree.css("div.card.azul")

        for card in cards:
            remate = self._parse_list_card(card)
            if remate and remate.numero_remate not in seen_remates:
                seen_remates.add(remate.numero_remate)
                remates.append(remate)

        return remates

    def _parse_list_card(self, card) -> Optional[RemateListItem]:
        """Parse a single remate card from list."""
        text = self._clean_text(card.text())

        # Extract numero_remate
        match = re.search(r"Remate N°\s*(\d+)", text)
        if not match:
            return None
        numero_remate = match.group(1)

        # Extract convocatoria
        convocatoria_match = re.search(
            r"Remate N°\s*\d+\s*-\s*([A-Z\s]+)(?=\s|$)", text
        )
        convocatoria = convocatoria_match.group(1).strip() if convocatoria_match else ""

        # Extract tipo
        tipo_match = re.search(r"\b(REMATE\s+SIMPLE|REMATE\s+EN\s+MASA)\b", text)
        tipo = tipo_match.group(1) if tipo_match else "REMATE SIMPLE"

        # Extract distrito
        distrito_match = re.search(
            r"fa-map-marker.*?([A-Z][A-Z\sÁÉÍÓÚÑ]+?)(?=Presentación|<|$)",
            text,
        )
        distrito = self._clean_text(distrito_match.group(1)) if distrito_match else ""

        # Extract fecha_presentacion
        fecha_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        fecha_str = fecha_match.group(1) if fecha_match else ""
        fecha_presentacion = self._parse_date(fecha_str) or date.today()

        # Extract hora
        hora_match = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))", text)
        hora_presentacion = hora_match.group(1) if hora_match else ""

        # Extract fase
        fase_match = re.search(
            r"(Publicación\s+e\s+Inscripcion|Validación\s+de\s+Inscripción|Presentación\s+de\s+Ofertas)",
            text,
        )
        fase = fase_match.group(1) if fase_match else "Publicación e Inscripcion"

        # Extract estado
        estado_match = re.search(r"(En\s+proceso|Finalizado|Suspendido)", text)
        estado = estado_match.group(1) if estado_match else "En proceso"

        # Extract precio_base (handles both PEN "S/." and USD "$" currencies)
        precio_match = re.search(r"Precio\s*Base\s*(S/\.|\$)\s*([\d,\.]+)", text)
        if precio_match:
            currency = precio_match.group(1)
            amount = precio_match.group(2)
            precio_base = f"{currency} {amount}"
        else:
            precio_base = None

        # Extract descripcion
        descripcion_match = re.search(
            r"<label>(.+?)</label>",
            str(card.html),
            re.DOTALL,
        )
        descripcion = (
            self._clean_text(descripcion_match.group(1)) if descripcion_match else ""
        )

        return RemateListItem(
            numero_remate=numero_remate,
            convocatoria=convocatoria,
            tipo=tipo,
            distrito=distrito,
            fecha_presentacion=fecha_presentacion,
            hora_presentacion=hora_presentacion,
            fase=fase,
            estado=estado,
            precio_base=precio_base,
            descripcion=descripcion,
        )

    def extract_card_info(self, xml: str) -> List[Dict[str, Any]]:
        """Extract card info including button IDs from list XML.

        Dynamically extracts full button IDs based on button text content.
        Button IDs are dynamic and change between requests.
        """
        cards_info = []

        cdata = self._extract_cdata(xml, "formBuscarRemateExterno:listaRemate")
        if not cdata:
            return cards_info

        tree = HTMLParser(cdata)
        cards = tree.css("div.card.azul")

        for card in cards:
            card_data = {
                "remate_index": None,
                "numero_remate": "",
                "seguimiento_id": None,
                "detalle_id": None,
            }

            buttons = card.css("button")
            for btn in buttons:
                btn_id = btn.attributes.get("id") or ""
                btn_text = btn.text(deep=True) or ""

                if "Detalle" in btn_text:
                    card_data["detalle_id"] = btn_id
                    match = re.search(
                        r"formBuscarRemateExterno:listaRemate:(\d+):j_idt", btn_id
                    )
                    if match:
                        card_data["remate_index"] = match.group(1)
                elif "Seguimiento" in btn_text:
                    card_data["seguimiento_id"] = btn_id

            card_html = str(card.html)
            remate_match = re.search(r"Remate N°\s*(\d+)", card_html)
            if remate_match:
                card_data["numero_remate"] = remate_match.group(1)

            cards_info.append(card_data)

        return cards_info

    def parse_detail_html(self, html: str, numero_remate: str) -> RemateDetail:
        """Parse detail page HTML combining base HTML and tab XMLs."""
        tree = HTMLParser(html)

        remate_tab = self._parse_remate_tab_from_html(tree)
        inmuebles_tab = InmueblesTab(
            distrito_judicial="",
            departamento="",
            provincia="",
            distrito="",
            inmuebles=[],
        )
        cronograma_tab = CronogramaTab(fases=[])

        return RemateDetail(
            numero_remate=numero_remate,
            url=self.DETAIL_URL,
            tabs=["Remate", "Inmuebles", "Cronograma"],
            remate_tab=remate_tab,
            inmuebles_tab=inmuebles_tab,
            cronograma_tab=cronograma_tab,
        )

    def _parse_remate_tab_from_html(self, tree: HTMLParser) -> RemateTab:
        """Parse Remate tab data from HTML."""

        def extract_label_value(label_text: str) -> Optional[str]:
            nodes = tree.css(".text-bold")
            for node in nodes:
                node_text = self._clean_text(node.text())
                if label_text.lower() in node_text.lower():
                    parent = node.parent
                    if not parent:
                        continue
                    children = parent.css("div")
                    for child in children:
                        child_classes = child.attributes.get("class") or ""
                        is_bold = "text-bold" in child_classes
                        child_text = self._clean_text(child.text())
                        if child == node or is_bold:
                            continue
                        if not child_text or child_text == node_text:
                            continue
                        if label_text.lower() in child_text.lower():
                            value_text = child_text.replace(node_text, "").strip()
                            if value_text:
                                return value_text
                            continue
                        return child_text
            return None

        expediente = extract_label_value("Expediente") or ""
        distrito_judicial = extract_label_value("Distrito Judicial") or ""
        organo_jurisdiccional = (
            extract_label_value("Órgano Jurisdiccional")
            or extract_label_value("Organo Jurisdiccional")
            or ""
        )
        instancia = extract_label_value("Instancia") or ""
        juez = extract_label_value("Juez") or ""
        especialista = extract_label_value("Especialista") or ""
        materia = extract_label_value("Materia") or ""
        resolucion = (
            extract_label_value("Resolución") or extract_label_value("Resolucion") or ""
        )
        fecha_res_str = (
            extract_label_value("Fecha Resolución")
            or extract_label_value("Fecha Resolucion")
            or ""
        )
        fecha_resolucion = self._parse_date(fecha_res_str) or date.today()

        archivo_node = tree.css_first('a[href="#"][onclick*="j_idt"]')
        archivo = archivo_node.text() if archivo_node else None

        convocatoria = extract_label_value("Convocatoria") or ""

        tasacion_str = (
            extract_label_value("Tasación") or extract_label_value("Tasacion") or ""
        )
        tasacion = self._parse_money(tasacion_str)

        precio_base_str = extract_label_value("Precio Base") or ""
        precio_base = self._parse_money(precio_base_str)

        incremento_str = extract_label_value("Incremento entre ofertas") or ""
        incremento = self._parse_money(incremento_str)

        arancel_str = extract_label_value("Arancel") or ""
        arancel = self._parse_money(arancel_str)

        oblaje_str = extract_label_value("Oblaje") or ""
        oblaje = self._parse_money(oblaje_str)

        descripcion = (
            extract_label_value("Descripción")
            or extract_label_value("Descripcion")
            or ""
        )

        nro_inscritos_str = (
            extract_label_value("N° inscritos")
            or extract_label_value("Nro inscritos")
            or "0"
        )
        try:
            match = re.search(r"\d+", nro_inscritos_str)
            nro_inscritos = int(match.group()) if match else 0
        except AttributeError, ValueError:
            nro_inscritos = 0

        return RemateTab(
            expediente=expediente,
            distrito_judicial=distrito_judicial,
            organo_jurisdiccional=organo_jurisdiccional,
            instancia=instancia,
            juez=juez,
            especialista=especialista,
            materia=materia,
            resolucion=resolucion,
            fecha_resolucion=fecha_resolucion,
            archivo=archivo,
            convocatoria=convocatoria,
            tasacion=tasacion,
            precio_base=precio_base,
            incremento_entre_ofertas=incremento,
            arancel=arancel,
            oblaje=oblaje,
            descripcion=descripcion,
            nro_inscritos=nro_inscritos,
        )

    def parse_inmuebles_xml(self, xml: str) -> InmueblesTab:
        """Parse inmuebles tab XML."""
        cdata = self._extract_cdata(xml, "formDetalleRemate:tvResumen")
        if not cdata:
            return InmueblesTab(
                distrito_judicial="",
                departamento="",
                provincia="",
                distrito="",
                inmuebles=[],
            )

        tree = HTMLParser(cdata)

        # Parse location info from panelgrid labels
        def extract_label_value(label_text: str) -> str:
            """Extract value from panelgrid label."""
            # Find the bold label div
            for node in tree.css(".text-bold"):
                node_text = self._clean_text(node.text())
                if label_text.lower() in node_text.lower():
                    # Get the parent and find the value div (sibling)
                    parent = node.parent
                    if parent:
                        # The value is in the next sibling div
                        children = parent.css("div")
                        for i, child in enumerate(children):
                            if child == node:
                                # Look for next non-bold sibling
                                for next_child in children[i + 1 :]:
                                    next_classes = (
                                        next_child.attributes.get("class") or ""
                                    )
                                    if "text-bold" not in next_classes:
                                        value = self._clean_text(next_child.text())
                                        if value and value != node_text:
                                            return value
                                break
            return ""

        distrito_judicial = extract_label_value("Distrito Judicial")
        departamento = extract_label_value("Departamento")
        provincia = extract_label_value("Provincia")
        distrito = extract_label_value("Distrito")

        inmuebles = []
        table = tree.css_first('[id*="dtResumenInmueble_data"]')
        if table:
            rows = table.css("tr")
            for row in rows:
                cells = row.css("td")
                if len(cells) >= 6:
                    try:
                        imagenes_text = self._clean_text(cells[5].text())
                        imagenes_match = re.search(r"(\d+)", imagenes_text)
                        imagenes = int(imagenes_match.group(1)) if imagenes_match else 0
                    except ValueError, AttributeError:
                        imagenes = 0

                    direccion = self._clean_text(cells[2].text())
                    area_m2 = self._extract_area_from_text(direccion)

                    # Fallback to inmuebles_tab level location if not found in address
                    inmueble = Inmueble(
                        partida_registral=self._clean_text(cells[0].text()),
                        tipo_inmueble=self._clean_text(cells[1].text()),
                        direccion=direccion,
                        carga_gravamen=self._clean_text(cells[3].text())
                        if len(cells) > 3
                        else None,
                        porcentaje_a_remstar=self._clean_text(cells[4].text())
                        if len(cells) > 4
                        else "",
                        imagenes=imagenes,
                        area_m2=area_m2,
                    )
                    inmuebles.append(inmueble)

        return InmueblesTab(
            distrito_judicial=distrito_judicial,
            departamento=departamento,
            provincia=provincia,
            distrito=distrito,
            inmuebles=inmuebles,
        )

    def parse_cronograma_xml(self, xml: str) -> CronogramaTab:
        """Parse cronograma tab XML."""
        cdata = self._extract_cdata(xml, "formDetalleRemate:tvResumen")
        if not cdata:
            return CronogramaTab(fases=[])

        tree = HTMLParser(cdata)

        fases = []
        table = tree.css_first('[id*="dtCronograma_data"]')
        if table:
            rows = table.css("tr")
            for row in rows:
                cells = row.css("td")
                if len(cells) >= 4:
                    try:
                        nro_text = self._clean_text(cells[0].text())
                        nro = int(nro_text)
                    except ValueError:
                        nro = 0

                    fase = CronogramaFase(
                        nro=nro,
                        fase=self._clean_text(cells[1].text()),
                        fecha_inicio=self._parse_datetime(
                            self._clean_text(cells[2].text())
                        )
                        or datetime.now(),
                        fecha_fin=self._parse_datetime(
                            self._clean_text(cells[3].text())
                        )
                        or datetime.now(),
                    )
                    fases.append(fase)

        return CronogramaTab(fases=fases)

    def _extract_area_from_text(self, text: str) -> Optional[float]:
        """Extract area in m2 from text, converting HA to M2 if needed."""
        if not text:
            return None

        m2_pattern = r"([\d,.]+)\s*M2\b"
        m2_match = re.search(m2_pattern, text, re.IGNORECASE)
        if m2_match:
            try:
                value = m2_match.group(1).replace(",", "")
                return float(value)
            except ValueError:
                pass

        ha_pattern = r"([\d,.]+)\s*HA\b"
        ha_match = re.search(ha_pattern, text, re.IGNORECASE)
        if ha_match:
            try:
                value = ha_match.group(1).replace(",", "")
                return float(value) * 10000
            except ValueError:
                pass

        return None

    def merge_detail_data(
        self,
        base_detail: RemateDetail,
        inmuebles_tab: InmueblesTab,
        cronograma_tab: CronogramaTab,
    ) -> RemateDetail:
        """Merge tab data into base detail."""
        return RemateDetail(
            numero_remate=base_detail.numero_remate,
            url=base_detail.url,
            tabs=base_detail.tabs,
            remate_tab=base_detail.remate_tab,
            inmuebles_tab=inmuebles_tab,
            cronograma_tab=cronograma_tab,
        )

    def parse_seguimiento_html(self, html: str, numero_remate: str) -> "Seguimiento":
        """Parse seguimiento page HTML."""
        from .models import Seguimiento, Expediente, SeguimientoEvento

        tree = HTMLParser(html)

        def extract_label_value_from_card(card, label_text: str) -> str:
            """Extract value from label within a specific card."""
            for node in card.css(".text-bold"):
                node_text = self._clean_text(node.text())
                if label_text.lower() in node_text.lower():
                    parent = node.parent
                    if parent:
                        children = parent.css("div")
                        for i, child in enumerate(children):
                            if child == node:
                                for next_child in children[i + 1 :]:
                                    next_classes = (
                                        next_child.attributes.get("class") or ""
                                    )
                                    if "text-bold" not in next_classes:
                                        value = self._clean_text(next_child.text())
                                        if value and value != node_text:
                                            return value
                                break
            return ""

        def extract_label_value_global(label_text: str) -> str:
            """Extract value from label anywhere in the page."""
            for node in tree.css(".text-bold"):
                node_text = self._clean_text(node.text())
                if label_text.lower() in node_text.lower():
                    parent = node.parent
                    if parent:
                        children = parent.css("div")
                        for i, child in enumerate(children):
                            if child == node:
                                for next_child in children[i + 1 :]:
                                    next_classes = (
                                        next_child.attributes.get("class") or ""
                                    )
                                    if "text-bold" not in next_classes:
                                        value = self._clean_text(next_child.text())
                                        if value and value != node_text:
                                            return value
                                break
            return ""

        # Parse expediente (common for all events)
        nro_expediente = extract_label_value_global("N° Expediente")
        distrito_judicial = extract_label_value_global("Distrito judicial")
        especialidad = extract_label_value_global("Especialidad")
        instancia = extract_label_value_global("Instancia")
        organo_jurisdiccional = extract_label_value_global("Órgano Jurisdiccional")

        # Parse all events from the datagrid
        eventos = []
        datagrid = tree.css_first('[id*="dgListaConvocatoria_content"]')
        if datagrid:
            # Find all event cards (card gris class)
            event_cards = datagrid.css(".card.gris")
            for card in event_cards:
                nro_convocatoria = extract_label_value_from_card(
                    card, "N° Convocatoria"
                )
                fecha_registro_str = extract_label_value_from_card(
                    card, "Fecha de registro"
                )
                procesado_por = extract_label_value_from_card(card, "Procesado por")
                reanudado = extract_label_value_from_card(card, "¿Reanudado?")
                fase_convocatoria = extract_label_value_from_card(
                    card, "Fase convocatoria"
                )
                estado_convocatoria = extract_label_value_from_card(
                    card, "Estado convocatoria"
                )
                fecha_desierto_str = extract_label_value_from_card(
                    card, "Fecha de desierto"
                )

                fecha_registro = self._parse_date(fecha_registro_str) or date.today()
                fecha_desierto = self._parse_date(fecha_desierto_str)

                if nro_convocatoria:  # Only add if we found a convocatoria
                    eventos.append(
                        SeguimientoEvento(
                            nro_convocatoria=nro_convocatoria,
                            fecha_registro=fecha_registro,
                            procesado_por=procesado_por,
                            reanudado=reanudado,
                            fase_convocatoria=fase_convocatoria,
                            estado_convocatoria=estado_convocatoria,
                            fecha_desierto=fecha_desierto,
                        )
                    )

        return Seguimiento(
            expediente=Expediente(
                nro_expediente=nro_expediente,
                distrito_judicial=distrito_judicial,
                especialidad=especialidad,
                instancia=instancia,
                organo_jurisdiccional=organo_jurisdiccional,
            ),
            eventos=eventos,
        )
