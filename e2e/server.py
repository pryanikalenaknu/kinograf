"""Сервер для приймальних тестів: підставна Wikidata, свіже сховище й API на uvicorn.

Запуск: ``python server.py`` з віртуального середовища backend. Порт API задає
``E2E_API_PORT`` (типово 8001), ключ адміністратора — ``E2E_ADMIN_KEY``.
"""

import os
import tempfile
from pathlib import Path

import fake_wikidata
import uvicorn

from kinograf.api import create_app
from kinograf.config import Settings
from kinograf.opendata import WikidataClient, WikidataLoader
from kinograf.services import Services

WIKIDATA_PORT = int(os.getenv("E2E_WIKIDATA_PORT", "8902"))
API_PORT = int(os.getenv("E2E_API_PORT", "8001"))


def main() -> None:
    """Готує сховище з тестовими даними через звичайне оновлення й запускає API."""
    fake_wikidata.start(WIKIDATA_PORT)
    data = Path(tempfile.mkdtemp(prefix="kinograf-e2e-"))
    settings = Settings(
        sparql_endpoint=f"http://127.0.0.1:{WIKIDATA_PORT}/sparql",
        database_path=str(data / "kinograf.db"),
        graph_path=str(data / "graph.ttl"),
        admin_key=os.getenv("E2E_ADMIN_KEY", "e2e-key"),
        retry_delay=0.1,
    )
    client = WikidataClient(settings.sparql_endpoint, settings.user_agent, retry_delay=0.1)
    services = Services.create(settings, WikidataLoader(client, settings.min_year))
    log = services.update.run(services.update.start())
    if log.status != "success":
        raise SystemExit(f"тестові дані не завантажено: {log.message}")
    uvicorn.run(create_app(services), host="127.0.0.1", port=API_PORT, log_level="warning")


if __name__ == "__main__":
    main()
