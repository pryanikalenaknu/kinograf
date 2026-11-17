import { useCallback, useMemo, useState } from 'react';
import { ADMIN_STORAGE_KEY, AdminContext } from './admin.js';

function storedKey() {
  try {
    return sessionStorage.getItem(ADMIN_STORAGE_KEY) || '';
  } catch {
    return '';
  }
}

/** Зберігає ключ адміністратора лише в пам'яті вкладки (sessionStorage). */
export function AdminProvider({ children }) {
  const [adminKey, setAdminKey] = useState(storedKey);

  const login = useCallback((key) => {
    sessionStorage.setItem(ADMIN_STORAGE_KEY, key);
    setAdminKey(key);
  }, []);

  const logout = useCallback(() => {
    sessionStorage.removeItem(ADMIN_STORAGE_KEY);
    setAdminKey('');
  }, []);

  const value = useMemo(
    () => ({ adminKey, isAdmin: Boolean(adminKey), login, logout }),
    [adminKey, login, logout],
  );
  return <AdminContext.Provider value={value}>{children}</AdminContext.Provider>;
}
