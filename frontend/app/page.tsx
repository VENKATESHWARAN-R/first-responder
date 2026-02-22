'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../lib/api';

export default function HomePage() {
  const [items, setItems] = useState<any[]>([]);
  const [q, setQ] = useState('');
  const [error, setError] = useState('');
  useEffect(() => {
    apiFetch('/api/namespaces').then(setItems).catch((e) => setError(String(e)));
  }, []);
  const filtered = useMemo(() => items.filter((it) => it.namespace.includes(q)), [items, q]);
  return (
    <main className="container">
      <h1>Namespace Observatory</h1>
      <input aria-label="Search namespaces" placeholder="Search namespaces" value={q} onChange={(e) => setQ(e.target.value)} />
      {error && <p role="alert">{error}</p>}
      {filtered.length === 0 ? <div className="empty">No access to namespaces yet. Ask an admin for RBAC assignment.</div> : (
        <div className="grid" style={{ marginTop: 16 }}>
          {filtered.map((ns) => (
            <Link className="card" key={ns.namespace} href={`/namespaces/${ns.namespace}`}>
              <h3>{ns.namespace}</h3>
              <span className="badge">{ns.health}</span>
              <p>Deployments: {ns.deployments}</p>
              <p>Pods: R{ns.pods.running}/P{ns.pods.pending}/F{ns.pods.failed}</p>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
