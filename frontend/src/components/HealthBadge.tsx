"use client";

const classMap: Record<string, string> = {
  Healthy: "badge badge-healthy",
  Degraded: "badge badge-degraded",
  Critical: "badge badge-critical",
  Running: "badge badge-healthy",
  Pending: "badge badge-degraded",
  Failed: "badge badge-critical",
  Succeeded: "badge badge-healthy",
  Warning: "badge badge-degraded",
  Normal: "badge badge-info",
};

export default function HealthBadge({ status }: { status: string }) {
  const cls = classMap[status] || "badge badge-unknown";
  return <span className={cls}>{status}</span>;
}
