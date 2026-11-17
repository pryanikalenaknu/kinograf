/** Модальні вікна: діалог по центру й шторка знизу екрана. */

import { useEffect, useRef } from 'react';
import { Icon } from './Icon.jsx';
import { useFocusTrap } from './useFocusTrap.js';
import './Overlay.css';

function useEscape(onClose) {
  useEffect(() => {
    const close = (event) => event.key === 'Escape' && onClose();
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [onClose]);
}

export function Dialog({ title, onClose, children, role = 'dialog' }) {
  const ref = useRef(null);
  useEscape(onClose);
  useFocusTrap(ref);
  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div ref={ref} className="dialog" role={role} aria-modal="true" aria-label={title} tabIndex={-1}>
        <h2 className="panel-title">{title}</h2>
        {children}
      </div>
    </>
  );
}

export function Sheet({ title, onClose, children }) {
  const ref = useRef(null);
  useEscape(onClose);
  useFocusTrap(ref);
  return (
    <div className="overlay sheet-backdrop" onClick={onClose}>
      <div
        ref={ref}
        tabIndex={-1}
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="sheet-handle" />
        <div className="sheet-head">
          <h2 className="panel-title">{title}</h2>
          <button type="button" className="btn-plain" aria-label="Закрити" onClick={onClose}>
            <Icon name="close" size={20} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
