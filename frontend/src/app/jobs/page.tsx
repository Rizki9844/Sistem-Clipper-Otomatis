"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { listJobs, cancelJob, retryJob } from "@/lib/api/jobs";
import { Job } from "@/lib/api/types";
import StatusBadge from "@/components/StatusBadge";
import ProgressBar from "@/components/ProgressBar";
import { TableRowSkeleton } from "@/components/LoadingSkeleton";
import { useToast } from "@/components/Toast";

export default function JobsPage() {
    return (
        <Suspense fallback={
            <div className="space-y-6">
                {Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} />)}
            </div>
        }>
            <JobsContent />
        </Suspense>
    );
}

function JobsContent() {
    const { addToast } = useToast();
    const searchParams = useSearchParams();
    const videoIdParam = searchParams.get("video_id");

    const [jobs, setJobs] = useState<Job[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>("all");

    useEffect(() => {
        loadJobs();
    }, [filter, videoIdParam]);

    async function loadJobs() {
        setLoading(true);
        try {
            const params: Record<string, unknown> = { limit: 50 };
            if (filter !== "all") params.status = filter;
            if (videoIdParam) params.video_id = videoIdParam;
            const data = await listJobs(params);
            setJobs(data);
        } catch {
            addToast("error", "Failed to load jobs");
        } finally {
            setLoading(false);
        }
    }

    async function handleCancel(id: string) {
        try {
            const res = await cancelJob(id);
            addToast("info", res.message);
            loadJobs();
        } catch {
            addToast("error", "Failed to cancel job");
        }
    }

    async function handleRetry(id: string) {
        try {
            const res = await retryJob(id);
            addToast("success", res.message);
            loadJobs();
        } catch {
            addToast("error", "Failed to retry job");
        }
    }

    const filters = ["all", "queued", "processing", "completed", "failed", "cancelled"];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="animate-fadeIn">
                <h1 className="text-3xl font-bold">
                    <span className="bg-gradient-to-r from-sky-400 to-violet-400 bg-clip-text text-transparent">
                        Jobs
                    </span>
                </h1>
                <p className="text-slate-500 mt-1">
                    {videoIdParam ? "Jobs for selected video" : "All processing jobs"}
                </p>
            </div>

            {/* Filters */}
            <div className="flex gap-2 flex-wrap animate-fadeIn" style={{ animationDelay: "100ms" }}>
                {filters.map((f) => (
                    <button
                        key={f}
                        onClick={() => setFilter(f)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${filter === f
                            ? "bg-violet-500/15 text-violet-300 border border-violet-500/20"
                            : "bg-white/5 text-slate-500 border border-white/5 hover:text-slate-300"
                            }`}
                    >
                        {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                ))}
            </div>

            {/* Jobs Table */}
            <div className="glass-card overflow-hidden animate-fadeIn" style={{ animationDelay: "150ms" }}>
                {/* Table Header */}
                <div className="grid grid-cols-12 px-6 py-3 border-b border-white/5 text-xs text-slate-500 uppercase tracking-wider font-medium">
                    <span className="col-span-3">Job ID</span>
                    <span className="col-span-2">Status</span>
                    <span className="col-span-2">Step</span>
                    <span className="col-span-2">Progress</span>
                    <span className="col-span-1">Clips</span>
                    <span className="col-span-2 text-right">Actions</span>
                </div>

                {loading ? (
                    Array.from({ length: 8 }).map((_, i) => <TableRowSkeleton key={i} />)
                ) : jobs.length === 0 ? (
                    <div className="px-6 py-12 text-center">
                        <p className="text-slate-500">No jobs found</p>
                    </div>
                ) : (
                    jobs.map((job) => (
                        <Link
                            key={job.id}
                            href={`/jobs/${job.id}`}
                            className="grid grid-cols-12 items-center px-6 py-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors group"
                        >
                            <div className="col-span-3">
                                <p className="text-sm font-mono text-slate-300 group-hover:text-violet-300 transition-colors">
                                    {job.id.slice(-12)}
                                </p>
                                <p className="text-xs text-slate-600 mt-0.5">
                                    {new Date(job.created_at).toLocaleString([], {
                                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                                    })}
                                </p>
                            </div>

                            <div className="col-span-2">
                                <StatusBadge status={job.status} />
                            </div>

                            <div className="col-span-2">
                                <p className="text-xs text-slate-400">{job.current_step}</p>
                            </div>

                            <div className="col-span-2 flex items-center gap-2">
                                <ProgressBar
                                    value={job.overall_progress}
                                    size="sm"
                                    accent={
                                        job.status === "completed"
                                            ? "emerald"
                                            : job.status === "failed"
                                                ? "amber"
                                                : "violet"
                                    }
                                />
                                <span className="text-xs text-slate-500 font-mono w-10 text-right">
                                    {job.overall_progress.toFixed(0)}%
                                </span>
                            </div>

                            <div className="col-span-1">
                                <span className="text-sm text-slate-400">
                                    {job.total_clips_rendered}/{job.total_clips_found}
                                </span>
                            </div>

                            <div className="col-span-2 flex justify-end gap-2" onClick={(e) => e.preventDefault()}>
                                {job.status === "processing" && (
                                    <button
                                        onClick={() => handleCancel(job.id)}
                                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors"
                                    >
                                        Cancel
                                    </button>
                                )}
                                {job.status === "failed" && (
                                    <button
                                        onClick={() => handleRetry(job.id)}
                                        className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-colors"
                                    >
                                        Retry
                                    </button>
                                )}
                            </div>
                        </Link>
                    ))
                )}
            </div>
        </div>
    );
}
