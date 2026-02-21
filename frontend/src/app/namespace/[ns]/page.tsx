"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  getNamespaceSummary,
  getWorkloads,
  getPods,
  getEvents,
  getConfig,
  type Workload,
  type Pod,
  type EventItem,
  type ConfigItem,
} from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { LoadingSpinner, ErrorBox, EmptyState } from "@/components/StatusStates";
import SortableTable from "@/components/SortableTable";
import HealthBadge from "@/components/HealthBadge";

export default function NamespaceDetailPage({ params }: { params: Promise<{ ns: string }> }) {
  const { ns } = use(params);
  const router = useRouter();
  const [tab, setTab] = useState<"workloads" | "pods" | "events" | "config">("workloads");

  const summary = useFetch(() => getNamespaceSummary(ns), [ns]);
  const workloads = useFetch(() => getWorkloads(ns), [ns]);
  const pods = useFetch(() => getPods(ns), [ns]);
  const events = useFetch(() => getEvents(ns), [ns]);
  const config = useFetch(() => getConfig(ns), [ns]);

  const s = summary.data;

  return (
    <div className="page-container">
      <div className="breadcrumb">
        <Link href="/">Overview</Link>
        <span className="breadcrumb-sep">/</span>
        <span>{ns}</span>
      </div>

      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">{ns}</h1>
          {s && (
            <p className="page-subtitle">
              <HealthBadge status={s.health} />
            </p>
          )}
        </div>
        <button className="btn" onClick={() => { summary.refetch(); workloads.refetch(); pods.refetch(); events.refetch(); config.refetch(); }}>
          Refresh
        </button>
      </div>

      {summary.loading && <LoadingSpinner />}
      {summary.error && <ErrorBox message={summary.error} />}

      {s && (
        <div className="stat-grid">
          <div className="card stat-card">
            <div className="stat-value">
              {s.deployments_ready}/{s.deployments_total}
            </div>
            <div className="stat-label">Deployments Ready</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value">{s.pods_running}</div>
            <div className="stat-label">Pods Running</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value" style={s.pods_failed > 0 ? { color: "var(--danger)" } : undefined}>
              {s.pods_failed}
            </div>
            <div className="stat-label">Pods Failed</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value" style={s.warning_events > 5 ? { color: "var(--warning)" } : undefined}>
              {s.warning_events}
            </div>
            <div className="stat-label">Warning Events</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value">{s.top_restart_count}</div>
            <div className="stat-label">Top Restarts</div>
          </div>
          <div className="card stat-card">
            <div className="stat-value">{s.pods_pending}</div>
            <div className="stat-label">Pods Pending</div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="tabs">
        {(["workloads", "pods", "events", "config"] as const).map((t) => (
          <button key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
            {t === "events" && events.data ? ` (${events.data.length})` : ""}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "workloads" && (
        <WorkloadsTab
          data={workloads.data}
          loading={workloads.loading}
          error={workloads.error}
          onRowClick={(w: Workload) => router.push(`/workload/${w.kind}/${ns}/${w.name}`)}
        />
      )}
      {tab === "pods" && (
        <PodsTab
          data={pods.data}
          loading={pods.loading}
          error={pods.error}
          onRowClick={(p: Pod) => router.push(`/pod/${ns}/${p.name}`)}
        />
      )}
      {tab === "events" && (
        <EventsTab data={events.data} loading={events.loading} error={events.error} />
      )}
      {tab === "config" && (
        <ConfigTab data={config.data} loading={config.loading} error={config.error} />
      )}
    </div>
  );
}

function WorkloadsTab({
  data,
  loading,
  error,
  onRowClick,
}: {
  data: Workload[] | null;
  loading: boolean;
  error: string | null;
  onRowClick: (w: Workload) => void;
}) {
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBox message={error} />;
  if (!data || data.length === 0) return <EmptyState title="No workloads" />;
  return (
    <SortableTable
      columns={[
        { key: "kind", label: "Kind" },
        { key: "name", label: "Name" },
        {
          key: "replicas",
          label: "Ready / Desired",
          render: (w: Workload) => `${w.ready} / ${w.desired}`,
          sortValue: (w: Workload) => w.ready,
        },
        {
          key: "available",
          label: "Available",
          sortValue: (w: Workload) => w.available,
        },
        {
          key: "health",
          label: "Status",
          render: (w: Workload) => (
            <HealthBadge status={w.ready >= w.desired && w.desired > 0 ? "Healthy" : "Degraded"} />
          ),
          sortValue: (w: Workload) => (w.ready >= w.desired ? 1 : 0),
        },
      ]}
      data={data as unknown as Record<string, unknown>[]}
      onRowClick={onRowClick as (item: Record<string, unknown>) => void}
    />
  );
}

function PodsTab({
  data,
  loading,
  error,
  onRowClick,
}: {
  data: Pod[] | null;
  loading: boolean;
  error: string | null;
  onRowClick: (p: Pod) => void;
}) {
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBox message={error} />;
  if (!data || data.length === 0) return <EmptyState title="No pods" />;
  return (
    <SortableTable
      columns={[
        { key: "name", label: "Name" },
        {
          key: "phase",
          label: "Phase",
          render: (p: Pod) => <HealthBadge status={p.phase} />,
        },
        { key: "node", label: "Node" },
        {
          key: "restart_count",
          label: "Restarts",
          sortValue: (p: Pod) => p.restart_count,
        },
        {
          key: "start_time",
          label: "Started",
          render: (p: Pod) =>
            p.start_time ? new Date(p.start_time).toLocaleString() : "—",
        },
      ]}
      data={data as unknown as Record<string, unknown>[]}
      onRowClick={onRowClick as (item: Record<string, unknown>) => void}
    />
  );
}

function EventsTab({
  data,
  loading,
  error,
}: {
  data: EventItem[] | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBox message={error} />;
  if (!data || data.length === 0) return <EmptyState title="No events" />;
  return (
    <SortableTable
      columns={[
        {
          key: "type",
          label: "Type",
          render: (e: EventItem) => <HealthBadge status={e.type} />,
        },
        { key: "reason", label: "Reason" },
        { key: "message", label: "Message" },
        { key: "involved_object", label: "Object" },
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
      data={data as unknown as Record<string, unknown>[]}
    />
  );
}

function ConfigTab({
  data,
  loading,
  error,
}: {
  data: ConfigItem[] | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorBox message={error} />;
  if (!data || data.length === 0) return <EmptyState title="No config resources" />;
  return (
    <SortableTable
      columns={[
        { key: "kind", label: "Kind" },
        { key: "name", label: "Name" },
      ]}
      data={data as unknown as Record<string, unknown>[]}
    />
  );
}
