import re
from datetime import date, datetime

from selectolax.parser import HTMLParser, Node

from models import (
    Card,
    CronogramaFase,
    CronogramaTab,
    Expediente,
    Inmueble,
    InmueblesTab,
    RemateDetail,
    RemateListItem,
    RemateTab,
    Seguimiento,
    SeguimientoEvento,
)

DETAIL_URL = "https://remaju.pj.gob.pe/remaju/pages/publico/mostrarDetalleRemate.xhtml"
LIST_ID = "formBuscarRemateExterno:listaRemate"
TABS_ID = "formDetalleRemate:tvResumen"


def clean(text: str | None) -> str:
    return " ".join(text.split()) if text else ""


def parse_date(value: str | None) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except (ValueError, AttributeError):
        return None


def parse_datetime(value: str | None) -> datetime | None:
    for pattern in ("%d/%m/%Y %H:%M:%S %p", "%d/%m/%Y %I:%M:%S %p"):
        try:
            return datetime.strptime(value.strip(), pattern)
        except (ValueError, AttributeError):
            continue
    return None


def parse_money(value: str) -> str:
    if not value:
        return ""
    match = re.search(r"S/\.\s*([\d,\.]+)", value)
    return f"S/. {match.group(1)}" if match else clean(value)


def parse_area(text: str) -> float | None:
    for pattern, factor in ((r"([\d,.]+)\s*M2\b", 1), (r"([\d,.]+)\s*HA\b", 10000)):
        match = re.search(pattern, text or "", re.IGNORECASE)
        if match:
            try:
                return float(match.group(1).replace(",", "")) * factor
            except ValueError:
                continue
    return None


def cdata(xml: str, element_id: str) -> str | None:
    match = re.search(rf'<update[^>]*id="{re.escape(element_id)}"[^>]*>\s*<!\[CDATA\[(.*?)\]\]>', xml, re.DOTALL)
    return match.group(1) if match else None


def sibling_value(scope: HTMLParser | Node, label: str) -> str:
    for node in scope.css(".text-bold"):
        text = clean(node.text())
        if label.lower() not in text.lower() or not node.parent:
            continue
        children = node.parent.css("div")
        position = next((index for index, child in enumerate(children) if child == node), None)
        if position is None:
            continue
        for child in children[position + 1:]:
            if "text-bold" in (child.attributes.get("class") or ""):
                continue
            value = clean(child.text())
            if value and value != text:
                return value
    return ""


def remate_value(tree: HTMLParser, label: str) -> str | None:
    for node in tree.css(".text-bold"):
        text = clean(node.text())
        if label.lower() not in text.lower() or not node.parent:
            continue
        for child in node.parent.css("div"):
            value = clean(child.text())
            if child == node or "text-bold" in (child.attributes.get("class") or ""):
                continue
            if not value or value == text:
                continue
            if label.lower() in value.lower():
                remainder = value.replace(text, "").strip()
                if remainder:
                    return remainder
                continue
            return value
    return None


def first_value(tree: HTMLParser, *labels: str) -> str:
    return next((value for label in labels if (value := remate_value(tree, label))), "")


def list_cards(xml: str) -> list[Node]:
    content = cdata(xml, LIST_ID)
    return HTMLParser(content).css("div.card.azul") if content else []


def listing(xml: str) -> list[RemateListItem]:
    items: dict[str, RemateListItem] = {}
    for node in list_cards(xml):
        item = list_item(node)
        if item and item.numero_remate not in items:
            items[item.numero_remate] = item
    return list(items.values())


