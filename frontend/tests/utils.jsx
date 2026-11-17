import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ADMIN_STORAGE_KEY } from '../src/api/admin.js';
import { AdminProvider } from '../src/api/AdminProvider.jsx';
import { App } from '../src/App.jsx';

export function renderApp(route = '/', { adminKey } = {}) {
  if (adminKey) {
    sessionStorage.setItem(ADMIN_STORAGE_KEY, adminKey);
  }
  return render(
    <MemoryRouter initialEntries={[route]}>
      <AdminProvider>
        <App />
      </AdminProvider>
    </MemoryRouter>,
  );
}

export function jsonResponse(body, status = 200) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      status,
      headers: { 'Content-Type': 'application/json' },
    }),
  );
}
