"""Refactored REMAJU data downloader with parsing and JSON export."""

import json
import re
import time
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

import requests

from src.remaju.captcha_solver import BrowserDownloader


def log(message: str) -> None:
    """Print message with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


from src.remaju.parser import RemajuParser
from src.remaju.models import (
    Auction,
    RemateListItem,
    RemateDetail,
    InmueblesTab,
    CronogramaTab,
)
from src.remaju.geocoding import GeocodingClient
from src.remaju.exchange import ExchangeRateClient, parse_money_with_currency
from src.remaju.debug_logger import DebugLogger, init_debug_logger, get_debug_logger


class InvalidDetailPageException(Exception):
    """Raised when we receive an invalid detail page (homepage instead of detail)."""

    pass


class RemajuSiteClient:
    """Client for interacting with REMAJU website."""

    BASE_URL = "https://remaju.pj.gob.pe"
    LIST_URL = f"{BASE_URL}/remaju/pages/publico/remateExterno.xhtml"
    DETAIL_URL = f"{BASE_URL}/remaju/pages/publico/mostrarDetalleRemate.xhtml"

    def __init__(
        self, headless: bool = False, debug_logger: Optional[DebugLogger] = None
    ):
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
        self.debug_logger = debug_logger

    def _make_request(
        self,
        method: str,
        url: str,
        headers: Optional[dict] = None,
        data: Optional[dict] = None,
        auction_number: Optional[str] = None,
        request_type: str = "request",
    ) -> Tuple[requests.Response, int]:
        """Make HTTP request with debug logging.

        Returns:
            Tuple of (response, request_number)
        """
        request_num = 0
        if self.debug_logger and self.debug_logger.enabled:
            request_num = self.debug_logger.log_request(
                url=url,
                method=method,
                headers={**self.session.headers, **(headers or {})},
                payload=data,
                auction_number=auction_number,
                request_type=request_type,
            )

        if method.upper() == "GET":
            response = self.session.get(url, headers=headers)
        else:
            response = self.session.post(url, data=data, headers=headers)

        response.raise_for_status()

        if self.debug_logger and self.debug_logger.enabled:
            self.debug_logger.log_response(
                request_num=request_num,
                response_text=response.text,
                status_code=response.status_code,
                auction_number=auction_number,
                request_type=request_type,
            )

        return response, request_num

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
        log(f"Fetching {self.LIST_URL}...")
        response, request_num = self._make_request(
            "GET", self.LIST_URL, request_type="list_init"
        )
        html = response.text

        if self._has_captcha(html):
            log("CAPTCHA detected, using browser...")
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

    def fetch_page(self, offset: int = 0, rows: int = 4) -> Tuple[str, int]:
        """Fetch a specific page using AJAX POST.

        Returns:
            Tuple of (xml_response, request_number)
        """
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

        response, request_num = self._make_request(
            "POST",
            self.LIST_URL,
            headers=headers,
            data=payload,
            request_type="list_page",
        )
        xml = response.text

        new_view_state = self._extract_view_state_from_xml(xml)
        if new_view_state:
            self.view_state = new_view_state

        return xml, request_num

    def click_detail_button(
        self, detalle_id: str, auction_number: Optional[str] = None
    ) -> int:
        """Click the detail button to register the selection.

        Returns:
            Request number
        """
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

        response, request_num = self._make_request(
            "POST",
            self.LIST_URL,
            headers=headers,
            data=payload,
            auction_number=auction_number,
            request_type="detail_click",
        )

        new_view_state = self._extract_view_state_from_xml(response.text)
        if new_view_state:
            self.view_state = new_view_state

        return request_num

    def _is_valid_detail_page(self, html: str) -> bool:
        """Check if HTML contains expected detail page content."""
        # Must have the detail form
        if "formDetalleRemate" not in html:
            return False
        # Must have detail page specific content (not homepage)
        if "BIENVENIDOS A REM@JU" in html or "formInicio" in html:
            return False
        # Should have expected labels
        expected_labels = ["Expediente", "Distrito Judicial", "Tasaci", "Precio Base"]
        return any(label in html for label in expected_labels)

    def get_detail_page(self, auction_number: Optional[str] = None) -> Tuple[str, int]:
        """Get the detail page after clicking the detail button.

        Validates that the response contains expected detail page content.
        Raises InvalidDetailPageException if we get the homepage instead.

        Returns:
            Tuple of (html, request_number)

        Raises:
            InvalidDetailPageException: If we can't get a valid detail page
        """
        # Add headers to maintain session context from the AJAX click
        headers = {
            "Referer": self.LIST_URL,
        }
        response, request_num = self._make_request(
            "GET",
            self.DETAIL_URL,
            headers=headers,
            auction_number=auction_number,
            request_type="detail_page",
        )
        html = response.text

        if self._is_valid_detail_page(html):
            self.view_state = self._extract_view_state(html)
            return html, request_num

        # Invalid response - raise exception immediately (no retry)
        raise InvalidDetailPageException(
            f"Invalid detail page for auction {auction_number}"
        )

    def fetch_detail_tab(
        self, tab_name: str, auction_number: Optional[str] = None
    ) -> Tuple[str, int]:
        """Fetch a specific tab from the detail page.

        Returns:
            Tuple of (xml, request_number)
        """
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

        response, request_num = self._make_request(
            "POST",
            self.DETAIL_URL,
            headers=headers,
            data=payload,
            auction_number=auction_number,
            request_type=f"detail_tab_{tab_name}",
        )
        xml = response.text

        new_view_state = self._extract_view_state_from_xml(xml)
        if new_view_state:
            self.view_state = new_view_state

        return xml, request_num

    def close_detail_page(
        self, auction_number: Optional[str] = None, follow_redirect: bool = False
    ) -> int:
        """Close/clean up detail page by clicking return button.

        This makes a POST request to mostrarDetalleRemate.xhtml
        to properly clean up the detail view before moving to next auction.

        Args:
            auction_number: Associated auction number
            follow_redirect: If True, follow redirect to list page (use when
                           done with all auctions on current page). If False,
                           just extract ViewState from response without navigating.

        Returns:
            Request number
        """
        time.sleep(0.5)

        payload = {
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "formDetalleRemate:j_idt171",
            "javax.faces.partial.execute": "@all",
            "formDetalleRemate:j_idt171": "formDetalleRemate:j_idt171",
            "formDetalleRemate": "formDetalleRemate",
            "formDetalleRemate:tvResumen_activeIndex": "2",
            "javax.faces.ViewState": self.view_state,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
        }

        response, request_num = self._make_request(
            "POST",
            self.DETAIL_URL,
            headers=headers,
            data=payload,
            auction_number=auction_number,
            request_type="detail_close",
        )

        response_text = response.text

        # Extract ViewState from the response (whether it's a redirect or not)
        new_view_state = self._extract_view_state_from_xml(response_text)
        if new_view_state:
            self.view_state = new_view_state

        # Only follow redirect if explicitly requested (e.g., when done with page)
        if follow_redirect and "<redirect" in response_text:
            redirect_match = re.search(r'<redirect[^>]*url="([^"]+)"', response_text)
            if redirect_match:
                redirect_path = redirect_match.group(1)
                redirect_url = (
                    f"{self.BASE_URL}{redirect_path}"
                    if redirect_path.startswith("/")
                    else redirect_path
                )
                list_response, _ = self._make_request(
                    "GET",
                    redirect_url,
                    auction_number=auction_number,
                    request_type="list_redirect",
                )
                self.view_state = self._extract_view_state(list_response.text)

        return request_num

    def _reset_session_to_list(self, auction_number: Optional[str] = None) -> None:
        """Reset session by navigating to list page and extracting fresh ViewState.

        This is needed after a failed detail page fetch to ensure the next
        auction detail click works properly.
        """
        list_response, _ = self._make_request(
            "GET",
            self.LIST_URL,
            auction_number=auction_number,
            request_type="list_redirect",
        )
        self.view_state = self._extract_view_state(list_response.text)
        log(f"  ✓ Session reset to list page")


class RemajuDataService:
    """Service for downloading and processing REMAJU data."""

    def __init__(
        self,
        output_dir: Path = Path("data"),
        enable_geocoding: bool = True,
        enable_exchange: bool = True,
        headless: bool = False,
        debug: bool = False,
    ):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

        # Initialize debug logger
        self.debug_logger = init_debug_logger(
            enabled=debug, debug_dir=output_dir / "debug"
        )
        if debug:
            log(f"✓ Debug logging enabled: {self.debug_logger.debug_dir}")

        self.client = RemajuSiteClient(
            headless=headless, debug_logger=self.debug_logger
        )
        self.parser = RemajuParser()
        self.geocoding_client = None
        self.exchange_client = None

        if enable_geocoding:
            try:
                self.geocoding_client = GeocodingClient()
                print("✓ Geocoding enabled")
            except ValueError as e:
                log(f"⚠ Geocoding disabled: {e}")

        if enable_exchange:
            try:
                self.exchange_client = ExchangeRateClient()
                print("✓ Exchange rate enabled")
            except ValueError as e:
                log(f"⚠ Exchange rate disabled: {e}")

    def download_page(
        self, page_num: int, rows_per_page: int = 4
    ) -> tuple[List[RemateListItem], List[dict]]:
        """Download a single page of remates.

        Args:
            page_num: Page number (0-indexed)
            rows_per_page: Number of rows per page

        Returns:
            Tuple of (list of remates, list of card info with button IDs)
        """
        offset = page_num * rows_per_page

        try:
            if page_num == 0:
                # First page is already loaded in get_list_page
                xml, request_num = self.client.fetch_page(offset, rows_per_page)
            else:
                xml, request_num = self.client.fetch_page(offset, rows_per_page)

            remates = self.parser.parse_list_xml(xml)
            cards_info = self.parser.extract_card_info(xml)

            if self.debug_logger and self.debug_logger.enabled:
                self.debug_logger.log_parsed_object(
                    request_num=request_num,
                    parsed_object=remates,
                    request_type="list_page",
                    object_type="remates_list",
                )
                self.debug_logger.log_parsed_object(
                    request_num=request_num,
                    parsed_object=cards_info,
                    request_type="list_page",
                    object_type="cards_info",
                )

            return remates, cards_info

        except Exception as e:
            log(f"Error on page {page_num + 1}: {e}")
            return [], []

    def download_detail(
        self, remate: RemateListItem, card_info: Optional[dict]
    ) -> RemateDetail:
        """Download detail data for a remate."""
        log(f"\nDownloading detail for remate {remate.numero_remate}...")

        if not card_info:
            log(f"⚠ Could not find card info for remate {remate.numero_remate}")
            return self._create_empty_detail(remate.numero_remate)

        auction_num = remate.numero_remate
        debug = get_debug_logger()

        self.client.click_detail_button(
            card_info["detalle_id"], auction_number=auction_num
        )

        try:
            detail_html, detail_req_num = self.client.get_detail_page(
                auction_number=auction_num
            )
        except InvalidDetailPageException as e:
            log(f"  ✗ Skipping auction {auction_num}: {e}")
            # Reset session by going back to list page
            self.client._reset_session_to_list(auction_number=auction_num)
            return self._create_empty_detail(remate.numero_remate)

        base_detail = self.parser.parse_detail_html(detail_html, remate.numero_remate)

        if debug and debug.enabled:
            debug.log_parsed_object(
                request_num=detail_req_num,
                parsed_object=base_detail,
                auction_number=auction_num,
                request_type="detail_page",
                object_type="remate_tab",
            )

        inmuebles_xml, inmuebles_req_num = self.client.fetch_detail_tab(
            "inmuebles", auction_number=auction_num
        )
        inmuebles_tab = self.parser.parse_inmuebles_xml(inmuebles_xml)

        if debug and debug.enabled:
            debug.log_parsed_object(
                request_num=inmuebles_req_num,
                parsed_object=inmuebles_tab,
                auction_number=auction_num,
                request_type="detail_tab_inmuebles",
                object_type="inmuebles_tab",
            )

        cronograma_xml, cronograma_req_num = self.client.fetch_detail_tab(
            "cronograma", auction_number=auction_num
        )
        cronograma_tab = self.parser.parse_cronograma_xml(cronograma_xml)

        if debug and debug.enabled:
            debug.log_parsed_object(
                request_num=cronograma_req_num,
                parsed_object=cronograma_tab,
                auction_number=auction_num,
                request_type="detail_tab_cronograma",
                object_type="cronograma_tab",
            )

        detail = self.parser.merge_detail_data(
            base_detail, inmuebles_tab, cronograma_tab
        )

        if debug and debug.enabled:
            debug.log_parsed_object(
                request_num=detail_req_num,
                parsed_object=detail,
                auction_number=auction_num,
                request_type="detail_page",
                object_type="full_detail",
            )

        self._geocode_inmuebles(detail)
        self._compute_exchange_rates(detail)

        # Log summary of extracted data
        self._log_detail_summary(detail)

        # Close detail page to reset session for next auction
        # Don't follow redirect to stay on current list page
        self.client.close_detail_page(auction_number=auction_num, follow_redirect=False)

        return detail

    def _log_detail_summary(self, detail: RemateDetail) -> None:
        """Log summary of extracted money, location and phase data."""
        remate_tab = detail.remate_tab
        inmuebles_tab = detail.inmuebles_tab
        cronograma_tab = detail.cronograma_tab

        # Log money information
        money_parts = []
        if remate_tab.precio_base:
            money_parts.append(f"precio_base: {remate_tab.precio_base}")
        if remate_tab.tasacion:
            money_parts.append(f"tasacion: {remate_tab.tasacion}")
        if remate_tab.arancel:
            money_parts.append(f"arancel: {remate_tab.arancel}")
        if remate_tab.oblaje:
            money_parts.append(f"oblaje: {remate_tab.oblaje}")

        if money_parts:
            log(f"  Money: {', '.join(money_parts)}")
        else:
            log(f"  Money: No amounts found")

        # Log location information
        location_parts = []
        if inmuebles_tab.departamento:
            location_parts.append(f"depto: {inmuebles_tab.departamento}")
        if inmuebles_tab.provincia:
            location_parts.append(f"prov: {inmuebles_tab.provincia}")
        if inmuebles_tab.distrito:
            location_parts.append(f"dist: {inmuebles_tab.distrito}")

        if location_parts:
            log(f"  Location: {', '.join(location_parts)}")
        else:
            log(f"  Location: Not found")

        # Log phase information
        if cronograma_tab.fases:
            current_phase = None
            for fase in cronograma_tab.fases:
                current_phase = fase.fase
            print(
                f"  Phase: {len(cronograma_tab.fases)} phase(s), current: {current_phase}"
            )
        else:
            log(f"  Phase: No phases found")

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

        log(f"  Geocoding {len(detail.inmuebles_tab.inmuebles)} inmueble(s)...")

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
                log(f"    Inmueble {i + 1}: ✓ Geocoded ({lat}, {lon})")

    def _compute_exchange_rates(self, detail: RemateDetail) -> None:
        """Compute and store prices in both PEN and USD.

        Detects currency from the value string (S/. for PEN, $ for USD)
        and stores in appropriate fields, computing the conversion if rate available.
        """
        if not detail.remate_tab:
            return

        remate_tab = detail.remate_tab
        rate = None

        # Get exchange rate if client available
        if self.exchange_client:
            rate = self.exchange_client.get_pen_to_usd_rate()
            if rate:
                remate_tab.exchange_rate = rate
                remate_tab.exchange_rate_date = date.today()

        def process_money_field(value_str: str, pen_field: str, usd_field: str) -> None:
            """Process a money field, detect currency and store in appropriate fields."""
            value, currency = parse_money_with_currency(value_str)
            if value is None:
                return

            if currency == "PEN":
                # Value is in PEN
                setattr(remate_tab, pen_field, value)
                if rate:
                    setattr(remate_tab, usd_field, value * rate)
            elif currency == "USD":
                # Value is in USD
                setattr(remate_tab, usd_field, value)
                if rate:
                    setattr(remate_tab, pen_field, value / rate)

        # Process each money field
        process_money_field(
            remate_tab.precio_base, "precio_base_pen", "precio_base_usd"
        )
        process_money_field(remate_tab.arancel, "arancel_pen", "arancel_usd")
        process_money_field(remate_tab.oblaje, "oblaje_pen", "oblaje_usd")

        if rate:
            log(f"  ✓ Exchange rate applied: 1 PEN = {rate:.4f} USD")

    def download_auctions(
        self, max_pages: int = 1, rows_per_page: int = 4
    ) -> List[Auction]:
        """Download complete auction data page by page.

        Flow:
        - Retrieve page 1, extract all details
        - Retrieve page 2, extract all details
        - etc.
        """
        log("Starting auction download...\n")

        # Get initial page to establish session
        self.client.get_list_page()

        all_auctions = []

        for page_num in range(max_pages):
            log("=" * 50)
            log(f"Processing Page {page_num + 1}/{max_pages}")
            log("=" * 50)

            # Download current page
            remates, cards_info = self.download_page(page_num, rows_per_page)

            if not remates:
                log(f"No remates found on page {page_num + 1}, stopping")
                break

            log(f"Found {len(remates)} remates on this page")

            # Build lookup for card info
            cards_by_remate = {
                card["numero_remate"]: card
                for card in cards_info
                if card.get("numero_remate")
            }

            # Process each remate on this page before moving to next page
            for i, remate in enumerate(remates, 1):
                print(f"\n[{i}/{len(remates)}] Processing {remate.numero_remate}...")
                try:
                    card_info = cards_by_remate.get(remate.numero_remate)
                    detail = self.download_detail(remate, card_info)
                    auction = Auction(
                        numero_remate=remate.numero_remate,
                        list_data=remate,
                        detail=detail,
                        seguimiento=None,
                    )
                    all_auctions.append(auction)
                    print(f"  ✓ Successfully processed {remate.numero_remate}")
                except Exception as e:
                    print(f"  ⚠ Error processing {remate.numero_remate}: {e}")
                    import traceback

                    traceback.print_exc()
                    continue

            print(
                f"\nPage {page_num + 1} complete. Total auctions: {len(all_auctions)}"
            )

            # Close detail page after processing all auctions on this page
            if remates:
                self.client.close_detail_page(
                    auction_number=remates[-1].numero_remate, follow_redirect=True
                )

            # Small delay between pages
            if page_num < max_pages - 1:
                time.sleep(2)

        log("=" * 50)
        log(f"Download complete. Total auctions: {len(all_auctions)}")
        log("=" * 50)

        return all_auctions

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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging of requests and responses",
    )

    args = parser.parse_args()

    service = RemajuDataService(
        output_dir=Path(args.output),
        enable_geocoding=not args.no_geocoding,
        enable_exchange=not args.no_exchange,
        headless=not args.headed,
        debug=args.debug,
    )

    auctions = service.download_auctions(max_pages=args.pages)
    service.save_auctions(auctions)

    print("\n✓ Download complete!")


if __name__ == "__main__":
    main()
