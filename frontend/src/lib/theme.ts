export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'tf_theme';

export function getStoredTheme(): Theme | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === 'light' || v === 'dark') return v;
    return null;
  } catch {
    return null;
  }
}

export function applyTheme(theme: Theme) {
  const root = document.documentElement;
  if (theme === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
}

export function setTheme(theme: Theme) {
  try { localStorage.setItem(STORAGE_KEY, theme); } catch {}
  applyTheme(theme);
}

export function initTheme(defaultTheme: Theme = 'light') {
  const stored = getStoredTheme();
  applyTheme(stored || defaultTheme);
}

export function toggleTheme() {
  const root = document.documentElement;
  const isDark = root.classList.contains('dark');
  const next: Theme = isDark ? 'light' : 'dark';
  setTheme(next);
  return next;
}
