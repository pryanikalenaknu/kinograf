# КіноГраф

Вебзастосунок-довідник українських фільмів від 1991 року, побудований на зв'язаних відкритих даних [Wikidata](https://www.wikidata.org). Застосунок отримує дані через SPARQL і подає їх як каталог, сторінки фільмів і персоналій, граф зв'язків і статистику.

Проєкт з дисципліни «Принципи, методи зв'язування даних у застосуваннях Semantic Web», магістратура ФІТ КНУ імені Тараса Шевченка.

## Стан роботи

| Етап | Стан |
|---|---|
| Проєкт застосунку: аналіз, UML-діаграми, макети | виконано |
| Модуль відкритих даних | реалізовано, покрито тестами |
| Сховище, рівень доступу до даних, рівень програми (REST API) | реалізовано, покрито тестами |
| Рівень інтерфейсу | реалізовано, покрито тестами компонентів |
| Docker Compose | реалізовано, перевірено |
| Приймальні тести (Playwright, 14 сценаріїв) | реалізовано |
| Фінальна перевірка: справжні дані, покриття, перевірка безпеки | виконано |

## Макет

Еталонні екрани в десктопній (1440 px) і мобільній (390 px) версіях — у теці [`design/screens`](design/screens), інтерактивний прототип — [`design/prototype/KinoGraf.html`](design/prototype/KinoGraf.html), усі стани екранів — на дошках [`design/figma-board`](design/figma-board). Інтерактивний прототип у Figma: https://www.figma.com/design/0Xilac0MOvyFZHqwQe0Dt7/Uni-Project?node-id=0-1.

## Знімки екранів

