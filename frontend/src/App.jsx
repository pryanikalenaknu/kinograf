/** Маршрути застосунку. */

import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout.jsx';
import { CatalogPage } from './pages/CatalogPage.jsx';
import { FilmPage } from './pages/FilmPage.jsx';
import { NotFoundPage } from './pages/NotFoundPage.jsx';
import { PersonPage } from './pages/PersonPage.jsx';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<CatalogPage />} />
        <Route path="films/:qid" element={<FilmPage />} />
        <Route path="people/:qid" element={<PersonPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
