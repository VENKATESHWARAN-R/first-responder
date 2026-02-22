'use client';

import { createContext, useContext, useEffect, useState } from 'react';
import { apiFetch } from '../lib/api';

type Theme = 'minimal' | 'neo-brutal';

const ThemeContext = createContext<{ theme: Theme; setTheme: (t: Theme) => void }>({
  theme: 'minimal',
  setTheme: () => undefined,
});

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>('minimal');

  const readCookieTheme = (): Theme | null => {
    const cookieValue = document.cookie
      .split('; ')
      .find((row) => row.startsWith('theme_pref='))
      ?.split('=')[1];
    if (cookieValue === 'minimal' || cookieValue === 'neo-brutal') {
      return cookieValue;
    }
    return null;
  };

  useEffect(() => {
    const localTheme = localStorage.getItem('theme_pref') as Theme | null;
    const cookieTheme = readCookieTheme();
    const savedTheme = localTheme || cookieTheme;
    if (savedTheme) {
      setTheme(savedTheme);
      return;
    }

    apiFetch('/api/me')
      .then((me) => {
        const serverTheme = me?.theme_pref as Theme | undefined;
        if (serverTheme === 'minimal' || serverTheme === 'neo-brutal') {
          setTheme(serverTheme);
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme_pref', theme);
    document.cookie = `theme_pref=${theme}; path=/; max-age=31536000; samesite=lax`;
  }, [theme]);

  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
