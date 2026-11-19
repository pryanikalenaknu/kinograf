/** Сторінка 4.10 «Відкриті дані»: п'ять зірок, опис набору, зв'язки з іншими наборами, доступ до даних. */

import { Link } from 'react-router-dom';
import { api } from '../api/client.js';
import { useApi } from '../api/useApi.js';
import { formatDateTime, formatNumber } from '../components/format.js';
import { Icon } from '../components/Icon.jsx';
import { EmptyState, ErrorState, LoadingState } from '../components/States.jsx';
import './OpenDataPage.css';

const STARS = [
  { title: 'Доступні в інтернеті з відкритою ліцензією', note: 'CC0 1.0, як і дані Wikidata' },
  { title: 'Структуровані й придатні для обробки програмами', note: 'граф RDF, таблиці CSV і JSON' },
  { title: 'У відкритих форматах', note: 'Turtle, JSON-LD, CSV' },
  { title: 'Сутності позначено адресами URI', note: '/id/film/{qid}, /id/person/{qid}' },
  { title: "Зв'язані з іншими наборами", note: 'Wikidata, DBpedia, IMDb, Вікіпедія' },
];

const ACCESS = [
  {
    title: 'Постійна адреса фільму',
    path: '/id/film/{qid}',
    note: 'сторінка або RDF за заголовком Accept',
  },
  { title: 'Дані фільму', path: '/data/film/{qid}.ttl · .jsonld', note: 'Turtle або JSON-LD' },
  { title: 'Опис набору', path: '/.well-known/void', note: "VoID: обсяг, ліцензія, зв'язки" },
  { title: 'Увесь набір', path: '/data/kinograf.ttl', note: 'один файл Turtle' },
  { title: 'Точка SPARQL', path: '/data/sparql', note: 'протокол SPARQL 1.1' },
];

const VOCABULARIES = 'schema.org, OWL, Dublin Core, VoID';

function Stars({ count }) {
  return (
    <span className="od-stars" role="img" aria-label={`${count} з 5`}>
      {[1, 2, 3, 4, 5].map((star) => (
        <span key={star} aria-hidden="true" className={star <= count ? 'od-star-on' : undefined}>
          ★
        </span>
      ))}
    </span>
  );
}

