# REMAJU Website Scraping Documentation

## Overview
Website: https://remaju.pj.gob.pe/remaju/pages/publico/remateExterno.xhtml
Technology: JavaServer Faces (JSF) with PrimeFaces 8.0
Total Records: 197 remates
Records per page: 4

## Key Findings

### 1. Technology Stack
- **Frontend**: PrimeFaces 8.0 (JSF framework)
- **State Management**: Uses `javax.faces.ViewState` hidden field
- **AJAX**: All interactions use PrimeFaces AJAX (PrimeFaces.ab)
- **Security**: Has CAPTCHA protection on list page, but NOT on detail/seguimiento pages

### 2. Important Discovery: No CAPTCHA on Detail/Seguimiento Pages

**CRITICAL**: While the list page has CAPTCHA, the detail and seguimiento pages do NOT require CAPTCHA verification. This means we can:
1. Use saved HTML fixtures for the list page (or manually download once)
2. Access detail and seguimiento pages directly using requests

### 3. Page Structure

#### Main List Page (`remateExterno.xhtml`)
- Shows 4 remates per page
- Pagination with pages 1-5 (50 total pages for 197 records)
- Has CAPTCHA protection
- Each remate has 3 action buttons:
  - **Seguimiento**: Shows tracking/history (goes to `mostrarSeguimientoRemate.xhtml`)
  - **Detalle**: Shows detailed info with 3 tabs (goes to `mostrarDetalleRemate.xhtml`)
  - **Aviso**: Shows auction notice

#### Detail Page (`mostrarDetalleRemate.xhtml`)
URL: `https://remaju.pj.gob.pe/remaju/pages/publico/mostrarDetalleRemate.xhtml`

Has 3 tabs:
1. **Remate**: General auction information
2. **Inmuebles**: Property details table
3. **Cronograma**: Schedule/timeline with 5 phases

**Note**: This page can be accessed directly without CAPTCHA.

#### Seguimiento Page (`mostrarSeguimientoRemate.xhtml`)
URL: `https://remaju.pj.gob.pe/remaju/pages/publico/mostrarSeguimientoRemate.xhtml`

Shows:
- Expediente details
- Convocatoria tracking information
- No tabs, single view

**Note**: This page can be accessed directly without CAPTCHA.

### 4. Data Structure

#### Remate Card (List View)
```json
{
  "numero_remate": "22096",
  "convocatoria": "PRIMERA CONVOCATORIA",
  "tipo": "REMATE SIMPLE",
  "distrito": "SAN BORJA",
  "fecha_presentacion": "26/02/2026",
  "hora_presentacion": "11:59 AM",
  "fase": "Publicación e Inscripcion",
  "estado": "En proceso",
  "precio_base": "S/. 1,163,355.99",
  "descripcion": "..."
}
```

#### Remate Detail (Remate Tab)
```json
{
  "expediente": "15700-2023-0-1817-JR-CO-07",
  "distrito_judicial": "LIMA",
  "organo_jurisdiccional": "7°JUZGADO CIVIL-COMERCIAL",
  "instancia": "JUZGADO ESPECIALIZADO",
  "juez": "VARILLAS SOLANO, JUAN GUSTAVO",
  "especialista": "CACERES CASTILLO EDWARD JESUS",
  "materia": "EJECUCION DE GARANTIAS",
  "resolucion": "6",
  "fecha_resolucion": "21/04/2025",
  "convocatoria": "PRIMERA CONVOCATORIA",
  "tasacion": "S/. 1,745,033.98",
  "precio_base": "S/. 1,163,355.99",
  "incremento_entre_ofertas": "S/. 3,490.07",
  "arancel": "S/. 1,100.00",
  "oblaje": "S/. 174,503.40",
  "descripcion": "...",
  "nro_inscritos": 0
}
```

#### Inmuebles (Properties Tab)
```json
{
  "distrito_judicial": "LIMA",
  "departamento": "LIMA",
  "provincia": "LIMA",
  "distrito": "SAN BORJA",
  "inmuebles": [
    {
      "partida_registral": "12714204",
      "tipo_inmueble": "DEPARTAMENTO",
      "direccion": "DEPARTAMENTO 802, OCTAVO PISO Y AZOTEA...",
      "carga_gravamen": "HIPOTECA CONSTRUCTORA IVALEX S.A.C....",
      "porcentaje_a_remstar": "100%",
      "imagenes": 0
    }
  ]
}
```

