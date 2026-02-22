"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type User, logout } from "@/lib/api";

interface HeaderProps {
  user: User | null;
  onLogout?: () => void;
}

export default function Header({ user, onLogout }: HeaderProps) {
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await logout();
    } catch {
      /* ignore */
    }
    onLogout?.();
    router.push("/");
    router.refresh();
  };

  return (
    <header className="app-header">
      <Link href="/" className="app-header-brand" style={{ textDecoration: "none" }}>
        NSO — Namespace Observatory
      </Link>
      {user && (
        <nav className="app-header-nav">
          <Link href="/">Overview</Link>
          <Link href="/settings">Settings</Link>
          {user.role === "admin" && <Link href="/admin">Admin</Link>}
          <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
            {user.email}
          </span>
          <button onClick={handleLogout} className="btn btn-sm">
            Logout
          </button>
        </nav>
      )}
    </header>
  );
}
