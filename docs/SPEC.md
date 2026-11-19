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
| 12 | Постійні адреси сутностей | `/id/film/{qid}` і `/id/person/{qid}` відповідають `303 See Other`: вебпереглядачу — на сторінку, програмі — на документ Turtle або JSON-LD за заголовком `Accept`; невідома сутність — 404 |
| 13 | Зв'язки з іншими наборами | для фільмів і персоналій зберігаються ідентифікатор IMDb (`P345`), стаття української та англійської Вікіпедії; документ сутності містить `owl:sameAs` на Wikidata й DBpedia і `schema:sameAs` на IMDb і Вікіпедію; панель «Відкриті дані» на картках 4.2 і 4.3 |
| 14 | Опис і вивантаження набору | опис VoID на `/.well-known/void` (кількість трійок і сутностей, ліцензія CC0, джерело, словники, набори зв'язків з кількістю), повний набір у Turtle, точка SPARQL за протоколом SPARQL 1.1, екран 4.10 «Відкриті дані»; розмітка schema.org JSON-LD на сторінках фільмів і персоналій |
| 15 | Перевірка якості за правилами | правила SHACL у `backend/kinograf/rdf/shapes.ttl` перевіряють локальний RDF-граф під час кожного оновлення; на екрані 4.6 — зведення за правилами, список фільмів із зауваженнями, фільтр за правилом і рівнем, посилання «Виправити у Wikidata» на потрібну властивість; правила й звіт перевірки завантажуються в Turtle |

## 3. Дані

Відбір у Wikidata: `P31 = Q11424`, `P495 = Q212`, рік `P577` ≥ 1991. Ролі: `P57` режисер, `P58` сценарист, `P86` композитор, `P161` актор. Жанри `P136`, нагороди `P166`, тривалість `P2047`, зображення `P18`. Завантаження вже реалізоване в `kinograf.opendata`.

Посилання на інші набори беруться окремими запитами для фільмів і для персоналій вибірки: ідентифікатор IMDb `P345` і назви статей Вікіпедії через `schema:about` / `schema:isPartOf` (`https://uk.wikipedia.org/`, `https://en.wikipedia.org/`). Якщо значень кілька, береться одне (`SAMPLE`).

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
external_links(qid TEXT PRIMARY KEY, imdb_id TEXT, ukwiki TEXT, enwiki TEXT)
quality_issues(film_qid TEXT, rule TEXT, severity TEXT, message TEXT, property TEXT, value TEXT,
               PRIMARY KEY (film_qid, rule))
```

`external_links` спільна для фільмів і персоналій. `quality_issues` заповнюється перевіркою SHACL наприкінці оновлення; `rule` — локальна назва форми з `shapes.ttl` (`director`, `duration-range`…), `severity` — `violation` / `warning` / `info`, `property` — властивість Wikidata для посилання «Виправити» (`P57`), `value` — значення, що порушує правило (для `duration-range`, `announced`).

Оновлення замінює дані в одній транзакції. `films_added` і `films_changed` рахуються порівнянням із попереднім станом.

### RDF-граф

Сутності — URI Wikidata (`http://www.wikidata.org/entity/Q…`), властивості — `wdt:P…`, назви — `rdfs:label` з мовою `uk`. Граф зберігається у `graph.ttl` і завантажується під час старту. До графа додається `wdt:P345` (IMDb), щоб у SPARQL-консолі можна було шукати фільми з посиланнями.

Цей граф — робоча копія даних Wikidata: його використовують SPARQL-консоль, граф зв'язків і перевірка SHACL. Те, що застосунок публікує назовні, — окремий граф `linked.ttl` у словнику schema.org з власними URI (розділ 7).

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
| GET | `/api/opendata` | — | `OpenDataOverview` для екрана 4.10 |
| GET | `/api/quality/rules` | — | `QualityReport`: дата перевірки, кількість фільмів, зведення за правилами |
| GET | `/api/quality/issues` | `rule`, `severity`, `page` | `Page` з `FilmIssues` по 12 |
| GET | `/api/quality/shapes.ttl`, `/api/quality/report.ttl` | — | правила SHACL і звіт останньої перевірки (Turtle) |

`FilmDetails` і `PersonProfile` отримують поле `links: EntityLinks`. Об'єкти передачі даних — як у `docs/uml/05d_class_dto.puml`, `05e_class_linked_data.puml` і `05f_class_quality.puml`.

Маршрути зв'язаних даних (поза `/api`, розділ 7) — `/id/…`, `/data/…`, `/.well-known/void`.

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
| `/open-data` | 4.10 Відкриті дані | `desktop_4-10.png`, `phone_4-10.png` |

Пункт меню «Відкриті дані» стоїть після «SPARQL» (і на десктопі, і в боковій шторці на телефоні). Панель «Відкриті дані» є на 4.2 (під учасниками) і 4.3 (під постійними співробітниками), розділ «Перевірка за правилами» — на 4.6 під діаграмою повноти. Додаткові еталони: `phone_4-2-open-data.png`, `phone_4-3-open-data.png`, `desktop_4-6-rules.png`, `phone_4-6-rules.png`, `desktop_4-10-access.png`, `phone_4-10-access.png`; усі нові стани — у `design/figma-board/doshka-4.html`. Етапи оновлення на 4.9: Фільми, Учасники, Жанри, Нагороди, Посилання, Запис у сховище, Публікація, Перевірка якості.

- Стани кожного екрана (завантаження, порожньо, помилка й додаткові) — у `design/figma-board/doshka-*.html`.
- Розмітка й стилі — у `design/prototype/KinoGraf.html`; нові екрани й стани (4.10, панель «Відкриті дані», перевірка за правилами) є лише на дошках `design/figma-board/doshka-*.html`. Переносити вигляд, а не код дослівно. Еталонні знімки перезнімає `e2e/render-design.mjs`.
- Межа мобільної версії — 768 px. На телефоні меню згортається, фільтри відкриваються шторкою знизу, картки йдуть в одну колонку.
- Ключ адміністратора зберігається лише в пам'яті вкладки (`sessionStorage`) і передається в `X-Admin-Key`.
- Під час оновлення панель опитує `/api/admin/update/{id}` раз на 2 с і показує етапи.

## 6. Нефункціональні вимоги

- Користувацькі запити обслуговуються з локального сховища, без звернення до Wikidata.
- Відповідь каталогу — до 300 мс на 1 400 фільмах.
- Контраст тексту не менше 4,5:1, область натискання не менше 44 × 44 px.
- Запуск усього застосунку — `docker compose up --build`.

## 7. Відкриті зв'язані дані

КіноГраф не лише бере дані з Wikidata, а й сам публікує їх за принципами зв'язаних даних: кожна сутність має постійну HTTP-адресу, за якою програма отримує RDF, а дані зв'язано з іншими наборами. Це відповідає п'ятій зірці шкали відкритих даних Тіма Бернерса-Лі.

### Адреси

Усі адреси будуються від базової `KINOGRAF_BASE_URL` (типово `http://localhost:8080`). Після її зміни потрібне оновлення даних, бо адреси записано в `linked.ttl`.

| Адреса | Відповідь |
|---|---|
| `/id/film/{qid}`, `/id/person/{qid}` | `303 See Other` за заголовком `Accept`: `text/turtle` → `/data/{вид}/{qid}.ttl`, `application/ld+json` → `/data/{вид}/{qid}.jsonld`, інше (зокрема `text/html` і `*/*`) → `/films/{qid}` або `/people/{qid}`. Заголовок `Vary: Accept`. Невідома сутність — 404 |
| `/data/film/{qid}.ttl`, `.jsonld`; `/data/person/{qid}.ttl`, `.jsonld` | документ про сутність (`text/turtle; charset=utf-8` або `application/ld+json`) |
| `/data/kinograf.ttl` | увесь опублікований граф |
| `/data/sparql` | точка доступу за протоколом SPARQL 1.1: `GET ?query=`, `POST` з формою `query=` або тілом `application/sparql-query`; результат `application/sparql-results+json` (типово) або `text/csv`; запит виконується над опублікованим графом з тими самими обмеженнями, що й консоль (лише `SELECT` і `ASK`, без `SERVICE` і `FROM`, 10 с, 1 000 рядків, два запити одночасно) |
| `/.well-known/void` | опис набору у VoID: Turtle типово, JSON-LD за `Accept: application/ld+json` |

`Accept` розбирається з урахуванням ваг `q`. Усі відповіді цих маршрутів мають `Access-Control-Allow-Origin: *`, щоб дані могли використовувати інші сайти. nginx і Vite передають `/id/`, `/data/` і `/.well-known/void` контейнеру `api`; для `/data/sparql` діє те саме обмеження частоти, що й для `/api/sparql`.

### Опублікований граф `linked.ttl`

Будується під час оновлення з даних SQLite. Префікси: `schema:` = `https://schema.org/`, `owl:`, `dcterms:`, `foaf:`, `void:`, `xsd:`.

| Що | Трійки |
|---|---|
| Фільм `<{base}/id/film/{qid}>` | `a schema:Movie`; `schema:name` (мова `uk`); `schema:datePublished` (`xsd:date`); `schema:duration` (`"PT{n}M"^^xsd:duration`, якщо є); `schema:image`; `schema:genre` → URI жанру у Wikidata; `schema:award` (назва нагороди, текст); `schema:countryOfOrigin wd:Q212`; `schema:director`, `schema:author` (сценарист), `schema:musicBy` (композитор), `schema:actor` → URI персоналій КіноГраф; `schema:url` → `{base}/films/{qid}` |
| Персоналія `<{base}/id/person/{qid}>` | `a schema:Person`; `schema:name`; `schema:url` → `{base}/people/{qid}` |
| Жанр (URI Wikidata) | `rdfs:label` (мова `uk`) |
| Зв'язки з іншими наборами | `owl:sameAs` → `wd:{qid}` (завжди) і `<http://dbpedia.org/resource/{стаття англійської Вікіпедії}>`; `schema:sameAs` → `<https://www.imdb.com/title/{tt…}/>` або `<https://www.imdb.com/name/{nm…}/>` і `<https://uk.wikipedia.org/wiki/{стаття}>`. `owl:sameAs` — лише для наборів, що публікують RDF (Wikidata, DBpedia); IMDb і Вікіпедія — вебсторінки, тому `schema:sameAs` |

Назва статті перетворюється на адресу заміною пробілів на `_` і кодуванням решти символів, як у самій Вікіпедії (`urllib.parse.quote(title.replace(" ", "_"), safe="()_,'!*")`).

**Документ про сутність** містить трійки, де сутність є підметом, назви сутностей, на які вона посилається, а для персоналії — фільми, де вона бере участь (трійки з нею як додатком і назви цих фільмів). До документа додаються трійки про сам документ: `foaf:primaryTopic`, `dcterms:license <https://creativecommons.org/publicdomain/zero/1.0/>`, `void:inDataset <{base}/.well-known/void#dataset>`. JSON-LD серіалізується rdflib з контекстом `{"@vocab": "https://schema.org/", "owl": …, "dcterms": …, "foaf": …, "void": …}`.

### Опис набору (VoID)

`<{base}/.well-known/void#dataset> a void:Dataset` з полями: `dcterms:title "КіноГраф"@uk`, `dcterms:description`, `dcterms:license` (CC0 1.0), `dcterms:source <https://www.wikidata.org/>`, `dcterms:modified` (час останнього успішного оновлення), `foaf:homepage <{base}/>`, `void:uriSpace "{base}/id/"`, `void:sparqlEndpoint <{base}/data/sparql>`, `void:dataDump <{base}/data/kinograf.ttl>`, `void:exampleResource` (один фільм), `void:vocabulary` (schema.org, OWL, Dublin Core), `void:triples`, `void:entities`, `void:classPartition` для `schema:Movie` і `schema:Person` з `void:entities`.

Набори зв'язків — `void:subset` типу `void:Linkset` з `void:subjectsTarget` (КіноГраф), `void:objectsTarget` (опис цільового набору з `foaf:homepage`), `void:linkPredicate` і `void:triples`: Wikidata (`owl:sameAs`), DBpedia (`owl:sameAs`), IMDb (`schema:sameAs`), українська Вікіпедія (`schema:sameAs`).

### Розмітка сторінок

Поки відкрита сторінка фільму або персоналії, компонент `StructuredData` додає в `<head>` елемент `<script type="application/ld+json">` з документом `/data/{вид}/{qid}.jsonld` і прибирає його при переході. Розмітку перевіряють на validator.schema.org (вкладка «Фрагмент коду»).

## 8. Перевірка якості SHACL

Правила — у `backend/kinograf/rdf/shapes.ttl`, перевіряються бібліотекою pyshacl над локальним графом у термінах Wikidata (не над опублікованим), бо виправляти треба саме записи Wikidata. Ціль — усі підмети `wdt:P495`.

| Правило (`kgs:`) | Назва | Рівень | Властивість |
|---|---|---|---|
| `release-date` | Дата виходу | помилка (`sh:Violation`) | P577 |
| `duration-range` | Тривалість від 1 до 600 хв | помилка | P2047 |
| `title-uk` | Назва українською | попередження (`sh:Warning`) | `rdfs:label` → мітка у Wikidata |
| `director` | Режисер | попередження | P57 |
| `cast` | Актори | попередження | P161 |
| `genre` | Жанр | попередження | P136 |
| `duration` | Тривалість | підказка (`sh:Info`) | P2047 |
| `screenwriter` | Сценарист | підказка | P58 |
| `image` | Зображення | підказка | P18 |
| `announced` | Фільм уже вийшов (SPARQL-обмеження) | підказка | P577 |

- Перевірка триває 10–15 с на 1 400 фільмах, тому виконується в останньому етапі оновлення (`validation`), а не під час запиту. Результати записуються в `quality_issues`, звіт pyshacl — у `data/shacl-report.ttl`.
- Ідентифікатор правила — локальна назва `sh:sourceShape` або `sh:sourceConstraint` у просторі `urn:kinograf:shapes:`; назва, рівень і повідомлення читаються з `shapes.ttl` (`sh:name`, `sh:severity`, `sh:message`), порядок — `sh:order`.
- Посилання «Виправити у Wikidata»: `https://www.wikidata.org/wiki/{qid}#{P…}` (властивість із `sh:resultPath`); для `title-uk` — `https://www.wikidata.org/wiki/{qid}` без якоря.
- Етапи оновлення: `films`, `participations`, `genres`, `awards`, `links`, `storage`, `publication`, `validation`.

Очікувані числа на даних від 30.10.2026 (для перевірки реалізації): 1 404 фільми, із зауваженнями 1 390; `release-date` 0, `duration-range` 1 (тривалість 5 345 хв), `title-uk` 382, `director` 445, `cast` 742, `genre` 712, `duration` 512, `screenwriter` 757, `image` 1 383, `announced` 10 (залежить від поточної дати).
