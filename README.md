# Remaju - REMAJU Judicial Auction Scraper

A Python application for scraping and visualizing judicial auction data from REMAJU (Sistema de Remates Virtuales del Poder Judicial del Perú).

## Features

- **Data Scraping**: Download auction data from REMAJU website
- **Data Modeling**: Pydantic models for type-safe data handling
- **HTML Parsing**: Fast HTML parsing using selectolax
- **Data Visualization**: Interactive Streamlit dashboard
- **Testing**: Comprehensive test suite with mocked HTTP requests

## Installation

Install all dependencies using uv:

```bash
uv sync
```

This will install:
- pydantic: Data validation and modeling
- streamlit: Web application framework
- selectolax: Fast HTML parsing
- responses: HTTP request mocking for tests
- pandas: Data manipulation
- requests: HTTP client

## Usage

### Quick Start (using Makefile)

```bash
# Install dependencies
make install

# Download auction data (with automatic geocoding)
make download

# Launch the application
make run

# Run tests
make test

# Clean data files
make clean
```

### Manual Commands

#### 1. Download Auction Data

```bash
# Download only the first auction (default) with geocoding
uv run python download.py

# Download first 5 auctions
uv run python download.py --limit 5

# Download all auctions (use with caution - 197 total)
uv run python download.py --limit 0

# Download without geocoding (if you don't have API key)
uv run python download.py --no-geocoding

# Save to custom directory
uv run python download.py --output ./my_data --filename my_auctions.json

# Show help
uv run python download.py --help
```

Downloaded data is saved to `data/auctions.json` by default.

**Features:**
- ✅ **Merges data** with existing auctions (updates based on `numero_remate`)
- ✅ **Automatic geocoding** - Adds latitude/longitude to each inmueble
- ✅ **Smart caching** - Geocoding results are cached to minimize API calls
- ✅ **Fallback fixtures** - Uses saved HTML when website returns landing page

**Geocoding Requirements:**
- Set `geocoding_api_key` in `.env` file
- Geocoding is enabled by default (use `--no-geocoding` to disable)
- Cache stored in `data/geocoding_cache.json`

### 2. Visualize Data

Launch the Streamlit dashboard to explore the data:

```bash
uv run streamlit run main.py
```

The dashboard provides:
- **List View**: Table view of all auctions with filters
- **Detail View**: Complete auction information including:
  - General information (expediente, judge, prices)
  - Properties (inmuebles) with details
  - Schedule (cronograma) with timeline
  - Tracking (seguimiento) information

### 4. Run Tests

Run the test suite with mocked HTTP requests:

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_retrieve_auctions.py

