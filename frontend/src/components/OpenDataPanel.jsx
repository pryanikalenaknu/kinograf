/** Панель «Відкриті дані» на сторінках фільму й персоналії: інші набори, постійна адреса, RDF. */

import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { copyText } from './clipboard.js';
import { Icon } from './Icon.jsx';
import './OpenDataPanel.css';

const DATASETS = [
  { key: 'wikidata', label: 'Wikidata' },
  { key: 'imdb', label: 'IMDb' },
  { key: 'wikipedia', label: 'Вікіпедія' },
  { key: 'dbpedia', label: 'DBpedia' },
];

/** Шлях адреси без вузла, щоб документ відкривався з тієї ж адреси, що й застосунок. */
function localPath(url) {
  try {
    return new URL(url).pathname;
  } catch {
    return url;
  }
}

function fileName(url) {
  return localPath(url).split('/').pop();
}

/**
 * @param {{links: {uri: string, wikidata: string, imdb: string|null, wikipedia: string|null,
 *   dbpedia: string|null, turtle: string, jsonld: string}, stacked?: boolean}} props
 */
export function OpenDataPanel({ links, stacked = false }) {
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!status) {
      return undefined;
    }
    const timer = setTimeout(() => setStatus(''), 2000);
    return () => clearTimeout(timer);
  }, [status]);

  const copy = async () => {
    setStatus((await copyText(links.uri)) ? 'Адресу скопійовано' : 'Не вдалося скопіювати');
  };

  const datasets = DATASETS.filter(({ key }) => links[key]);
  return (
    <section
      className={stacked ? 'panel odp odp-stacked' : 'panel odp'}
      aria-labelledby="odp-title"
    >
      <div className="odp-head">
        <h2 id="odp-title" className="panel-title">
          Відкриті дані
        </h2>
        <Link to="/open-data" className="odp-about">
          Про набір даних →
        </Link>
      </div>
      {datasets.length > 0 && (
        <div className="odp-row">
          <span className="label muted odp-label">В інших наборах</span>
          <ul className="odp-datasets">
            {datasets.map(({ key, label }) => (
              <li key={key}>
                <a
                  className="odp-chip"
                  href={links[key]}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {label}
                  <Icon name="external" size={16} />
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="odp-row">
        <span className="label muted odp-label" id="odp-uri-label">
          Постійна адреса
        </span>
        <div className="odp-uri-block">
          <div className="odp-uri-line">
            <code className="odp-uri" title={links.uri} aria-labelledby="odp-uri-label">
              {links.uri}
            </code>
            <button
              type="button"
              className="btn btn-icon odp-copy"
              aria-label="Копіювати адресу"
              onClick={copy}
            >
              <Icon name={status === 'Адресу скопійовано' ? 'check' : 'copy'} />
            </button>
          </div>
          <div className="odp-formats">
            <a className="btn" href={localPath(links.turtle)} download={fileName(links.turtle)}>
              <Icon name="download" />
              Turtle
            </a>
            <a className="btn" href={localPath(links.jsonld)} download={fileName(links.jsonld)}>
              <Icon name="download" />
              JSON-LD
            </a>
          </div>
        </div>
      </div>
      <span className="visually-hidden" role="status">
        {status}
      </span>
    </section>
  );
}
