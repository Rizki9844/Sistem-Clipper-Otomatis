"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getJob, cancelJob, retryJob } from "@/lib/api/jobs";
import { listClips } from "@/lib/api/clips";
import { Job, Clip, WSProgressEvent } from "@/lib/api/types";
import { useWebSocket } from "@/hooks/useWebSocket";
import StatusBadge from "@/components/StatusBadge";
import ProgressBar from "@/components/ProgressBar";
import PipelineStepper from "@/components/PipelineStepper";
import { useToast } from "@/components/Toast";
import { Skeleton } from "@/components/LoadingSkeleton";

export default function JobDetailPage() {
    const params = useParams();
    const jobId = params.id as string;
    const { addToast } = useToast();

    const [job, setJob] = useState<Job | null>(null);
    const [clips, setClips] = useState<Clip[]>([]);
    const [loading, setLoading] = useState(true);

    const isActive = job?.status === "processing" || job?.status === "queued";

    // Real-time updates via WebSocket
    const onProgress = useCallback((event: WSProgressEvent) => {
        if (event.type === "progress" || event.type === "initial") {
            setJob((prev) => {
                if (!prev) return prev;
                return {
                    ...prev,
                    status: (event.status as Job["status"]) || prev.status,
                    current_step: event.step || prev.current_step,
                    overall_progress: event.progress ?? prev.overall_progress,
                    steps: event.steps || prev.steps,
                };
            });
        }
    }, []);

    useWebSocket({ jobId, onProgress, enabled: isActive });

    useEffect(() => {
        loadData();
    }, [jobId]);

    async function loadData() {
        setLoading(true);
        try {
            const [jobData, clipsData] = await Promise.all([
                getJob(jobId),
                listClips({ job_id: jobId, limit: 50 }),
            ]);
            setJob(jobData);
            setClips(clipsData);
        } catch {
            addToast("error", "Failed to load job details");
        } finally {
            setLoading(false);
        }
    }

    async function handleCancel() {
        try {
            await cancelJob(jobId);
            addToast("info", "Job cancelled");
            loadData();
        } catch {
            addToast("error", "Failed to cancel job");
        }
    }

    async function handleRetry() {
        try {
            await retryJob(jobId);
            addToast("success", "Job retried");
            loadData();
        } catch {
            addToast("error", "Failed to retry job");
        }
    }

    if (loading) {
        return (
            <div className="space-y-6">
                <Skeleton className="h-8 w-64" />
                <Skeleton className="h-20 w-full" />
                <Skeleton className="h-48 w-full" />
            </div>
        );
    }

    if (!job) {
        return (
            <div className="glass-card p-12 text-center">
                <p className="text-slate-400">Job not found</p>
            </div>
        );
    }

    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between animate-fadeIn">
                <div>
                    <div className="flex items-center gap-3">
                        <h1 className="text-2xl font-bold text-white">Job {job.id.slice(-8)}</h1>
                        <StatusBadge status={job.status} size="md" />
                        {isActive && (
                            <span className="flex items-center gap-1.5 text-xs text-violet-400">
                                <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
                                Live
                            </span>
                        )}
                    </div>
                    <p className="text-sm text-slate-500 mt-1">
                        Created {new Date(job.created_at).toLocaleString()} ·{" "}
                        {job.processing_time || "In progress"}
                    </p>
                </div>

                <div className="flex gap-2">
                    {job.status === "processing" && (
                        <button
                            onClick={handleCancel}
                            className="px-4 py-2 rounded-xl text-sm font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors"
                        >
                            Cancel
                        </button>
                    )}
                    {job.status === "failed" && (
                        <button
                            onClick={handleRetry}
                            className="px-4 py-2 rounded-xl text-sm font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 hover:bg-amber-500/20 transition-colors"
                        >
                            🔄 Retry
                        </button>
                    )}
                </div>
            </div>

            {/* Overall Progress */}
            <div className="glass-card p-6 animate-fadeIn" style={{ animationDelay: "100ms" }}>
                <div className="flex items-center justify-between mb-4">
                    <h2 className="font-semibold text-white">Overall Progress</h2>
                    <span className="text-2xl font-bold text-violet-400 font-mono">
                        {job.overall_progress.toFixed(1)}%
                    </span>
                </div>
                <ProgressBar
                    value={job.overall_progress}
                    size="lg"
                    animated={isActive}
                    accent={
                        job.status === "completed" ? "emerald" :
                            job.status === "failed" ? "amber" : "violet"
                    }
                />
            </div>

            {/* Pipeline Steps */}
            <div className="glass-card p-6 animate-fadeIn" style={{ animationDelay: "150ms" }}>
                <h2 className="font-semibold text-white mb-6">Pipeline Steps</h2>
                <PipelineStepper steps={job.steps} />
            </div>

            {/* Step Details */}
            <div className="glass-card overflow-hidden animate-fadeIn" style={{ animationDelay: "200ms" }}>
                <div className="px-6 py-4 border-b border-white/5">
                    <h2 className="font-semibold text-white">Step Details</h2>
                </div>
                {job.steps.map((step) => (
                    <div key={step.name} className="px-6 py-4 border-b border-white/5 last:border-0">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-3">
                                <span className="text-lg">{
                                    { download: "📥", transcribe: "🎙️", analyze: "🧠", edit: "✂️", render: "🎨" }[step.name] || "●"
                                }</span>
                                <span className="text-sm font-medium text-slate-300">{step.display}</span>
                            </div>
                            <StatusBadge status={step.status} />
                        </div>
                        <div className="ml-10 space-y-2">
                            <ProgressBar value={step.progress} size="sm" accent={
                                step.status === "completed" ? "emerald" :
                                    step.status === "failed" ? "amber" :
                                        step.status === "running" ? "violet" : "sky"
                            } />
                            <div className="flex gap-4 text-xs text-slate-600">
                                {step.started_at && <span>Started: {new Date(step.started_at).toLocaleTimeString()}</span>}
                                {step.completed_at && <span>Completed: {new Date(step.completed_at).toLocaleTimeString()}</span>}
                            </div>
                            {step.error && (
                                <p className="text-xs text-rose-400 bg-rose-500/5 px-3 py-2 rounded-lg">{step.error}</p>
                            )}
                        </div>
                    </div>
                ))}
            </div>

            {/* Job Config */}
            <div className="glass-card p-6 animate-fadeIn" style={{ animationDelay: "250ms" }}>
                <h2 className="font-semibold text-white mb-4">Configuration</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    {[
                        { label: "Quality", value: job.config.quality_preset },
                        { label: "Aspect Ratio", value: job.config.target_aspect_ratio },
                        { label: "Max Clips", value: job.config.max_clips },
                        { label: "Min Score", value: job.config.min_highlight_score },
                        { label: "Captions", value: job.config.add_captions ? "Yes" : "No" },
                        { label: "Face Tracking", value: job.config.face_tracking ? "Yes" : "No" },
                        { label: "Portrait Crop", value: job.config.crop_to_portrait ? "Yes" : "No" },
                        { label: "Audio Normalize", value: job.config.normalize_audio ? "Yes" : "No" },
                    ].map((item) => (
                        <div key={item.label} className="bg-white/[0.02] rounded-xl p-3">
                            <p className="text-[11px] text-slate-500 uppercase tracking-wider">{item.label}</p>
                            <p className="text-sm text-slate-300 font-medium mt-0.5">{String(item.value)}</p>
                        </div>
                    ))}
                </div>
            </div>

            {/* Generated Clips */}
            {clips.length > 0 && (
                <div className="glass-card overflow-hidden animate-fadeIn" style={{ animationDelay: "300ms" }}>
                    <div className="px-6 py-4 border-b border-white/5 flex items-center justify-between">
                        <h2 className="font-semibold text-white">
                            Generated Clips ({clips.length})
                        </h2>
                        <Link href={`/clips?job_id=${jobId}`} className="text-xs text-violet-400 hover:text-violet-300">
                            View All →
                        </Link>
                    </div>
                    {clips.map((clip) => (
                        <Link
                            key={clip.id}
                            href={`/clips/${clip.id}`}
                            className="flex items-center gap-4 px-6 py-3 border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition-colors"
                        >
                            <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center text-sm font-bold text-amber-400">
                                {clip.highlight_score.toFixed(1)}
                            </div>
                            <div className="flex-1 min-w-0">
                                <p className="text-sm text-slate-300 truncate">{clip.hook_text || "Clip"}</p>
                                <p className="text-xs text-slate-500">{clip.duration.toFixed(1)}s · {clip.category}</p>
                            </div>
                            <StatusBadge status={clip.review_status} />
                        </Link>
                    ))}
                </div>
            )}

            {/* Error Message */}
            {job.error_message && (
                <div className="glass-card p-6 border-rose-500/20 animate-fadeIn">
                    <h2 className="font-semibold text-rose-400 mb-2">❌ Error</h2>
                    <p className="text-sm text-slate-400">{job.error_message}</p>
                </div>
            )}
        </div>
    );
}
