"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getClip, reviewClip, getDownloadUrl } from "@/lib/api/clips";
import { Clip } from "@/lib/api/types";
import StatusBadge from "@/components/StatusBadge";
import { useToast } from "@/components/Toast";
import { Skeleton } from "@/components/LoadingSkeleton";

export default function ClipDetailPage() {
    const params = useParams();
    const clipId = params.id as string;
    const router = useRouter();
    const { addToast } = useToast();

    const [clip, setClip] = useState<Clip | null>(null);
    const [loading, setLoading] = useState(true);
    const [reviewNotes, setReviewNotes] = useState("");
    const [downloading, setDownloading] = useState(false);

    useEffect(() => {
        loadClip();
    }, [clipId]);

    async function loadClip() {
        setLoading(true);
        try {
            const data = await getClip(clipId);
            setClip(data);
        } catch {
            addToast("error", "Failed to load clip");
        } finally {
            setLoading(false);
        }
    }

    async function handleReview(action: "approve" | "reject") {
        try {
            await reviewClip(clipId, action, reviewNotes || undefined);
            addToast("success", `Clip ${action}d`);
            loadClip();
        } catch {
            addToast("error", `Failed to ${action} clip`);
        }
    }

    async function handleDownload() {
        setDownloading(true);
        try {
            const { download_url } = await getDownloadUrl(clipId);
            window.open(download_url, "_blank");
        } catch {
            addToast("error", "Failed to get download URL");
        } finally {
            setDownloading(false);
        }
    }

    function getScoreColor(score: number): string {
        if (score >= 8) return "text-emerald-400";
        if (score >= 6) return "text-amber-400";
        if (score >= 4) return "text-sky-400";
        return "text-slate-400";
    }

    if (loading) {
        return (
            <div className="space-y-6 max-w-4xl mx-auto">
                <Skeleton className="h-8 w-48" />
                <Skeleton className="h-[400px] w-full" />
                <Skeleton className="h-32 w-full" />
            </div>
        );
    }

    if (!clip) {
        return (
            <div className="glass-card p-12 text-center">
                <p className="text-slate-400">Clip not found</p>
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between animate-fadeIn">
                <div>
                    <button
                        onClick={() => router.back()}
                        className="text-sm text-slate-500 hover:text-slate-300 transition-colors mb-2 inline-flex items-center gap-1"
                    >
                        ← Back
                    </button>
                    <h1 className="text-2xl font-bold text-white">
                        {clip.hook_text || `Clip ${clip.id.slice(-8)}`}
                    </h1>
                    <div className="flex items-center gap-3 mt-2">
                        <StatusBadge status={clip.review_status} size="md" />
                        <StatusBadge status={clip.status} />
                        <span className={`text-lg font-bold ${getScoreColor(clip.highlight_score)}`}>
                            ⭐ {clip.highlight_score.toFixed(1)}
                        </span>
                    </div>
                </div>

                <button
                    onClick={handleDownload}
                    disabled={downloading || !clip.blob_url}
                    className="px-4 py-2.5 rounded-xl text-sm font-medium bg-violet-600 text-white hover:bg-violet-500 disabled:bg-slate-800 disabled:text-slate-600 transition-colors"
                >
                    {downloading ? "Getting URL..." : "⬇️ Download"}
                </button>
            </div>

            {/* Video Player */}
            <div className="glass-card overflow-hidden animate-fadeIn" style={{ animationDelay: "100ms" }}>
                {clip.blob_url ? (
                    <video
                        controls
                        className="w-full max-h-[500px] bg-black"
                        preload="metadata"
                    >
                        <source src={clip.blob_url} type="video/mp4" />
                        Your browser does not support the video tag.
                    </video>
                ) : (
                    <div className="h-[400px] bg-slate-900 flex items-center justify-center">
                        <div className="text-center">
                            <span className="text-5xl opacity-30">🎬</span>
                            <p className="text-slate-500 mt-3">Video not yet rendered</p>
                        </div>
                    </div>
                )}
            </div>

            {/* Clip Info Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Metadata */}
                <div className="glass-card p-6 animate-fadeIn" style={{ animationDelay: "150ms" }}>
                    <h2 className="font-semibold text-white mb-4">Clip Details</h2>
                    <div className="space-y-3">
                        {[
                            { label: "Duration", value: `${clip.duration.toFixed(1)}s` },
                            { label: "Time Range", value: `${clip.start_time.toFixed(1)}s — ${clip.end_time.toFixed(1)}s` },
                            { label: "Category", value: clip.category || "—" },
                            { label: "Captions", value: clip.has_captions ? "Yes" : "No" },
                            { label: "Face Tracking", value: clip.has_face_tracking ? "Yes" : "No" },
                            { label: "Created", value: new Date(clip.created_at).toLocaleString() },
                        ].map((item) => (
                            <div key={item.label} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
                                <span className="text-xs text-slate-500 uppercase tracking-wider">{item.label}</span>
                                <span className="text-sm text-slate-300">{item.value}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* AI Analysis */}
                <div className="glass-card p-6 animate-fadeIn" style={{ animationDelay: "200ms" }}>
                    <h2 className="font-semibold text-white mb-4">AI Analysis</h2>
                    <div className="space-y-4">
                        <div>
                            <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Hook Text</p>
                            <p className="text-sm text-slate-300">{clip.hook_text || "—"}</p>
                        </div>

                        {clip.suggested_title && (
                            <div>
                                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Suggested Title</p>
                                <p className="text-sm text-violet-300">{clip.suggested_title}</p>
                            </div>
                        )}

                        {clip.ai_reasoning && (
                            <div>
                                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">AI Reasoning</p>
                                <p className="text-sm text-slate-400 leading-relaxed">{clip.ai_reasoning}</p>
                            </div>
                        )}

                        {clip.hashtags && clip.hashtags.length > 0 && (
                            <div>
                                <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Hashtags</p>
                                <div className="flex flex-wrap gap-1.5">
                                    {clip.hashtags.map((tag) => (
                                        <span
                                            key={tag}
                                            className="text-xs px-2 py-1 rounded-md bg-violet-500/10 text-violet-400 border border-violet-500/20"
                                        >
                                            #{tag}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Review Section */}
            {clip.review_status === "pending" && (
                <div className="glass-card p-6 animate-fadeIn" style={{ animationDelay: "250ms" }}>
                    <h2 className="font-semibold text-white mb-4">Review This Clip</h2>

                    <textarea
                        value={reviewNotes}
                        onChange={(e) => setReviewNotes(e.target.value)}
                        placeholder="Optional notes..."
                        className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:ring-0 mb-4 resize-none h-20"
                    />

                    <div className="flex gap-3">
                        <button
                            onClick={() => handleReview("approve")}
                            className="flex-1 py-3 rounded-xl text-sm font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-all active:scale-[0.98]"
                        >
                            ✅ Approve Clip
                        </button>
                        <button
                            onClick={() => handleReview("reject")}
                            className="flex-1 py-3 rounded-xl text-sm font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-all active:scale-[0.98]"
                        >
                            ❌ Reject Clip
                        </button>
                    </div>
                </div>
            )}

            {/* Previous Review */}
            {clip.review_status !== "pending" && (
                <div className="glass-card p-6 animate-fadeIn" style={{ animationDelay: "250ms" }}>
                    <h2 className="font-semibold text-white mb-2">Review Result</h2>
                    <div className="flex items-center gap-3">
                        <StatusBadge status={clip.review_status} size="md" />
                        {clip.review_notes && (
                            <span className="text-sm text-slate-400">— {clip.review_notes}</span>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
