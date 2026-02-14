# Remaju

## Testing

This project uses [pytest](https://pytest.org/) for testing.

### Running Tests

```bash
# Run all tests
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_main.py
```

### Test Structure

Tests are located in the `tests/` directory and follow the naming convention `test_*.py`.

### Writing Tests

Create a new test file in the `tests/` directory:

```python
def test_example():
    assert True
```

Run the test with:
```bash
uv run pytest tests/test_example.py -v
```
