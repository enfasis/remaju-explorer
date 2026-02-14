"""Refactored REMAJU data downloader with parsing and JSON export."""

import json
import re
import time
from datetime import date
from pathlib import Path
from typing import List, Optional, Dict, Any

import requests

from src.remaju.captcha_solver import BrowserDownloader
from src.remaju.new_parser import NewRemajuParser
from src.remaju.models import Auction, RemateListItem, RemateDetail, Seguimiento
from src.remaju.geocoding import GeocodingClient
from src.remaju.exchange import ExchangeRateClient, parse_money_value


class RemajuSiteClient:
    """Client for interacting with REMAJU website."""

    BASE_URL = "https://remaju.pj.gob.pe"
    LIST_URL = f"{BASE_URL}/remaju/pages/publico/remateExterno.xhtml"
    DETAIL_URL = f"{BASE_URL}/remaju/pages/publico/mostrarDetalleRemate.xhtml"

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
        return html

    def fetch_page(self, offset: int = 0, rows: int = 4) -> str:
        """Fetch a specific page using AJAX POST."""
        if not self.view_state:
            raise ValueError("No ViewState available. Call get_list_page() first.")

        time.sleep(0.5)

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

    def click_detail_button(self, detalle_id: str) -> None:
        """Click the detail button to register the selection."""
        time.sleep(0.5)

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

    def get_detail_page(self) -> str:
        """Get the detail page after clicking the detail button."""
        response = self.session.get(self.DETAIL_URL)
        response.raise_for_status()
        html = response.text
        self.view_state = self._extract_view_state(html)
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

        time.sleep(0.5)
        config = tab_configs[tab_name]

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

        return xml


