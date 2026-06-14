// context/SettingsContext.jsx

'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

const SettingsContext = createContext(null);

const THEME_KEY = 'nc_theme';
const SIDEBAR_KEY = 'nc_sidebar_collapsed';

export function SettingsProvider({ children }) {
  const [theme, setTheme] = useState('system');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const storedTheme = window.localStorage.getItem(THEME_KEY) || 'system';
    const storedSidebar = window.localStorage.getItem(SIDEBAR_KEY) === 'true';

    setTheme(storedTheme);
    setSidebarCollapsed(storedSidebar);
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted || typeof window === 'undefined') return;

    const root = window.document.documentElement;
    const apply = (value) => {
      if (value === 'dark') {
        root.classList.add('dark');
      } else if (value === 'light') {
        root.classList.remove('dark');
      } else {
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
        root.classList.toggle('dark', prefersDark);
      }
    };

    apply(theme);
    window.localStorage.setItem(THEME_KEY, theme);

    if (theme === 'system') {
      const media = window.matchMedia('(prefers-color-scheme: dark)');
      const listener = (event) => root.classList.toggle('dark', event.matches);
      media.addEventListener('change', listener);
      return () => media.removeEventListener('change', listener);
    }

    return undefined;
  }, [theme, mounted]);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev;
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(SIDEBAR_KEY, String(next));
      }
      return next;
    });
  }, []);

  const value = useMemo(
    () => ({
      theme,
      setTheme,
      sidebarCollapsed,
      toggleSidebar,
      mounted,
    }),
    [theme, sidebarCollapsed, toggleSidebar, mounted]
  );

  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettingsContext() {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error('useSettingsContext must be used within a SettingsProvider');
  }
  return context;
}