"use client";

import { use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getWorkloadDetail, type Pod, type WorkloadDetail } from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { LoadingSpinner, ErrorBox, EmptyState } from "@/components/StatusStates";
import SortableTable from "@/components/SortableTable";
import HealthBadge from "@/components/HealthBadge";

export default function WorkloadDetailPage({
  params,
}: {
  params: Promise<{ kind: string; ns: string; name: string }>;
}) {
  const { kind, ns, name } = use(params);
  const router = useRouter();
  const { data, loading, error, refetch } = useFetch(
    () => getWorkloadDetail(kind, ns, name),
    [kind, ns, name],
  );

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="page-container"><ErrorBox message={error} /></div>;
  if (!data) return <div className="page-container"><EmptyState title="Workload not found" /></div>;

  const w: WorkloadDetail = data;
  const healthy = w.ready >= w.desired && w.desired > 0;

  return (
    <div className="page-container">
      <div className="breadcrumb">
        <Link href="/">Overview</Link>
        <span className="breadcrumb-sep">/</span>
        <Link href={`/namespace/${ns}`}>{ns}</Link>
        <span className="breadcrumb-sep">/</span>
        <span>
          {kind}/{name}
        </span>
      </div>

      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">
            {kind}: {name}
          </h1>
          <p className="page-subtitle">
            <HealthBadge status={healthy ? "Healthy" : "Degraded"} />
          </p>
        </div>
        <button className="btn" onClick={refetch}>
          Refresh
        </button>
      </div>

      <div className="stat-grid">
        <div className="card stat-card">
          <div className="stat-value">{w.desired}</div>
          <div className="stat-label">Desired</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{w.ready}</div>
          <div className="stat-label">Ready</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{w.available}</div>
          <div className="stat-label">Available</div>
        </div>
      </div>

      {/* Images */}
      <div className="card mb-4">
        <div className="card-title">Container Images</div>
        {w.images.length === 0 ? (
          <span style={{ color: "var(--text-muted)" }}>None</span>
        ) : (
          <ul style={{ listStyle: "none", padding: 0 }}>
            {w.images.map((img, i) => (
              <li key={i} className="text-mono" style={{ fontSize: "0.85rem", padding: "4px 0" }}>
                {img}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Conditions */}
      {w.conditions.length > 0 && (
        <div className="card mb-4">
          <div className="card-title">Rollout Conditions</div>
          <SortableTable
            columns={[
              { key: "type", label: "Type" },
              {
                key: "status",
                label: "Status",
                render: (c: Record<string, unknown>) => (
                  <HealthBadge status={c.status === "True" ? "Healthy" : "Degraded"} />
                ),
              },
              { key: "message", label: "Message" },
            ]}
            data={w.conditions as unknown as Record<string, unknown>[]}
          />
        </div>
      )}

      {/* Pods */}
      <div className="card">
        <div className="card-title">Pods ({w.pods?.length ?? 0})</div>
        {w.pods && w.pods.length > 0 ? (
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
            ]}
            data={w.pods as unknown as Record<string, unknown>[]}
            onRowClick={(p) => router.push(`/pod/${ns}/${(p as unknown as Pod).name}`)}
          />
        ) : (
          <EmptyState title="No pods found for this workload" />
        )}
      </div>
    </div>
  );
}
