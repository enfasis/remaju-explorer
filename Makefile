.PHONY: help download sample process trace run test clean install build test-container web-build dev

help:
	@echo "build/install: build collector and web images"
	@echo "test: run collector and web tests without network"
	@echo "dev/run: start the static explorer on localhost:5173"
	@echo "web-build: build the static explorer"
	@echo "sample/download: run a non-publishable live source sample"
	@echo "process RUN=var/private/runs/<id>: post-process a cached run (no paid services)"
	@echo "trace RUN_ID=<id>: download a refresh run trace from the private R2 bucket (read-only, via Infisical)"

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

trace:
	@test -n "$(RUN_ID)" || { echo "usage: make trace RUN_ID=<run id>"; exit 1; }
	@infisical run --silent -- sh -c 'export AWS_ACCESS_KEY_ID="$$R2_DEBUG_ACCESS_KEY_ID" AWS_SECRET_ACCESS_KEY="$$R2_DEBUG_SECRET_ACCESS_KEY" AWS_ENDPOINT_URL="$$R2_ENDPOINT"; \
		docker compose run --rm --build -e AWS_ACCESS_KEY_ID -e AWS_SECRET_ACCESS_KEY -e AWS_ENDPOINT_URL collector \
		python src/collector/storage.py fetch --private "$$R2_PRIVATE_BUCKET" --run-id "$(RUN_ID)" --target var/private/runs'

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
