/** Каркас сторінки: верхня панель і вміст поточного маршруту. */

import { useEffect } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { ErrorBoundary } from './ErrorBoundary.jsx';
import { TopBar } from './TopBar.jsx';

export function Layout() {
  const { pathname } = useLocation();

  useEffect(() => {
    window.scrollTo?.(0, 0);
  }, [pathname]);

  return (
    <>
      <a className="skip-link" href="#content">
        Перейти до вмісту
      </a>
      <TopBar />
      <main id="content">
        <ErrorBoundary key={pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
    </>
  );
}
