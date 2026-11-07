import os

from playwright.sync_api import sync_playwright


def main() -> None:
    errors: list[str] = []
    url = os.environ.get("EXPLORER_URL", "http://127.0.0.1:5173/")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page()
        page.route("https://api.exchangerate-api.com/**", lambda route: route.fulfill(json={"base": "PEN", "date": "2026-11-07", "rates": {"USD": 0.25}}))
        page.route("https://tile.openstreetmap.org/**", lambda route: route.abort())
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url, wait_until="networkidle")
        page.get_by_role("link", name="explorador remaju").wait_for()
        page.get_by_role("heading", name="Remates", exact=True).wait_for()
        page.locator(".item").first.wait_for()
        assert page.locator(".item").count() == 12
        page.get_by_label("Ver precios en").select_option("USD")
        assert page.locator(".item").count() == 12
        page.get_by_role("button", name="Abrir glosario").click()
        page.get_by_role("heading", name="Guía rápida").wait_for()
        page.get_by_role("button", name="Cerrar glosario").click()
        page.get_by_label("Mostrar mapa").check()
        page.get_by_role("region", name="Mapa de Perú").wait_for()
        page.get_by_text("No hay coordenadas registradas", exact=False).wait_for()
        page.locator(".item").first.click(position={"x": 10, "y": 10})
        page.get_by_role("button", name="Inmuebles", exact=True).click()
        page.get_by_role("heading", name="Cargas y gravámenes").first.wait_for()
        page.get_by_role("button", name="Cronograma", exact=True).click()
        assert page.locator("tbody tr").count() == 5
        page.get_by_role("button", name="Documentos", exact=True).click()
        page.get_by_text("La resolución y el aviso requieren navegación", exact=False).wait_for()
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("button", name="Activar modo oscuro").click()
        assert page.locator("html").get_attribute("data-theme") == "dark"
        assert not errors, errors
        browser.close()


if __name__ == "__main__":
    main()
