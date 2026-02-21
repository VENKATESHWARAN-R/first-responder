"use client";

import { useEffect, useState } from "react";
import { type User, getMe } from "@/lib/api";
import Header from "@/components/Header";
import LoginPage from "./LoginPage";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMe()
      .then((u) => {
        setUser(u);
        // Apply persisted theme
        document.documentElement.setAttribute("data-theme", u.theme_pref || "minimal");
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <div className="spinner" />
      </div>
    );
  }

  if (!user) {
    return (
      <LoginPage
        onLogin={(u) => {
          setUser(u);
          document.documentElement.setAttribute("data-theme", u.theme_pref || "minimal");
        }}
      />
    );
  }

  return (
    <>
      <Header user={user} onLogout={() => setUser(null)} />
      {children}
    </>
  );
}
