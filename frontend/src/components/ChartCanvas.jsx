/** Обгортка Chart.js: створює діаграму на полотні й оновлює її при зміні налаштувань. */

import {
  BarController,
  BarElement,
  CategoryScale,
  Chart,
  Filler,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { useEffect, useRef } from 'react';

Chart.register(
  BarController,
  BarElement,
  CategoryScale,
  Filler,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
);

export function ChartCanvas({ config, label, className }) {
  const canvas = useRef(null);
  const chart = useRef(null);

  useEffect(() => {
    chart.current = new Chart(canvas.current, config);
    return () => chart.current.destroy();
  }, [config]);

  return (
    <div className={className}>
      <canvas ref={canvas} role="img" aria-label={label} />
    </div>
  );
}
