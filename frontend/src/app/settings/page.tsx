"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMe, updateTheme, type User } from "@/lib/api";
import { LoadingSpinner } from "@/components/StatusStates";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleThemeChange = async (theme: string) => {
    if (!user) return;
    setSaving(true);
    try {
      const updated = await updateTheme(theme);
      setUser(updated);
      document.documentElement.setAttribute("data-theme", theme);
      setToast("Theme updated!");
      setTimeout(() => setToast(null), 2000);
    } catch {
      setToast("Failed to update theme");
      setTimeout(() => setToast(null), 2000);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div className="page-container">
      <div className="breadcrumb">
        <Link href="/">Overview</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Settings</span>
      </div>

      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Customize your Namespace Observatory experience</p>
      </div>

      {/* Theme Selector */}
      <div className="card mb-4">
        <div className="card-title">Theme</div>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", marginBottom: 16 }}>
          Choose a visual style for the interface. Your preference is saved to your profile.
        </p>
        <div style={{ display: "flex", gap: 16 }}>
          <ThemeOption
            name="Minimal"
            value="minimal"
            current={user?.theme_pref || "minimal"}
            description="Clean, light design with subtle borders and smooth shadows"
            onSelect={handleThemeChange}
            disabled={saving}
          />
          <ThemeOption
            name="Neo-Brutal"
            value="neo-brutal"
            current={user?.theme_pref || "minimal"}
            description="Bold borders, thick shadows, high-contrast blocks"
            onSelect={handleThemeChange}
            disabled={saving}
          />
        </div>
      </div>

      {/* Profile Info */}
      <div className="card">
        <div className="card-title">Profile</div>
        <div style={{ fontSize: "0.9rem" }}>
          <div style={{ marginBottom: 8 }}>
            <strong>Email:</strong> {user?.email}
          </div>
          <div style={{ marginBottom: 8 }}>
            <strong>Role:</strong>{" "}
            <span className="badge badge-info">{user?.role}</span>
          </div>
          <div>
            <strong>Allowed Namespaces:</strong>{" "}
            {user?.allowed_namespaces.includes("*")
              ? "All namespaces"
              : user?.allowed_namespaces.join(", ") || "None"}
          </div>
        </div>
      </div>

      {toast && <div className="toast toast-success">{toast}</div>}
    </div>
  );
}

function ThemeOption({
  name,
  value,
  current,
  description,
  onSelect,
  disabled,
}: {
  name: string;
  value: string;
  current: string;
  description: string;
  onSelect: (v: string) => void;
  disabled: boolean;
}) {
  const active = current === value;
  return (
    <button
      className="card"
      onClick={() => onSelect(value)}
      disabled={disabled}
      style={{
        flex: 1,
        cursor: disabled ? "wait" : "pointer",
        borderColor: active ? "var(--accent)" : undefined,
        borderWidth: active ? "3px" : undefined,
        textAlign: "left",
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: 4, fontSize: "1rem" }}>
        {name}
        {active && <span style={{ color: "var(--accent)", marginLeft: 8 }}>Active</span>}
      </div>
      <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>{description}</div>
    </button>
  );
}