#### Cronograma (Schedule Tab)
5 phases:
1. Publicación e Inscripcion (13/02/2026 - 22/02/2026)
2. Validación de Inscripción (23/02/2026 - 25/02/2026)
3. Presentación de Ofertas (26/02/2026 - 27/02/2026)
4. Pago Saldo (02/03/2026 - 04/03/2026)
5. Validación del Saldo (05/03/2026 - 09/03/2026)

#### Seguimiento
```json
{
  "expediente": {
    "nro_expediente": "15700-2023-0-1817-JR-CO-07",
    "distrito_judicial": "LIMA",
    "especialidad": "COMERCIAL",
    "instancia": "JUZGADO ESPECIALIZADO",
    "organo_jurisdiccional": "7°JUZGADO CIVIL-COMERCIAL"
  },
  "seguimiento": {
    "nro_convocatoria": "PRIMERA CONVOCATORIA",
    "fecha_registro": "12/02/2026",
    "procesado_por": "ORDEN JUDICIAL",
    "reanudado": "NO",
    "fase_convocatoria": "Publicación e Inscripcion",
    "estado_convocatoria": "En proceso"
  }
}
```

### 5. Implementation Architecture

#### Parser (`src/remaju/parser.py`)
Uses **selectolax** for fast HTML parsing:

```python
from selectolax.parser import HTMLParser

class RemajuParser:
    def __init__(self, html: str):
        self.tree = HTMLParser(html)
    
    def parse_list_page(self) -> List[RemateListItem]:
        # Parse cards with id pattern: formBuscarRemateExterno:listaRemate:X:j_idt125
        cards = self.tree.css('[id*="listaRemate:"][id*="j_idt125"]')
        return [self._parse_remate_card(card) for card in cards]
    
    def parse_detail_page(self, numero_remate: str) -> RemateDetail:
        # Parse all 3 tabs
        remate_tab = self._parse_remate_tab()
        inmuebles_tab = self._parse_inmuebles_tab()
        cronograma_tab = self._parse_cronograma_tab()
        return RemateDetail(...)
    
    def parse_seguimiento_page(self) -> Seguimiento:
        # Parse expediente and seguimiento sections
        return Seguimiento(...)
```

#### Downloader (`download.py`)
Uses **requests** library:

```python
class RemajuDownloader:
    def download_list_page(self) -> str:
        # Note: This may hit CAPTCHA
        return self.session.get(self.LIST_URL).text
    
    def download_detail_page(self, remate_id: str) -> str:
        # No CAPTCHA here!
        return self.session.get(self.DETAIL_URL).text
    
    def download_seguimiento_page(self, remate_id: str) -> str:
        # No CAPTCHA here!
        return self.session.get(self.SEGUIMIENTO_URL).text
```

#### Testing (`tests/`)
Uses **responses** library for mocking:

```python
@pytest.fixture
def mock_list_page(mock_responses, list_page_html):
    mock_responses.add(
        responses.GET,
        "https://remaju.pj.gob.pe/remaju/pages/publico/remateExterno.xhtml",
        body=list_page_html,
        status=200
    )
```

### 6. Important CSS Selectors

```css
/* Remate cards (4 per page) */
[id*='listaRemate:'][id*='j_idt125']

/* Action buttons for remate at index {i} */
formBuscarRemateExterno:listaRemate:{i}:j_idt164  /* Seguimiento */
formBuscarRemateExterno:listaRemate:{i}:j_idt165  /* Detalle */
formBuscarRemateExterno:listaRemate:{i}:j_idt167  /* Aviso */

/* Pagination */
formBuscarRemateExterno:listaRemate_paginator_bottom
.ui-paginator-page  /* Page number buttons */
.ui-paginator-next  /* Next button */
.ui-paginator-prev  /* Previous button */

/* Labels (bold text) */
.text-bold

/* Data tables */
[id*="dtResumenInmueble_data"]  /* Inmuebles table */
[id*="dtCronograma_data"]       /* Cronograma table */
```

