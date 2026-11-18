/** Полотно графа зв'язків на vis-network: вузли «фільм» і «персоналія», масштаб, вибір вузла. */

import { useEffect, useImperativeHandle, useRef } from 'react';
import { DataSet, Network } from 'vis-network/standalone';
import { token } from './chartTheme.js';
import { personImage } from './graphImages.js';

const ROLE_TOKENS = {
  director: '--color-role-director',
  screenwriter: '--color-role-writer',
  composer: '--color-role-composer',
  cast: '--color-role-actor',
};

function visNode(node, selected) {
  const isSelected = node.id === selected;
  const text = token('--color-text');
  if (node.type === 'film') {
    const background = isSelected ? token('--color-accent') : token('--color-primary');
    return {
      id: node.id,
      label: node.label,
      shape: 'box',
      margin: { top: 8, bottom: 8, left: 14, right: 14 },
      widthConstraint: { maximum: 180 },
      color: { background, border: background, highlight: { background, border: background } },
      font: {
        face: 'Inter, sans-serif',
        size: 12,
        color: isSelected ? text : token('--color-on-primary'),
      },
      borderWidth: node.level === 0 ? 3 : 1,
      shapeProperties: { borderRadius: 4 },
    };
  }
  const color = isSelected ? token('--color-accent') : token(ROLE_TOKENS[node.role]);
  return {
    id: node.id,
    label: node.label,
    shape: 'image',
    image: personImage(node.label, color),
    size: node.level === 0 ? 20 : 14,
    font: { face: 'Inter, sans-serif', size: 11, color: text },
  };
}

/**
 * Полотно графа. Через `ref` доступні `zoomIn()`, `zoomOut()`, `fit()` і `focus(id)`.
 *
 * @param {{nodes: object[], edges: object[], selected: string|null,
 *   onSelect: (id: string|null) => void, onZoom: (scale: number) => void}} props
 */
export function GraphCanvas({ nodes, edges, selected, onSelect, onZoom, ref }) {
  const container = useRef(null);
  const network = useRef(null);
  const dataset = useRef(null);
  const handlers = useRef({ onSelect, onZoom });
  const fitTimer = useRef(null);

  useEffect(() => {
    handlers.current = { onSelect, onZoom };
  }, [onSelect, onZoom]);

  useEffect(() => {
    dataset.current = new DataSet(nodes.map((node) => visNode(node, null)));
    const edgeColor = token('--color-border');
    const visEdges = edges.map((edge) => ({
      from: edge.from,
      to: edge.to,
      title: edge.roles.join(', '),
      color: { color: token('--color-text-muted'), highlight: token('--color-primary') },
      width: 1,
    }));
    network.current = new Network(
      container.current,
      { nodes: dataset.current, edges: new DataSet(visEdges) },
      {
        autoResize: true,
        interaction: { hover: true, tooltipDelay: 150 },
        physics: { solver: 'forceAtlas2Based', stabilization: { iterations: 200 } },
        edges: { smooth: false, color: edgeColor },
      },
    );
    const notifyZoom = () => handlers.current.onZoom?.(network.current.getScale());
    network.current.on('click', (event) => handlers.current.onSelect(event.nodes[0] ?? null));
    network.current.on('zoom', notifyZoom);
    network.current.once('stabilizationIterationsDone', () => {
      network.current.setOptions({ physics: false });
      network.current.fit();
      notifyZoom();
    });
    return () => {
      clearTimeout(fitTimer.current);
      network.current.destroy();
    };
  }, [nodes, edges]);

  useEffect(() => {
    dataset.current?.update(nodes.map((node) => visNode(node, selected)));
  }, [nodes, selected]);

  useImperativeHandle(ref, () => {
    const zoomTo = (factor) => {
      const scale = network.current.getScale() * factor;
      network.current.moveTo({ scale, animation: { duration: 200 } });
      handlers.current.onZoom?.(scale);
    };
    return {
      zoomIn: () => zoomTo(1.25),
      zoomOut: () => zoomTo(0.8),
      fit: () => {
        network.current.fit({ animation: { duration: 200 } });
        clearTimeout(fitTimer.current);
        fitTimer.current = setTimeout(
          () => handlers.current.onZoom?.(network.current.getScale()),
          220,
        );
      },
      focus: (id) => {
        network.current.selectNodes([id]);
        network.current.focus(id, { scale: 1.2, animation: { duration: 300 } });
        handlers.current.onZoom?.(1.2);
      },
    };
  }, []);

  return <div ref={container} className="graph-network" />;
}
