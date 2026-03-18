"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { listAllJobs } from "@/lib/api/admin";
import { AdminJobEntry } from "@/lib/api/types";
import StatusBadge from "@/components/StatusBadge";
import ProgressBar from "@/components/ProgressBar";

export default function AdminJobsPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [jobs, setJobs] = useState<AdminJobEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  useEffect(() => {
    if (!isLoading && !user?.is_admin) router.replace("/");
  }, [user, isLoading, router]);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listAllJobs({
        status: statusFilter || undefined,
        limit: PAGE_SIZE,
        skip: page * PAGE_SIZE,
      });
      setJobs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, page]);

  useEffect(() => {
    if (user?.is_admin) fetchJobs();
  }, [user, fetchJobs]);

  if (isLoading || !user?.is_admin) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">All Jobs Monitor</h1>
        <p className="text-slate-500 text-sm mt-1">Real-time view of all users' processing jobs</p>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-wrap gap-3 items-center">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
          className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-slate-200 focus:outline-none"
        >
          <option value="">All Statuses</option>
          <option value="queued">Queued</option>
          <option value="processing">Processing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
        <button
          onClick={fetchJobs}
          className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-sm text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
        >
          🔄 Refresh
        </button>
        <span className="text-xs text-slate-500 ml-auto">{jobs.length} jobs</span>
      </div>

      {/* Jobs Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/5 text-left">
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Job ID</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">User</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Status</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Progress</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Clips</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Time</th>
                <th className="px-5 py-3 text-xs text-slate-500 font-semibold uppercase tracking-wider">Created</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-white/5">
                    {Array.from({ length: 7 }).map((_, j) => (
                      <td key={j} className="px-5 py-4">
                        <div className="h-4 rounded bg-white/5 animate-pulse w-20" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-500">No jobs found</td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="border-b border-white/5 hover:bg-white/2 transition-colors">
                    <td className="px-5 py-4 font-mono text-xs text-slate-400">
                      {job.id.slice(-8)}
                    </td>
                    <td className="px-5 py-4">
                      <p className="text-xs text-slate-300">{job.user_email}</p>
                    </td>
                    <td className="px-5 py-4">
                      <StatusBadge status={job.status} />
                    </td>
                    <td className="px-5 py-4 w-36">
                      <ProgressBar
                        value={job.overall_progress}
                        size="sm"
                        accent={
                          job.status === "completed" ? "emerald" :
                          job.status === "failed" ? "rose" : "violet"
                        }
                      />
                      <span className="text-[10px] text-slate-500">{job.overall_progress.toFixed(0)}%</span>
                    </td>
                    <td className="px-5 py-4 text-slate-400 text-xs">
                      {job.total_clips_rendered}/{job.total_clips_found}
                    </td>
                    <td className="px-5 py-4 text-slate-500 text-xs">
                      {job.processing_time || "—"}
                    </td>
                    <td className="px-5 py-4 text-slate-500 text-xs">
                      {new Date(job.created_at).toLocaleDateString()}{" "}
                      {new Date(job.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-5 py-3 border-t border-white/5 flex items-center justify-between">
          <button
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
            className="text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            ← Prev
          </button>
          <span className="text-xs text-slate-500">Page {page + 1}</span>
          <button
            disabled={jobs.length < PAGE_SIZE}
            onClick={() => setPage((p) => p + 1)}
            className="text-sm text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
}
