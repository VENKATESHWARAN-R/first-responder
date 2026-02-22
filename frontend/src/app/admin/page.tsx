"use client";

import { useState } from "react";
import Link from "next/link";
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  type User,
} from "@/lib/api";
import { useFetch } from "@/lib/hooks";
import { LoadingSpinner, ErrorBox, EmptyState } from "@/components/StatusStates";

export default function AdminPage() {
  const { data: users, loading, error, refetch } = useFetch(listUsers);
  const [showCreate, setShowCreate] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [toast, setToast] = useState<{ type: string; message: string } | null>(null);

  const showToast = (type: string, message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 3000);
  };

  const handleDelete = async (user: User) => {
    if (!confirm(`Delete user ${user.email}?`)) return;
    try {
      await deleteUser(user.id);
      showToast("success", `Deleted ${user.email}`);
      refetch();
    } catch (err: unknown) {
      showToast("error", err instanceof Error ? err.message : "Failed to delete");
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error) return <div className="page-container"><ErrorBox message={error} /></div>;

  return (
    <div className="page-container">
      <div className="breadcrumb">
        <Link href="/">Overview</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Admin</span>
      </div>

      <div className="page-header flex-between">
        <div>
          <h1 className="page-title">User Management</h1>
          <p className="page-subtitle">{users?.length ?? 0} users</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
          Create User
        </button>
      </div>

      {!users || users.length === 0 ? (
        <EmptyState title="No users" />
      ) : (
        <div className="card">
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Namespaces</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.email}</td>
                    <td>
                      <span className={`badge ${u.role === "admin" ? "badge-info" : "badge-unknown"}`}>
                        {u.role}
                      </span>
                    </td>
                    <td style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {u.allowed_namespaces.includes("*")
                        ? "All"
                        : u.allowed_namespaces.join(", ") || "None"}
                    </td>
                    <td>
                      <div className="flex gap-2">
                        <button className="btn btn-sm" onClick={() => setEditingUser(u)}>
                          Edit
                        </button>
                        <button className="btn btn-sm btn-danger" onClick={() => handleDelete(u)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showCreate && (
        <CreateUserModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            showToast("success", "User created");
            refetch();
          }}
          onError={(msg) => showToast("error", msg)}
        />
      )}

      {editingUser && (
        <EditUserModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onSaved={() => {
            setEditingUser(null);
            showToast("success", "User updated");
            refetch();
          }}
          onError={(msg) => showToast("error", msg)}
        />
      )}

      {toast && (
        <div className={`toast toast-${toast.type}`}>{toast.message}</div>
      )}
    </div>
  );
}

function CreateUserModal({
  onClose,
  onCreated,
  onError,
}: {
  onClose: () => void;
  onCreated: () => void;
  onError: (msg: string) => void;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("viewer");
  const [namespaces, setNamespaces] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const nsList = namespaces
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await createUser({ email, password, role, allowed_namespaces: nsList });
      onCreated();
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Create User</h2>
        <form onSubmit={handleSubmit}>
          <div className="input-group mb-4">
            <label>Email</label>
            <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div className="input-group mb-4">
            <label>Password</label>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <div className="input-group mb-4">
            <label>Role</label>
            <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="input-group mb-4">
            <label>Allowed Namespaces (comma-separated, * for all)</label>
            <input
              className="input"
              placeholder="default, kube-system"
              value={namespaces}
              onChange={(e) => setNamespaces(e.target.value)}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Creating…" : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditUserModal({
  user,
  onClose,
  onSaved,
  onError,
}: {
  user: User;
  onClose: () => void;
  onSaved: () => void;
  onError: (msg: string) => void;
}) {
  const [role, setRole] = useState(user.role);
  const [namespaces, setNamespaces] = useState(user.allowed_namespaces.join(", "));
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const nsList = namespaces
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      await updateUser(user.id, {
        role,
        allowed_namespaces: nsList,
        ...(password ? { password } : {}),
      });
      onSaved();
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : "Failed to update user");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2 className="modal-title">Edit User: {user.email}</h2>
        <form onSubmit={handleSubmit}>
          <div className="input-group mb-4">
            <label>Role</label>
            <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="viewer">Viewer</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          <div className="input-group mb-4">
            <label>Allowed Namespaces (comma-separated, * for all)</label>
            <input
              className="input"
              value={namespaces}
              onChange={(e) => setNamespaces(e.target.value)}
            />
          </div>
          <div className="input-group mb-4">
            <label>New Password (leave blank to keep current)</label>
            <input
              className="input"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="modal-actions">
            <button type="button" className="btn" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
