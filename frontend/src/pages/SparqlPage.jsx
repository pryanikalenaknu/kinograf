/** Сторінка 4.7 «SPARQL-консоль»: редактор із підсвіткою, приклади, таблиця результатів, експорт. */

import { useRef, useState } from 'react';
import { api } from '../api/client.js';
import { saveFile } from '../components/download.js';
import { ExportDialog } from '../components/ExportDialog.jsx';
import { formatNumber, plural } from '../components/format.js';
import { Icon } from '../components/Icon.jsx';
import { EXAMPLES, errorLine, highlightLine } from '../components/sparql.js';
import './SparqlPage.css';

const ENTITY = 'http://www.wikidata.org/entity/';

function Editor({ value, onChange, onRun, badLine }) {
  const lines = value.split('\n');
  return (
    <div className="editor">
      <div className="editor-gutter" aria-hidden="true">
        {lines.map((_, index) => (
          <div key={index} className={index + 1 === badLine ? 'editor-bad' : undefined}>
            {index + 1}
          </div>
        ))}
      </div>
      <div className="editor-area">
        <pre aria-hidden="true">
          {lines.map((line, index) => (
            <div key={index}>
              {line
                ? highlightLine(line).map((token, position) => (
                    <span key={position} className={`sparql-${token.kind}`}>
                      {token.text}
                    </span>
                  ))
                : ' '}
            </div>
          ))}
        </pre>
        <textarea
          value={value}
          spellCheck={false}
          wrap="off"
          aria-label="Текст SPARQL-запиту"
          style={{ height: lines.length * 22 + 24 }}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
              event.preventDefault();
              onRun();
            }
          }}
        />
      </div>
    </div>
  );
}

function Cell({ value }) {
  if (value === undefined) {
    return <span className="muted">—</span>;
  }
  if (/^https?:\/\//.test(value)) {
    const label = value.startsWith(ENTITY) ? `wd:${value.slice(ENTITY.length)}` : value;
    return (
      <a href={value} target="_blank" rel="noopener noreferrer">
        {label}
      </a>
    );
  }
  return value;
}

function resultMeta(result) {
  const rows = result.rows.length;
  const seconds = (result.elapsed_ms / 1000).toFixed(2).replace('.', ',');
  const count = `${formatNumber(rows)} ${plural(rows, ['рядок', 'рядки', 'рядків'])}`;
  return result.truncated
    ? `${count} · ${seconds} с · показано лише перші ${formatNumber(rows)}`
    : `${count} · ${seconds} с`;
}

function Results({ state, onExport }) {
  const { status, result, error } = state;
  return (
    <section className="panel results" aria-label="Результати">
      <div className="results-head">
        <div className="results-title">
          <span className="results-heading">Результати</span>
          {status === 'done' && <span className="label muted">{resultMeta(result)}</span>}
        </div>
        {status === 'done' && result.rows.length > 0 && (
          <button type="button" className="btn" onClick={onExport}>
            <Icon name="download" />
            Експорт
          </button>
        )}
      </div>
      {status === 'idle' && (
        <p className="results-note label muted">
          Оберіть приклад або напишіть запит і натисніть «Виконати».
        </p>
      )}
      {status === 'running' && (
        <p className="results-note results-running label muted" aria-busy="true">
          <span className="spinner" />
          Виконання запиту…
        </p>
      )}
      {status === 'error' && (
        <div className="results-error" role="alert">
          <Icon name="alert" />
          {error}
        </div>
      )}
      {status === 'done' && result.rows.length === 0 && (
        <div className="results-note">
          <strong>Порожній результат</strong>
          <span className="label muted">Запит виконано, але жоден запис не відповідає умовам.</span>
        </div>
      )}
      {status === 'done' && result.rows.length > 0 && (
        <div className="results-scroll">
          <table className="results-table">
            <thead>
              <tr>
                {result.columns.map((column) => (
                  <th key={column} scope="col">
                    ?{column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.map((row, index) => (
                <tr key={index}>
                  {result.columns.map((column) => (
                    <td key={column}>
                      <Cell value={row[column]} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function SparqlPage() {
  const [example, setExample] = useState(0);
  const [query, setQuery] = useState(EXAMPLES[0].query);
  const [state, setState] = useState({ status: 'idle' });
  const [exporting, setExporting] = useState({ open: false, busy: false, error: '' });
  const latestRun = useRef(0);

  const pick = (index) => {
    latestRun.current += 1;
    setExample(index);
    setQuery(EXAMPLES[index].query);
    setState({ status: 'idle' });
  };

  const run = async () => {
    if (state.status === 'running') {
      return;
    }
    latestRun.current += 1;
    const id = latestRun.current;
    const executed = query;
    setState({ status: 'running' });
    try {
      const result = await api.sparql(executed);
      if (id === latestRun.current) {
        setState({ status: 'done', result, query: executed });
      }
    } catch (error) {
      if (id === latestRun.current) {
        setState({ status: 'error', error: error.message });
      }
    }
  };

  const download = async (format) => {
    setExporting({ open: true, busy: true, error: '' });
    try {
      saveFile(await api.exportSparql(state.query, format), `sparql.${format}`);
      setExporting({ open: false, busy: false, error: '' });
    } catch (error) {
      setExporting({ open: true, busy: false, error: error.message });
    }
  };

  return (
    <div className="page sparql">
      <div className="sparql-heading">
        <h1 className="page-title">SPARQL-консоль</h1>
        <p className="page-subtitle">Запити до відкритих даних Wikidata</p>
      </div>
      <aside className="sparql-examples desktop-only" aria-label="Готові приклади">
        <span className="label muted">Готові приклади</span>
        {EXAMPLES.map((item, index) => (
          <button
            key={item.label}
            type="button"
            aria-pressed={index === example}
            onClick={() => pick(index)}
          >
            {item.label}
          </button>
        ))}
      </aside>
      <div className="sparql-main">
        <label className="sparql-select phone-only">
          Готовий приклад
          <select
            className="select"
            value={example}
            onChange={(event) => pick(Number(event.target.value))}
          >
            {EXAMPLES.map((item, index) => (
              <option key={item.label} value={index}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <section className="panel query">
          <div className="query-head">
            <span className="results-heading">Запит</span>
            <button
              type="button"
              className="btn btn-primary"
              disabled={state.status === 'running'}
              onClick={run}
            >
              <Icon name="play" size={14} />
              Виконати
            </button>
          </div>
          <Editor
            value={query}
            onChange={(text) => {
              setQuery(text);
              setExample(-1);
            }}
            onRun={run}
            badLine={state.status === 'error' ? errorLine(state.error) : null}
          />
        </section>
        <Results state={state} onExport={() => setExporting({ open: true, busy: false, error: '' })} />
      </div>
      {exporting.open && (
        <ExportDialog
          title="Експорт результатів запиту"
          busy={exporting.busy}
          error={exporting.error}
          onClose={() => setExporting({ open: false, busy: false, error: '' })}
          onExport={download}
        />
      )}
    </div>
  );
}