# Run with coverage
uv run pytest --cov
```

The test suite includes:
- `TestParseListPage`: Tests for parsing the auction list
- `TestParseDetailPage`: Tests for parsing detail pages (all 3 tabs)
- `TestParseSeguimientoPage`: Tests for parsing tracking pages
- `TestDownloadWithMocks`: Tests for download functionality with mocked HTTP
- `TestAuctionModel`: Tests for the Auction model

## Project Structure

```
remaju/
├── src/
│   └── remaju/
│       ├── __init__.py          # Package initialization
│       ├── models.py            # Pydantic models
│       ├── parser.py            # HTML parser with selectolax
│       └── geocoding.py         # Google Maps geocoding with caching
├── tests/
│   ├── conftest.py              # Pytest fixtures
│   ├── test_retrieve_auctions.py # Main test suite
│   ├── fixtures/                # HTML test fixtures
│   │   ├── remate_externo_list_page1.html
│   │   ├── detalle_remate_22096_full.html
│   │   └── seguimiento_remate_22096.html
│   └── data/                    # Scraped data and documentation
│       ├── scraped_data.json
│       └── SCRAPING_DOCUMENTATION.md
├── data/                        # Downloaded auction data (created by download.py)
│   ├── auctions.json            # Auction data
│   └── geocoding_cache.json     # Geocoding cache
├── download.py                  # Download script (with integrated geocoding)
├── main.py                      # Streamlit visualization app
├── README.md                    # This file
└── pyproject.toml               # Project configuration
```

## Data Models

### Auction
Complete auction combining list, detail and seguimiento:

```python
{
  "numero_remate": "22096",
  "list_data": RemateListItem,
  "detail": RemateDetail,
  "seguimiento": Seguimiento
}
```

### RemateListItem
Auction information from list page:

```python
{
  "numero_remate": "22096",
  "convocatoria": "PRIMERA CONVOCATORIA",
  "tipo": "REMATE SIMPLE",
  "distrito": "SAN BORJA",
  "fecha_presentacion": "2026-02-26",
  "hora_presentacion": "11:59 AM",
  "fase": "Publicación e Inscripcion",
  "estado": "En proceso",
  "precio_base": "S/. 1,163,355.99",
  "descripcion": "..."
}
```

### RemateDetail
Complete detail with 3 tabs:

```python
{
  "numero_remate": "22096",
  "tabs": ["Remate", "Inmuebles", "Cronograma"],
  "remate_tab": RemateTab,       # General info
  "inmuebles_tab": InmueblesTab,  # Properties
  "cronograma_tab": CronogramaTab # Schedule
}
```

### Seguimiento
Tracking information:

```python
{
  "expediente": Expediente,
  "seguimiento": SeguimientoData
}
```

## HTML Parsing

The parser uses **selectolax** for fast HTML parsing. Key features:

- CSS selectors for element extraction
- Text cleaning and normalization
- Date/datetime parsing
- Money amount parsing
- Label-value pair extraction

Example usage:

```python
from remaju.parser import RemajuParser

# Parse list page
parser = RemajuParser(html_content)
remates = parser.parse_list_page()

# Parse detail page
detail = parser.parse_detail_page("22096")

# Parse seguimiento page
seguimiento = parser.parse_seguimiento_page()
```

## Testing Strategy

Tests use the **responses** library to mock HTTP requests:

1. **Fixtures**: HTML files saved in `tests/fixtures/`
2. **Mocks**: HTTP responses are mocked in `conftest.py`
3. **Isolation**: No real HTTP requests during testing
4. **Coverage**: Tests cover parsing, downloading, and model validation

To update fixtures with fresh data:
```bash
# Download fresh HTML and copy to fixtures
# (Requires manual download from the website)
```

## Configuration

### Environment Variables

No environment variables required for basic usage.

### Custom Data Directory

You can customize the output directory:

```python
from download import RemajuDownloader
from pathlib import Path

downloader = RemajuDownloader(output_dir=Path("./custom_data"))
auctions = downloader.download_auctions(limit=5)
downloader.save_auctions(auctions, "my_auctions.json")
```

## API Endpoints

The scraper interacts with these endpoints:

- **List**: `https://remaju.pj.gob.pe/remaju/pages/publico/remateExterno.xhtml`
- **Detail**: `https://remaju.pj.gob.pe/remaju/pages/publico/mostrarDetalleRemate.xhtml`
- **Seguimiento**: `https://remaju.pj.gob.pe/remaju/pages/publico/mostrarSeguimientoRemate.xhtml`

## Development

### Adding New Tests

1. Add fixtures to `tests/fixtures/`
2. Add mock responses to `conftest.py`
3. Write tests in `tests/test_retrieve_auctions.py`

### Extending Models

1. Add fields to models in `src/remaju/models.py`
2. Update parser in `src/remaju/parser.py`
3. Update tests and fixtures

### Running Linting

```bash
# If ruff is installed
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Notes

- **CAPTCHA**: The list page has CAPTCHA, but detail and seguimiento pages don't require it
- **Rate Limiting**: Be respectful when downloading large amounts of data
- **Data Freshness**: Auction data changes frequently, run download.py regularly
- **Storage**: Each auction includes full detail (~50KB), plan storage accordingly

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest`
5. Submit a pull request

## Support

For issues or questions, please open an issue on GitHub.

## Resources

- [selectolax Documentation](https://github.com/rushter/selectolax)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [REMAJU Website](https://remaju.pj.gob.pe)
