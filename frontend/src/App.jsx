/** Маршрути застосунку. */

import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout.jsx';
import { NotFoundPage } from './pages/NotFoundPage.jsx';

export function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}
