"""Download auction data from REMAJU website."""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from remaju.models import Auction, RemateListItem, RemateDetail, Seguimiento
from remaju.parser import RemajuParser
from remaju.geocoding import GeocodingClient
from remaju.exchange import ExchangeRateClient, parse_money_value
from datetime import date


class RemajuDownloader:
    """Downloader for REMAJU auction data."""

    BASE_URL = "https://remaju.pj.gob.pe"
    LIST_URL = f"{BASE_URL}/remaju/pages/publico/remateExterno.xhtml"
    DETAIL_URL = f"{BASE_URL}/remaju/pages/publico/mostrarDetalleRemate.xhtml"
    SEGUIMIENTO_URL = f"{BASE_URL}/remaju/pages/publico/mostrarSeguimientoRemate.xhtml"

    def __init__(self, output_dir: Path = Path("data"), enable_geocoding: bool = True):
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Origin": self.BASE_URL,
            }
        )
        self.enable_geocoding = enable_geocoding
        self.geocoding_client = None
        self.exchange_client = None
        self.current_view_state = None

        if enable_geocoding:
            try:
                self.geocoding_client = GeocodingClient()
                print("✓ Geocoding enabled")
            except ValueError as e:
                print(f"⚠ Geocoding disabled: {e}")

        try:
            self.exchange_client = ExchangeRateClient()
            print("✓ Exchange rate enabled")
        except ValueError as e:
            print(f"⚠ Exchange rate disabled: {e}")

    def download_list_page(self) -> Optional[str]:
        """Download the auction list page."""
        print(f"Downloading list page from {self.LIST_URL}...")
        response = self.session.get(self.LIST_URL)
        response.raise_for_status()
        html = response.text

        self.current_view_state = self._extract_view_state(html)
        return html

    def _extract_view_state(self, html: str) -> Optional[str]:
        """Extract ViewState from HTML."""
        import re

        # Pattern 1: Standard format
        match = re.search(r'name="javax\.faces\.ViewState"[^>]*value="([^"]+)"', html)
        if match:
            return match.group(1)
        # Pattern 2: JSON format
        match = re.search(r'"javax\.faces\.ViewState":"([^"]+)"', html)
        if match:
            return match.group(1)
        # Pattern 3: With prefix like j_id1:javax.faces.ViewState:0
        match = re.search(
            r'id="[^"]*javax\.faces\.ViewState[^"]*"[^>]*value="([^"]+)"', html
        )
        if match:
            return match.group(1)
        return None

    def _make_ajax_post(
        self, url: str, payload: dict, headers: dict = None
    ) -> requests.Response:
        """Make AJAX POST request with proper headers."""
        post_headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Faces-Request": "partial/ajax",
            "X-Requested-With": "XMLHttpRequest",
        }
        if headers:
            post_headers.update(headers)
        return self.session.post(url, data=payload, headers=post_headers)

    def _is_detail_page(self, html: str) -> bool:
        """Check if HTML contains detail page data.

        Args:
            html: HTML content to check

        Returns:
            True if this is a detail page with data
        """
        parser = RemajuParser(html)
        # Check if expediente field has data
        expediente = parser._extract_label_value("Expediente")
        return expediente and expediente.strip() != ""

    def download_detail_page(self, remate_id: str) -> Optional[str]:
        """Download detail page for a specific remate using AJAX POST requests.

        The detail page uses PrimeFaces tabs that require AJAX POST to load content.
        We load the Remate tab first, then Inmuebles, then Cronograma.

        Args:
            remate_id: The remate number

        Returns:
            HTML content combining all tabs
        """
        print(f"Downloading detail page for remate {remate_id}...")

        # First, GET the page to establish session and get ViewState
        try:
            response = self.session.get(self.DETAIL_URL)
            response.raise_for_status()
            base_html = response.text
            self.current_view_state = self._extract_view_state(base_html)

            if not self.current_view_state:
                print(f"  ⚠ Could not extract ViewState from detail page")
                return None

        except Exception as e:
            print(f"  ⚠ Error fetching detail page: {e}")
            return None

        # Load each tab via AJAX POST
        tabs_data = {}

        for tab_name, tab_param in [
            ("remate", "formDetalleRemate:tvResumen:tbRemate"),
            ("inmuebles", "formDetalleRemate:tvResumen:tbInmuebles"),
            ("cronograma", "formDetalleRemate:tvResumen:tbCronograma"),
        ]:
            try:
                payload = {
                    "javax.faces.partial.ajax": "true",
                    "javax.faces.source": "formDetalleRemate:tvResumen",
                    "javax.faces.partial.execute": "formDetalleRemate:tvResumen",
                    "javax.faces.partial.render": "formDetalleRemate:tvResumen",
                    "formDetalleRemate:tvResumen": "formDetalleRemate:tvResumen",
                    "formDetalleRemate:tvResumen_newTab": tab_param,
                    "formDetalleRemate": "formDetalleRemate",
                    "javax.faces.ViewState": self.current_view_state,
                }

                response = self._make_ajax_post(self.DETAIL_URL, payload)
                response.raise_for_status()
                tabs_data[tab_name] = response.text
                print(f"  ✓ Loaded {tab_name} tab")

                # Extract updated ViewState if present
                new_view_state = self._extract_view_state(response.text)
                if new_view_state:
                    self.current_view_state = new_view_state

            except Exception as e:
                print(f"  ⚠ Error loading {tab_name} tab: {e}")
                tabs_data[tab_name] = ""

        # Combine all tab data into a single HTML structure
        combined_html = self._combine_detail_tabs(base_html, tabs_data)
        return combined_html

    def _combine_detail_tabs(self, base_html: str, tabs_data: dict) -> str:
        """Combine AJAX responses into a single HTML document.

        Args:
            base_html: The initial page HTML
            tabs_data: Dict with tab_name -> AJAX response HTML

        Returns:
            Combined HTML document
        """
        # For now, return the base HTML with tab content injected
        # The parser looks for specific IDs in the HTML
        combined = base_html

        # Replace tab content if we have it
        for tab_name, content in tabs_data.items():
            if content:
                # Extract the actual content from the partial update
                # PrimeFaces returns XML with CDATA sections
                import re

                # Look for CDATA content
                cdata_pattern = r"<!\[CDATA\[(.*?)\]\]>"
                matches = re.findall(cdata_pattern, content, re.DOTALL)

                if matches:
                    # Use the last/most relevant CDATA section
                    tab_content = matches[-1]
                    # Inject into base HTML by replacing the empty tab div
                    # This is a simple approach - may need refinement
                    combined = self._inject_tab_content(combined, tab_name, tab_content)

        return combined

    def _inject_tab_content(self, html: str, tab_name: str, content: str) -> str:
        """Inject tab content into the base HTML.

        Args:
            html: Base HTML
            tab_name: Name of the tab (remate, inmuebles, cronograma)
            content: Tab content to inject

        Returns:
            HTML with injected content
        """
        import re

        # Map tab names to their container IDs
        tab_ids = {
            "remate": "formDetalleRemate:tvResumen:tbRemate",
            "inmuebles": "formDetalleRemate:tvResumen:tbInmuebles",
            "cronograma": "formDetalleRemate:tvResumen:tbCronograma",
        }

        tab_id = tab_ids.get(tab_name)
        if not tab_id:
            return html

        # Create a pattern to find the tab div
        # Replace the empty tab content with our loaded content
        escaped_id = tab_id.replace(":", "\\:")
        pattern = rf'(<div[^>]*id="{escaped_id}"[^>]*>)(.*?)(</div>)'

        # Simple replacement - inject content between tags
        # Note: This is a basic implementation
        def replacer(match):
            return match.group(1) + content + match.group(3)

        return re.sub(pattern, replacer, html, flags=re.DOTALL)

    def download_seguimiento_page(self, remate_id: str) -> Optional[str]:
        """Download seguimiento page for a specific remate using AJAX POST.

        The seguimiento page requires a POST request to load the actual data.

        Args:
            remate_id: The remate number

        Returns:
            HTML content of the seguimiento page
        """
        print(f"Downloading seguimiento page for remate {remate_id}...")

        # First, GET the page to establish session and get ViewState
        try:
            response = self.session.get(self.SEGUIMIENTO_URL)
            response.raise_for_status()
            base_html = response.text
            self.current_view_state = self._extract_view_state(base_html)

            if not self.current_view_state:
                print(f"  ⚠ Could not extract ViewState from seguimiento page")
                return None

        except Exception as e:
            print(f"  ⚠ Error fetching seguimiento page: {e}")
            return None

        # Load the seguimiento data via AJAX POST
        try:
            payload = {
                "javax.faces.partial.ajax": "true",
                "javax.faces.source": "formSeguimientoRemate",
                "javax.faces.partial.execute": "@all",
                "javax.faces.partial.render": "formSeguimientoRemate",
                "formSeguimientoRemate": "formSeguimientoRemate",
                "javax.faces.ViewState": self.current_view_state,
            }

            response = self._make_ajax_post(self.SEGUIMIENTO_URL, payload)
            response.raise_for_status()
            seguimiento_content = response.text
            print(f"  ✓ Loaded seguimiento data via POST")

            # Combine base HTML with seguimiento content
            combined_html = self._inject_seguimiento_content(
                base_html, seguimiento_content
            )
            return combined_html

        except Exception as e:
            print(f"  ⚠ Error loading seguimiento data: {e}")
            return None

    def _inject_seguimiento_content(self, base_html: str, content: str) -> str:
        """Inject seguimiento content into base HTML.

        Args:
            base_html: Base HTML page
            content: AJAX response content

        Returns:
            Combined HTML
        """
        import re

        # Extract CDATA content from the AJAX response
        cdata_pattern = r"<!\[CDATA\[(.*?)\]\]>"
        matches = re.findall(cdata_pattern, content, re.DOTALL)

        if matches:
            seguimiento_content = matches[-1]
            # Inject into the formSeguimientoRemate container
            pattern = r'(<form[^>]*id="formSeguimientoRemate"[^>]*>)(.*?)(</form>)'

            def replacer(match):
                return match.group(1) + seguimiento_content + match.group(3)

            return re.sub(pattern, replacer, base_html, flags=re.DOTALL)

        return base_html

    def _geocode_inmuebles(self, detail: RemateDetail) -> None:
        """Add geocoding (lat/lon) to all inmuebles in the detail.

        Uses the Google Maps Geocoding API with caching.

        Args:
            detail: The RemateDetail containing inmuebles to geocode
        """
        if not self.geocoding_client:
            return

        if not detail or not detail.inmuebles_tab or not detail.inmuebles_tab.inmuebles:
            return

        print(f"  Geocoding {len(detail.inmuebles_tab.inmuebles)} inmueble(s)...")

        geocoded = 0
        cached = 0
        failed = 0

        for i, inmueble in enumerate(detail.inmuebles_tab.inmuebles):
            # Skip if already has coordinates
            if inmueble.latitude and inmueble.longitude:
                print(
                    f"    Inmueble {i + 1}: Already has coordinates ({inmueble.latitude}, {inmueble.longitude})"
                )
                cached += 1
                continue

            # Build address data
            address_data = {
                "direccion": inmueble.direccion,
                "distrito": detail.inmuebles_tab.distrito,
                "provincia": detail.inmuebles_tab.provincia,
                "departamento": detail.inmuebles_tab.departamento,
            }

            # Geocode
            result = self.geocoding_client.geocode_inmueble(address_data)

            if result:
                lat, lon = result
                inmueble.latitude = lat
                inmueble.longitude = lon
                geocoded += 1
                print(f"    Inmueble {i + 1}: ✓ Geocoded ({lat}, {lon})")
            else:
                failed += 1
                print(f"    Inmueble {i + 1}: ✗ Failed to geocode")

        print(f"  Geocoding complete: {geocoded} new, {cached} cached, {failed} failed")

    def _compute_exchange_rates(self, detail: RemateDetail) -> None:
        """Compute and store prices in both PEN and USD.

        Args:
            detail: The RemateDetail to compute prices for
        """
        if not self.exchange_client or not detail or not detail.remate_tab:
            return

        print("  Computing exchange rates...")

        # Get current exchange rate
        rate = self.exchange_client.get_pen_to_usd_rate()
        if not rate:
            print("  ⚠ Could not get exchange rate")
            return

        remate_tab = detail.remate_tab

        # Parse and convert precio_base
        pen_value = parse_money_value(remate_tab.precio_base)
        if pen_value:
            remate_tab.precio_base_pen = pen_value
            remate_tab.precio_base_usd = pen_value * rate

        # Parse and convert arancel
        pen_value = parse_money_value(remate_tab.arancel)
        if pen_value:
            remate_tab.arancel_pen = pen_value
            remate_tab.arancel_usd = pen_value * rate

        # Parse and convert oblaje
        pen_value = parse_money_value(remate_tab.oblaje)
        if pen_value:
            remate_tab.oblaje_pen = pen_value
            remate_tab.oblaje_usd = pen_value * rate

        # Store exchange rate info
        remate_tab.exchange_rate = rate
        remate_tab.exchange_rate_date = date.today()

        print(f"  ✓ Exchange rate applied: 1 PEN = {rate:.4f} USD")

    def download_auction(
        self,
        remate: RemateListItem,
        include_detail: bool = True,
        include_seguimiento: bool = True,
    ) -> Auction:
        """Download complete data for a single auction.

        Args:
            remate: The remate list item
            include_detail: Whether to download detail page
            include_seguimiento: Whether to download seguimiento page

        Returns:
            Complete Auction object
        """
        detail = None
        seguimiento = None

        if include_detail:
            detail_html = self.download_detail_page(remate.numero_remate)
            parser = RemajuParser(detail_html)
            detail = parser.parse_detail_page(remate.numero_remate)

            # Geocode inmuebles after parsing detail
            self._geocode_inmuebles(detail)

            # Compute exchange rates
            self._compute_exchange_rates(detail)

        if include_seguimiento:
            seguimiento_html = self.download_seguimiento_page(remate.numero_remate)
            parser = RemajuParser(seguimiento_html)
            seguimiento = parser.parse_seguimiento_page()

        return Auction(
            numero_remate=remate.numero_remate,
            list_data=remate,
            detail=detail,
            seguimiento=seguimiento,
        )

    def download_auctions(self, limit: Optional[int] = 1) -> List[Auction]:
        """Download auction data.

        Args:
            limit: Maximum number of auctions to download. None for all.

        Returns:
            List of Auction objects
        """
        # Download list page
        list_html = self.download_list_page()
        parser = RemajuParser(list_html)
        remates = parser.parse_list_page()

        print(f"Found {len(remates)} remates on list page")

        # Limit the number of remates to process
        if limit:
            remates = remates[:limit]
            print(f"Processing first {len(remates)} remate(s)")

        # Download details for each remate
        auctions = []
        for i, remate in enumerate(remates, 1):
            print(f"\nProcessing remate {i}/{len(remates)}: {remate.numero_remate}")
            try:
                auction = self.download_auction(remate)
                auctions.append(auction)
            except Exception as e:
                print(f"Error downloading remate {remate.numero_remate}: {e}")
                continue

        return auctions

    def save_auctions(self, auctions: List[Auction], filename: str = "auctions.json"):
        """Save auctions to JSON file, merging with existing data.

        Updates existing auctions based on numero_remate, adds new ones.

        Args:
            auctions: List of Auction objects
            filename: Output filename
        """
        output_file = self.output_dir / filename

        # Load existing data if file exists
        existing_auctions: Dict[str, dict] = {}
        if output_file.exists():
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for auction_data in data.get("auctions", []):
                        numero_remate = auction_data.get("numero_remate")
                        if numero_remate:
                            existing_auctions[numero_remate] = auction_data
                print(
                    f"\nLoaded {len(existing_auctions)} existing auctions from {output_file}"
                )
            except (json.JSONDecodeError, IOError) as e:
                print(f"\nWarning: Could not load existing file: {e}")
                existing_auctions = {}

        # Merge new auctions with existing
        merged_count = 0
        added_count = 0
        for auction in auctions:
            auction_dict = auction.model_dump()
            numero_remate = auction.numero_remate

            if numero_remate in existing_auctions:
                # Update existing auction
                existing_auctions[numero_remate] = auction_dict
                merged_count += 1
            else:
                # Add new auction
                existing_auctions[numero_remate] = auction_dict
                added_count += 1

        # Convert to list and save
        data = {
            "auctions": list(existing_auctions.values()),
            "count": len(existing_auctions),
        }

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        print(
            f"Saved {added_count} new, {merged_count} updated, {len(existing_auctions)} total auction(s) to {output_file}"
        )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Download auction data from REMAJU website"
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data",
        help="Output directory for downloaded data (default: data)",
    )
    parser.add_argument(
        "--limit",
        "-l",
        type=int,
        default=1,
        help="Number of auctions to download (default: 1, use 0 for all)",
    )
    parser.add_argument(
        "--filename",
        "-f",
        type=str,
        default="auctions.json",
        help="Output filename (default: auctions.json)",
    )
    parser.add_argument(
        "--no-geocoding",
        action="store_true",
        help="Disable geocoding of inmuebles",
    )

    args = parser.parse_args()

    # Create downloader
    output_dir = Path(args.output)
    downloader = RemajuDownloader(output_dir, enable_geocoding=not args.no_geocoding)

    # Determine limit (0 means all)
    limit = None if args.limit == 0 else args.limit

    # Download auctions
    auctions = downloader.download_auctions(limit=limit)

    # Save to file
    downloader.save_auctions(auctions, args.filename)

    print("\nDownload complete!")


if __name__ == "__main__":
    main()
