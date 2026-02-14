# Agent Instructions for Remaju

## Testing

- **Run all tests**: `uv run pytest`
- **Run tests with verbose output**: `uv run pytest -v`
- **Run specific test file**: `uv run pytest tests/<test_file>.py`
- **Run with coverage** (if coverage is added): `uv run pytest --cov`

## Project Structure

- Python 3.14+ project managed with uv
- Tests located in `tests/` directory
- Main code in `main.py`

## Development Commands

```bash
# Install dependencies
uv sync

# Run the application
uv run python main.py

# Run tests
uv run pytest

# Add new dependency
uv add <package-name>

# Add dev dependency
uv add --dev <package-name>
```
