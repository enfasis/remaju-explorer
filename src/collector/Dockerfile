FROM ghcr.io/astral-sh/uv:0.9.28 AS uv
FROM python:3.14-slim
COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app
COPY src/collector/pyproject.toml src/collector/uv.lock ./src/collector/
RUN cd src/collector && uv sync --locked
COPY . .
ENV PATH="/app/src/collector/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src/collector"
CMD ["pytest", "-q", "src/collector/tests"]
