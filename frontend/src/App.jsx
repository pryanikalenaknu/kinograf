/** Маршрути застосунку. */

import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout.jsx';
import { CatalogPage } from './pages/CatalogPage.jsx';
import { NotFoundPage } from './pages/NotFoundPage.jsx';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<CatalogPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