def list_item(card: Node) -> RemateListItem | None:
    text = clean(card.text())
    number = re.search(r"Remate N°\s*(\d+)", text)
    if not number:
        return None
    convocatoria = re.search(r"Remate N°\s*\d+\s*-\s*([A-Z\s]+)(?=\s|$)", text)
    tipo = re.search(r"\b(REMATE\s+SIMPLE|REMATE\s+EN\s+MASA)\b", text)
    distrito = re.search(r"fa-map-marker.*?([A-Z][A-Z\sÁÉÍÓÚÑ]+?)(?=Presentación|<|$)", text)
    fecha = re.search(r"(\d{2}/\d{2}/\d{4})", text)
    hora = re.search(r"(\d{1,2}:\d{2}\s*(?:AM|PM))", text)
    fase = re.search(r"(Publicación\s+e\s+Inscripcion|Validación\s+de\s+Inscripción|Presentación\s+de\s+Ofertas)", text)
    estado = re.search(r"(En\s+proceso|Finalizado|Suspendido)", text)
    precio = re.search(r"Precio\s*Base\s*(S/\.|\$)\s*([\d,\.]+)", text)
    descripcion = re.search(r"<label>(.+?)</label>", str(card.html), re.DOTALL)
    return RemateListItem(
        numero_remate=number.group(1),
        convocatoria=convocatoria.group(1).strip() if convocatoria else "",
        tipo=tipo.group(1) if tipo else "REMATE SIMPLE",
        distrito=clean(distrito.group(1)) if distrito else "",
        fecha_presentacion=parse_date(fecha.group(1) if fecha else "") or date.today(),
        hora_presentacion=hora.group(1) if hora else "",
        fase=fase.group(1) if fase else "Publicación e Inscripcion",
        estado=estado.group(1) if estado else "En proceso",
        precio_base=f"{precio.group(1)} {precio.group(2)}" if precio else None,
        descripcion=clean(descripcion.group(1)) if descripcion else "",
    )


def card_actions(xml: str) -> list[dict[str, str | None]]:
    actions = []
    for node in list_cards(xml):
        action: dict[str, str | None] = {"remate_index": None, "numero_remate": "", "seguimiento_id": None, "detalle_id": None}
        for button in node.css("button"):
            button_id = button.attributes.get("id") or ""
            label = button.text(deep=True) or ""
            if "Detalle" in label:
                action["detalle_id"] = button_id
                index = re.search(rf"{LIST_ID}:(\d+):j_idt", button_id)
                action["remate_index"] = index.group(1) if index else None
            elif "Seguimiento" in label:
                action["seguimiento_id"] = button_id
        number = re.search(r"Remate N°\s*(\d+)", str(node.html))
        action["numero_remate"] = number.group(1) if number else ""
        actions.append(action)
    return actions


def cards(xml: str) -> list[Card]:
    actions = {action["numero_remate"]: action for action in card_actions(xml)}
    return [
        Card(item, str(actions[item.numero_remate]["detalle_id"]), actions[item.numero_remate]["seguimiento_id"])
        for item in listing(xml)
        if actions.get(item.numero_remate, {}).get("detalle_id")
    ]


def advertised_total(html: str) -> int | None:
    match = re.search(rf'id:"{re.escape(LIST_ID)}",paginator:\{{[^}}]*rowCount:(\d+)', html)
    return int(match.group(1)) if match else None


def button_id(html: str, form: str, label: str) -> str | None:
    for match in re.finditer(rf'<button[^>]*id="({re.escape(form)}:j_idt\d+)"[^>]*>(.*?)</button>', html, re.IGNORECASE | re.DOTALL):
        if label in match.group(2):
            return match.group(1)
    return None


def remate_tab(html: str) -> RemateTab:
    tree = HTMLParser(html)
    inscritos = re.search(r"\d+", first_value(tree, "N° inscritos", "Nro inscritos") or "0")
    archivo = tree.css_first('a[href="#"][onclick*="j_idt"]')
    return RemateTab(
        expediente=first_value(tree, "Expediente"),
        distrito_judicial=first_value(tree, "Distrito Judicial"),
        organo_jurisdiccional=first_value(tree, "Órgano Jurisdiccional", "Organo Jurisdiccional"),
        instancia=first_value(tree, "Instancia"),
        juez=first_value(tree, "Juez"),
        especialista=first_value(tree, "Especialista"),
        materia=first_value(tree, "Materia"),
        resolucion=first_value(tree, "Resolución", "Resolucion"),
        fecha_resolucion=parse_date(first_value(tree, "Fecha Resolución", "Fecha Resolucion")) or date.today(),
        archivo=archivo.text() if archivo else None,
        convocatoria=first_value(tree, "Convocatoria"),
        tasacion=parse_money(first_value(tree, "Tasación", "Tasacion")),
        precio_base=parse_money(first_value(tree, "Precio Base")),
        incremento_entre_ofertas=parse_money(first_value(tree, "Incremento entre ofertas")),
        arancel=parse_money(first_value(tree, "Arancel")),
        oblaje=parse_money(first_value(tree, "Oblaje")),
        descripcion=first_value(tree, "Descripción", "Descripcion"),
        nro_inscritos=int(inscritos.group()) if inscritos else 0,
    )


