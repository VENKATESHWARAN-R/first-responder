'use client';

import { useState } from 'react';
import { apiFetch } from '../../lib/api';

export default function LoginPage() {
  const [email, setEmail] = useState('admin@example.com');
  const [password, setPassword] = useState('admin123!');
  const [msg, setMsg] = useState('');
  async function submit() {
    try {
      await apiFetch('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
      setMsg('Login successful');
      window.location.href = '/';
    } catch (e) {
      setMsg(String(e));
    }
  }
  return <main className="container"><h1>Login</h1><div className="card"><input value={email} onChange={(e)=>setEmail(e.target.value)} /><input type="password" value={password} onChange={(e)=>setPassword(e.target.value)} /><button className="button" onClick={submit}>Login</button><p>{msg}</p></div></main>;
}
