/** Сторінка для невідомої адреси. */

import { EmptyState } from '../components/States.jsx';

export function NotFoundPage() {
  return (
    <div className="page">
      <EmptyState title="Сторінку не знайдено" text="Перевірте адресу або поверніться до каталогу." />
    </div>
  );
}
