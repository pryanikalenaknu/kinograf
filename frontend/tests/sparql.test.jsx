import { fireEvent, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { saveFile } from '../src/components/download.js';
import { EXAMPLES, errorLine, highlightLine } from '../src/components/sparql.js';
import { mockApi } from './fixtures.js';
import { renderApp } from './utils.jsx';

vi.mock('../src/components/download.js', () => ({ saveFile: vi.fn() }));

const RESULT = {
  columns: ['film', 'filmLabel'],
  rows: [
    { film: 'http://www.wikidata.org/entity/Q4', filmLabel: 'Поводир' },
    { film: 'http://www.wikidata.org/entity/Q3' },
  ],
  truncated: false,
  elapsed_ms: 480,
};

describe('підсвітка SPARQL', () => {
  it('розпізнає ключові слова, змінні, префікси, рядки й IRI', () => {
    const kinds = highlightLine('SELECT ?film WHERE { ?film rdfs:label "Мамай"@uk ; <http://x> }')
      .filter((token) => token.text.trim())
      .map((token) => `${token.kind}:${token.text}`);
    expect(kinds).toEqual([
      'keyword:SELECT',
      'variable:?film',
      'keyword:WHERE',
      'plain:{',
      'variable:?film',
      'prefixed:rdfs:label',
      'string:"Мамай"@uk',
      'plain:;',
      'iri:<http://x>',
      'plain:}',
    ]);
  });

  it('позначає коментар цілим рядком', () => {
    expect(highlightLine('  # коментар ?x')).toEqual([{ text: '  # коментар ?x', kind: 'comment' }]);
  });

  it('знаходить номер рядка в повідомленні про помилку', () => {
    expect(errorLine('синтаксична помилка: Expected {, found end (at char 40), (line:3, col:7)')).toBe(3);
    expect(errorLine('дозволено лише запити SELECT')).toBeNull();
  });
});

describe('SPARQL-консоль', () => {
  it('виконує приклад і показує таблицю результатів', async () => {
    const fetchMock = mockApi({ '/sparql': RESULT });
    renderApp('/sparql');
    await userEvent.click(screen.getByRole('button', { name: 'Виконати' }));
    const results = screen.getByRole('region', { name: 'Результати' });
    expect(await within(results).findByText('2 рядки · 0,48 с')).toBeInTheDocument();
    expect(within(results).getAllByRole('columnheader').map((cell) => cell.textContent)).toEqual([
      '?film',
      '?filmLabel',
    ]);
    expect(within(results).getByRole('link', { name: 'wd:Q4' })).toHaveAttribute(
      'href',
      'http://www.wikidata.org/entity/Q4',
    );
    expect(within(results).getByText('—')).toBeInTheDocument();
    expect(JSON.parse(fetchMock.mock.calls[0][1].body).query).toBe(EXAMPLES[0].query);
  });

  it('підставляє готовий приклад у редактор', async () => {
    mockApi({});
    renderApp('/sparql');
    const examples = screen.getByRole('complementary', { name: 'Готові приклади' });
    await userEvent.click(
      within(examples).getByRole('button', { name: 'Режисери з найбільшою кількістю фільмів' }),
    );
    expect(screen.getByRole('textbox', { name: 'Текст SPARQL-запиту' })).toHaveValue(
      EXAMPLES[1].query,
    );
    expect(
      within(examples).getByRole('button', { name: 'Режисери з найбільшою кількістю фільмів' }),
    ).toHaveAttribute('aria-pressed', 'true');
  });

  it('показує помилку сервера й позначає рядок', async () => {
    mockApi({
      '/sparql': {
        status: 400,
        body: { detail: 'синтаксична помилка: Expected end of text (line:2, col:1)' },
      },
    });
    renderApp('/sparql');
    const editor = screen.getByRole('textbox', { name: 'Текст SPARQL-запиту' });
    fireEvent.change(editor, { target: { value: 'SELECT * WHERE {}\nбуба' } });
    fireEvent.keyDown(editor, { key: 'Enter', ctrlKey: true });
    expect(await screen.findByRole('alert')).toHaveTextContent('синтаксична помилка');
    expect(document.querySelector('.editor-bad')).toHaveTextContent('2');
  });

  it('повідомляє про порожній результат', async () => {
    mockApi({ '/sparql': { ...RESULT, rows: [] } });
    renderApp('/sparql');
    await userEvent.click(screen.getByRole('button', { name: 'Виконати' }));
    expect(await screen.findByText('Порожній результат')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Експорт' })).not.toBeInTheDocument();
  });

  it('позначає обрізаний результат', async () => {
    mockApi({ '/sparql': { ...RESULT, truncated: true } });
    renderApp('/sparql');
    await userEvent.click(screen.getByRole('button', { name: 'Виконати' }));
    expect(await screen.findByText(/показано лише перші 2/)).toBeInTheDocument();
  });

  it('експортує результат у вибраному форматі', async () => {
    const fetchMock = mockApi({ '/sparql': RESULT, '/export/sparql': { ok: true } });
    renderApp('/sparql');
    await userEvent.click(screen.getByRole('button', { name: 'Виконати' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Експорт' }));
    const dialog = screen.getByRole('dialog', { name: 'Експорт результатів запиту' });
    await userEvent.click(within(dialog).getByRole('radio', { name: /Turtle/ }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Завантажити' }));
    const [url, options] = fetchMock.mock.calls.at(-1);
    expect(url).toBe('/api/export/sparql');
    expect(JSON.parse(options.body)).toEqual({ query: EXAMPLES[0].query, format: 'ttl' });
    expect(saveFile).toHaveBeenCalledWith(expect.any(Blob), 'sparql.ttl');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('показує помилку експорту в діалозі', async () => {
    mockApi({
      '/sparql': RESULT,
      '/export/sparql': { status: 408, body: { detail: 'запит виконувався довше 10 с' } },
    });
    renderApp('/sparql');
    await userEvent.click(screen.getByRole('button', { name: 'Виконати' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Експорт' }));
    await userEvent.click(screen.getByRole('button', { name: 'Завантажити' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('запит виконувався довше 10 с');
  });
});
