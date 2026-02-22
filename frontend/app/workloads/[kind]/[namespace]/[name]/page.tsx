'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { apiFetch } from '../../../../../lib/api';

export default function WorkloadDetail() {
  const { kind, namespace, name } = useParams<{kind:string; namespace:string; name:string}>();
  const [item, setItem] = useState<any>(null);
  useEffect(() => { apiFetch(`/api/workloads/${kind}/${namespace}/${name}`).then(setItem); }, [kind, namespace, name]);
  if (!item) return <main className="container">Loading...</main>;
  return <main className="container"><h1>{kind} {name}</h1><div className="card"><p>Replicas {item.ready}/{item.desired}</p><p>Images: {item.images.join(', ')}</p><p>Conditions: {(item.conditions || []).map((c:any)=>c.type + ':' + c.message).join(' | ')}</p></div><h3>Pods</h3><ul>{(item.pods || []).map((p:any)=><li key={p.name}><Link href={`/pods/${namespace}/${p.name}`}>{p.name}</Link></li>)}</ul></main>;
}
