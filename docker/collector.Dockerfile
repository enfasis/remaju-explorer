FROM ghcr.io/astral-sh/uv:0.9.28 AS uv
FROM python:3.14-slim
COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
CMD ["pytest", "-q"]
