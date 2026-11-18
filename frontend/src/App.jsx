/** Маршрути застосунку. */

import { lazy, Suspense } from 'react';
import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout.jsx';
import { LoadingState } from './components/States.jsx';
import { CatalogPage } from './pages/CatalogPage.jsx';
import { FilmPage } from './pages/FilmPage.jsx';
import { NotFoundPage } from './pages/NotFoundPage.jsx';
import { PersonPage } from './pages/PersonPage.jsx';

const GraphPage = lazy(() =>
  import('./pages/GraphPage.jsx').then((module) => ({ default: module.GraphPage })),
);
const StatsPage = lazy(() =>
  import('./pages/StatsPage.jsx').then((module) => ({ default: module.StatsPage })),
);
const QualityPage = lazy(() =>
  import('./pages/QualityPage.jsx').then((module) => ({ default: module.QualityPage })),
);

function Lazy({ children }) {
  return (
    <Suspense
      fallback={
        <div className="page">
          <LoadingState />
        </div>
      }
    >
      {children}
    </Suspense>
  );
}

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<CatalogPage />} />
        <Route path="films/:qid" element={<FilmPage />} />
        <Route path="people/:qid" element={<PersonPage />} />
        <Route path="graph" element={<Lazy><GraphPage /></Lazy>} />
        <Route path="graph/:qid" element={<Lazy><GraphPage /></Lazy>} />
        <Route path="stats" element={<Lazy><StatsPage /></Lazy>} />
        <Route path="quality" element={<Lazy><QualityPage /></Lazy>} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
