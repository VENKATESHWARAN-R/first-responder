"use client";

import { use } from "react";
import Link from "next/link";
import { getPodDetail, type PodDetail, type Diagnostic, type EventItem, type ContainerStatus } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { LoadingSpinner, ErrorBox, EmptyState } from "@/components/StatusStates";
import SortableTable from "@/components/SortableTable";
import HealthBadge from "@/components/HealthBadge";

export default function PodDetailPage({
  params,
}: {
  params: Promise<{ ns: string; name: string }>;
}) {
  const { ns, name } = use(params);
  const { data, loading, error, refetch } = useFetch(
    () => getPodDetail(ns, name),
    [ns, name],
  );

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="page-container"><ErrorBox message={error} /></div>;
  if (!data) return <div className="page-container"><EmptyState title="Pod not found" /></div>;

  const pod: PodDetail = data;

  return (
    <div className="page-container">
      <div className="breadcrumb">
        <Link href="/">Overview</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/namespace/${ns}`}>{ns}</Link>
        <span className="breadcrumb-sep">/</span>
        <span>{name}</span>
      </div>

      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">{name}</h1>
          <p className="page-subtitle">
            <HealthBadge status={pod.phase} />
            {pod.node && (
              <span style={{ marginLeft: 12, color: "var(--text-secondary)", fontSize: "0.9rem" }}>
                Node: {pod.node}
              </span>
            )}
          </p>
        </div>
        <button className="btn" onClick={refetch}>
          Refresh
        </button>
      </div>

      {/* Pod Info */}
      <div className="stat-grid">
        <div className="card stat-card">
          <div className="stat-value">{pod.phase}</div>
          <div className="stat-label">Phase</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{pod.restart_count}</div>
          <div className="stat-label">Total Restarts</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value" style={{ fontSize: "1rem" }}>{pod.node || "—"}</div>
          <div className="stat-label">Node</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value" style={{ fontSize: "1rem" }}>
            {pod.start_time ? new Date(pod.start_time).toLocaleString() : "—"}
          </div>
          <div className="stat-label">Start Time</div>
        </div>
      </div>

      {/* Diagnostics */}
      {pod.likely_causes.length > 0 && (
        <div className="mb-4">
          <h2 style={{ fontSize: "1.2rem", fontWeight: 700, marginBottom: 12 }}>
            Likely Causes
          </h2>
          {pod.likely_causes.map((d: Diagnostic) => (
            <div key={d.id} className={`card diagnostic-card severity-${d.severity}`}>
              <div className="flex-between">
                <div className="diagnostic-title">{d.title}</div>
                <HealthBadge status={d.severity === "critical" ? "Critical" : "Degraded"} />
              </div>
              <div className="diagnostic-signal">{d.signal}</div>
              <div className="diagnostic-desc">{d.description}</div>
              <div className="diagnostic-remediation">{d.remediation}</div>
            </div>
          ))}
        </div>
      )}

      {/* Container Statuses */}
      <div className="card mb-4">
        <div className="card-title">Containers ({pod.containers.length})</div>
        {pod.containers.map((c: ContainerStatus) => (
          <div
            key={c.name}
            style={{
              padding: "12px 0",
              borderBottom: "1px solid var(--border-color)",
            }}
          >
            <div className="flex-between" style={{ marginBottom: 8 }}>
              <strong>{c.name}</strong>
              <div className="flex gap-2">
                <HealthBadge status={c.ready ? "Running" : "Pending"} />
                <span className="badge badge-info">Restarts: {c.restart_count}</span>
              </div>
            </div>
            <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              <div>
                Image: <span className="text-mono">{c.image}</span>
              </div>
              <div>
                State: <strong>{c.state.state}</strong>
                {c.state.reason && ` — ${c.state.reason}`}
                {c.state.message && ` (${c.state.message})`}
              </div>
              {c.last_state && c.last_state.state !== "unknown" && (
                <div>
                  Last State: <strong>{c.last_state.state}</strong>
                  {c.last_state.reason && ` — ${c.last_state.reason}`}
                  {c.last_state.exit_code !== undefined && ` (exit code: ${c.last_state.exit_code})`}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Events */}
      <div className="card">
        <div className="card-title">Events ({pod.events.length})</div>
        {pod.events.length > 0 ? (
          <SortableTable
            columns={[
              {
                key: "type",
                label: "Type",
                render: (e: EventItem) => <HealthBadge status={e.type} />,
              },
              { key: "reason", label: "Reason" },
              { key: "message", label: "Message" },
              {
                key: "count",
                label: "Count",
                sortValue: (e: EventItem) => e.count,
              },
              {
                key: "last_seen",
                label: "Last Seen",
                render: (e: EventItem) =>
                  e.last_seen ? new Date(e.last_seen).toLocaleString() : "—",
              },
            ]}
            data={pod.events as unknown as Record<string, unknown>[]}
          />
        ) : (
          <EmptyState title="No events" />
        )}
      </div>
    </div>
  );
}
