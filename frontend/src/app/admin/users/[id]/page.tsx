"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter, useParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { getAdminUser, updateUser } from "@/lib/api/admin";
import { AdminUserDetail } from "@/lib/api/types";

export default function AdminUserDetailPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const params = useParams();
  const userId = params.id as string;

  const [target, setTarget] = useState<AdminUserDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!isLoading && !user?.is_admin) router.replace("/");
  }, [user, isLoading, router]);

  useEffect(() => {
    if (user?.is_admin && userId) {
      getAdminUser(userId)
        .then(setTarget)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [user, userId]);

  const handleSave = async (field: keyof AdminUserDetail, value: unknown) => {
    if (!target) return;
    setSaving(true);
    try {
      await updateUser(userId, { [field]: value } as Parameters<typeof updateUser>[1]);
      setTarget({ ...target, [field]: value });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error(e);
    } finally {
      setSaving(false);
    }
  };

  if (isLoading || !user?.is_admin) return null;

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Back */}
      <Link href="/admin/users" className="text-sm text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1">
        ← Back to Users
      </Link>

      {loading || !target ? (
        <div className="glass-card p-8 animate-pulse">
          <div className="h-6 bg-white/5 rounded w-48 mb-4" />
          <div className="h-4 bg-white/5 rounded w-32" />
        </div>
      ) : (
        <>
          {/* User Header */}
          <div className="glass-card p-6">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold text-white">{target.full_name || "No name"}</h1>
                <p className="text-slate-400 mt-1">{target.email}</p>
                <div className="flex gap-2 mt-3">
                  <span className={`text-xs px-2 py-1 rounded-full border ${
                    target.is_active
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                  }`}>
                    {target.is_active ? "Active" : "Inactive"}
                  </span>
                  {target.is_admin && (
                    <span className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">Admin</span>
                  )}
                  <span className={`text-xs px-2 py-1 rounded-full border ${
                    target.plan_tier === "pro"
                      ? "bg-violet-500/10 text-violet-400 border-violet-500/20"
                      : "bg-white/5 text-slate-400 border-white/10"
                  }`}>
                    {target.plan_tier === "pro" ? "⭐ Pro" : "🆓 Free"}
                  </span>
                </div>
              </div>
              <div className="text-right text-xs text-slate-500">
                <p>Joined: {new Date(target.created_at).toLocaleDateString()}</p>
                <p>Last login: {target.last_login ? new Date(target.last_login).toLocaleDateString() : "Never"}</p>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="glass-card p-4 text-center">
              <p className="text-2xl font-bold text-violet-400">{target.total_videos}</p>
              <p className="text-xs text-slate-500 mt-1">Videos</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-2xl font-bold text-sky-400">{target.total_jobs}</p>
              <p className="text-xs text-slate-500 mt-1">Jobs</p>
            </div>
            <div className="glass-card p-4 text-center">
              <p className="text-2xl font-bold text-amber-400">{target.total_clips}</p>
              <p className="text-xs text-slate-500 mt-1">Clips</p>
            </div>
          </div>

          {/* Admin Controls */}
          <div className="glass-card p-6 space-y-5">
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Account Controls</h2>

            {/* Active status */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-200 font-medium">Account Status</p>
                <p className="text-xs text-slate-500">Deactivated users cannot log in</p>
              </div>
              <button
                disabled={saving}
                onClick={() => handleSave("is_active", !target.is_active)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
                  target.is_active
                    ? "bg-rose-500/10 text-rose-400 hover:bg-rose-500/20 border border-rose-500/20"
                    : "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20 border border-emerald-500/20"
                }`}
              >
                {target.is_active ? "Deactivate Account" : "Activate Account"}
              </button>
            </div>

            {/* Admin role */}
            <div className="flex items-center justify-between border-t border-white/5 pt-5">
              <div>
                <p className="text-sm text-slate-200 font-medium">Admin Role</p>
                <p className="text-xs text-slate-500">Grants access to admin panel</p>
              </div>
              <button
                disabled={saving || target.id === user.id}
                onClick={() => handleSave("is_admin", !target.is_admin)}
                className={`px-4 py-2 rounded-xl text-sm font-medium transition-colors border ${
                  target.is_admin
                    ? "bg-amber-500/10 text-amber-400 hover:bg-amber-500/20 border-amber-500/20"
                    : "bg-white/5 text-slate-400 hover:bg-white/10 border-white/10"
                }`}
              >
                {target.is_admin ? "Remove Admin" : "Make Admin"}
              </button>
            </div>

            {/* Plan */}
            <div className="flex items-center justify-between border-t border-white/5 pt-5">
              <div>
                <p className="text-sm text-slate-200 font-medium">Plan Tier</p>
                <p className="text-xs text-slate-500">Pro = unlimited quota</p>
              </div>
              <div className="flex gap-2">
                <button
                  disabled={saving || target.plan_tier === "free"}
                  onClick={() => handleSave("plan_tier", "free")}
                  className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
                    target.plan_tier === "free"
                      ? "bg-sky-500/10 text-sky-400 border-sky-500/20"
                      : "bg-white/5 text-slate-500 border-white/10 hover:bg-white/10"
                  }`}
                >
                  🆓 Free
                </button>
                <button
                  disabled={saving || target.plan_tier === "pro"}
                  onClick={() => handleSave("plan_tier", "pro")}
                  className={`px-4 py-2 rounded-xl text-sm font-medium border transition-colors ${
                    target.plan_tier === "pro"
                      ? "bg-violet-500/10 text-violet-400 border-violet-500/20"
                      : "bg-white/5 text-slate-500 border-white/10 hover:bg-white/10"
                  }`}
                >
                  ⭐ Pro
                </button>
              </div>
            </div>

            {saved && (
              <p className="text-sm text-emerald-400 text-center animate-fadeIn">✅ Saved successfully</p>
            )}
          </div>
        </>
      )}
    </div>
  );
}
