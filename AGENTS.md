# Agent Instructions for Remaju

## Code Style
- Remove all comments from code
- Be concise and direct
- Use type hints where appropriate
- Keep functions focused and small

## Testing
- **Run all tests**: `uv run pytest` or `make test`
- **Run tests with verbose output**: `uv run pytest -v`
- **Run specific test file**: `uv run pytest tests/<test_file>.py`

## Project Structure
- Python 3.14+ project managed with uv
- Tests located in `tests/` directory
- Main code in `src/remaju/`
- Entry points: `download.py`, `main.py`

## Development Commands

```bash
# Install dependencies
make install

# Run the application
make run

# Download data
make download

# Run tests
make test

# Add new dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>
```

## File Organization
- `src/remaju/models.py` - Pydantic models
- `src/remaju/parser.py` - HTML parser
- `src/remaju/geocoding.py` - Google Maps geocoding
- `download.py` - Download script with geocoding
- `main.py` - Streamlit visualization
