"""hCaptcha solver using Playwright and hcaptcha-challenger."""

import asyncio
import json
import pickle
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass

from playwright.async_api import async_playwright, Page, Browser, BrowserContext


@dataclass
class SessionData:
    """Session data extracted from browser after solving CAPTCHA."""

    cookies: list
    headers: dict
    local_storage: dict
    session_storage: dict


class CaptchaSolver:
    """hCaptcha solver using Playwright with stealth and hcaptcha-challenger."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cookies_file: Path = Path("data/cookies.pkl"),
        headless: bool = False,
    ):
        self.api_key = api_key
        self.cookies_file = cookies_file
        self.cookies_file.parent.mkdir(parents=True, exist_ok=True)
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def _get_api_key(self) -> str:
        """Get Gemini API key from environment or init."""
        import os

        if self.api_key:
            return self.api_key

        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set. "
                "Please set it to enable CAPTCHA solving."
            )
        return key

    def _load_cookies(self) -> Optional[list]:
        """Load saved cookies if they exist."""
        if self.cookies_file.exists():
            try:
                with open(self.cookies_file, "rb") as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"⚠ Could not load cookies: {e}")
        return None

    def _save_cookies(self, cookies: list):
        """Save cookies to file."""
        try:
            with open(self.cookies_file, "wb") as f:
                pickle.dump(cookies, f)
            print(f"✓ Cookies saved to {self.cookies_file}")
        except Exception as e:
            print(f"⚠ Could not save cookies: {e}")

    def _has_captcha(self, html: str) -> bool:
        """Check if HTML contains hCaptcha."""
        return "h-captcha" in html.lower() or "hcaptcha" in html.lower()

    async def _solve_captcha(self, page: Page) -> bool:
        """Solve hCaptcha challenge on the page."""
        try:
            from hcaptcha_challenger.agent import AgentV, AgentConfig
            from hcaptcha_challenger.utils import SiteKey

            print("🤖 Initializing hCaptcha solver...")

            # Get API key - will raise ValueError if not set
            api_key = self._get_api_key()
            print(f"   Using API key: {api_key[:10]}...")

            agent_config = AgentConfig(GEMINI_API_KEY=api_key)
            agent = AgentV(page=page, agent_config=agent_config)

            print("🖱️  Clicking checkbox...")
            await agent.robotic_arm.click_checkbox()

            print("⏳ Waiting for challenge...")
            await agent.wait_for_challenge()

            if agent.cr_list:
                from hcaptcha_challenger.models import CaptchaResponse

                cr: CaptchaResponse = agent.cr_list[-1]
                print(
                    f"✓ Challenge result: {json.dumps(cr.model_dump(by_alias=True), indent=2)}"
                )
                return cr.is_pass if hasattr(cr, "is_pass") else True

            return True

        except Exception as e:
            print(f"⚠ Error solving CAPTCHA: {e}")
            return False

    async def _extract_session_data(self, page: Page) -> SessionData:
        """Extract session data from browser page."""
        cookies = await page.context.cookies()

        local_storage = await page.evaluate("() => Object.assign({}, localStorage)")
        session_storage = await page.evaluate("() => Object.assign({}, sessionStorage)")

        headers = {
            "User-Agent": await page.evaluate("() => navigator.userAgent"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

        return SessionData(
            cookies=cookies,
            headers=headers,
            local_storage=local_storage,
            session_storage=session_storage,
        )

    async def solve_and_get_session(
        self, url: str
    ) -> Optional[tuple[str, SessionData]]:
        """Navigate to URL, solve CAPTCHA if present, and return page content with session data."""
        print(f"🌐 Opening browser (headless={self.headless})...")
        async with async_playwright() as p:
            print("   Launching Chromium...")
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            print("   ✓ Browser launched")

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            )

            # Load cookies if available
            saved_cookies = self._load_cookies()
            if saved_cookies:
                await context.add_cookies(saved_cookies)
                print("✓ Loaded saved cookies")

            page = await context.new_page()

            # Add stealth script
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = { runtime: {} };
            """)

            print(f"🌐 Navigating to {url}...")
            await page.goto(url, wait_until="load", timeout=60000)

            html = await page.content()

            if self._has_captcha(html):
                print("🛡️  CAPTCHA detected, solving...")
                success = await self._solve_captcha(page)
                if not success:
                    print("❌ Failed to solve CAPTCHA")
                    await browser.close()
                    return None
                print("✓ CAPTCHA solved successfully")

                # Submit the form with the CAPTCHA response
                print("📤 Submitting form...")
                try:
                    # Click the submit button
                    await page.click('input[type="submit"]')
                    # Wait for navigation to complete
                    await page.wait_for_load_state("networkidle")
                    print("✓ Form submitted, page loaded")
                except Exception as e:
                    print(f"⚠ Error submitting form: {e}")

                # Get updated HTML after solving and submitting
                html = await page.content()
            else:
                print("✓ No CAPTCHA detected")

            # Wait a moment for any redirects or page updates
            await asyncio.sleep(2)

            # Extract session data
            session_data = await self._extract_session_data(page)

            # Save cookies for future use
            self._save_cookies(session_data.cookies)

            await browser.close()
            return html, session_data

    def solve(self, url: str) -> Optional[tuple[str, SessionData]]:
        """Synchronous wrapper for solve_and_get_session."""
        return asyncio.run(self.solve_and_get_session(url))

    def solve_with_click(
        self, url: str, remate_id: str
    ) -> Optional[tuple[str, SessionData]]:
        """Navigate to URL and click the Detalle button for a specific remate.

        This is needed because detail pages require navigation from the list page.

        Args:
            url: The list page URL
            remate_id: The remate number to click on

        Returns:
            Tuple of (html_content, session_data)
        """
        return asyncio.run(self._solve_with_click_async(url, remate_id))

    def solve_with_seguimiento_click(
        self, url: str, remate_id: str
    ) -> Optional[tuple[str, SessionData]]:
        """Navigate to URL and click the Seguimiento button for a specific remate.

        This is needed because seguimiento pages require navigation from the list page.

        Args:
            url: The list page URL
            remate_id: The remate number to click on

        Returns:
            Tuple of (html_content, session_data)
        """
        return asyncio.run(self._solve_with_seguimiento_click_async(url, remate_id))

    async def _solve_with_click_async(
        self, url: str, remate_id: str
    ) -> Optional[tuple[str, SessionData]]:
        """Async version of solve_with_click."""
        print(f"🌐 Opening browser (headless={self.headless})...")
        async with async_playwright() as p:
            print("   Launching Chromium...")
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            print("   ✓ Browser launched")

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            )

            # Load cookies if available
            saved_cookies = self._load_cookies()
            if saved_cookies:
                await context.add_cookies(saved_cookies)
                print("✓ Loaded saved cookies")

            page = await context.new_page()

            # Add stealth script
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = { runtime: {} };
            """)

            print(f"🌐 Navigating to list page...")
            await page.goto(url, wait_until="load", timeout=60000)

            html = await page.content()

            if self._has_captcha(html):
                print("🛡️  CAPTCHA detected, solving...")
                success = await self._solve_captcha(page)
                if not success:
                    print("❌ Failed to solve CAPTCHA")
                    await browser.close()
                    return None
                print("✓ CAPTCHA solved successfully")

                # Submit the form
                print("📤 Submitting form...")
                try:
                    await page.click('input[type="submit"]')
                    await page.wait_for_load_state("networkidle")
                    print("✓ Form submitted, page loaded")
                except Exception as e:
                    print(f"⚠ Error submitting form: {e}")

                html = await page.content()
            else:
                print("✓ No CAPTCHA detected")

            # Now click the Detalle button for the specific remate
            print(f"🖱️  Clicking Detalle button for remate {remate_id}...")

            # Find the Detalle button - it has text "Detalle"
            try:
                # Wait for the page to fully load
                await page.wait_for_load_state("networkidle")

                # Find all buttons with "Detalle" text
                buttons = await page.query_selector_all("button")
                for button in buttons:
                    text = await button.text_content()
                    if text and "Detalle" in text:
                        print(f"   Found Detalle button: {text.strip()}")
                        # Click this button
                        await button.click()
                        print("✓ Clicked Detalle button")
                        # Wait for navigation to complete
                        await page.wait_for_load_state("networkidle")
                        # Wait for the detail page to load
                        await asyncio.sleep(3)
                        break
            except Exception as e:
                print(f"⚠ Error clicking Detalle button: {e}")

            # Get the final HTML
            html = await page.content()

            # Check if we got the detail page
            if "pgDetalleRemate" in html or "formDetalleRemate" in html:
                print("✓ Got detail page")

                # Wait for tab content to load
                print("   Waiting for tab content to load...")
                await asyncio.sleep(2)

                # Try to click on each tab to ensure content loads
                try:
                    # Click on Inmuebles tab
                    tab_links = await page.query_selector_all("a[href*='tbInmuebles']")
                    for link in tab_links:
                        await link.click()
                        await asyncio.sleep(1)
                        print("   Clicked Inmuebles tab")
                        break

                    # Click on Cronograma tab
                    tab_links = await page.query_selector_all("a[href*='tbCronograma']")
                    for link in tab_links:
                        await link.click()
                        await asyncio.sleep(1)
                        print("   Clicked Cronograma tab")
                        break
                except Exception as e:
                    print(f"⚠ Error clicking tabs: {e}")

                # Get final HTML after tab clicks
                html = await page.content()
            else:
                print("⚠ Still on list page, trying direct navigation")

            # Extract session data
            session_data = await self._extract_session_data(page)

            # Save cookies for future use
            self._save_cookies(session_data.cookies)

            await browser.close()
            return html, session_data

    async def _solve_with_seguimiento_click_async(
        self, url: str, remate_id: str
    ) -> Optional[tuple[str, SessionData]]:
        """Navigate to URL and click the Seguimiento button for a specific remate."""
        print(f"🌐 Opening browser (headless={self.headless})...")
        async with async_playwright() as p:
            print("   Launching Chromium...")
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            print("   ✓ Browser launched")

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            )

            # Load cookies if available
            saved_cookies = self._load_cookies()
            if saved_cookies:
                await context.add_cookies(saved_cookies)
                print("✓ Loaded saved cookies")

            page = await context.new_page()

            # Add stealth script
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                window.chrome = { runtime: {} };
            """)

            print(f"🌐 Navigating to list page...")
            await page.goto(url, wait_until="load", timeout=60000)

            html = await page.content()

            if self._has_captcha(html):
                print("🛡️  CAPTCHA detected, solving...")
                success = await self._solve_captcha(page)
                if not success:
                    print("❌ Failed to solve CAPTCHA")
                    await browser.close()
                    return None
                print("✓ CAPTCHA solved successfully")

                # Submit the form
                print("📤 Submitting form...")
                try:
                    await page.click('input[type="submit"]')
                    await page.wait_for_load_state("networkidle")
                    print("✓ Form submitted, page loaded")
                except Exception as e:
                    print(f"⚠ Error submitting form: {e}")

                html = await page.content()
            else:
                print("✓ No CAPTCHA detected")

            # Now click the Seguimiento button for the specific remate
            print(f"🖱️  Clicking Seguimiento button for remate {remate_id}...")

            try:
                await page.wait_for_load_state("networkidle")

                # Find all buttons with "Seguimiento" text
                buttons = await page.query_selector_all("button")
                for button in buttons:
                    text = await button.text_content()
                    if text and "Seguimiento" in text:
                        print(f"   Found Seguimiento button: {text.strip()}")
                        await button.click()
                        print("✓ Clicked Seguimiento button")
                        # Wait longer for navigation
                        await page.wait_for_load_state("networkidle")
                        await asyncio.sleep(5)
                        break
            except Exception as e:
                print(f"⚠ Error clicking Seguimiento button: {e}")

            html = await page.content()

            if "formSeguimientoRemate" in html:
                print("✓ Got seguimiento page")
            elif "pgNavegacion" in html:
                # Check if we navigated to a different page
                if "Seguimiento" in html and "Remate" in html:
                    print("✓ Got seguimiento page (found in content)")
                else:
                    print("⚠ Still on list/navigation page")
            else:
                print("⚠ Unexpected page content")

            session_data = await self._extract_session_data(page)
            self._save_cookies(session_data.cookies)

            await browser.close()
            return html, session_data


