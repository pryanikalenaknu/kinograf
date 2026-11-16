# КіноГраф — специфікація для реалізації

Повний документ проєкту з обґрунтуваннями зберігається окремо (`docs/project.pdf`, якщо додано). Тут — те, що потрібно для коду.

## 1. Ролі

| Роль | Доступ |
|---|---|
| Користувач | усі екрани, крім адміністрування; без входу |
| Адміністратор | усе, що користувач, плюс оновлення даних і журнал; доступ за ключем `KINOGRAF_ADMIN_KEY` |

## 2. Функції

| № | Функція | Критерій готовності |
|---|---|---|
| 1 | Каталог | пагінація по 12, сортування за роком (спадання) і назвою, повнотекстовий пошук за назвою (FTS5, українська й англійська назва) |
| 2 | Фільтри | діапазон років, період (`1991-2013` / `2014-now`), жанр, режисер, «лише з акторами»; фільтри поєднуються |
| 3 | Картка фільму | назва, рік, тривалість, постер, жанри, нагороди, учасники за ролями, посилання на Wikidata, до 8 пов'язаних фільмів за кількістю спільних учасників; відсутні дані — «У відкритих даних не вказано» |
| 4 | Сторінка персоналії | ролі, кількість фільмів, хронологія за роками, фільмографія (рік, назва, роль), до 8 постійних співробітників із кількістю спільних фільмів |
| 5 | Граф зв'язків | вузли «фільм» і «персоналія» навколо вибраного вузла, глибина 1 або 2, не більше 150 вузлів |
| 6 | Статистика | фільми за роками; жанри у двох періодах; топ-10 режисерів і топ-10 акторів |
| 7 | Якість даних | частка фільмів із режисером, акторами, жанром, постером; повнота за роками; дата останнього оновлення |
| 8 | SPARQL-консоль | запит до локального RDF-графа, лише `SELECT`, обмеження 10 с і 1 000 рядків, готові приклади |
| 9 | Експорт | результати каталогу й SPARQL у CSV, JSON, Turtle |
| 10 | Оновлення даних | фоновий процес: фільми → учасники → жанри → нагороди → запис у SQLite і RDF; журнал зі статусом |
| 11 | Доступ адміністратора | заголовок `X-Admin-Key`; неправильний ключ — 401 |

## 3. Дані

Відбір у Wikidata: `P31 = Q11424`, `P495 = Q212`, рік `P577` ≥ 1991. Ролі: `P57` режисер, `P58` сценарист, `P86` композитор, `P161` актор. Жанри `P136`, нагороди `P166`, тривалість `P2047`, зображення `P18`. Завантаження вже реалізоване в `kinograf.opendata`.

### Схема SQLite

```sql
films(qid TEXT PRIMARY KEY, title TEXT NOT NULL, release_date TEXT NOT NULL, year INTEGER NOT NULL,
      duration_min INTEGER, image_url TEXT)
people(qid TEXT PRIMARY KEY, name TEXT NOT NULL)
participations(film_qid TEXT, person_qid TEXT, role TEXT, PRIMARY KEY (film_qid, person_qid, role))
genres(qid TEXT PRIMARY KEY, name TEXT NOT NULL)
film_genres(film_qid TEXT, genre_qid TEXT, PRIMARY KEY (film_qid, genre_qid))
awards(qid TEXT PRIMARY KEY, name TEXT NOT NULL)
film_awards(film_qid TEXT, award_qid TEXT, PRIMARY KEY (film_qid, award_qid))
update_log(id INTEGER PRIMARY KEY, started_at TEXT, finished_at TEXT, status TEXT,
           films_added INTEGER, films_changed INTEGER, message TEXT)
films_fts — віртуальна таблиця FTS5 за title
```

Оновлення замінює дані в одній транзакції. `films_added` і `films_changed` рахуються порівнянням із попереднім станом.

### RDF-граф

