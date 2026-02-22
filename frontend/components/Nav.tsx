import Link from 'next/link';

export function Nav() {
  return (
    <nav>
      <Link href="/">Overview</Link>
      <Link href="/settings">Settings</Link>
      <Link href="/admin">Admin</Link>
      <Link href="/login">Login</Link>
    </nav>
  );
}
