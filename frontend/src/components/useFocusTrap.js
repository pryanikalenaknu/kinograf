import { useEffect } from 'react';

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Переводить фокус у модальне вікно, утримує клавішу Tab усередині нього
 * й повертає фокус на попередній елемент після закриття.
 *
 * @param {import('react').RefObject<HTMLElement>} ref вікно
 */
export function useFocusTrap(ref) {
  useEffect(() => {
    const node = ref.current;
    const previous = document.activeElement;
    const items = () => [...node.querySelectorAll(FOCUSABLE)];
    (items()[0] ?? node).focus();
    const trap = (event) => {
      const focusable = items();
      if (event.key !== 'Tab' || focusable.length === 0) {
        return;
      }
      const first = focusable[0];
      const last = focusable.at(-1);
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    node.addEventListener('keydown', trap);
    return () => {
      node.removeEventListener('keydown', trap);
      previous?.focus?.();
    };
  }, [ref]);
}
