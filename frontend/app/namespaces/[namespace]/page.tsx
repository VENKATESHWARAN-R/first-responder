'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiFetch } from '../../../lib/api';

export default function NamespaceDetail() {
  const { namespace } = useParams<{ namespace: string }>();
  const [tab, setTab] = useState('workloads');
  const [summary, setSummary] = useState<any>(null);
  const [workloads, setWorkloads] = useState<any[]>([]);
  const [pods, setPods] = useState<any[]>([]);
  const [events, setEvents] = useState<any[]>([]);
  const [config, setConfig] = useState<any>({ configmaps: [], secrets: [] });
  useEffect(() => {
    apiFetch(`/api/namespaces/${namespace}/summary`).then(setSummary);
    apiFetch(`/api/namespaces/${namespace}/workloads`).then(setWorkloads);
    apiFetch(`/api/namespaces/${namespace}/pods`).then(setPods);
    apiFetch(`/api/namespaces/${namespace}/events`).then(setEvents);
    apiFetch(`/api/namespaces/${namespace}/config`).then(setConfig);
  }, [namespace]);

  return <main className="container"><h1>Namespace: {namespace}</h1>
  {summary && <div className="grid"><div className="card">Health {summary.health}</div><div className="card">Deployments {summary.deployments}</div><div className="card">Top restart {summary.top_restart_count}</div><div className="card">Warnings {events.filter((e)=>e.type==='Warning').length}</div></div>}
  <div className="tabs">{['workloads','pods','events','config'].map(t=><button className="button" key={t} onClick={()=>setTab(t)}>{t}</button>)}</div>
  {tab==='workloads' && <table className="table"><thead><tr><th>Name</th><th>Kind</th><th>Ready</th></tr></thead><tbody>{workloads.map(w=><tr key={w.kind+w.name}><td><Link href={`/workloads/${w.kind}/${namespace}/${w.name}`}>{w.name}</Link></td><td>{w.kind}</td><td>{w.ready}/{w.desired}</td></tr>)}</tbody></table>}
  {tab==='pods' && <table className="table"><thead><tr><th>Name</th><th>Phase</th><th>Restarts</th></tr></thead><tbody>{pods.map((p)=><tr key={p.name}><td><Link href={`/pods/${namespace}/${p.name}`}>{p.name}</Link></td><td>{p.phase}</td><td>{p.restart_count}</td></tr>)}</tbody></table>}
  {tab==='events' && <table className="table"><thead><tr><th>Type</th><th>Reason</th><th>Message</th></tr></thead><tbody>{events.map((e,i)=><tr key={i}><td>{e.type}</td><td>{e.reason}</td><td>{e.message}</td></tr>)}</tbody></table>}
  {tab==='config' && <div className="card"><p>ConfigMaps: {config.configmaps.join(', ') || 'None'}</p><p>Secrets: {config.secrets.join(', ') || 'None'}</p></div>}
  </main>;
}
