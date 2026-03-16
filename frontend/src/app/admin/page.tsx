"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { getAdminStats } from "@/lib/api/admin";
import { AdminStats } from "@/lib/api/types";
import StatCard from "@/components/StatCard";
import { CardSkeleton } from "@/components/LoadingSkeleton";

export default function AdminDashboard() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoading && !user?.is_admin) router.replace("/");
  }, [user, isLoading, router]);

  useEffect(() => {
    if (user?.is_admin) {
      getAdminStats()
        .then(setStats)
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [user]);

  if (isLoading || !user?.is_admin) return null;

  return (
    <div className="space-y-8">
      <div className="animate-fadeIn">
        <div className="flex items-center gap-3">
          <span className="text-3xl">🛡️</span>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-amber-400 to-orange-400 bg-clip-text text-transparent">
              Admin Dashboard
            </h1>
            <p className="text-slate-500 mt-1">System-wide overview — all users</p>
          </div>
        </div>
      </div>

      {/* Quick Links */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link href="/admin/users" className="glass-card p-5 flex items-center gap-4 group hover:border-amber-500/30 transition-all">
          <div className="w-12 h-12 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-xl group-hover:scale-110 transition-transform">👥</div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-amber-300 transition-colors">Manage Users</h3>
            <p className="text-xs text-slate-500">Activate, deactivate, change plans</p>
          </div>
          <span className="ml-auto text-slate-600 group-hover:text-amber-400 text-xl">→</span>
        </Link>
        <Link href="/admin/jobs" className="glass-card p-5 flex items-center gap-4 group hover:border-sky-500/30 transition-all">
          <div className="w-12 h-12 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-xl group-hover:scale-110 transition-transform">📋</div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-sky-300 transition-colors">Monitor Jobs</h3>
            <p className="text-xs text-slate-500">All users' processing jobs</p>
          </div>
          <span className="ml-auto text-slate-600 group-hover:text-sky-400 text-xl">→</span>
        </Link>
      </div>

      {/* Stats */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => <CardSkeleton key={i} />)}
        </div>
      ) : stats ? (
        <>
          <div>
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Users</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard icon="👥" label="Total Users" value={stats.users.total} accent="violet" />
              <StatCard icon="✅" label="Active" value={stats.users.active} accent="emerald" />
              <StatCard icon="🆓" label="Free Plan" value={stats.users.free_plan} accent="sky" />
              <StatCard icon="⭐" label="Pro Plan" value={stats.users.pro_plan} accent="amber" />
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Jobs</h2>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard icon="📋" label="Total" value={stats.jobs.total} accent="violet" />
              <StatCard icon="⚡" label="Processing" value={stats.jobs.processing} accent="sky" />
              <StatCard icon="✅" label="Completed" value={stats.jobs.completed} accent="emerald" />
              <StatCard icon="❌" label="Failed" value={stats.jobs.failed} accent="rose" />
            </div>
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">Content</h2>
            <div className="grid grid-cols-2 sm:grid-cols-2 gap-4">
              <StatCard icon="🎬" label="Total Videos" value={stats.videos.total} accent="violet" />
              <StatCard icon="✂️" label="Total Clips" value={stats.clips.total} accent="amber" />
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
