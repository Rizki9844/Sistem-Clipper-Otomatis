"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import StatCard from "@/components/StatCard";
import StatusBadge from "@/components/StatusBadge";
import ProgressBar from "@/components/ProgressBar";
import { CardSkeleton, TableRowSkeleton } from "@/components/LoadingSkeleton";
import { getDashboardStats } from "@/lib/api/jobs";
import { listJobs } from "@/lib/api/jobs";
import { DashboardStats, Job } from "@/lib/api/types";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentJobs, setRecentJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statsData, jobsData] = await Promise.all([
          getDashboardStats(),
          listJobs({ limit: 5 }),
        ]);
        setStats(statsData);
        setRecentJobs(jobsData);
      } catch (err) {
        console.error("Failed to fetch dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="animate-fadeIn">
        <h1 className="text-3xl font-bold">
          <span className="bg-gradient-to-r from-violet-400 via-sky-400 to-violet-400 bg-clip-text text-transparent">
            Dashboard
          </span>
        </h1>
        <p className="text-slate-500 mt-1">Overview of your video processing pipeline</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => <CardSkeleton key={i} />)
        ) : stats ? (
          <>
            <StatCard icon="🎬" label="Total Videos" value={stats.total_videos} accent="violet" delay={0} />
            <StatCard icon="⚡" label="Processing" value={stats.jobs_processing} accent="sky" delay={50} />
            <StatCard icon="✅" label="Completed" value={stats.jobs_completed} accent="emerald" delay={100} />
            <StatCard icon="❌" label="Failed" value={stats.jobs_failed} accent="rose" delay={150} />
            <StatCard icon="✂️" label="Total Clips" value={stats.total_clips} accent="amber" delay={200} />
            <StatCard
              icon="⏱️"
              label="Avg Time"
              value={stats.avg_processing_time_minutes}
              suffix="min"
              accent="sky"
              delay={250}
            />
          </>
        ) : null}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Quick Submit */}
        <Link
          href="/submit"
          className="glass-card p-6 flex items-center gap-4 group cursor-pointer animate-fadeIn"
          style={{ animationDelay: "300ms" }}
        >
          <div className="w-14 h-14 rounded-2xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
            🔗
          </div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-violet-300 transition-colors">
              Submit New Video
            </h3>
            <p className="text-sm text-slate-500">Paste a YouTube, TikTok, or any video URL</p>
          </div>
          <span className="ml-auto text-slate-600 group-hover:text-violet-400 transition-colors text-xl">→</span>
        </Link>

        {/* Review Clips */}
        <Link
          href="/clips?review_status=pending"
          className="glass-card p-6 flex items-center gap-4 group cursor-pointer animate-fadeIn"
          style={{ animationDelay: "350ms" }}
        >
          <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
            ✂️
          </div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-amber-300 transition-colors">
              Review Clips
            </h3>
            <p className="text-sm text-slate-500">
              {stats ? `${stats.total_clips - stats.clips_approved - stats.clips_rejected} pending` : "..."}
            </p>
          </div>
          <span className="ml-auto text-slate-600 group-hover:text-amber-400 transition-colors text-xl">→</span>
        </Link>

        {/* View Jobs */}
        <Link
          href="/jobs"
          className="glass-card p-6 flex items-center gap-4 group cursor-pointer animate-fadeIn"
          style={{ animationDelay: "400ms" }}
        >
          <div className="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
            ⚙️
          </div>
          <div>
            <h3 className="font-semibold text-white group-hover:text-sky-300 transition-colors">
              All Jobs
            </h3>
            <p className="text-sm text-slate-500">
              {stats ? `${stats.total_jobs} total` : "..."}
            </p>
          </div>
          <span className="ml-auto text-slate-600 group-hover:text-sky-400 transition-colors text-xl">→</span>
        </Link>
      </div>

      {/* Recent Jobs Table */}
      <div className="glass-card overflow-hidden animate-fadeIn" style={{ animationDelay: "450ms" }}>
        <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
          <h2 className="font-semibold text-white">Recent Jobs</h2>
          <Link
            href="/jobs"
            className="text-xs text-violet-400 hover:text-violet-300 transition-colors"
          >
            View All →
          </Link>
        </div>

        {loading ? (
          <div>
            {Array.from({ length: 5 }).map((_, i) => (
              <TableRowSkeleton key={i} />
            ))}
          </div>
        ) : recentJobs.length === 0 ? (
          <div className="px-6 py-12 text-center">
            <p className="text-slate-500">No jobs yet. Submit a video URL to get started!</p>
          </div>
        ) : (
          <div>
            {recentJobs.map((job) => (
              <Link
                key={job.id}
                href={`/jobs/${job.id}`}
                className="flex items-center gap-4 px-6 py-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors group"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-200 truncate group-hover:text-violet-300 transition-colors">
                    Job {job.id.slice(-8)}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {new Date(job.created_at).toLocaleDateString()}{" "}
                    {new Date(job.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </p>
                </div>
                <StatusBadge status={job.status} />
                <div className="w-32">
                  <ProgressBar value={job.overall_progress} size="sm" accent={
                    job.status === "completed" ? "emerald" :
                      job.status === "failed" ? "amber" : "violet"
                  } />
                </div>
                <span className="text-xs text-slate-500 font-mono w-12 text-right">
                  {job.overall_progress.toFixed(0)}%
                </span>
                {job.processing_time && (
                  <span className="text-xs text-slate-600 w-16 text-right">{job.processing_time}</span>
                )}
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
