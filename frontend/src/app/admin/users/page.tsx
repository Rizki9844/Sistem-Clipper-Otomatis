"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { listAllUsers, updateUser, deleteUser } from "@/lib/api/admin";
import { AdminUserDetail } from "@/lib/api/types";
import StatusBadge from "@/components/StatusBadge";

export default function AdminUsersPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [users, setUsers] = useState<AdminUserDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState<string>("");
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoading && !user?.is_admin) router.replace("/");
  }, [user, isLoading, router]);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAllUsers({
        search: search || undefined,
        plan_tier: planFilter || undefined,
        is_active: activeFilter === "" ? undefined : activeFilter === "true",
        limit: 50,
      });
      setUsers(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [search, planFilter, activeFilter]);

  useEffect(() => {
    if (user?.is_admin) fetchUsers();
  }, [user, fetchUsers]);

  const handleToggleActive = async (u: AdminUserDetail) => {
    setActionLoading(u.id);
    try {
      await updateUser(u.id, { is_active: !u.is_active });
      await fetchUsers();
    } finally {
      setActionLoading(null);
    }
  };

  const handleChangePlan = async (u: AdminUserDetail, plan: "free" | "pro") => {
    setActionLoading(u.id);
    try {
      await updateUser(u.id, { plan_tier: plan });
      await fetchUsers();
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (u: AdminUserDetail) => {
    if (!confirm(`Hapus user ${u.email} dan SEMUA datanya? Tidak bisa dibatalkan!`)) return;
    setActionLoading(u.id);
    try {
      await deleteUser(u.id);
      await fetchUsers();
    } finally {
      setActionLoading(null);
    }
  };

  if (isLoading || !user?.is_admin) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">User Management</h1>
          <p className="text-slate-500 text-sm mt-1">{users.length} users found</p>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Search by email or name..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 min-w-48 px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-violet-500/50"
        />
        <select
          value={planFilter}
          onChange={(e) => setPlanFilter(e.target.value)}
          className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-slate-200 focus:outline-none"
        >
          <option value="">All Plans</option>
          <option value="free">Free</option>
          <option value="pro">Pro</option>
        </select>
        <select
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value)}
          className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-slate-200 focus:outline-none"
        >
          <option value="">All Status</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {/* Users Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5 text-left">
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">User</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Plan</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Quota</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Stats</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Status</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-white/5">
                    {Array.from({ length: 6 }).map((_, j) => (
                      <td key={j} className="px-5 py-4">
                        <div className="h-4 rounded bg-white/5 animate-pulse w-20" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-12 text-center text-slate-500">No users found</td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-4">
                      <Link href={`/admin/users/${u.id}`} className="group">
                        <p className="font-medium text-slate-200 group-hover:text-amber-300 transition-colors">
                          {u.full_name || "—"}
                          {u.is_admin && <span className="ml-2 text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">Admin</span>}
                        </p>
                        <p className="text-xs text-slate-500">{u.email}</p>
                      </Link>
                    </td>
                    <td className="px-5 py-4">
                      <select
                        value={u.plan_tier}
                        disabled={actionLoading === u.id}
                        onChange={(e) => handleChangePlan(u, e.target.value as "free" | "pro")}
                        className={`px-2 py-1 rounded-lg text-xs border focus:outline-none cursor-pointer
                          ${u.plan_tier === "pro"
                            ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                            : "bg-white/5 border-white/10 text-slate-400"
                          }`}
                      >
                        <option value="free">🆓 Free</option>
                        <option value="pro">⭐ Pro</option>
                      </select>
                    </td>
                    <td className="px-5 py-4 text-slate-400 text-xs">
                      {u.monthly_quota === 0
                        ? <span className="text-violet-400">Unlimited</span>
                        : `${u.used_quota}/${u.monthly_quota}`
                      }
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex gap-3 text-xs text-slate-500">
                        <span>🎬 {u.total_videos}</span>
                        <span>⚙️ {u.total_jobs}</span>
                        <span>✂️ {u.total_clips}</span>
                      </div>
                    </td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full ${
                        u.is_active
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                      }`}>
                        {u.is_active ? "● Active" : "● Inactive"}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleToggleActive(u)}
                          disabled={actionLoading === u.id}
                          className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                            u.is_active
                              ? "bg-rose-500/10 text-rose-400 hover:bg-rose-500/20"
                              : "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                          }`}
                        >
                          {u.is_active ? "Deactivate" : "Activate"}
                        </button>
                        <button
                          onClick={() => handleDelete(u)}
                          disabled={actionLoading === u.id}
                          className="text-xs px-3 py-1.5 rounded-lg bg-white/5 text-slate-500 hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
