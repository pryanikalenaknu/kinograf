import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { renderApp } from './utils.jsx';

vi.mock('../src/pages/CatalogPage.jsx', () => ({ CatalogPage: () => <h1>Каталог фільмів</h1> }));

describe('верхня панель і маршрути', () => {
  it('показує головне меню з активним розділом', () => {
    renderApp('/stats');
    const nav = screen.getAllByRole('navigation', { name: 'Головне меню' })[0];
    const links = within(nav).getAllByRole('link').map((link) => link.textContent);
    expect(links).toEqual(['Каталог', 'Граф', 'Статистика', 'Якість даних', 'SPARQL']);
    expect(within(nav).getByRole('link', { name: 'Статистика' })).toHaveAttribute(
      'aria-current',
      'page',
    );
    expect(screen.getByRole('link', { name: 'Вхід для адміністратора' })).toBeInTheDocument();
  });

  it('позначає каталог активним на картці фільму', () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => new Promise(() => {}));
    renderApp('/films/Q1');
    const nav = screen.getAllByRole('navigation', { name: 'Головне меню' })[0];
    expect(within(nav).getByRole('link', { name: 'Каталог' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('відкриває й закриває бокову шторку меню', async () => {
    renderApp('/');
    await userEvent.click(screen.getByRole('button', { name: 'Відкрити меню' }));
    expect(screen.getAllByRole('navigation', { name: 'Головне меню' })).toHaveLength(2);
    await userEvent.click(screen.getByRole('button', { name: 'Закрити меню' }));
    expect(screen.getAllByRole('navigation', { name: 'Головне меню' })).toHaveLength(1);
  });

  it('закриває шторку після вибору розділу й клавішею Escape', async () => {
    renderApp('/');
    await userEvent.click(screen.getByRole('button', { name: 'Відкрити меню' }));
    const drawer = screen.getAllByRole('navigation', { name: 'Головне меню' })[1];
    await userEvent.click(within(drawer).getByRole('link', { name: 'Статистика' }));
    expect(screen.getAllByRole('navigation', { name: 'Головне меню' })).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: 'Відкрити меню' }));
    await userEvent.keyboard('{Escape}');
    expect(screen.getAllByRole('navigation', { name: 'Головне меню' })).toHaveLength(1);
  });

  it('показує сторінку «не знайдено» для невідомої адреси', () => {
    renderApp('/nema');
    expect(screen.getByRole('heading', { name: 'Сторінку не знайдено' })).toBeInTheDocument();
  });
});

