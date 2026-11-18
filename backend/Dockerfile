# Контейнер api: FastAPI на uvicorn. Дані (SQLite і graph.ttl) зберігаються в томі /app/data.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KINOGRAF_DATABASE_PATH=/app/data/kinograf.db \
    KINOGRAF_GRAPH_PATH=/app/data/graph.ttl

WORKDIR /app

COPY pyproject.toml requirements.lock ./
COPY kinograf ./kinograf
RUN pip install --no-cache-dir -c requirements.lock . \
    && useradd --create-home --uid 1000 kinograf \
    && mkdir -p /app/data \
    && chown kinograf /app/data

USER kinograf
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/genres')"

CMD ["uvicorn", "kinograf.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
