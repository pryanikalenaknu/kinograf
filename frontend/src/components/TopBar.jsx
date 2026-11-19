/** Верхня панель: логотип, головне меню, вхід і вихід адміністратора; на вузькому екрані — бокова шторка. */

import { startTransition, useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAdmin } from '../api/admin.js';
import { Icon } from './Icon.jsx';
import { useFocusTrap } from './useFocusTrap.js';
import './TopBar.css';

const NAV = [
  { to: '/', label: 'Каталог', match: ['/', '/films', '/people'] },
  { to: '/graph', label: 'Граф', match: ['/graph'] },
  { to: '/stats', label: 'Статистика', match: ['/stats'] },
  { to: '/quality', label: 'Якість даних', match: ['/quality'] },
  { to: '/sparql', label: 'SPARQL', match: ['/sparql'] },
  { to: '/open-data', label: 'Відкриті дані', match: ['/open-data'] },
];

const ADMIN_ITEM = { to: '/admin', label: 'Адміністрування', match: ['/admin'] };

function isActive(item, pathname) {
  return item.match.some((prefix) =>
    prefix === '/' ? pathname === '/' : pathname === prefix || pathname.startsWith(`${prefix}/`),
  );
}

function Drawer({ children }) {
  const ref = useRef(null);
  useFocusTrap(ref);
  return (
    <nav
      ref={ref}
      tabIndex={-1}
      className="drawer"
      aria-label="Головне меню"
      onClick={(event) => event.stopPropagation()}
    >
      {children}
    </nav>
  );
}

export function TopBar() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { isAdmin, logout } = useAdmin();
  const [menuOpen, setMenuOpen] = useState(false);
  const items = isAdmin ? [...NAV, ADMIN_ITEM] : NAV;
  const loginPage = pathname === '/admin/login';

  useEffect(() => {
    if (!menuOpen) {
      return undefined;
    }
    const close = (event) => event.key === 'Escape' && setMenuOpen(false);
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [menuOpen]);

  const handleLogout = () => {
    setMenuOpen(false);
    navigate('/');
    startTransition(logout);
  };

  const navLinks = (className, onClick) =>
    items.map((item) => (
      <Link
        key={item.to}
        to={item.to}
        className={className}
        aria-current={isActive(item, pathname) && !loginPage ? 'page' : undefined}
        onClick={onClick}
      >
        {item.label}
      </Link>
    ));

  return (
    <header className="topbar">
      <Link to="/" className="topbar-brand">
        <Icon name="film" size={24} className="topbar-logo" />
        КіноГраф
      </Link>
      <nav className="topbar-nav topbar-wide" aria-label="Головне меню">
        {navLinks('topbar-link')}
      </nav>
      <div className="topbar-side">
        {isAdmin ? (
          <>
            <span className="topbar-badge">Адміністратор</span>
            <button type="button" className="topbar-logout topbar-wide" onClick={handleLogout}>
              <Icon name="logout" />
              Вийти
            </button>
          </>
        ) : (
          <Link to="/admin/login" className="topbar-login topbar-wide">
            Вхід для адміністратора
          </Link>
        )}
        <button
          type="button"
          className="topbar-menu topbar-narrow"
          aria-label="Відкрити меню"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(true)}
        >
          <Icon name="menu" size={24} />
        </button>
      </div>
      {menuOpen && (
        <div className="overlay topbar-narrow" onClick={() => setMenuOpen(false)}>
          <Drawer>
            <div className="drawer-head">
              <span className="drawer-brand">КіноГраф</span>
              <button
                type="button"
                className="btn-plain"
                aria-label="Закрити меню"
                onClick={() => setMenuOpen(false)}
              >
                <Icon name="close" size={22} />
              </button>
            </div>
            {navLinks('drawer-link', () => setMenuOpen(false))}
            <div className="drawer-foot">
              {isAdmin ? (
                <button type="button" className="btn drawer-logout" onClick={handleLogout}>
                  <Icon name="logout" />
                  Вийти
                </button>
              ) : (
                <Link
                  to="/admin/login"
                  className="drawer-login"
                  onClick={() => setMenuOpen(false)}
                >
                  Вхід для адміністратора
                </Link>
              )}
            </div>
          </Drawer>
        </div>
      )}
    </header>
  );
}
