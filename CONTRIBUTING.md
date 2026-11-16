# Правила розробки КіноГраф

КіноГраф — вебзастосунок-довідник українських фільмів від 1991 року на основі відкритих даних Wikidata. Навчальний проєкт з дисципліни «Принципи, методи зв'язування даних у застосуваннях Semantic Web», ФІТ КНУ.

## Порядок роботи

1. Перед початком прочитати `docs/SPEC.md` і `docs/IMPLEMENTATION_PLAN.md`.
2. Виконувати задачі з `docs/IMPLEMENTATION_PLAN.md` по одній, у вказаному порядку.
3. Після задачі: `ruff check .`, `ruff format --check .`, `pytest` (для інтерфейсу — `npm test` і `npm run lint`), позначка `[x]` у плані й коміт з повідомленням українською.

## Джерела вимог

| Що | Де |
|---|---|
| Функції, модель даних, REST API, екрани | `docs/SPEC.md` |
| Порядок робіт і критерії готовності | `docs/IMPLEMENTATION_PLAN.md` |
| UML-діаграми (прецеденти, діяльність, розгортання, класи, компоненти, пакети) | `docs/uml/*.puml` і `*.png` |
| Вигляд екранів (десктоп і телефон) | `design/screens/*.png` |
| Усі стани екранів | `design/figma-board/doshka-*.html` |
| Розмітка й стилі прототипу | `design/prototype/KinoGraf.html` |
| Кольори, шрифти, відступи | `design/tokens.css` |

Діаграми класів і пакетів — обов'язкова структура коду. Якщо реалізація вимагає відхилення, спершу оновити відповідний `.puml` і перегенерувати PNG.

## Стек

- Серверна частина: Python 3.12, FastAPI, uvicorn, SQLite з FTS5, rdflib, SPARQLWrapper.
- Інтерфейс: React + Vite, React Router, Chart.js, vis-network.
- Тести: pytest і pytest-cov (сервер), Vitest і Testing Library (інтерфейс), Playwright (приймальні тести).
- Стиль: ruff (PEP 8), ESLint.
- Розгортання: Docker Compose (контейнери `web` з nginx і `api` з uvicorn).

## Структура

```
backend/kinograf/
  api/            маршрутизатори FastAPI; знає лише services
  services/       логіка й об'єкти передачі даних
  repositories/   доступ до SQLite
  rdf/            RDF-граф: побудова, SPARQL, експорт у Turtle
  opendata/       клієнт і завантажувач Wikidata
  models/         моделі предметної області
  config.py       налаштування зі змінних середовища
backend/tests/
frontend/src/{pages,components,api}
frontend/tests/
e2e/              приймальні тести Playwright
```

Залежності лише вниз: `api → services → repositories / rdf / opendata → models`. Жодних циклів.

## Правила коду

- Кожен модуль, клас і публічна функція мають docstring у стилі Google українською. Коментарів усередині функцій не писати: код має бути зрозумілим сам по собі.
- Назви змістовні, без зайвих абстракцій і «універсальності на майбутнє».
- Кожна задача — разом із тестами. Тести не звертаються до мережі: Wikidata підмінюється, як у `backend/tests/conftest.py`. Цільове покриття сервера — не менше 70%.
- Не видаляти й не послаблювати наявні тести, щоб вони проходили.
- Інтерфейс українською, жодного тексту капсом. Кольори й шрифти — лише з `design/tokens.css`.
- Секрети не комітити: `.env` у `.gitignore`, ключ адміністратора — змінна `KINOGRAF_ADMIN_KEY`.

## Корисні команди

```bash
cd backend && pip install -e ".[dev]" && pytest
python -m kinograf.opendata          # перевірка завантаження з Wikidata
python -m kinograf.update            # оновлення даних
cd frontend && npm install && npm run dev
cd e2e && npm install && npm test    # приймальні тести
docker compose up --build            # запуск усього застосунку
```
