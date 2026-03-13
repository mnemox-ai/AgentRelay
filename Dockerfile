FROM python:3.12-slim

WORKDIR /app

# Install system deps for asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
COPY scripts/entrypoint.sh .

RUN sed -i 's/\r$//' entrypoint.sh && \
    pip install --no-cache-dir . && \
    chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
