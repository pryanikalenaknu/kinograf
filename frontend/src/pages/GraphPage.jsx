/** Сторінка 4.4 «Граф зв'язків»: фільми й персоналії навколо вибраного вузла, глибина 1 або 2. */

import { useCallback, useMemo, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api } from '../api/client.js';
import { useApi } from '../api/useApi.js';
import { filmsCount, ROLE_COLORS, ROLE_LABELS } from '../components/format.js';
import { GraphCanvas } from '../components/GraphCanvas.jsx';
import { Icon } from '../components/Icon.jsx';
import { RoleTag } from '../components/People.jsx';
import { EmptyState, RequestState } from '../components/States.jsx';
import { useIsPhone } from '../components/useIsPhone.js';
import './GraphPage.css';

const ROLE_ORDER = ['director', 'screenwriter', 'composer', 'cast'];

const LEGEND = [
  { label: 'Фільм', color: 'var(--color-primary)', square: true },
  ...ROLE_ORDER.map((role) => ({
    label: role === 'cast' ? 'Актор' : ROLE_LABELS[role].one,
    color: ROLE_COLORS[role],
  })),
  { label: 'Вибраний', color: 'var(--color-accent)' },
];

function prepare(graph) {
  const roles = new Map();
  graph.edges.forEach((edge) => {
    roles.set(edge.to, [...(roles.get(edge.to) ?? []), ...edge.roles]);
  });
  const nodes = graph.nodes.map((node) => {
    const nodeRoles = ROLE_ORDER.filter((role) => roles.get(node.id)?.includes(role));
    return { ...node, roles: nodeRoles, role: nodeRoles[0] ?? 'cast' };
  });
  return { nodes, edges: graph.edges };
}

function Legend({ className }) {
  return (
    <div className={`graph-legend ${className}`}>
      {LEGEND.map((item) => (
        <span key={item.label}>
          <span
            className="graph-legend-mark"
            style={{ background: item.color, borderRadius: item.square ? 2 : '50%' }}
          />
          {item.label}
        </span>
      ))}
    </div>
  );
}