class RemajuDataService:
    """Service for downloading and processing REMAJU data."""

    def __init__(
        self,
        output_dir: Path = Path("data"),
        enable_geocoding: bool = True,
        enable_exchange: bool = True,
        headless: bool = False,
    ):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.client = RemajuSiteClient(headless=headless)
        self.parser = NewRemajuParser()
        self.geocoding_client = None
        self.exchange_client = None

        if enable_geocoding:
            try:
                self.geocoding_client = GeocodingClient()
                print("✓ Geocoding enabled")
            except ValueError as e:
                print(f"⚠ Geocoding disabled: {e}")

        if enable_exchange:
            try:
                self.exchange_client = ExchangeRateClient()
                print("✓ Exchange rate enabled")
            except ValueError as e:
                print(f"⚠ Exchange rate disabled: {e}")

    def download_list(
        self, max_pages: int = 3, rows_per_page: int = 4
    ) -> List[RemateListItem]:
        """Download list of remates."""
        all_remates = []
        seen_remates = set()

        self.client.get_list_page()

        for page in range(max_pages):
            offset = page * rows_per_page

            try:
                xml = self.client.fetch_page(offset, rows_per_page)
                remates = self.parser.parse_list_xml(xml)

                if not remates:
                    print(f"No remates found on page {page + 1}, stopping")
                    break

                for remate in remates:
                    if remate.numero_remate not in seen_remates:
                        seen_remates.add(remate.numero_remate)
                        all_remates.append(remate)

                print(
                    f"Page {page + 1}: Found {len(remates)} remates, total: {len(all_remates)}"
                )
                time.sleep(1)

            except Exception as e:
                print(f"Error on page {page + 1}: {e}")
                break

        return all_remates

    def download_detail(self, remate: RemateListItem) -> RemateDetail:
        """Download detail data for a remate."""
        print(f"\nDownloading detail for remate {remate.numero_remate}...")

        cards_info = self._get_cards_info()
        card_info = next(
            (c for c in cards_info if c["numero_remate"] == remate.numero_remate), None
        )

        if not card_info:
            print(f"⚠ Could not find card info for remate {remate.numero_remate}")
            return self._create_empty_detail(remate.numero_remate)

        self.client.click_detail_button(card_info["detalle_id"])
        detail_html = self.client.get_detail_page()

        base_detail = self.parser.parse_detail_html(detail_html, remate.numero_remate)

        inmuebles_xml = self.client.fetch_detail_tab("inmuebles")
        inmuebles_tab = self.parser.parse_inmuebles_xml(inmuebles_xml)

        cronograma_xml = self.client.fetch_detail_tab("cronograma")
        cronograma_tab = self.parser.parse_cronograma_xml(cronograma_xml)

        detail = self.parser.merge_detail_data(
            base_detail, inmuebles_tab, cronograma_tab
        )

        self._geocode_inmuebles(detail)
        self._compute_exchange_rates(detail)

        return detail

    def _get_cards_info(self) -> List[Dict[str, Any]]:
        """Get card info including button IDs."""
        xml = self.client.fetch_page(offset=0, rows=4)
        return self.parser.extract_card_info(xml)

    def _create_empty_detail(self, numero_remate: str) -> RemateDetail:
        """Create empty detail when download fails."""
        from src.remaju.models import RemateTab, InmueblesTab, CronogramaTab

        return RemateDetail(
            numero_remate=numero_remate,
            url=self.client.DETAIL_URL,
            tabs=["Remate", "Inmuebles", "Cronograma"],
            remate_tab=RemateTab(
                expediente="",
                distrito_judicial="",
                organo_jurisdiccional="",
                instancia="",
                juez="",
                especialista="",
                materia="",
                resolucion="",
                fecha_resolucion=date.today(),
                convocatoria="",
                tasacion="",
                precio_base="",
                incremento_entre_ofertas="",
                arancel="",
                oblaje="",
                descripcion="",
                nro_inscritos=0,
            ),
            inmuebles_tab=InmueblesTab(
                distrito_judicial="",
                departamento="",
                provincia="",
                distrito="",
                inmuebles=[],
            ),
            cronograma_tab=CronogramaTab(fases=[]),
        )

    def _geocode_inmuebles(self, detail: RemateDetail) -> None:
        """Add geocoding to inmuebles."""
        if not self.geocoding_client or not detail.inmuebles_tab.inmuebles:
            return

        print(f"  Geocoding {len(detail.inmuebles_tab.inmuebles)} inmueble(s)...")

        for i, inmueble in enumerate(detail.inmuebles_tab.inmuebles):
            if inmueble.latitude and inmueble.longitude:
                continue

            address_data = {
                "direccion": inmueble.direccion,
                "distrito": detail.inmuebles_tab.distrito,
                "provincia": detail.inmuebles_tab.provincia,
                "departamento": detail.inmuebles_tab.departamento,
            }

            result = self.geocoding_client.geocode_inmueble(address_data)
            if result:
                lat, lon = result
                inmueble.latitude = lat
                inmueble.longitude = lon
                print(f"    Inmueble {i + 1}: ✓ Geocoded ({lat}, {lon})")

    def _compute_exchange_rates(self, detail: RemateDetail) -> None:
        """Compute and store prices in both PEN and USD."""
        if not self.exchange_client or not detail.remate_tab:
            return

        rate = self.exchange_client.get_pen_to_usd_rate()
        if not rate:
            return

        remate_tab = detail.remate_tab

        pen_value = parse_money_value(remate_tab.precio_base)
        if pen_value:
            remate_tab.precio_base_pen = pen_value
            remate_tab.precio_base_usd = pen_value * rate

        pen_value = parse_money_value(remate_tab.arancel)
        if pen_value:
            remate_tab.arancel_pen = pen_value
            remate_tab.arancel_usd = pen_value * rate

        pen_value = parse_money_value(remate_tab.oblaje)
        if pen_value:
            remate_tab.oblaje_pen = pen_value
            remate_tab.oblaje_usd = pen_value * rate

        remate_tab.exchange_rate = rate
        remate_tab.exchange_rate_date = date.today()

        print(f"  ✓ Exchange rate applied: 1 PEN = {rate:.4f} USD")

    def download_auctions(self, max_pages: int = 1) -> List[Auction]:
        """Download complete auction data."""
        print("Starting auction download...\n")

        remates = self.download_list(max_pages=max_pages)
        print(f"\nFound {len(remates)} remates")

        auctions = []
        for i, remate in enumerate(remates, 1):
            print(f"\n[{i}/{len(remates)}] Processing {remate.numero_remate}...")
            try:
                detail = self.download_detail(remate)
                auction = Auction(
                    numero_remate=remate.numero_remate,
                    list_data=remate,
                    detail=detail,
                    seguimiento=None,
                )
                auctions.append(auction)
            except Exception as e:
                print(f"  ⚠ Error: {e}")
                continue

        return auctions

    def save_auctions(self, auctions: List[Auction], filename: str = "auctions.json"):
        """Save auctions to JSON file."""
        output_file = self.output_dir / filename

        existing_auctions: Dict[str, dict] = {}
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for auction_data in data.get("auctions", []):
                        numero_remate = auction_data.get("numero_remate")
                        if numero_remate:
                            existing_auctions[numero_remate] = auction_data
                print(f"\nLoaded {len(existing_auctions)} existing auctions")
            except (json.JSONDecodeError, IOError) as e:
                print(f"\nWarning: Could not load existing file: {e}")

        merged_count = 0
        added_count = 0
        for auction in auctions:
            auction_dict = auction.model_dump()
            numero_remate = auction.numero_remate

            if numero_remate in existing_auctions:
                existing_auctions[numero_remate] = auction_dict
                merged_count += 1
            else:
                existing_auctions[numero_remate] = auction_dict
                added_count += 1

        data = {
            "auctions": list(existing_auctions.values()),
            "count": len(existing_auctions),
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(
            f"Saved {added_count} new, {merged_count} updated, "
            f"{len(existing_auctions)} total auction(s) to {output_file}"
        )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Download REMAJU auction data")
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data",
        help="Output directory (default: data)",
    )
    parser.add_argument(
        "--pages",
        "-p",
        type=int,
        default=1,
        help="Number of pages to download (default: 1)",
    )
    parser.add_argument("--no-geocoding", action="store_true", help="Disable geocoding")
    parser.add_argument(
        "--no-exchange", action="store_true", help="Disable exchange rate conversion"
    )
    parser.add_argument(
        "--headed", action="store_true", help="Run browser in headed mode"
    )

    args = parser.parse_args()

    service = RemajuDataService(
        output_dir=Path(args.output),
        enable_geocoding=not args.no_geocoding,
        enable_exchange=not args.no_exchange,
        headless=not args.headed,
    )

    auctions = service.download_auctions(max_pages=args.pages)
    service.save_auctions(auctions)

    print("\n✓ Download complete!")


if __name__ == "__main__":
    main()
