/**
 * API client for communicating with the backend.
 * All requests go through the Next.js rewrite proxy → FastAPI.
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = body.detail || msg;
    } catch {
      /* ignore */
    }
    throw new ApiError(res.status, msg);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────

export interface User {
  id: number;
  email: string;
  role: string;
  allowed_namespaces: string[];
  theme_pref: string;
}

export function login(email: string, password: string) {
  return request<{ message: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout() {
  return request<{ message: string }>("/api/auth/logout", { method: "POST" });
}

export function getMe() {
  return request<User>("/api/me");
}

export function updateTheme(theme_pref: string) {
  return request<User>("/api/me/theme", {
    method: "PATCH",
    body: JSON.stringify({ theme_pref }),
  });
}

// ── Admin ─────────────────────────────────────────────────────────────

export function listUsers() {
  return request<User[]>("/api/admin/users");
}

export function createUser(data: {
  email: string;
  password: string;
  role: string;
  allowed_namespaces: string[];
}) {
  return request<User>("/api/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function updateUser(
  id: number,
  data: { role?: string; allowed_namespaces?: string[]; password?: string },
) {
  return request<User>(`/api/admin/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export function deleteUser(id: number) {
  return request<void>(`/api/admin/users/${id}`, { method: "DELETE" });
}

// ── Kubernetes ────────────────────────────────────────────────────────

export interface NamespaceSummary {
  name: string;
  health: string;
  deployments_ready: number;
  deployments_total: number;
  pods_running: number;
  pods_pending: number;
  pods_failed: number;
  pods_total: number;
  top_restart_count: number;
  warning_events: number;
  last_refreshed: string;
}

export function getNamespaces() {
  return request<NamespaceSummary[]>("/api/namespaces");
}

export function getNamespaceSummary(ns: string) {
  return request<NamespaceSummary>(`/api/namespaces/${ns}/summary`);
}

export interface Workload {
  kind: string;
  name: string;
  namespace: string;
  desired: number;
  ready: number;
  available: number;
  images: string[];
  conditions: { type: string; status: string; message: string }[];
}

export function getWorkloads(ns: string) {
  return request<Workload[]>(`/api/namespaces/${ns}/workloads`);
}

export interface Pod {
  name: string;
  namespace: string;
  phase: string;
  node: string | null;
  start_time: string | null;
  restart_count: number;
  containers: ContainerStatus[];
}

export interface ContainerStatus {
  name: string;
  ready: boolean;
  restart_count: number;
  state: { state: string; reason?: string; message?: string; exit_code?: number };
  last_state: { state: string; reason?: string; message?: string; exit_code?: number } | null;
  image: string;
}

export function getPods(ns: string) {
  return request<Pod[]>(`/api/namespaces/${ns}/pods`);
}

export interface PodDetail extends Pod {
  events: EventItem[];
  likely_causes: Diagnostic[];
}

export interface Diagnostic {
  id: string;
  severity: string;
  title: string;
  description: string;
  remediation: string;
  signal: string;
}

export function getPodDetail(ns: string, name: string) {
  return request<PodDetail>(`/api/pods/${ns}/${name}`);
}

export interface EventItem {
  type: string;
  reason: string;
  message: string;
  source: string;
  first_seen: string | null;
  last_seen: string | null;
  count: number;
  involved_object: string;
}

export function getEvents(ns: string) {
  return request<EventItem[]>(`/api/namespaces/${ns}/events`);
}

export interface ConfigItem {
  kind: string;
  name: string;
  namespace: string;
}

export function getConfig(ns: string) {
  return request<ConfigItem[]>(`/api/namespaces/${ns}/config`);
}

export interface WorkloadDetail extends Workload {
  selector: Record<string, string>;
  pods: Pod[];
}

export function getWorkloadDetail(kind: string, ns: string, name: string) {
  return request<WorkloadDetail>(`/api/workloads/${kind}/${ns}/${name}`);
}

export interface JobItem {
  kind: string;
  name: string;
  namespace: string;
  active?: number;
  succeeded?: number;
  failed?: number;
  start_time?: string | null;
  completion_time?: string | null;
  schedule?: string;
  last_schedule?: string | null;
}

export function getJobs(ns: string) {
  return request<JobItem[]>(`/api/namespaces/${ns}/jobs`);
}
