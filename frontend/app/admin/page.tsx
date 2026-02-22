'use client';

import { useEffect, useState } from 'react';
import { apiFetch } from '../../lib/api';

export default function AdminPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [form, setForm] = useState({ email: '', password: '', role: 'viewer', allowed_namespaces: '' });
  const load = () => apiFetch('/api/admin/users').then(setUsers).catch(() => setUsers([]));
  useEffect(() => { load(); }, []);
  const create = async () => {
    await apiFetch('/api/admin/users', { method: 'POST', body: JSON.stringify({ ...form, allowed_namespaces: form.allowed_namespaces.split(',').map((x) => x.trim()).filter(Boolean) }) });
    setForm({ email: '', password: '', role: 'viewer', allowed_namespaces: '' });
    load();
  };
  return <main className="container"><h1>Admin Users</h1><div className="card"><input placeholder="email" value={form.email} onChange={(e)=>setForm({...form,email:e.target.value})}/><input type="password" placeholder="password" value={form.password} onChange={(e)=>setForm({...form,password:e.target.value})}/><input placeholder="namespaces csv" value={form.allowed_namespaces} onChange={(e)=>setForm({...form,allowed_namespaces:e.target.value})}/><button className="button" onClick={create}>Create user</button></div><table className="table"><thead><tr><th>Email</th><th>Role</th><th>Namespaces</th></tr></thead><tbody>{users.map((u)=><tr key={u.id}><td>{u.email}</td><td>{u.role}</td><td>{u.allowed_namespaces.join(', ')}</td></tr>)}</tbody></table></main>;
}
