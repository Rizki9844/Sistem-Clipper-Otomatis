"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { listVideos, deleteVideo } from "@/lib/api/videos";
import { Video } from "@/lib/api/types";
import StatusBadge from "@/components/StatusBadge";
import { GallerySkeleton } from "@/components/LoadingSkeleton";
import { useToast } from "@/components/Toast";

const platformIcons: Record<string, string> = {
    youtube: "📺",
    tiktok: "🎵",
    instagram: "📸",
    twitter: "🐦",
    facebook: "📘",
    twitch: "🟣",
};

function formatDuration(seconds: number | null): string {
    if (!seconds) return "--:--";
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatFileSize(bytes: number): string {
    if (bytes === 0) return "—";
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export default function VideosPage() {
    const { addToast } = useToast();
    const [videos, setVideos] = useState<Video[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<string>("all");

    useEffect(() => {
        loadVideos();
    }, [filter]);

    async function loadVideos() {
        setLoading(true);
        try {
            const data = await listVideos(
                filter !== "all" ? { status: filter, limit: 50 } : { limit: 50 }
            );
            setVideos(data);
        } catch {
            addToast("error", "Failed to load videos");
        } finally {
            setLoading(false);
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Delete this video and all associated data?")) return;
        try {
            await deleteVideo(id);
            setVideos((prev) => prev.filter((v) => v.id !== id));
            addToast("success", "Video deleted");
        } catch {
            addToast("error", "Failed to delete video");
        }
    }

    const filters = ["all", "pending", "downloading", "transcribing", "processing", "completed"];

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between animate-fadeIn">
                <div>
                    <h1 className="text-3xl font-bold">
                        <span className="bg-gradient-to-r from-violet-400 to-sky-400 bg-clip-text text-transparent">
                            Videos
                        </span>
                    </h1>
                    <p className="text-slate-500 mt-1">All source videos in the system</p>
                </div>
                <Link
                    href="/submit"
                    className="px-4 py-2.5 rounded-xl bg-violet-600 text-white text-sm font-medium hover:bg-violet-500 transition-colors"
                >
                    + Submit URL
                </Link>
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

            {/* Video Grid */}
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <GallerySkeleton key={i} />
                    ))}
                </div>
            ) : videos.length === 0 ? (
                <div className="glass-card p-12 text-center animate-fadeIn">
                    <p className="text-4xl mb-4">🎬</p>
                    <p className="text-slate-400">No videos found</p>
                    <Link href="/submit" className="text-sm text-violet-400 hover:text-violet-300 mt-2 inline-block">
                        Submit your first video →
                    </Link>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {videos.map((video, i) => (
                        <div
                            key={video.id}
                            className="glass-card overflow-hidden animate-fadeIn group"
                            style={{ animationDelay: `${i * 50}ms` }}
                        >
                            {/* Thumbnail */}
                            <div className="relative h-40 bg-slate-800/50 flex items-center justify-center overflow-hidden">
                                {video.thumbnail_url ? (
                                    <img
                                        src={video.thumbnail_url}
                                        alt={video.original_filename}
                                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                                    />
                                ) : (
                                    <span className="text-4xl opacity-30">🎬</span>
                                )}
                                {/* Duration badge */}
                                {video.duration_seconds && (
                                    <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-md bg-black/70 text-[11px] font-mono text-white">
                                        {formatDuration(video.duration_seconds)}
                                    </span>
                                )}
                                {/* Platform badge */}
                                {video.source_platform && (
                                    <span className="absolute top-2 left-2 text-lg">
                                        {platformIcons[video.source_platform] || "🔗"}
                                    </span>
                                )}
                            </div>

                            {/* Info */}
                            <div className="p-4 space-y-3">
                                <div>
                                    <p className="text-sm font-medium text-slate-200 truncate">{video.original_filename}</p>
                                    <p className="text-xs text-slate-500 mt-0.5">
                                        {formatFileSize(video.file_size_bytes)} ·{" "}
                                        {new Date(video.created_at).toLocaleDateString()}
                                    </p>
                                </div>

                                <div className="flex items-center justify-between">
                                    <StatusBadge status={video.status} />
                                    <div className="flex gap-2">
                                        <Link
                                            href={`/jobs?video_id=${video.id}`}
                                            className="text-xs text-slate-500 hover:text-violet-400 transition-colors"
                                        >
                                            Jobs
                                        </Link>
                                        <button
                                            onClick={() => handleDelete(video.id)}
                                            className="text-xs text-slate-600 hover:text-rose-400 transition-colors"
                                        >
                                            Delete
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
