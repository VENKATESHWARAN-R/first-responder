export async function apiFetch(path: string, init?: RequestInit) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE ?? 'http://localhost:8000'}${path}`, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) }
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