Сутності — URI Wikidata (`http://www.wikidata.org/entity/Q…`), властивості — `wdt:P…`, назви — `rdfs:label` з мовою `uk`. Граф зберігається у `graph.ttl` і завантажується під час старту.

## 4. REST API

Усі відповіді — JSON. Документація OpenAPI — `/api/docs`.

| Метод | Шлях | Параметри / тіло | Відповідь |
|---|---|---|---|
| GET | `/api/films` | `q`, `year_from`, `year_to`, `period`, `genre`, `director`, `has_cast`, `sort` (`year`/`title`), `page` | `Page` |
| GET | `/api/films/{qid}` | — | `FilmDetails` |
| GET | `/api/people/{qid}` | — | `PersonProfile` |
| GET | `/api/graph/{qid}` | `depth` (1 або 2) | `GraphData` |
| GET | `/api/genres`, `/api/directors` | — | списки для фільтрів |
| GET | `/api/stats` | — | `Stats` |
| POST | `/api/sparql` | `{"query": "..."}` | `{"columns": [...], "rows": [...], "elapsed_ms": n}` |
| GET | `/api/export/films` | ті самі фільтри + `format` (`csv`/`json`/`ttl`) | файл |
| POST | `/api/export/sparql` | `{"query": "...", "format": "..."}` | файл |
| GET | `/api/admin/log` | заголовок `X-Admin-Key` | список `UpdateLog` |
| POST | `/api/admin/update` | заголовок `X-Admin-Key` | `UpdateLog` зі статусом `running`; 409, якщо вже виконується |
| GET | `/api/admin/update/{id}` | заголовок `X-Admin-Key` | `UpdateLog` з поточним етапом |

Об'єкти передачі даних — як у `docs/uml/05d_class_dto.puml`.

## 5. Інтерфейс

| Маршрут | Екран | Еталон |
|---|---|---|
| `/` | 4.1 Каталог (головне вікно) | `design/screens/desktop_4-1.png`, `phone_4-1.png` |
| `/films/:qid` | 4.2 Картка фільму | `desktop_4-2.png`, `phone_4-2.png` |
| `/people/:qid` | 4.3 Сторінка персоналії | `desktop_4-3.png`, `phone_4-3.png` |
| `/graph/:qid` | 4.4 Граф зв'язків | `desktop_4-4.png`, `phone_4-4.png` |
| `/stats` | 4.5 Статистика | `desktop_4-5.png`, `phone_4-5.png` |
| `/quality` | 4.6 Якість даних | `desktop_4-6.png`, `phone_4-6.png` |
| `/sparql` | 4.7 SPARQL-консоль | `desktop_4-7.png`, `phone_4-7.png` |
| `/admin/login` | 4.8 Вхід адміністратора | `desktop_4-8.png`, `phone_4-8.png` |
| `/admin` | 4.9 Панель адміністрування | `desktop_4-9.png`, `phone_4-9.png` |

- Стани кожного екрана (завантаження, порожньо, помилка й додаткові) — у `design/figma-board/doshka-*.html`.
- Розмітка й стилі — у `design/prototype/KinoGraf.html`. Переносити вигляд, а не код дослівно.
- Межа мобільної версії — 768 px. На телефоні меню згортається, фільтри відкриваються шторкою знизу, картки йдуть в одну колонку.
- Ключ адміністратора зберігається лише в пам'яті вкладки (`sessionStorage`) і передається в `X-Admin-Key`.
- Під час оновлення панель опитує `/api/admin/update/{id}` раз на 2 с і показує етапи.

## 6. Нефункціональні вимоги

- Користувацькі запити обслуговуються з локального сховища, без звернення до Wikidata.
- Відповідь каталогу — до 300 мс на 1 400 фільмах.
- Контраст тексту не менше 4,5:1, область натискання не менше 44 × 44 px.
- Запуск усього застосунку — `docker compose up --build`.
