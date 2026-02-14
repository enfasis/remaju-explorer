# REMAJU Auction Data Downloader

This is a Python project for downloading and processing auction data from the REMAJU (Remates Judiciales) website.

We use `uv` for running and managing the app.

To test functionality, run:

```bash
uv run edx-dle
```

Use modern Python 3.14 syntax. Prefer self-documenting code with clear names and method structure. Avoid comments. Keep the code and design simple overall.

## Flow Diagram

```
                    REMAJU Download Flow - View State Management
═══════════════════════════════════════════════════════════════════════════════

 1. INITIALIZATION
─────────────────
┌──────────────────────────────────────┐
│ get_list_page()                      │
│   GET /remateExterno.xhtml           │
│   • Extract view_state from HTML     │
│   • self.view_state = vs1            │
│   • self.list_view_state = vs1       │
│   • self.current_list_offset = 0     │
└──────────────────────┬───────────────┘
                       │
                       ▼

 2. LIST PAGINATION (Working - First Page)
───────────────────────────────────────────
┌──────────────────────────────┐
│ fetch_page(offset=0, rows=N) │
│   POST /remateExterno.xhtml  │
│   • Uses self.list_view_state│
│   • Sends vs1 in payload     │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ AJAX Response (XML)                  │
│   • Contains remate list (CDATA)     │
│   • Contains NEW view_state (vs2)    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Update state                         │
│   • self.list_view_state = vs2       │
│   • self.current_list_offset = 0     │
└──────────────────────────────────────┘
                       │
                       ▼

 3. LIST PAGINATION (Page 2)
────────────────────────────
┌──────────────────────────────┐
│ fetch_page(offset=N, rows=N) │
│   POST /remateExterno.xhtml  │
│   • Uses self.list_view_state│
│   • Sends vs2 in payload     │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ AJAX Response (XML)                  │
│   • Contains page 2 data             │
│   • Contains NEW view_state (vs3)    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Update state                         │
│   • self.list_view_state = vs3       │
│   • self.current_list_offset = 4     │
└──────────────────────────────────────┘
                       │
                       ▼

 4. DETAIL DOWNLOAD FLOW (Per Remate)
─────────────────────────────────────
┌──────────────────────────────────────┐
│ download_detail(remate)              │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ refresh_list_page()                  │
│   GET /remateExterno.xhtml           │
│   • Resets to list context           │
│   • Extract view_state from HTML     │
│   • self.view_state = vs4            │
│   • self.list_view_state = vs4       │
│                                      │
│   IF current_list_offset > 0:        │
│   fetch_page(current_offset, rows) │
│     • Restores to current offset     │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────┐
│ _get_cards_info()            │
│   fetch_page(offset=N, rows) │
│   • Uses self.list_view_state│
│   • Returns correct cards!   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Find card with matching remate #     │
│   • Get detalle_id from card info    │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ click_detail_button(detalle_id)      │
│   POST /remateExterno.xhtml          │
│   • Uses self.view_state             │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ get_detail_page()                    │
│   GET /mostrarDetalleRemate.xhtml    │
│   • Extract view_state from HTML     │
│   • self.view_state = vs5            │
└──────────┬───────────────────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│ Fetch detail tabs                    │
│   fetch_detail_tab("inmuebles")      │
│   fetch_detail_tab("cronograma")     │
│   • Uses self.view_state             │
└──────────────────────────────────────┘
                       │
                       ▼

 5. THE FIX - Offset Tracking
─────────────────────────────

 PROBLEM (Before Fix):
 ─────────────────────
 • refresh_list_page() always reset to page 1
 • _get_cards_info() returned first 4 items only
 • Could not find remates from page 2+

 SOLUTION (Implemented):
 ───────────────────────
 ┌──────────────────────────────────────┐
 │ RemajuSiteClient                     │
 │   + current_list_offset = 0          │
 │   + rows_per_page = N (default 4)    │
 │                                      │
 │ After fetch_page(offset, rows):      │
 │   current_list_offset = offset       │
 │                                      │
 │ In refresh_list_page():              │
 │   After GET, IF offset > 0:          │
 │     fetch_page(current_offset, rows) │
 │     • Restores correct list position │
 └──────────────────────────────────────┘

 STATE TRACKING:
 ───────────────
 • self.view_state        - Current page view state
 • self.list_view_state   - List page view state
 • self.current_list_offset - Current position in list
 • self.rows_per_page     - Items per page (configurable, default 4)

 PAGE SIZE CONFIGURATION:
 ────────────────────────
 The number of items retrieved per page can be configured using the
 page_size parameter. This affects the payload fields:
   • formBuscarRemateExterno:listaRemate_rows
   • formBuscarRemateExterno:listaRemate_rppDD

 Example: page_size=8 will retrieve 8 items per page instead of 4.
 ```

## Architecture

```
download.py
├── RemajuSiteClient          # HTTP client for REMAJU website
│   ├── get_list_page()       # Initial list page fetch
│   ├── fetch_page()          # AJAX pagination
│   ├── refresh_list_page()   # Restore list context + offset
│   ├── click_detail_button() # Select remate for detail view
│   ├── get_detail_page()     # Fetch detail HTML
│   └── fetch_detail_tab()    # Fetch detail tabs (inmuebles/cronograma)
│
└── RemajuDataService         # High-level data operations
    ├── download_list()       # Download paginated list
    ├── download_detail()     # Download single remate details
    └── download_auctions()   # Complete workflow

src/remaju/
├── new_parser.py             # HTML/XML parser for AJAX responses
├── models.py                 # Pydantic data models
├── captcha_solver.py         # Browser automation for CAPTCHA
├── geocoding.py              # Google Maps geocoding
└── exchange.py               # Exchange rate conversion
```

## Commands

```bash
# Install dependencies
make install

# Run the application
make run

# Download data
make download

# Run tests
make test

# Download with options
python download.py --pages 2 --debug debug_output

# Download with custom page size (8 items per page)
python download.py --pages 2 --page-size 8

# Download all options
python download.py --pages 3 --page-size 8 --output data --debug debug_output
```
