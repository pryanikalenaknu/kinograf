/** Кольори й шрифти для Chart.js, прочитані з токенів `design/tokens.css`. */

export function token(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function chartTheme() {
  return {
    primary: token('--color-primary'),
    primaryLight: token('--color-primary-light'),
    accent: token('--color-accent'),
    actor: token('--color-role-actor'),
    text: token('--color-text'),
    muted: token('--color-text-muted'),
    border: token('--color-border'),
    surface: token('--color-surface'),
    font: { family: 'Inter, sans-serif', size: 12 },
  };
}

/** Спільні налаштування осей і підказок. */
export function baseOptions(theme) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: theme.text,
        titleColor: theme.surface,
        bodyColor: theme.surface,
        titleFont: { ...theme.font, weight: '500', size: 14 },
        bodyFont: { ...theme.font, size: 13 },
        displayColors: false,
        padding: 8,
        cornerRadius: 6,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { color: theme.border },
        ticks: { color: theme.muted, font: theme.font, maxRotation: 0, autoSkipPadding: 12 },
      },
      y: { display: false, beginAtZero: true },
    },
  };
}
