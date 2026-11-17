import { createContext, useContext } from 'react';

export const ADMIN_STORAGE_KEY = 'kinograf-admin-key';

export const AdminContext = createContext(null);

/**
 * Повертає стан адміністратора: ключ, ознаку входу, функції входу й виходу.
 *
 * @returns {{adminKey: string, isAdmin: boolean, login: (key: string) => void, logout: () => void}}
 */
export function useAdmin() {
  return useContext(AdminContext);
}
