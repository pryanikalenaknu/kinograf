/** Діалог вибору формату експорту: CSV, JSON або Turtle. */

import { useState } from 'react';
import { Dialog } from './Overlay.jsx';
import './ExportDialog.css';

const FORMATS = [
  { value: 'csv', label: 'CSV', description: 'Таблиця для Excel чи Google Таблиць' },
  { value: 'json', label: 'JSON', description: "Масив об'єктів для розробників" },
  { value: 'ttl', label: 'Turtle', description: 'RDF-трійки для графових баз' },
];

export function ExportDialog({ title, onClose, onExport, busy = false, error }) {
  const [format, setFormat] = useState('csv');
  return (
    <Dialog title={title} onClose={onClose}>
      <span className="label muted">Оберіть формат файлу</span>
      <div role="radiogroup" aria-label="Формат файлу" className="export-formats">
        {FORMATS.map((item) => (
          <label key={item.value} className="export-format">
            <input
              type="radio"
              name="export-format"
              value={item.value}
              checked={format === item.value}
              onChange={() => setFormat(item.value)}
            />
            <span className="export-dot" />
            <span className="export-text">
              <span className="export-label">{item.label}</span>
              <span className="label muted">{item.description}</span>
            </span>
          </label>
        ))}
      </div>
      {error && (
        <p className="export-error" role="alert">
          {error}
        </p>
      )}
      <div className="dialog-actions">
        <button type="button" className="btn btn-ghost" onClick={onClose}>
          Скасувати
        </button>
        <button
          type="button"
          className="btn btn-primary"
          disabled={busy}
          onClick={() => onExport(format)}
        >
          Завантажити
        </button>
      </div>
    </Dialog>
  );
}
