'use client';

import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiFetch } from '../../../../lib/api';

export default function PodDetail() {
  const { namespace, pod } = useParams<{namespace:string; pod:string}>();
  const [item, setItem] = useState<any>(null);
  useEffect(() => { apiFetch(`/api/pods/${namespace}/${pod}`).then(setItem); }, [namespace, pod]);
  if (!item) return <main className="container">Loading...</main>;
  return <main className="container"><h1>Pod {pod}</h1><div className="card"><p>Phase: {item.phase}</p><p>Node: {item.node}</p><p>Likely cause: {item.likely_cause?.diagnosis} (signal: {item.likely_cause?.signal})</p></div><table className="table"><thead><tr><th>Container</th><th>State</th><th>Last State</th><th>Restarts</th></tr></thead><tbody>{item.container_statuses.map((c:any)=><tr key={c.name}><td>{c.name}</td><td>{c.state_reason || c.state}</td><td>{c.last_state_reason}</td><td>{c.restart_count}</td></tr>)}</tbody></table><h3>Events</h3><ul>{item.events.map((e:any,i:number)=><li key={i}>{e.type} {e.reason}: {e.message}</li>)}</ul></main>;
}