function FiveStars() {
  return (
    <section className="panel od-panel" aria-labelledby="od-stars-title">
      <div className="od-panel-head">
        <h2 id="od-stars-title" className="panel-title">
          П'ять зірок відкритих даних
        </h2>
        <span className="label muted">за шкалою Тіма Бернерса-Лі</span>
      </div>
      <ol className="od-rows">
        {STARS.map((item, index) => (
          <li key={item.title} className="od-star-row">
            <Stars count={index + 1} />
            <span className="od-star-text">
              <span className="od-strong">{item.title}</span>
              <span className="label muted">{item.note}</span>
            </span>
            <span className="od-check">
              <Icon name="check" size={20} />
              <span className="visually-hidden">виконано</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Dataset({ overview }) {
  const rows = [
    [
      'Ліцензія',
      <a key="license" href={overview.license} target="_blank" rel="noopener noreferrer">
        CC0 1.0
      </a>,
    ],
    [
      'Джерело',
      <a key="source" href={overview.source} target="_blank" rel="noopener noreferrer">
        Wikidata
      </a>,
    ],
    ['Оновлено', overview.modified ? formatDateTime(overview.modified) : '—'],
    ['Трійок', formatNumber(overview.triples)],
    ['Фільмів', formatNumber(overview.films)],
    ['Персоналій', formatNumber(overview.people)],
    ['Словники', VOCABULARIES],
  ];
  return (
    <section className="panel od-panel" aria-labelledby="od-dataset-title">
      <h2 id="od-dataset-title" className="panel-title">
        Набір даних
      </h2>
      <dl className="od-facts">
        {rows.map(([term, value]) => (
          <div key={term} className="od-fact">
            <dt className="label muted">{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Count({ value, total }) {
  const share = total > 0 ? Math.min(value / total, 1) : 0;
  return (
    <span className="od-count">
      <span className="od-count-value">{formatNumber(value)}</span>
      <span className="od-track" aria-hidden="true">
        <span className="od-bar" style={{ width: `${share * 100}%` }} />
      </span>
    </span>
  );
}

function Linksets({ overview }) {
  return (
    <section className="panel od-panel" aria-labelledby="od-links-title">
      <div className="od-panel-head">
        <h2 id="od-links-title" className="panel-title">
          Зв'язки з іншими наборами
        </h2>
        <span className="label muted">
          скільки сутностей КіноГраф мають відповідник в іншому наборі
        </span>
      </div>
      <table className="od-table desktop-only">
        <thead>
          <tr>
            <th scope="col">Набір</th>
            <th scope="col">Властивість</th>
            <th scope="col">Фільмів</th>
            <th scope="col">Персоналій</th>
          </tr>
        </thead>
        <tbody>
          {overview.linksets.map((item) => (
            <tr key={item.target}>
              <th scope="row">
                <a href={item.homepage} target="_blank" rel="noopener noreferrer">
                  {item.target}
                </a>
              </th>
              <td>
                <code className="od-code-muted">{item.predicate}</code>
              </td>
              <td>
                <Count value={item.films} total={overview.films} />
              </td>
              <td>
                <Count value={item.people} total={overview.people} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul className="od-rows phone-only">
        {overview.linksets.map((item) => (
          <li key={item.target} className="od-link-row">
            <span className="od-link-head">
              <span className="od-strong">{item.target}</span>
              <code className="od-code-muted">{item.predicate}</code>
            </span>
            <span className="label muted">
              фільмів {formatNumber(item.films)} · персоналій {formatNumber(item.people)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function turtleString(text) {
  return text.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
}

function Example({ baseUrl, qid }) {
  const request = useApi(() => api.film(qid), [qid]);
  const details = request.data;
  if (!details) {
    return null;
  }
  const uri = `${baseUrl}/id/film/${qid}`;
  const director = details.participants.director?.[0];
  return (
    <figure className="od-example">
      <figcaption className="label muted">Приклад: дані фільму у форматі Turtle</figcaption>
      <pre className="od-pre" aria-label="Приклад запиту й відповіді">
        <span className="muted">$ </span>
        {`curl -L -H "Accept: text/turtle" \\\n    ${uri}\n\n`}
        <span className="od-iri">{`<${uri}>`}</span>
        {'\n    '}
        <span className="od-kw">a</span>
        {' schema:Movie ;\n    schema:name '}
        <span className="od-literal">{`"${turtleString(details.film.title)}"@uk`}</span>
        {' ;\n    schema:datePublished '}
        <span className="od-literal">{`"${details.film.release_date}"^^xsd:date`}</span>
        {' ;\n'}
        {director && (
          <>
            {'    schema:director '}
            <span className="od-iri">{`<${baseUrl}/id/person/${director.qid}>`}</span>
            {' ;\n'}
          </>
        )}
        {`    owl:sameAs wd:${qid} .\n`}
        <span className="muted">
          {'# а також owl:sameAs на DBpedia і schema:sameAs\n# на IMDb і Вікіпедію, якщо вони є у Wikidata'}
        </span>
      </pre>
      <Link to={`/films/${qid}`} className="od-more">
        Відкрити сторінку цього фільму →
      </Link>
    </figure>
  );
}

function Access({ overview }) {
  return (
    <section className="panel od-panel" aria-labelledby="od-access-title">
      <h2 id="od-access-title" className="panel-title">
        Як отримати дані
      </h2>
      <div className="od-access">
        <ul className="od-rows">
          {ACCESS.map((item) => (
            <li key={item.title} className="od-access-row">
              <span className="od-strong">{item.title}</span>
              <code className="od-code">{item.path}</code>
              <span className="label muted">{item.note}</span>
            </li>
          ))}
        </ul>
        {overview.example_film && (
          <Example baseUrl={overview.base_url} qid={overview.example_film} />
        )}
      </div>
    </section>
  );
}

export function OpenDataPage() {
  const request = useApi(() => api.opendata(), []);
  const overview = request.data;

  let content;
  if (request.loading) {
    content = <LoadingState />;
  } else if (request.error) {
    content = (
      <ErrorState
        text="Не вдалося отримати опис набору. Спробуйте ще раз за хвилину."
        onRetry={request.reload}
      />
    );
  } else if (overview.films === 0) {
    content = <EmptyState text="Набір ще не опубліковано: дані не завантажено з Wikidata." />;
  }
  if (content) {
    return <div className="page">{content}</div>;
  }

  return (
    <div className="page od">
      <div className="od-heading">
        <div className="od-intro">
          <h1 className="page-title">Відкриті дані</h1>
          <p className="muted">
            КіноГраф публікує дані про фільми й персоналії як зв'язані відкриті дані: кожна
            сутність має постійну адресу, а записи пов'язано з Wikidata, DBpedia, IMDb і
            Вікіпедією.
          </p>
        </div>
        <div className="od-actions">
          <a className="btn btn-primary" href="/data/kinograf.ttl" download="kinograf.ttl">
            <Icon name="download" />
            Завантажити набір (Turtle)
          </a>
          <a className="btn" href="/.well-known/void" target="_blank" rel="noopener noreferrer">
            Опис набору (VoID)
            <Icon name="external" />
          </a>
        </div>
      </div>
      <div className="od-columns">
        <FiveStars />
        <Dataset overview={overview} />
      </div>
      <Linksets overview={overview} />
      <Access overview={overview} />
    </div>
  );
}