def inmuebles_tab(xml: str) -> InmueblesTab:
    content = cdata(xml, TABS_ID)
    if not content:
        return InmueblesTab(distrito_judicial="", departamento="", provincia="", distrito="", inmuebles=[])
    tree = HTMLParser(content)
    table = tree.css_first('[id*="dtResumenInmueble_data"]')
    rows = [row.css("td") for row in table.css("tr")] if table else []
    return InmueblesTab(
        distrito_judicial=sibling_value(tree, "Distrito Judicial"),
        departamento=sibling_value(tree, "Departamento"),
        provincia=sibling_value(tree, "Provincia"),
        distrito=sibling_value(tree, "Distrito"),
        inmuebles=[inmueble(cells) for cells in rows if len(cells) >= 6],
    )


def inmueble(cells: list[Node]) -> Inmueble:
    images = re.search(r"(\d+)", clean(cells[5].text()))
    address = clean(cells[2].text())
    return Inmueble(
        partida_registral=clean(cells[0].text()),
        tipo_inmueble=clean(cells[1].text()),
        direccion=address,
        carga_gravamen=clean(cells[3].text()),
        porcentaje_a_remstar=clean(cells[4].text()),
        imagenes=int(images.group(1)) if images else 0,
        area_m2=parse_area(address),
    )


def cronograma_tab(xml: str) -> CronogramaTab:
    content = cdata(xml, TABS_ID)
    table = HTMLParser(content).css_first('[id*="dtCronograma_data"]') if content else None
    rows = [row.css("td") for row in table.css("tr")] if table else []
    return CronogramaTab(fases=[fase(cells) for cells in rows if len(cells) >= 4])


def fase(cells: list[Node]) -> CronogramaFase:
    number = clean(cells[0].text())
    return CronogramaFase(
        nro=int(number) if number.isdigit() else 0,
        fase=clean(cells[1].text()),
        fecha_inicio=parse_datetime(clean(cells[2].text())) or datetime.now(),
        fecha_fin=parse_datetime(clean(cells[3].text())) or datetime.now(),
    )


def detail(numero_remate: str, html: str, inmuebles_xml: str, cronograma_xml: str) -> RemateDetail:
    return RemateDetail(
        numero_remate=numero_remate,
        url=DETAIL_URL,
        tabs=["Remate", "Inmuebles", "Cronograma"],
        remate_tab=remate_tab(html),
        inmuebles_tab=inmuebles_tab(inmuebles_xml),
        cronograma_tab=cronograma_tab(cronograma_xml),
    )


def seguimiento(html: str) -> Seguimiento:
    tree = HTMLParser(html)
    grid = tree.css_first('[id*="dgListaConvocatoria_content"]')
    events = [evento(card) for card in grid.css(".card.gris")] if grid else []
    return Seguimiento(
        expediente=Expediente(
            nro_expediente=sibling_value(tree, "N° Expediente"),
            distrito_judicial=sibling_value(tree, "Distrito judicial"),
            especialidad=sibling_value(tree, "Especialidad"),
            instancia=sibling_value(tree, "Instancia"),
            organo_jurisdiccional=sibling_value(tree, "Órgano Jurisdiccional"),
        ),
        eventos=[event for event in events if event],
    )


def evento(card: Node) -> SeguimientoEvento | None:
    number = sibling_value(card, "N° Convocatoria")
    if not number:
        return None
    return SeguimientoEvento(
        nro_convocatoria=number,
        fecha_registro=parse_date(sibling_value(card, "Fecha de registro")) or date.today(),
        procesado_por=sibling_value(card, "Procesado por"),
        reanudado=sibling_value(card, "¿Reanudado?"),
        fase_convocatoria=sibling_value(card, "Fase convocatoria"),
        estado_convocatoria=sibling_value(card, "Estado convocatoria"),
        fecha_desierto=parse_date(sibling_value(card, "Fecha de desierto")),
    )