### 7. URLs
- **List**: https://remaju.pj.gob.pe/remaju/pages/publico/remateExterno.xhtml
- **Detail**: https://remaju.pj.gob.pe/remaju/pages/publico/mostrarDetalleRemate.xhtml
- **Seguimiento**: https://remaju.pj.gob.pe/remaju/pages/publico/mostrarSeguimientoRemate.xhtml

### 8. Current Implementation Strategy

#### Using Requests + selectolax (IMPLEMENTED)

**Advantages:**
- ✅ No browser automation needed
- ✅ Fast parsing with selectolax
- ✅ Easy to test with mocked responses
- ✅ Detail/Seguimiento pages work without CAPTCHA
- ✅ Can use saved fixtures for list page

**Implementation:**
1. Use saved HTML fixtures for list page testing
2. Download list page once (manual or automated with CAPTCHA solving)
3. Parse remate IDs from list
4. For each remate, request detail and seguimiento pages directly
5. Parse all HTML with selectolax
6. Save structured data as JSON

**Files:**
- `src/remaju/parser.py` - HTML parsing with selectolax
- `src/remaju/models.py` - Pydantic data models
- `download.py` - Download script using requests
- `tests/test_retrieve_auctions.py` - Tests with mocked HTTP

### 9. Saved Test Files
All HTML sources saved in `tests/fixtures/`:
- `remate_externo_list_page1.html` - Main list page
- `detalle_remate_22096_full.html` - Detail page with all tabs
- `seguimiento_remate_22096.html` - Seguimiento page

### 10. Usage Workflow

#### For Testing (Mocked)
```python
# Tests use fixtures, no real HTTP requests
uv run pytest tests/test_retrieve_auctions.py
```

#### For Development
```python
# 1. Download data (uses requests)
uv run python download.py --limit 5

# 2. Visualize in Streamlit
uv run streamlit run main.py
```

### 11. Pagination Logic

The site shows 197 total remates with 4 per page = 50 pages.

**Pagination elements:**
- `.ui-paginator-page` - Page number links (1, 2, 3, 4, 5...)
- `.ui-paginator-next` - Next page button
- `.ui-paginator-prev` - Previous page button

**Note**: For testing, we use saved fixtures. For production scraping, handle pagination by:
1. Parsing current page
2. Clicking next page button (or calculating page URLs)
3. Repeating until all pages processed

### 12. Data Validation

Use saved HTML files to:
1. Test parsing logic without hitting the website
2. Validate selectors work correctly
3. Mock responses for unit tests
4. Detect website changes (if tests fail)

### 13. Next Steps

1. ✅ Implement requests-based scraper
2. ✅ Create selectolax parser
3. ✅ Build Pydantic models
4. ✅ Add test suite with mocks
5. ✅ Create Streamlit visualization
6. 🔄 Consider CAPTCHA solving for list page automation
7. 🔄 Add retry logic and error handling
8. 🔄 Implement incremental updates (only download new/changed auctions)

## Technical Notes

### HTML Parsing with selectolax

Selectolax is significantly faster than BeautifulSoup:

```python
# selectolax (fast)
from selectolax.parser import HTMLParser
tree = HTMLParser(html)
cards = tree.css('[id*="listaRemate:"]')

# BeautifulSoup (slower)
from bs4 import BeautifulSoup
soup = BeautifulSoup(html, 'html.parser')
cards = soup.find_all(id=lambda x: x and 'listaRemate:' in x)
```

### Pydantic Models

Type-safe data handling with validation:

```python
from pydantic import BaseModel
from datetime import date

class RemateListItem(BaseModel):
    numero_remate: str
    fecha_presentacion: date
    precio_base: Optional[str] = None
    
# Automatic validation
remate = RemateListItem(numero_remate="22096", fecha_presentacion="2026-02-26")
```

### Testing with responses

Mock HTTP requests without hitting real servers:

```python
import responses

@responses.activate
def test_download():
    responses.add(
        responses.GET,
        "https://remaju.pj.gob.pe/...",
        body="<html>...</html>",
        status=200
    )
    # Test code here
```

## Summary

This implementation uses:
- **requests**: HTTP client (no browser needed)
- **selectolax**: Fast HTML parsing
- **pydantic**: Data validation
- **responses**: HTTP mocking for tests
- **streamlit**: Web visualization

The key insight is that while the list page has CAPTCHA, detail and seguimiento pages do not, allowing us to use a simple requests-based approach with saved fixtures for testing.
