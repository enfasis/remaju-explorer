"""Simple REMAJU data downloader with pagination and browser CAPTCHA solving."""

import re
import time
from pathlib import Path

import requests
from selectolax.parser import HTMLParser

from src.remaju.captcha_solver import BrowserDownloader


class SimpleDownloader:
    """Simple downloader for REMAJU auction data."""

    BASE_URL = "https://remaju.pj.gob.pe"
    LIST_URL = f"{BASE_URL}/remaju/pages/publico/remateExterno.xhtml"
    DETAIL_URL = f"{BASE_URL}/remaju/pages/publico/mostrarDetalleRemate.xhtml"
    SEGUIMIENTO_URL = f"{BASE_URL}/remaju/pages/publico/mostrarSeguimientoRemate.xhtml"

    def __init__(self, headless: bool = False):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": self.BASE_URL,
            }
        )
        self.view_state = None
        self.browser = BrowserDownloader(headless=headless)

    def _extract_view_state(self, html: str) -> str:
        """Extract ViewState from HTML."""
        patterns = [
            r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"',
            r'"javax\.faces\.ViewState":"([^"]+)"',
            r'id="[^"]*javax\.faces\.ViewState[^"]*"[^>]*value="([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, html)
            if match:
                return match.group(1)
        return ""

    def _extract_view_state_from_xml(self, xml: str) -> str:
        """Extract ViewState from AJAX XML response."""
        match = re.search(
            r'<update[^>]*id="[^"]*ViewState[^"]*"[^>]*>\s*<!\[CDATA\[([^\]]+)\]\]>',
            xml,
        )
        if match:
            return match.group(1).strip()
        return ""

    def _has_captcha(self, html: str) -> bool:
        """Check if HTML contains CAPTCHA."""
        return (
            "h-captcha" in html.lower()
            or "hcaptcha" in html.lower()
            or "Radware" in html
        )

    def get_list_page(self) -> str:
        """Get initial list page with ViewState."""
        print(f"Fetching {self.LIST_URL}...")

        response = self.session.get(self.LIST_URL)
        response.raise_for_status()
        html = response.text

        if self._has_captcha(html):
            print("CAPTCHA detected, using browser...")
            html, session_data = self.browser.get_page(self.LIST_URL)
            self.session.headers.update(session_data.headers)
            for cookie in session_data.cookies:
                self.session.cookies.set(
                    cookie["name"],
                    cookie["value"],
                    domain=cookie.get("domain", ""),
                    path=cookie.get("path", "/"),
                )

        self.view_state = self._extract_view_state(html)
        print(f"Got ViewState: {self.view_state[:50]}...")
        return html

    def fetch_page(self, offset: int = 0, rows: int = 4) -> str:
        """Fetch a specific page using AJAX POST."""
        if not self.view_state:
            raise ValueError("No ViewState available. Call get_list_page() first.")

        print(f"Fetching page with offset={offset}, rows={rows}...")

        payload = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "formBuscarRemateExterno:listaRemate",
            "javax.faces.partial.execute": "formBuscarRemateExterno:listaRemate",
            "javax.faces.partial.render": "formBuscarRemateExterno:listaRemate",
            "javax.faces.behavior.event": "page",
            "javax.faces.partial.event": "page",
            "formBuscarRemateExterno:listaRemate_pagination": "true",
            "formBuscarRemateExterno:listaRemate_skipChildren": "true",
            "formBuscarRemateExterno:listaRemate_first": str(offset),
            "formBuscarRemateExterno:listaRemate_rows": str(rows),
            "formBuscarRemateExterno": "formBuscarRemateExterno",
            "formBuscarRemateExterno:j_idt76:filtroRemate": "",
            "formBuscarRemateExterno:j_idt76:filtroNroExpediente": "",
            "formBuscarRemateExterno:j_idt76:precioBaseDesde_input": "",
            "formBuscarRemateExterno:j_idt76:precioBaseDesde_hinput": "",
            "formBuscarRemateExterno:j_idt76:precioBaseHasta_input": "",
            "formBuscarRemateExterno:j_idt76:precioBaseHasta_hinput": "",
            "formBuscarRemateExterno:j_idt76:filtroTipoInmueble_focus": "",
            "formBuscarRemateExterno:j_idt76:filtroTipoInmueble_input": "",
            "formBuscarRemateExterno:j_idt76:filtroDepartamento_focus": "",
            "formBuscarRemateExterno:j_idt76:filtroDepartamento_input": "",
            "formBuscarRemateExterno:j_idt76:filtroProvincia_focus": "",
            "formBuscarRemateExterno:j_idt76:filtroProvincia_input": "",
            "formBuscarRemateExterno:j_idt76:filtroDistrito_focus": "",
            "formBuscarRemateExterno:j_idt76:filtroDistrito_input": "",
            "formBuscarRemateExterno:j_idt76:filtroFases_focus": "",
            "formBuscarRemateExterno:j_idt76:filtroFases_input": "1",
            "formBuscarRemateExterno:j_idt76_active": "0",
            "formBuscarRemateExterno:captcha": "",
            "formBuscarRemateExterno:listaRemate_rppDD": str(rows),
            "javax.faces.ViewState": self.view_state,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
        }

        response = self.session.post(self.LIST_URL, data=payload, headers=headers)
        response.raise_for_status()

        xml = response.text

        new_view_state = self._extract_view_state_from_xml(xml)
        if new_view_state:
            self.view_state = new_view_state

        return xml

    def extract_cards_from_xml(self, xml: str) -> list:
        """Extract card data from AJAX XML response."""
        cards = []

        cdata_match = re.search(
            r'<update[^>]*id="formBuscarRemateExterno:listaRemate"[^>]*>\s*<!\[CDATA\[(.*?)\]\]>',
            xml,
            re.DOTALL,
        )
        if not cdata_match:
            print("No CDATA content found in XML")
            return cards

        html_content = cdata_match.group(1)
        tree = HTMLParser(html_content)

        card_divs = tree.css("div.card.azul")
        print(f"Found {len(card_divs)} cards")

        for card in card_divs:
            card_data = {"remate_index": None, "numero_remate": ""}

            buttons = card.css("button")
            for btn in buttons:
                btn_id = btn.attributes.get("id") or ""
                btn_text = btn.text(deep=True) or ""

                if "Detalle" in btn_text:
                    match = re.search(
                        r"formBuscarRemateExterno:listaRemate:(\d+):j_idt", btn_id
                    )
                    if match:
                        card_data["remate_index"] = match.group(1)

            if card_data["remate_index"]:
                base_id = (
                    f"formBuscarRemateExterno:listaRemate:{card_data['remate_index']}"
                )
                card_data["seguimiento_id"] = f"{base_id}:j_idt168"
                card_data["detalle_id"] = f"{base_id}:j_idt169"

            card_html = str(card.html)
            remate_match = re.search(r"Remate N°\s*(\d+)", card_html)
            if remate_match:
                card_data["numero_remate"] = remate_match.group(1)

            cards.append(card_data)

        return cards

    def click_detail_button(self, detalle_id: str) -> None:
        """Click the detail button to register the selection."""
        print(f"Clicking detail button: {detalle_id}...")

        payload = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": detalle_id,
            "javax.faces.partial.execute": "@all",
            detalle_id: detalle_id,
            "formBuscarRemateExterno": "formBuscarRemateExterno",
            "javax.faces.ViewState": self.view_state,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
        }

        response = self.session.post(self.LIST_URL, data=payload, headers=headers)
        response.raise_for_status()

        new_view_state = self._extract_view_state_from_xml(response.text)
        if new_view_state:
            self.view_state = new_view_state

        print("Detail button clicked")

    def get_detail_page(self) -> str:
        """Get the detail page after clicking the detail button."""
        print(f"Fetching detail page...")

        response = self.session.get(self.DETAIL_URL)
        response.raise_for_status()

        html = response.text
        self.view_state = self._extract_view_state(html)

        print(f"Got detail page, ViewState: {self.view_state[:50]}...")
        return html

    def fetch_detail_tab(self, tab_name: str) -> str:
        """Fetch a specific tab from the detail page."""
        if not self.view_state:
            raise ValueError("No ViewState available")

        tab_configs = {
            "inmuebles": {
                "newTab": "formDetalleRemate:tvResumen:tbInmuebles",
                "tabindex": "1",
                "activeIndex": "1",
            },
            "cronograma": {
                "newTab": "formDetalleRemate:tvResumen:tbCronograma",
                "tabindex": "2",
                "activeIndex": "2",
            },
        }

        if tab_name not in tab_configs:
            raise ValueError(f"Unknown tab: {tab_name}")

        config = tab_configs[tab_name]
        print(f"Fetching {tab_name} tab...")

        payload = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "formDetalleRemate:tvResumen",
            "javax.faces.partial.execute": "formDetalleRemate:tvResumen",
            "javax.faces.partial.render": "formDetalleRemate:tvResumen:pgResumenRemate formDetalleRemate:tvResumen:pgResumenInmueble formDetalleRemate:tvResumen:pgResumenParte formDetalleRemate:tvResumen:pgResumenCronograma formDetalleRemate:tvResumen",
            "javax.faces.behavior.event": "tabChange",
            "javax.faces.partial.event": "tabChange",
            "formDetalleRemate:tvResumen_contentLoad": "true",
            "formDetalleRemate:tvResumen_newTab": config["newTab"],
            "formDetalleRemate:tvResumen_tabindex": config["tabindex"],
            "formDetalleRemate": "formDetalleRemate",
            "formDetalleRemate:tvResumen_activeIndex": config["activeIndex"],
            "javax.faces.ViewState": self.view_state,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
        }

        response = self.session.post(self.DETAIL_URL, data=payload, headers=headers)
        response.raise_for_status()

        xml = response.text

        new_view_state = self._extract_view_state_from_xml(xml)
        if new_view_state:
            self.view_state = new_view_state

        print(f"Got {tab_name} tab data")
        return xml

    def download_all_pages(self, rows_per_page: int = 4, max_pages: int = 5) -> list:
        """Download all pages and extract card data."""
        all_cards = []

        self.get_list_page()

        for page in range(max_pages):
            offset = page * rows_per_page

            try:
                xml = self.fetch_page(offset, rows_per_page)
                cards = self.extract_cards_from_xml(xml)

                if not cards:
                    print(f"No cards found on page {page + 1}, stopping")
                    break

                print(f"Page {page + 1}: Found {len(cards)} cards")
                all_cards.extend(cards)

                for card in cards:
                    print(
                        f"  - Remate {card.get('numero_remate', 'N/A')} "
                        f"(index={card.get('remate_index')}): "
                        f"detalle={card['detalle_id']}, seguimiento={card['seguimiento_id']}"
                    )

                time.sleep(1)

            except Exception as e:
                print(f"Error on page {page + 1}: {e}")
                break

        return all_cards

    def download_remate_detail(self, card: dict) -> dict:
        """Download all detail data for a remate."""
        print(f"\nDownloading detail for remate {card['numero_remate']}...")

        self.click_detail_button(card["detalle_id"])
        detail_html = self.get_detail_page()

        inmuebles_xml = self.fetch_detail_tab("inmuebles")
        cronograma_xml = self.fetch_detail_tab("cronograma")

        return {
            "numero_remate": card["numero_remate"],
            "base_html": detail_html,
            "inmuebles_xml": inmuebles_xml,
            "cronograma_xml": cronograma_xml,
        }


def main():
    """Main entry point."""
    downloader = SimpleDownloader(headless=False)
    cards = downloader.download_all_pages(rows_per_page=4, max_pages=3)

    print(f"\nTotal cards extracted: {len(cards)}")
    for card in cards:
        print(
            f"Remate {card.get('numero_remate', 'N/A')} "
            f"(index={card.get('remate_index')}): "
            f"detalle_id={card['detalle_id']}, seguimiento_id={card['seguimiento_id']}"
        )

    if cards:
        print("\nDownloading detail for first remate...")
        detail_data = downloader.download_remate_detail(cards[0])
        print(f"Detail data keys: {list(detail_data.keys())}")
        print(f"Base HTML length: {len(detail_data['base_html'])}")
        print(f"Inmuebles XML length: {len(detail_data['inmuebles_xml'])}")
        print(f"Cronograma XML length: {len(detail_data['cronograma_xml'])}")


if __name__ == "__main__":
    main()
