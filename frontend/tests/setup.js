import '@testing-library/jest-dom/vitest';
import { Blob as NodeBlob } from 'node:buffer';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

configure({ asyncUtilTimeout: 3000 });

afterEach(() => {
  cleanup();
  sessionStorage.clear();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

globalThis.Blob = NodeBlob;

window.scrollTo = () => {};

window.matchMedia ??= (query) => ({
  matches: false,
  media: query,
  addEventListener: () => {},
  removeEventListener: () => {},
});
