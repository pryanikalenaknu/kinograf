/** Розмітка schema.org: поки відкрита сторінка сутності, у `<head>` є її документ JSON-LD. */

import { useEffect } from 'react';
import { linkedDocument } from '../api/client.js';

export const STRUCTURED_DATA_ATTRIBUTE = 'data-kinograf-entity';

/**
 * Додає в `<head>` елемент `<script type="application/ld+json">` з документом
 * `/data/{kind}/{qid}.jsonld` і прибирає його, коли сторінку залишають.
 *
 * @param {{kind: 'film'|'person', qid: string}} props
 */
export function StructuredData({ kind, qid }) {
  useEffect(() => {
    let active = true;
    let script = null;
    linkedDocument(kind, qid)
      .then((data) => {
        if (!active) {
          return;
        }
        script = document.createElement('script');
        script.type = 'application/ld+json';
        script.setAttribute(STRUCTURED_DATA_ATTRIBUTE, `${kind}/${qid}`);
        script.textContent = JSON.stringify(data);
        document.head.append(script);
      })
      .catch(() => {});
    return () => {
      active = false;
      script?.remove();
    };
  }, [kind, qid]);
  return null;
}
