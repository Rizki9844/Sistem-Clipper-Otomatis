"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { listClips, reviewClip, batchReview } from "@/lib/api/clips";
import { Clip } from "@/lib/api/types";
import StatusBadge from "@/components/StatusBadge";
import { GallerySkeleton } from "@/components/LoadingSkeleton";
import { useToast } from "@/components/Toast";

export default function ClipsPage() {
    return (
        <Suspense fallback={
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {Array.from({ length: 8 }).map((_, i) => <GallerySkeleton key={i} />)}
            </div>
        }>
            <ClipsContent />
        </Suspense>
    );
}

function ClipsContent() {
    const { addToast } = useToast();
    const searchParams = useSearchParams();
    const jobIdParam = searchParams.get("job_id");
    const reviewParam = searchParams.get("review_status");

    const [clips, setClips] = useState<Clip[]>([]);
    const [loading, setLoading] = useState(true);
    const [reviewFilter, setReviewFilter] = useState<string>(reviewParam || "all");
    const [selected, setSelected] = useState<Set<string>>(new Set());
    const [sortBy, setSortBy] = useState<"score" | "time">("score");

    useEffect(() => {
        loadClips();
    }, [reviewFilter, sortBy, jobIdParam]);

    async function loadClips() {
        setLoading(true);
        try {
            const params: Record<string, unknown> = { limit: 50, sort_by: sortBy };
            if (reviewFilter !== "all") params.review_status = reviewFilter;
            if (jobIdParam) params.job_id = jobIdParam;
            const data = await listClips(params);
            setClips(data);
        } catch {
            addToast("error", "Failed to load clips");
        } finally {
            setLoading(false);
        }
    }

    function toggleSelect(id: string) {
        setSelected((prev) => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    }

    function selectAll() {
        if (selected.size === clips.length) {
            setSelected(new Set());
        } else {
            setSelected(new Set(clips.map((c) => c.id)));
        }
    }

    async function handleReview(id: string, action: "approve" | "reject") {
        try {
            await reviewClip(id, action);
            addToast("success", `Clip ${action}d`);
            loadClips();
        } catch {
            addToast("error", `Failed to ${action} clip`);
        }
    }

    async function handleBatchReview(action: "approve" | "reject") {
        if (selected.size === 0) return;
        try {
            const res = await batchReview(Array.from(selected), action);
            addToast("success", res.message);
            setSelected(new Set());
            loadClips();
        } catch {
            addToast("error", `Failed to ${action} clips`);
        }
    }

    function getScoreColor(score: number): string {
        if (score >= 8) return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
        if (score >= 6) return "text-amber-400 bg-amber-500/10 border-amber-500/20";
        if (score >= 4) return "text-sky-400 bg-sky-500/10 border-sky-500/20";
        return "text-slate-400 bg-slate-500/10 border-slate-500/20";
    }

    const reviewFilters = ["all", "pending", "approved", "rejected"];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between animate-fadeIn">
                <div>
                    <h1 className="text-3xl font-bold">
                        <span className="bg-gradient-to-r from-amber-400 to-rose-400 bg-clip-text text-transparent">
                            Clips
                        </span>
                    </h1>
                    <p className="text-slate-500 mt-1">AI-generated video clips for review</p>
                </div>

                {/* Batch Actions */}
                {selected.size > 0 && (
                    <div className="flex items-center gap-2 animate-slideIn">
                        <span className="text-sm text-slate-400">{selected.size} selected</span>
                        <button
                            onClick={() => handleBatchReview("approve")}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
                        >
                            ✅ Approve All
                        </button>
                        <button
                            onClick={() => handleBatchReview("reject")}
                            className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors"
                        >
                            ❌ Reject All
                        </button>
                    </div>
                )}
            </div>

            {/* Filters */}
            <div className="flex items-center justify-between animate-fadeIn" style={{ animationDelay: "100ms" }}>
                <div className="flex gap-2">
                    {reviewFilters.map((f) => (
                        <button
                            key={f}
                            onClick={() => setReviewFilter(f)}
                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${reviewFilter === f
                                ? "bg-violet-500/15 text-violet-300 border border-violet-500/20"
                                : "bg-white/5 text-slate-500 border border-white/5 hover:text-slate-300"
                                }`}
                        >
                            {f.charAt(0).toUpperCase() + f.slice(1)}
                        </button>
                    ))}
                </div>

                <div className="flex items-center gap-3">
                    <button onClick={selectAll} className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                        {selected.size === clips.length ? "Deselect All" : "Select All"}
                    </button>
                    <select
                        value={sortBy}
                        onChange={(e) => setSortBy(e.target.value as "score" | "time")}
                        className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-slate-400 focus:border-violet-500 focus:ring-0"
                    >
                        <option value="score">Sort by Score</option>
                        <option value="time">Sort by Time</option>
                    </select>
                </div>
            </div>

            {/* Clips Grid */}
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {Array.from({ length: 8 }).map((_, i) => (
                        <GallerySkeleton key={i} />
                    ))}
                </div>
            ) : clips.length === 0 ? (
                <div className="glass-card p-12 text-center animate-fadeIn">
                    <p className="text-4xl mb-4">✂️</p>
                    <p className="text-slate-400">No clips found</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                    {clips.map((clip, i) => (
                        <div
                            key={clip.id}
                            className={`glass-card overflow-hidden animate-fadeIn group relative ${selected.has(clip.id) ? "ring-2 ring-violet-500" : ""
                                }`}
                            style={{ animationDelay: `${i * 30}ms` }}
                        >
                            {/* Select Checkbox */}
                            <button
                                onClick={() => toggleSelect(clip.id)}
                                className={`absolute top-3 left-3 z-10 w-6 h-6 rounded-md border flex items-center justify-center transition-all ${selected.has(clip.id)
                                    ? "bg-violet-500 border-violet-500 text-white"
                                    : "bg-black/40 border-white/20 text-transparent group-hover:text-white/50"
                                    }`}
                            >
                                ✓
                            </button>

                            {/* Score Badge */}
                            <div className={`absolute top-3 right-3 z-10 px-2 py-1 rounded-lg border text-xs font-bold ${getScoreColor(clip.highlight_score)}`}>
                                {clip.highlight_score.toFixed(1)}
                            </div>

                            {/* Thumbnail / Preview */}
                            <Link href={`/clips/${clip.id}`}>
                                <div className="h-36 bg-gradient-to-br from-slate-800 to-slate-900 flex items-center justify-center cursor-pointer">
                                    <div className="text-center">
                                        <span className="text-3xl opacity-40">🎬</span>
                                        <p className="text-xs text-slate-600 mt-1">
                                            {clip.duration.toFixed(1)}s
                                        </p>
                                    </div>
                                </div>
                            </Link>

                            {/* Info */}
                            <div className="p-4 space-y-3">
                                <div>
                                    <p className="text-sm font-medium text-slate-200 line-clamp-2">
                                        {clip.hook_text || "Untitled clip"}
                                    </p>
                                    <div className="flex items-center gap-2 mt-1.5">
                                        <span className="text-[11px] text-slate-500 px-2 py-0.5 rounded-md bg-white/5">
                                            {clip.category || "general"}
                                        </span>
                                        <StatusBadge status={clip.review_status} />
                                    </div>
                                </div>

                                {/* Virality Score Bar — OpusClip style */}
                                <div className="space-y-1">
                                    <div className="flex items-center justify-between">
                                        <span className="text-[10px] text-slate-500 uppercase tracking-wider font-semibold">Virality Score</span>
                                        <span className={`text-xs font-bold ${
                                            clip.highlight_score >= 8 ? "text-emerald-400" :
                                            clip.highlight_score >= 6 ? "text-amber-400" :
                                            clip.highlight_score >= 4 ? "text-sky-400" : "text-slate-500"
                                        }`}>
                                            {clip.highlight_score >= 8 ? "🔥" :
                                             clip.highlight_score >= 6 ? "⚡" :
                                             clip.highlight_score >= 4 ? "📈" : "💤"}{" "}
                                            {clip.highlight_score.toFixed(1)}/10
                                        </span>
                                    </div>
                                    <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
                                        <div
                                            className={`h-full rounded-full transition-all duration-700 ${
                                                clip.highlight_score >= 8 ? "bg-gradient-to-r from-emerald-500 to-green-400" :
                                                clip.highlight_score >= 6 ? "bg-gradient-to-r from-amber-500 to-yellow-400" :
                                                clip.highlight_score >= 4 ? "bg-gradient-to-r from-sky-500 to-blue-400" :
                                                "bg-slate-600"
                                            }`}
                                            style={{ width: `${clip.highlight_score * 10}%` }}
                                        />
                                    </div>
                                </div>

                                {/* Actions */}
                                {clip.review_status === "pending" && (
                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleReview(clip.id, "approve")}
                                            className="flex-1 py-2 rounded-lg text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
                                        >
                                            ✅ Approve
                                        </button>
                                        <button
                                            onClick={() => handleReview(clip.id, "reject")}
                                            className="flex-1 py-2 rounded-lg text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors"
                                        >
                                            ❌ Reject
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