function NodeSearch({ nodes, onPick }) {
  const [text, setText] = useState('');
  const needle = text.trim().toLocaleLowerCase('uk');
  const hits = needle
    ? nodes.filter((node) => node.label.toLocaleLowerCase('uk').includes(needle)).slice(0, 8)
    : [];
  return (
    <div className="graph-search">
      <div className="graph-search-box">
        <Icon name="search" className="muted desktop-only" />
        <input
          value={text}
          placeholder="Знайти вузол"
          aria-label="Знайти вузол"
          onChange={(event) => setText(event.target.value)}
        />
      </div>
      {hits.length > 0 && (
        <ul className="graph-search-hits" role="listbox" aria-label="Знайдені вузли">
          {hits.map((node) => (
            <li
              key={node.id}
              role="option"
              aria-selected="false"
              tabIndex={0}
              onClick={() => {
                onPick(node.id);
                setText('');
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  onPick(node.id);
                  setText('');
                }
              }}
            >
              <span>{node.label}</span>
              <span className="muted">{node.type === 'film' ? 'фільм' : 'персоналія'}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function NodeDetails({ node, links, isCenter, onClear }) {
  const navigate = useNavigate();
  const isFilm = node.type === 'film';
  const details = useApi(
    () => (isFilm ? api.film(node.id) : api.person(node.id)),
    [node.id, isFilm],
  );
  let tags = null;
  let summary = '';
  if (details.data && isFilm) {
    const directors = details.data.participants.director.map((person) => person.name);
    summary = [details.data.film.year, directors.join(', ')].filter(Boolean).join(' · ');
    tags = details.data.genres.map((genre) => (
      <span key={genre.qid} className="tag">
        {genre.name}
      </span>
    ));
  } else if (details.data) {
    const films = details.data.filmography;
    summary = `${filmsCount(films.length)}: ${films.map((entry) => entry.film.title).join(', ')}`;
    tags = node.roles.map((role) => <RoleTag key={role} role={role} />);
  }
  const path = isFilm ? `/films/${node.id}` : `/people/${node.id}`;
  return (
    <>
      <span className="label muted">{isFilm ? 'Фільм' : 'Персоналія'}</span>
      <h2 className="panel-title">{node.label}</h2>
      {tags && <div className="tags graph-node-tags">{tags}</div>}
      <p className="label muted graph-node-summary">
        {details.loading ? 'Завантаження…' : summary}
      </p>
      <span className="label">Зв'язків у графі: {links}</span>
      <div className="graph-node-actions">
        <Link to={path} className="btn btn-primary">
          Відкрити сторінку
        </Link>
        {!isCenter && (
          <button type="button" className="btn" onClick={() => navigate(`/graph/${node.id}`)}>
            Зробити центром графа
          </button>
        )}
        <button type="button" className="btn btn-ghost desktop-only" onClick={onClear}>
          Зняти вибір
        </button>
      </div>
    </>
  );
}

function DefaultCenter() {
  const stats = useApi(() => api.stats(), []);
  if (stats.loading || stats.error) {
    return (
      <div className="page">
        <RequestState request={stats} />
      </div>
    );
  }
  const top = stats.data.top_directors[0];
  if (!top) {
    return (
      <div className="page">
        <h1 className="page-title">Граф зв'язків</h1>
        <EmptyState text="Дані ще не завантажено з Wikidata, тому графа поки немає." />
      </div>
    );
  }
  return <Navigate to={`/graph/${top.person.qid}`} replace />;
}

function Graph({ qid }) {
  const isPhone = useIsPhone();
  const [params, setParams] = useSearchParams();
  const depth = params.get('depth') === '1' ? 1 : 2;
  const request = useApi(() => api.graph(qid, depth), [qid, depth]);
  const [selection, setSelection] = useState({ qid: null, id: null });
  const [scale, setScale] = useState(1);
  const canvas = useRef(null);
  const graph = useMemo(() => (request.data ? prepare(request.data) : null), [request.data]);
  const selected = selection.qid === qid ? selection.id : null;
  const select = useCallback((id) => setSelection({ qid, id }), [qid]);

  if (request.loading || request.error) {
    return (
      <div className="page">
        <RequestState
          request={request}
          notFoundText="Фільму чи персоналії з таким ідентифікатором немає в графі."
        />
      </div>
    );
  }
  const center = graph.nodes.find((node) => node.level === 0);
  const node = graph.nodes.find((item) => item.id === selected);
  const links = node
    ? graph.edges.filter((edge) => edge.from === node.id || edge.to === node.id).length
    : 0;
  const pick = (id) => {
    select(id);
    canvas.current?.focus(id);
  };
  const depthSwitch = (
    <div className="segmented graph-depth" role="group" aria-label="Глибина графа">
      {[1, 2].map((value) => (
        <button
          key={value}
          type="button"
          aria-pressed={depth === value}
          onClick={() => setParams(value === 2 ? {} : { depth: '1' }, { replace: true })}
        >
          {value === 1 ? '1 рівень' : '2 рівні'}
        </button>
      ))}
    </div>
  );
  const zoom = (
    <>
      <button
        type="button"
        className="btn btn-icon graph-tool"
        aria-label="Зменшити"
        onClick={() => canvas.current?.zoomOut()}
      >
        <Icon name="zoomOut" />
      </button>
      <span className="label muted graph-zoom desktop-only">{Math.round(scale * 100)}%</span>
      <button
        type="button"
        className="btn btn-icon graph-tool"
        aria-label="Збільшити"
        onClick={() => canvas.current?.zoomIn()}
      >
        <Icon name="zoomIn" />
      </button>
      <button
        type="button"
        className="btn btn-icon graph-tool"
        aria-label="Вмістити граф"
        onClick={() => canvas.current?.fit()}
      >
        <Icon name="fit" />
      </button>
    </>
  );

  return (
    <div className="page graph">
      <div className="graph-heading">
        <h1 className="page-title">Граф зв'язків</h1>
        <span className="muted graph-summary">
          <span className="desktop-only">Центр: </span>«{center.label}»
          <span className="desktop-only">
            {' '}
            · Вузлів: {graph.nodes.length} · зв'язків: {graph.edges.length}
          </span>
        </span>
      </div>
      <div className="graph-toolbar">
        <NodeSearch nodes={graph.nodes} onPick={pick} />
        {depthSwitch}
        <div className="graph-zoom-tools desktop-only">{zoom}</div>
        <Legend className="desktop-only" />
      </div>
      <div className="graph-body">
        <div className="graph-canvas panel">
          {graph.edges.length === 0 ? (
            <p className="graph-alone muted">
              У відкритих даних немає учасників, пов'язаних із «{center.label}».
            </p>
          ) : (
            <GraphCanvas
              ref={canvas}
              nodes={graph.nodes}
              edges={graph.edges}
              selected={selected}
              onSelect={select}
              onZoom={setScale}
            />
          )}
          <div className="graph-zoom-float phone-only">{zoom}</div>
          <Legend className="graph-legend-float phone-only" />
        </div>
        <aside className="panel graph-panel desktop-only" aria-label="Вибраний вузол">
          {node && !isPhone ? (
            <NodeDetails
              node={node}
              links={links}
              isCenter={node.id === qid}
              onClear={() => select(null)}
            />
          ) : (
            <>
              <h2 className="panel-title">Вузол не вибрано</h2>
              <p className="label muted">
                Натисніть на фільм або персоналію, щоб побачити короткі дані. Вузли можна
                перетягувати, полотно — гортати й масштабувати коліщатком.
              </p>
            </>
          )}
        </aside>
      </div>
      {node && isPhone && (
        <div className="graph-sheet phone-only" role="dialog" aria-label={node.label}>
          <div className="sheet-handle" />
          <button
            type="button"
            className="btn-plain graph-sheet-close"
            aria-label="Закрити"
            onClick={() => select(null)}
          >
            <Icon name="close" size={20} />
          </button>
          <NodeDetails node={node} links={links} isCenter={node.id === qid} onClear={() => select(null)} />
        </div>
      )}
    </div>
  );
}

export function GraphPage() {
  const { qid } = useParams();
  return qid ? <Graph key={qid} qid={qid} /> : <DefaultCenter />;
}
