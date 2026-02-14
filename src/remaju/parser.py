"""HTML Parser for REMAJU website using selectolax."""

import logging
import re
from datetime import datetime, date
from typing import List, Optional, Dict, Any
from selectolax.parser import HTMLParser, Node

from .models import (
    RemateListItem,
    RemateDetail,
    RemateTab,
    InmueblesTab,
    CronogramaTab,
    Inmueble,
    CronogramaFase,
    Seguimiento,
    Expediente,
    SeguimientoData,
)

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RemajuParser:
    """Parser for REMAJU HTML pages."""

    BASE_URL = "https://remaju.pj.gob.pe"
    LIST_URL = f"{BASE_URL}/remaju/pages/publico/remateExterno.xhtml"
    DETAIL_URL = f"{BASE_URL}/remaju/pages/publico/mostrarDetalleRemate.xhtml"
    SEGUIMIENTO_URL = f"{BASE_URL}/remaju/pages/publico/mostrarSeguimientoRemate.xhtml"

    def __init__(self, html: str):
        """Initialize parser with HTML content."""
        self.tree = HTMLParser(html)
        logger.info(f"Parser initialized with HTML length: {len(html)}")

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        if not text:
            return ""
        return " ".join(text.split())

    def _extract_label_value(self, label_text: str) -> Optional[str]:
        """Extract value following a label in the HTML.

        Structure: <div class="ui-g">
                    <div class="ui-panelgrid-cell text-bold">Label</div>
                    <div class="ui-panelgrid-cell text-justify">Value</div>
                   </div>
        """
        logger.debug(f"Looking for label: '{label_text}'")

        # Find all divs with text-bold class (labels)
        nodes = self.tree.css(".text-bold")
        logger.debug(f"Found {len(nodes)} text-bold nodes")

        for i, node in enumerate(nodes):
            node_text = self._clean_text(node.text())

            # Check if this node matches our label
            if label_text.lower() in node_text.lower():
                logger.debug(f"  Found matching label at node {i}: '{node_text}'")

                # Get the parent (should be .ui-g)
                parent = node.parent
                if not parent:
                    continue

                # Get all children divs of the parent
                children = parent.css("div")
                logger.debug(f"  Parent has {len(children)} child divs")

                # Find the value div (not text-bold, not the label node)
                for child in children:
                    child_classes = child.attributes.get("class") or ""
                    is_bold = "text-bold" in child_classes
                    child_text = self._clean_text(child.text())

                    # Skip if this is the label node or if it's bold
                    if child == node or is_bold:
                        continue

                    # Skip if text is empty or is the label text
                    if not child_text or child_text == node_text:
                        continue

                    # Make sure the text doesn't contain the label
                    if label_text.lower() in child_text.lower():
                        # This might be a concatenated node, try to extract just the value
                        value_text = child_text.replace(node_text, "").strip()
                        if value_text:
                            logger.debug(
                                f"  Extracted value from concatenated: '{value_text}'"
                            )
                            return value_text
                        continue

                    logger.debug(f"  Found value: '{child_text}'")
                    return child_text

        logger.warning(f"  Label '{label_text}' not found or no value")
        return None

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string in format DD/MM/YYYY."""
        try:
            return datetime.strptime(date_str.strip(), "%d/%m/%Y").date()
        except ValueError, AttributeError:
            return None

    def _parse_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Parse datetime string in format DD/MM/YYYY HH:MM:SS AM/PM."""
        try:
            # Handle format like "13/02/2026 00:00:00 AM"
            return datetime.strptime(datetime_str.strip(), "%d/%m/%Y %H:%M:%S %p")
        except ValueError, AttributeError:
            try:
                # Try alternate format
                return datetime.strptime(datetime_str.strip(), "%d/%m/%Y %I:%M:%S %p")
            except ValueError, AttributeError:
                return None

    def _parse_money(self, money_str: str) -> str:
        """Parse and clean money string."""
        if not money_str:
            return ""
        # Extract S/. XX,XXX.XX format
        match = re.search(r"S/\.\s*([\d,\.]+)", money_str)
        if match:
            return f"S/. {match.group(1)}"
        return self._clean_text(money_str)

    def parse_list_page(self) -> List[RemateListItem]:
        """Parse remate list page and return list of remates."""
        logger.info("Parsing list page...")
        remates = []
        seen_remates = set()

        cards = self.tree.css('[id*="listaRemate:"][id*="j_idt"]')
        logger.info(f"Found {len(cards)} remate cards")

        for i, card in enumerate(cards):
            try:
                logger.info(f"Parsing card {i + 1}/{len(cards)}...")
                remate = self._parse_remate_card(card)
                if remate:
                    if remate.numero_remate not in seen_remates:
                        seen_remates.add(remate.numero_remate)
                        logger.info(f"  Parsed remate: {remate.numero_remate}")
                        remates.append(remate)
                    else:
                        logger.info(
                            f"  Skipping duplicate remate: {remate.numero_remate}"
                        )
                else:
                    logger.warning(f"  Failed to parse card {i + 1}")
            except Exception as e:
                logger.error(f"Error parsing remate card {i + 1}: {e}")
                continue

        logger.info(f"Successfully parsed {len(remates)} unique remates")
        return remates

    def _parse_remate_card(self, card: Node) -> Optional[RemateListItem]:
        """Parse a single remate card."""
        text = self._clean_text(card.text())
        logger.debug(f"Card text preview: {text[:200]}...")

        # Extract numero_remate
        match = re.search(r"Remate N°\s*(\d+)", text)
        if not match:
            logger.warning("Could not find numero_remate in card")
            return None
        numero_remate = match.group(1)
        logger.debug(f"Found numero_remate: {numero_remate}")

        # Extract convocatoria
        convocatoria_match = re.search(
            r"Remate N°\s*\d+\s*-\s*([A-Z\s]+)(?=\s|$)", text
        )
        convocatoria = convocatoria_match.group(1).strip() if convocatoria_match else ""

        # Extract tipo
        tipo_match = re.search(r"\b(REMATE\s+SIMPLE|REMATE\s+EN\s+MASA)\b", text)
        tipo = tipo_match.group(1) if tipo_match else "REMATE SIMPLE"

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

        # Extract precio_base
        precio_match = re.search(r"Precio\s*Base\s*S/\.\s*([\d,\.]+)", text)
        precio_base = f"S/. {precio_match.group(1)}" if precio_match else None

        # Extract descripcion (everything after estado/fase until end or next section)
        descripcion_match = re.search(
            r"(?:En\s+proceso|Finalizado|Suspendido|Publicación\s+e\s+Inscripcion)\s+(.+?)(?=Precio\s*Base|$)",
            text,
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

    def parse_detail_page(self, numero_remate: str) -> RemateDetail:
        """Parse detail page and return complete detail."""
        logger.info(f"Parsing detail page for remate {numero_remate}...")

        # Parse Remate tab
        logger.info("Parsing Remate tab...")
        remate_tab = self._parse_remate_tab()

        # Parse Inmuebles tab
        logger.info("Parsing Inmuebles tab...")
        inmuebles_tab = self._parse_inmuebles_tab()

        # Parse Cronograma tab
        logger.info("Parsing Cronograma tab...")
        cronograma_tab = self._parse_cronograma_tab()

        detail = RemateDetail(
            numero_remate=numero_remate,
            url=self.DETAIL_URL,
            tabs=["Remate", "Inmuebles", "Cronograma"],
            remate_tab=remate_tab,
            inmuebles_tab=inmuebles_tab,
            cronograma_tab=cronograma_tab,
        )

        logger.info(
            f"Detail parsed successfully with {len(cronograma_tab.fases)} fases"
        )
        return detail

    def _parse_remate_tab(self) -> RemateTab:
        """Parse Remate tab data."""
        logger.info("Extracting remate tab fields...")

        # Extract all fields using the label-value pairs
        expediente = self._extract_label_value("Expediente") or ""
        distrito_judicial = self._extract_label_value("Distrito Judicial") or ""
        organo_jurisdiccional = (
            self._extract_label_value("Órgano Jurisdiccional")
            or self._extract_label_value("Organo Jurisdiccional")
            or ""
        )
        instancia = self._extract_label_value("Instancia") or ""
        juez = self._extract_label_value("Juez") or ""
        especialista = self._extract_label_value("Especialista") or ""
        materia = self._extract_label_value("Materia") or ""

        resolucion = (
            self._extract_label_value("Resolución")
            or self._extract_label_value("Resolucion")
            or ""
        )
        fecha_res_str = (
            self._extract_label_value("Fecha Resolución")
            or self._extract_label_value("Fecha Resolucion")
            or ""
        )
        fecha_resolucion = self._parse_date(fecha_res_str) or date.today()

        # Check for archivo PDF
        archivo_node = self.tree.css_first('a[href="#"][onclick*="j_idt70"]')
        archivo = archivo_node.text() if archivo_node else None

        convocatoria = self._extract_label_value("Convocatoria") or ""

        tasacion_str = (
            self._extract_label_value("Tasación")
            or self._extract_label_value("Tasacion")
            or ""
        )
        tasacion = self._parse_money(tasacion_str)

        precio_base_str = self._extract_label_value("Precio Base") or ""
        precio_base = self._parse_money(precio_base_str)

        incremento_str = self._extract_label_value("Incremento entre ofertas") or ""
        incremento = self._parse_money(incremento_str)

        arancel_str = self._extract_label_value("Arancel") or ""
        arancel = self._parse_money(arancel_str)

        oblaje_str = self._extract_label_value("Oblaje") or ""
        oblaje = self._parse_money(oblaje_str)

        descripcion = (
            self._extract_label_value("Descripción")
            or self._extract_label_value("Descripcion")
            or ""
        )

        # Extract nro_inscritos
        nro_inscritos_str = (
            self._extract_label_value("N° inscritos")
            or self._extract_label_value("Nro inscritos")
            or "0"
        )
        try:
            nro_inscritos = int(re.search(r"\d+", nro_inscritos_str).group())
        except AttributeError, ValueError:
            nro_inscritos = 0

        logger.info(f"Remate tab parsed: expediente={expediente}, precio={precio_base}")

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

    def _extract_cell_value(self, cell) -> str:
        """Extract value from a table cell, excluding the label span.

        Table cells have structure:
        <td><span class="ui-column-title">Label</span>Value</td>
        """
        # Get all text content
        full_text = self._clean_text(cell.text())

        # Remove label span text
        label_span = cell.css_first(".ui-column-title")
        if label_span:
            label_text = self._clean_text(label_span.text())
            # Remove the label text from the full text
            value = full_text.replace(label_text, "").strip()
            return value

        return full_text

    def _extract_location_row(self) -> Dict[str, str]:
        """Extract Departamento, Provincia, Distrito from a single row.

        These three labels appear in the same .ui-g row, so we need special handling.

        Returns:
            Dict with departamento, provincia, distrito
        """
        result = {"departamento": "", "provincia": "", "distrito": ""}

        # Find all .ui-g rows
        ui_g_rows = self.tree.css(".ui-g")

        for row in ui_g_rows:
            # Check if this row contains "Departamento"
            bold_nodes = row.css(".text-bold")
            labels = [self._clean_text(node.text()) for node in bold_nodes]

            if (
                "Departamento" in labels
                and "Provincia" in labels
                and "Distrito" in labels
            ):
                logger.debug("Found location row with Departamento/Provincia/Distrito")

                # Get all children divs
                all_divs = row.css("div")

                for i, div in enumerate(all_divs):
                    text = self._clean_text(div.text())
                    is_bold = "text-bold" in (div.attributes.get("class") or "")

                    if is_bold:
                        # This is a label, look at the next non-bold div
                        if text == "Departamento" and i + 1 < len(all_divs):
                            result["departamento"] = self._clean_text(
                                all_divs[i + 1].text()
                            )
                        elif text == "Provincia" and i + 1 < len(all_divs):
                            result["provincia"] = self._clean_text(
                                all_divs[i + 1].text()
                            )
                        elif text == "Distrito" and i + 1 < len(all_divs):
                            result["distrito"] = self._clean_text(
                                all_divs[i + 1].text()
                            )

                break

        return result

    def _extract_area_from_text(self, text: str) -> Optional[float]:
        """Extract area in m2 from text, converting HA to M2 if needed.

        Examples:
            - "60.28 M2" -> 60.28
            - "5.9851 HA" -> 59851.0 (5.9851 * 10000)
            - "1,081.52 M2" -> 1081.52

        Args:
            text: Text to search for area values

        Returns:
            Area in square meters or None if not found
        """
        if not text:
            return None

        # Pattern for M2 (handles optional commas and decimals)
        m2_pattern = r"([\d,.]+)\s*M2\b"
        m2_match = re.search(m2_pattern, text, re.IGNORECASE)
        if m2_match:
            try:
                value = m2_match.group(1).replace(",", "")
                return float(value)
            except ValueError:
                pass

        # Pattern for HA (hectares) - convert to m2 (1 HA = 10,000 M2)
        ha_pattern = r"([\d,.]+)\s*HA\b"
        ha_match = re.search(ha_pattern, text, re.IGNORECASE)
        if ha_match:
            try:
                value = ha_match.group(1).replace(",", "")
                return float(value) * 10000
            except ValueError:
                pass

        return None

    def _parse_inmuebles_tab(self) -> InmueblesTab:
        """Parse Inmuebles tab data."""
        logger.info("Extracting inmuebles tab fields...")

        distrito_judicial = self._extract_label_value("Distrito Judicial") or ""

        # Extract Departamento, Provincia, Distrito from the location row
        location_data = self._extract_location_row()
        departamento = location_data["departamento"]
        provincia = location_data["provincia"]
        distrito = location_data["distrito"]

        logger.info(
            f"Location: Departamento={departamento}, Provincia={provincia}, Distrito={distrito}"
        )

        # Parse inmuebles table
        inmuebles = []

        # Find table rows in the inmuebles datatable
        table = self.tree.css_first('[id*="dtResumenInmueble_data"]')
        if table:
            rows = table.css("tr")
            logger.info(f"Found {len(rows)} inmueble rows")
            for i, row in enumerate(rows):
                cells = row.css("td")
                if len(cells) >= 6:
                    try:
                        imagenes_text = self._extract_cell_value(cells[5])
                        # Extract just the number from text like "Imagenes0"
                        imagenes_match = re.search(r"(\d+)", imagenes_text)
                        imagenes = int(imagenes_match.group(1)) if imagenes_match else 0
                    except ValueError, AttributeError:
                        imagenes = 0

                    direccion = self._extract_cell_value(cells[2])
                    area_m2 = self._extract_area_from_text(direccion)

                    inmueble = Inmueble(
                        partida_registral=self._extract_cell_value(cells[0]),
                        tipo_inmueble=self._extract_cell_value(cells[1]),
                        direccion=direccion,
                        carga_gravamen=self._extract_cell_value(cells[3])
                        if len(cells) > 3
                        else None,
                        porcentaje_a_remstar=self._extract_cell_value(cells[4])
                        if len(cells) > 4
                        else "",
                        imagenes=imagenes,
                        area_m2=area_m2,
                    )
                    logger.info(f"  Parsed inmueble {i + 1}: {inmueble.tipo_inmueble}")
                    inmuebles.append(inmueble)
        else:
            logger.warning("Inmuebles table not found")

        return InmueblesTab(
            distrito_judicial=distrito_judicial,
            departamento=departamento,
            provincia=provincia,
            distrito=distrito,
            inmuebles=inmuebles,
        )

    def _parse_cronograma_tab(self) -> CronogramaTab:
        """Parse Cronograma tab data."""
        logger.info("Extracting cronograma tab fields...")

        fases = []

        # Find table rows in the cronograma datatable
        table = self.tree.css_first('[id*="dtCronograma_data"]')
        if table:
            rows = table.css("tr")
            logger.info(f"Found {len(rows)} cronograma rows")
            for i, row in enumerate(rows):
                cells = row.css("td")
                if len(cells) >= 4:
                    try:
                        nro_text = self._extract_cell_value(cells[0])
                        nro = int(nro_text)
                    except ValueError:
                        nro = 0

                    fase = CronogramaFase(
                        nro=nro,
                        fase=self._extract_cell_value(cells[1]),
                        fecha_inicio=self._parse_datetime(
                            self._extract_cell_value(cells[2])
                        )
                        or datetime.now(),
                        fecha_fin=self._parse_datetime(
                            self._extract_cell_value(cells[3])
                        )
                        or datetime.now(),
                    )
                    logger.info(f"  Parsed fase {i + 1}: {fase.fase}")
                    fases.append(fase)
        else:
            logger.warning("Cronograma table not found")

        return CronogramaTab(fases=fases)

    def parse_seguimiento_page(self) -> Seguimiento:
        """Parse seguimiento page."""
        logger.info("Parsing seguimiento page...")

        # Parse expediente section
        nro_expediente = (
            self._extract_label_value("N° Expediente")
            or self._extract_label_value("Nro Expediente")
            or ""
        )
        distrito_judicial = self._extract_label_value("Distrito judicial") or ""
        especialidad = self._extract_label_value("Especialidad") or ""
        instancia = self._extract_label_value("Instancia") or ""
        organo_jurisdiccional = (
            self._extract_label_value("Órgano Jurisdiccional")
            or self._extract_label_value("Organo Jurisdiccional")
            or ""
        )

        expediente = Expediente(
            nro_expediente=nro_expediente,
            distrito_judicial=distrito_judicial,
            especialidad=especialidad,
            instancia=instancia,
            organo_jurisdiccional=organo_jurisdiccional,
        )

        # Parse seguimiento section
        nro_convocatoria = (
            self._extract_label_value("N° Convocatoria")
            or self._extract_label_value("Nro Convocatoria")
            or ""
        )
        fecha_reg_str = self._extract_label_value("Fecha de registro") or ""
        fecha_registro = self._parse_date(fecha_reg_str) or date.today()
        procesado_por = self._extract_label_value("Procesado por") or ""
        reanudado = self._extract_label_value("¿Reanudado?") or ""
        fase_convocatoria = self._extract_label_value("Fase convocatoria") or ""
        estado_convocatoria = self._extract_label_value("Estado convocatoria") or ""

        seguimiento_data = SeguimientoData(
            nro_convocatoria=nro_convocatoria,
            fecha_registro=fecha_registro,
            procesado_por=procesado_por,
            reanudado=reanudado,
            fase_convocatoria=fase_convocatoria,
            estado_convocatoria=estado_convocatoria,
        )

        logger.info(f"Seguimiento parsed: expediente={nro_expediente}")

        return Seguimiento(
            url=self.SEGUIMIENTO_URL,
            expediente=expediente,
            seguimiento=seguimiento_data,
        )
