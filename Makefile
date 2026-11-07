.PHONY: help download sample process run test clean install build test-container web-build dev

help:
	@echo "build/install: build collector and web images"
	@echo "test: run collector and web tests without network"
	@echo "dev/run: start the static explorer on localhost:5173"
	@echo "web-build: build the static explorer"
	@echo "sample/download: run a non-publishable live source sample"
	@echo "process RUN=var/private/runs/<id>: post-process a cached run (no paid services)"

build:
	docker compose build

test-container:
	docker compose build collector
	docker run --rm --network none remaju-collector:dev pytest -q src/collector/tests

download:
	docker compose run --rm collector python src/collector/main.py collect --mode sample

sample: download

process:
	docker compose run --rm collector python src/collector/main.py process --run-dir $(RUN)

run:
	docker compose up web

dev: run

web-build:
	docker compose run --rm --no-deps web npm run build

test:
	docker compose build
	docker run --rm --network none remaju-collector:dev pytest -q src/collector/tests
	docker run --rm --network none remaju-web:dev npm run test
	docker run --rm --network none remaju-web:dev npm run build

install:
	docker compose build

clean:
	@echo "Data and caches are preserved."
