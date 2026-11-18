import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useImperativeHandle } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { DRAMA, MAMAI, POVODYR, SANIN, ZAHAIKEVYCH, mockApi, requestedPaths } from './fixtures.js';
import { renderApp } from './utils.jsx';

const canvasCalls = vi.hoisted(() => []);

vi.mock('../src/components/GraphCanvas.jsx', () => ({
  GraphCanvas: ({ nodes, edges, selected, onSelect, ref }) => {
    useImperativeHandle(ref, () => ({
      zoomIn: () => canvasCalls.push('zoomIn'),
      zoomOut: () => canvasCalls.push('zoomOut'),
      fit: () => canvasCalls.push('fit'),
      focus: (id) => canvasCalls.push(`focus:${id}`),
    }));
    return (
      <div data-testid="canvas" data-edges={edges.length}>
        {nodes.map((node) => (
          <button
            key={node.id}
            type="button"
            data-role={node.role}
            aria-pressed={node.id === selected}
            onClick={() => onSelect(node.id)}
          >
            вузол {node.label}
          </button>
        ))}
      </div>
    );
  },
}));

const GRAPH = {
  nodes: [
    { id: 'Q4', label: 'Поводир', type: 'film', level: 0 },
    { id: 'Q11', label: 'Олесь Санін', type: 'person', level: 1 },
    { id: 'Q14', label: 'Алла Загайкевич', type: 'person', level: 1 },
    { id: 'Q3', label: 'Мамай', type: 'film', level: 2 },
  ],
  edges: [
    { from: 'Q4', to: 'Q11', roles: ['director', 'screenwriter'] },
    { from: 'Q4', to: 'Q14', roles: ['composer'] },
    { from: 'Q3', to: 'Q11', roles: ['director'] },
  ],
};

const FILM = {
  film: MAMAI,
  participants: { director: [SANIN], screenwriter: [], composer: [ZAHAIKEVYCH], cast: [] },
  genres: [DRAMA],
  awards: [],
  related: [],
};

describe('граф зв\'язків', () => {
  it('показує центр, кількість вузлів і зв\'язків', async () => {
    mockApi({ '/graph/Q4': GRAPH });
    renderApp('/graph/Q4');
    expect(await screen.findByText(/Вузлів: 4 · зв'язків: 3/)).toBeInTheDocument();
    expect(screen.getByText(/«Поводир»/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'вузол Олесь Санін' })).toHaveAttribute(
      'data-role',
      'director',
    );
    expect(screen.getByRole('button', { name: 'вузол Алла Загайкевич' })).toHaveAttribute(
      'data-role',
      'composer',
    );
  });

  it('за замовчуванням має глибину 2 і перемикає на 1 рівень', async () => {
    const fetchMock = mockApi({ '/graph/Q4': GRAPH });
    renderApp('/graph/Q4');
    const depth = await screen.findByRole('group', { name: 'Глибина графа' });
    expect(within(depth).getByRole('button', { name: '2 рівні' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await userEvent.click(within(depth).getByRole('button', { name: '1 рівень' }));
    await waitFor(() => expect(requestedPaths(fetchMock)).toContain('/api/graph/Q4?depth=1'));
    expect(requestedPaths(fetchMock)[0]).toBe('/api/graph/Q4?depth=2');
  });

  it('показує дані вибраного фільму в бічній панелі', async () => {
    mockApi({ '/graph/Q4': GRAPH, '/films/Q3': FILM });
    renderApp('/graph/Q4');
    expect(await screen.findByRole('heading', { name: 'Вузол не вибрано' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'вузол Мамай' }));
    const panel = screen.getByRole('complementary', { name: 'Вибраний вузол' });
    expect(within(panel).getByRole('heading', { name: 'Мамай' })).toBeInTheDocument();
    expect(await within(panel).findByText('2003 · Олесь Санін')).toBeInTheDocument();
    expect(within(panel).getByText("Зв'язків у графі: 1")).toBeInTheDocument();
    expect(within(panel).getByRole('link', { name: 'Відкрити сторінку' })).toHaveAttribute(
      'href',
      '/films/Q3',
    );
    await userEvent.click(within(panel).getByRole('button', { name: 'Зняти вибір' }));
    expect(screen.getByRole('heading', { name: 'Вузол не вибрано' })).toBeInTheDocument();
  });

  it('робить вибрану персоналію центром графа', async () => {
    const profile = {
      person: SANIN,
      filmography: [
        { film: POVODYR, roles: ['director'] },
        { film: MAMAI, roles: ['director'] },
      ],
      collaborators: [],
    };
    const fetchMock = mockApi({ '/graph/Q': GRAPH, '/people/Q11': profile });
    renderApp('/graph/Q4');
    await userEvent.click(await screen.findByRole('button', { name: 'вузол Олесь Санін' }));
    const panel = screen.getByRole('complementary', { name: 'Вибраний вузол' });
    expect(await within(panel).findByText('2 фільми: Поводир, Мамай')).toBeInTheDocument();
    await userEvent.click(within(panel).getByRole('button', { name: 'Зробити центром графа' }));
    await waitFor(() => expect(requestedPaths(fetchMock)).toContain('/api/graph/Q11?depth=2'));
  });

  it('знаходить вузол за назвою й наводить на нього', async () => {
    mockApi({ '/graph/Q4': GRAPH, '/films/Q3': FILM });
    renderApp('/graph/Q4');
    await userEvent.type(await screen.findByRole('textbox', { name: 'Знайти вузол' }), 'мам');
    const hits = screen.getByRole('listbox', { name: 'Знайдені вузли' });
    await userEvent.click(within(hits).getByRole('option', { name: /Мамай/ }));
    expect(canvasCalls).toContain('focus:Q3');
    expect(screen.getByRole('button', { name: 'вузол Мамай' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('масштабує полотно кнопками', async () => {
    mockApi({ '/graph/Q4': GRAPH });
    renderApp('/graph/Q4');
    await screen.findByTestId('canvas');
    await userEvent.click(screen.getAllByRole('button', { name: 'Збільшити' })[0]);
    await userEvent.click(screen.getAllByRole('button', { name: 'Зменшити' })[0]);
    await userEvent.click(screen.getAllByRole('button', { name: 'Вмістити граф' })[0]);
    expect(canvasCalls.slice(-3)).toEqual(['zoomIn', 'zoomOut', 'fit']);
  });

  it('без центру відкриває граф найактивнішого режисера', async () => {
    const fetchMock = mockApi({
      '/stats': { top_directors: [{ person: SANIN, films: 2 }] },
      '/graph/Q11': GRAPH,
    });
    renderApp('/graph');
    await waitFor(() => expect(requestedPaths(fetchMock)).toContain('/api/graph/Q11?depth=2'));
  });

  it('повідомляє про відсутню сутність', async () => {
    mockApi({});
    renderApp('/graph/Q999');
    expect(await screen.findByRole('heading', { name: 'Не знайдено' })).toBeInTheDocument();
  });
});