| Каталог | Картка фільму |
|---|---|
| ![Каталог](docs/screenshots/desktop_4-1.png) | ![Картка фільму](docs/screenshots/desktop_4-2.png) |
| **Граф зв'язків** | **Статистика** |
| ![Граф зв'язків](docs/screenshots/desktop_4-4.png) | ![Статистика](docs/screenshots/desktop_4-5.png) |

Усі дев'ять екранів у десктопній (1440 px) і мобільній (390 px) версіях — у теці [`docs/screenshots`](docs/screenshots). Знімки знято з даними Wikidata станом на 30.10.2026: 1 404 фільми, 2 797 персоналій. Оновити їх можна на запущеному застосунку:

```bash
cd e2e
KINOGRAF_ADMIN_KEY=... npm run screenshots
```

## Відкриті дані

Фільми відбираються у Wikidata за трьома ознаками: це фільм (`P31` = `Q11424`), країна походження Україна (`P495` = `Q212`), дата виходу (`P577`) від 1991 року. Учасники беруться з властивостей режисер (`P57`), сценарист (`P58`), композитор (`P86`) і актори (`P161`), а також завантажуються жанри (`P136`) і нагороди (`P166`). Дані Wikidata поширюються за ліцензією CC0.

## Структура репозиторію

```
backend/
  kinograf/
    config.py        налаштування зі змінних середовища
    models/          моделі предметної області
    opendata/        клієнт і завантажувач Wikidata, SPARQL-запити
    repositories/    доступ до SQLite з повнотекстовим пошуком FTS5
    rdf/             локальний RDF-граф, SPARQL-запити, експорт у Turtle
    services/        логіка застосунку й об'єкти передачі даних
    api/             REST API на FastAPI
    update.py        оновлення даних з командного рядка
  tests/             тести pytest
  Dockerfile         образ контейнера api
frontend/
  src/               інтерфейс на React: сторінки, компоненти, клієнт API
  tests/             тести Vitest і Testing Library
  Dockerfile         образ контейнера web (nginx)
  nginx.conf         статичні файли й проксі /api
e2e/                 приймальні тести Playwright і підставна Wikidata з тестовими даними
docker-compose.yml   запуск застосунку однією командою
docs/                специфікація, план реалізації, UML-діаграми (PlantUML і PNG), знімки екранів
design/              макети екранів, дошки для Figma, дизайн-токени
tools/figma-plugin/  плагін, що розставляє переходи в прототипі Figma
CONTRIBUTING.md      правила розробки: джерела вимог, стек, стиль коду
```

## Запуск у Docker

Потрібен Docker з Compose v2.24 або новішим.

```bash
cp .env.example .env          # задайте власний KINOGRAF_ADMIN_KEY
docker compose up --build
```

Застосунок відкривається на http://localhost:8080, документація API — на http://localhost:8080/api/docs. Контейнер `web` (nginx) віддає інтерфейс і передає запити `/api` контейнеру `api` (uvicorn). База SQLite і `graph.ttl` зберігаються в томі `kinograf-data`, тому не зникають після перезапуску.

Після першого запуску довідник порожній. Дані завантажує адміністратор кнопкою «Оновити дані з Wikidata» на сторінці «Адміністрування» або командою:

```bash
docker compose exec api python -m kinograf.update
```

Одночасно може виконуватися лише одне оновлення: команда й кнопка в панелі не заважають одна одній. Запущений API сам підхоплює новий `graph.ttl` після оновлення командою.

Оновлення триває кілька хвилин. Wikidata може обмежувати частоту запитів; паузу між повторами задає `KINOGRAF_RETRY_DELAY` (типово 60 с).

Якщо дані вже завантажено локально в `backend/data/`, їх можна перенести в том без звернення до Wikidata:

```bash
docker compose cp backend/data/kinograf.db api:/app/data/kinograf.db
docker compose cp backend/data/graph.ttl api:/app/data/graph.ttl
docker compose exec -u root api chown kinograf /app/data/kinograf.db /app/data/graph.ttl
docker compose restart api
```

## Розробка

Потрібні Python 3.12 і Node.js 22 або новіший.

Сервер:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

python -m kinograf.update     # завантаження даних з Wikidata у backend/data/
uvicorn kinograf.api.app:create_app --factory --reload --port 8000
pytest                        # тести з вимірюванням покриття
ruff check . && ruff format --check .
```

Інтерфейс (в іншому терміналі; Vite перенаправляє `/api` на `localhost:8000`):

```bash
cd frontend
npm install
npm run dev                   # http://localhost:5173
npm test
npm run lint
```

Приймальні тести (14 сценаріїв за прецедентами з `docs/uml/01_usecase.puml`) самі запускають API на тестових даних і інтерфейс, тому потрібні лише встановлені залежності сервера й інтерфейсу:

```bash
cd e2e
npm install
npx playwright install chromium
npm test
```

## Безпека

- SPARQL-консоль приймає лише `SELECT`, забороняє `SERVICE` і `FROM`, обмежує запит 10 с і 1 000 рядків; запит, що перевищив час, переривається, а одночасно виконуються не більше двох.
- Адміністративні дії доступні лише з ключем `KINOGRAF_ADMIN_KEY` у заголовку `X-Admin-Key`; ключ зберігається тільки в пам'яті вкладки.
- Параметри запитів мають межі (роки, номер сторінки, довжина тексту), значення CSV, схожі на формули, екрануються.
- nginx працює без прав root, додає заголовки безпеки (CSP, `X-Frame-Options`, `X-Content-Type-Options`) і обмежує частоту запитів до SPARQL і адміністрування; контейнери мають обмеження пам'яті й процесора.
- Залежності перевіряються `npm audit` і `pip-audit`; версії для образу api зафіксовано в `backend/requirements.lock`.

## Стандарт коду

Серверний код відповідає PEP 8 (перевірка `ruff`), кожен модуль, клас і функція мають docstring у стилі Google. Інтерфейс перевіряє ESLint. Тести й перевірка стилю запускаються автоматично в GitHub Actions на кожну зміну.

## Ліцензія

Код поширюється за ліцензією MIT, дані Wikidata — за ліцензією CC0.