class BrowserDownloader:
    """Browser-based downloader that can solve CAPTCHAs."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cookies_file: Path = Path("data/cookies.pkl"),
        headless: bool = False,
    ):
        self.solver = CaptchaSolver(
            api_key=api_key,
            cookies_file=cookies_file,
            headless=headless,
        )
        self.session_data: Optional[SessionData] = None

    def get_page(self, url: str) -> tuple[str, SessionData]:
        """Get page content, solving CAPTCHA if necessary.

        Returns:
            Tuple of (html_content, session_data)
        """
        result = self.solver.solve(url)

        if not result:
            raise RuntimeError("Failed to solve CAPTCHA or get session")

        html, self.session_data = result
        return html, self.session_data

    def get_detail_page(
        self, list_page_url: str, remate_id: str
    ) -> tuple[str, SessionData]:
        """Navigate from list page to detail page by clicking the Detalle button.

        This is needed because the detail page requires clicking from the list page.

        Args:
            list_page_url: URL of the list page
            remate_id: The remate number to click on

        Returns:
            Tuple of (html_content, session_data)
        """
        return self.solver.solve_with_click(list_page_url, remate_id)

    def get_seguimiento_page(
        self, list_page_url: str, remate_id: str
    ) -> tuple[str, SessionData]:
        """Navigate from list page to seguimiento page by clicking the Seguimiento button.

        This is needed because the seguimiento page requires clicking from the list page.

        Args:
            list_page_url: URL of the list page
            remate_id: The remate number to click on

        Returns:
            Tuple of (html_content, session_data)
        """
        return self.solver.solve_with_seguimiento_click(list_page_url, remate_id)

    def update_session(self, session_data: SessionData):
        """Update stored session data."""
        self.session_data = session_data
        self.solver._save_cookies(session_data.cookies)
