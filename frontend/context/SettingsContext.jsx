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
  const [theme, setThemeState] = useState('system');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const storedTheme = window.localStorage.getItem(THEME_KEY) || 'system';
    const storedSidebar = window.localStorage.getItem(SIDEBAR_KEY) === 'true';

    setThemeState(storedTheme);
    setSidebarCollapsed(storedSidebar);
    setMounted(true);
  }, []);

  const applyTheme = useCallback((value) => {
    const root = window.document.documentElement;
    if (value === 'dark') {
      root.classList.add('dark');
    } else if (value === 'light') {
      root.classList.remove('dark');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      root.classList.toggle('dark', prefersDark);
    }
  }, []);

  const setTheme = useCallback(
    (value) => {
      setThemeState(value);
      if (typeof window === 'undefined') return;
      window.localStorage.setItem(THEME_KEY, value);
      applyTheme(value);
    },
    [applyTheme]
  );

  useEffect(() => {
    if (!mounted || typeof window === 'undefined' || theme !== 'system') return;

    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const listener = (event) => {
      window.document.documentElement.classList.toggle('dark', event.matches);
    };
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
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
    [theme, setTheme, sidebarCollapsed, toggleSidebar, mounted]
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
