"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { getNamespaces, type NamespaceSummary } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { LoadingSpinner, ErrorBox, EmptyState } from "@/components/StatusStates";
import HealthBadge from "@/components/HealthBadge";

export default function OverviewPage() {
  const router = useRouter();
  const { data, loading, error, refetch } = useFetch(getNamespaces);
  const [search, setSearch] = useState("");

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="page-container"><ErrorBox message={error} /></div>;
  if (!data || data.length === 0) {
    return (
      <div className="page-container">
        <EmptyState
          title="No namespaces available"
          description="You don't have access to any namespaces, or the cluster is unreachable."
        />
      </div>
    );
  }

  const filtered = data.filter((ns) =>
    ns.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="page-container">
      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">Cluster Overview</h1>
          <p className="page-subtitle">
            Monitoring {data.length} namespace{data.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button className="btn" onClick={refetch}>
          Refresh
        </button>
      </div>

      <div className="search-bar">
        <input
          className="input"
          placeholder="Search namespaces…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="ns-grid">
        {filtered.map((ns) => (
          <NamespaceCard
            key={ns.name}
            ns={ns}
            onClick={() => router.push(`/namespace/${ns.name}`)}
          />
        ))}
      </div>
      {filtered.length === 0 && (
        <EmptyState title="No matching namespaces" description="Try a different search term." />
      )}
    </div>
  );
}

function NamespaceCard({ ns, onClick }: { ns: NamespaceSummary; onClick: () => void }) {
  return (
    <div className="card ns-card" onClick={onClick} role="button" tabIndex={0}>
      <div className="ns-card-header">
        <span className="ns-card-name">{ns.name}</span>
        <HealthBadge status={ns.health} />
      </div>
      <div className="ns-card-stats">
        <div className="ns-card-stat">
          <span className="ns-card-stat-label">Deployments</span>
          <span className="ns-card-stat-value">
            {ns.deployments_ready}/{ns.deployments_total}
          </span>
        </div>
        <div className="ns-card-stat">
          <span className="ns-card-stat-label">Pods</span>
          <span className="ns-card-stat-value">
            {ns.pods_running}/{ns.pods_total}
          </span>
        </div>
        <div className="ns-card-stat">
          <span className="ns-card-stat-label">Failed pods</span>
          <span className="ns-card-stat-value" style={ns.pods_failed > 0 ? { color: "var(--danger)" } : undefined}>
            {ns.pods_failed}
          </span>
        </div>
        <div className="ns-card-stat">
          <span className="ns-card-stat-label">Warnings</span>
          <span className="ns-card-stat-value" style={ns.warning_events > 0 ? { color: "var(--warning)" } : undefined}>
            {ns.warning_events}
          </span>
        </div>
        <div className="ns-card-stat">
          <span className="ns-card-stat-label">Restarts (top)</span>
          <span className="ns-card-stat-value">{ns.top_restart_count}</span>
        </div>
        <div className="ns-card-stat">
          <span className="ns-card-stat-label">Pending</span>
          <span className="ns-card-stat-value">{ns.pods_pending}</span>
        </div>
      </div>
      <div className="ns-card-footer">
        Last refreshed: {ns.last_refreshed ? new Date(ns.last_refreshed).toLocaleTimeString() : "—"}
      </div>
    </div>
  );
}
