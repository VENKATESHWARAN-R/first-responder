'use client';

import { useTheme } from '../../components/ThemeProvider';
import { apiFetch } from '../../lib/api';

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const persist = async (nextTheme: 'minimal' | 'neo-brutal') => {
    setTheme(nextTheme);
    await apiFetch('/api/me/theme', { method: 'PATCH', body: JSON.stringify({ theme_pref: nextTheme }) });
  };
  return (
    <main className="container">
      <h1>Settings</h1>
      <div className="card">
        <label htmlFor="theme">Theme</label>
        <select id="theme" value={theme} onChange={(e) => persist(e.target.value as 'minimal' | 'neo-brutal')}>
          <option value="minimal">Minimal</option>
          <option value="neo-brutal">Neo-brutal</option>
        </select>
      </div>
    </main>
  );
}
