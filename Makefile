.PHONY: download run test clean install

download:
	uv run python download.py

run:
	uv run streamlit run main.py

test:
	uv run pytest

install:
	uv sync

clean:
	rm -rf data/auctions.json data/geocoding_cache.json
