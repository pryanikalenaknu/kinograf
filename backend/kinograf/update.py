"""Оновлення даних з Wikidata з командного рядка.

Запуск: ``python -m kinograf.update``.
"""

from kinograf.config import load_settings
from kinograf.services import Services


def main(services: Services | None = None) -> int:
    """Виконує оновлення й друкує його підсумок.

    Args:
        services: Сервіси застосунку; за замовчуванням створюються з налаштувань середовища.

    Returns:
        Код завершення процесу: 0 — успішно, 1 — помилка.
    """
    services = services or Services.create(load_settings())
    log = services.update.run(services.update.start())
    if log.status == "success":
        print(f"оновлення завершено: додано {log.films_added}, змінено {log.films_changed}")
        return 0
    print(f"помилка оновлення на етапі «{log.stage}»: {log.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
