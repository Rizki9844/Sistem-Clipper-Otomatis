"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { submitUrl } from "@/lib/api/videos";
import { useToast } from "@/components/Toast";

const platformIcons: Record<string, string> = {
    youtube: "📺",
    tiktok: "🎵",
    instagram: "📸",
    twitter: "🐦",
    facebook: "📘",
    twitch: "🟣",
    default: "🔗",
};

function detectPlatform(url: string): string {
    if (url.includes("youtube.com") || url.includes("youtu.be")) return "youtube";
    if (url.includes("tiktok.com")) return "tiktok";
    if (url.includes("instagram.com")) return "instagram";
    if (url.includes("twitter.com") || url.includes("x.com")) return "twitter";
    if (url.includes("facebook.com") || url.includes("fb.watch")) return "facebook";
    if (url.includes("twitch.tv")) return "twitch";
    return "default";
}

export default function SubmitPage() {
    const router = useRouter();
    const { addToast } = useToast();

    const [url, setUrl] = useState("");
    const [quality, setQuality] = useState("balanced");
    const [cropToPortrait, setCropToPortrait] = useState(true);
    const [faceTracking, setFaceTracking] = useState(true);
    const [addCaptions, setAddCaptions] = useState(true);
    const [maxClips, setMaxClips] = useState(10);
    const [minScore, setMinScore] = useState(5.0);
    const [aspectRatio, setAspectRatio] = useState("9:16");
    const [language, setLanguage] = useState("");
    const [notifyTelegram, setNotifyTelegram] = useState(true);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [submitting, setSubmitting] = useState(false);

    const platform = url ? detectPlatform(url) : "default";
    const icon = platformIcons[platform];

    async function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        if (!url.trim()) return;

        setSubmitting(true);
        try {
            const res = await submitUrl({
                url: url.trim(),
                quality,
                crop_to_portrait: cropToPortrait,
                face_tracking: faceTracking,
                add_captions: addCaptions,
                max_clips: maxClips,
                min_highlight_score: minScore,
                target_aspect_ratio: aspectRatio,
                language: language || undefined,
                notify_whatsapp: false,
                notify_telegram: notifyTelegram,
            });
            addToast("success", res.message);
            router.push(`/jobs/${res.job_id}`);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to submit URL";
            addToast("error", msg);
        } finally {
            setSubmitting(false);
        }
    }

    return (
        <div className="max-w-2xl mx-auto space-y-8">
            {/* Header */}
            <div className="animate-fadeIn">
                <h1 className="text-3xl font-bold">
                    <span className="bg-gradient-to-r from-violet-400 to-amber-400 bg-clip-text text-transparent">
                        Submit Video URL
                    </span>
                </h1>
                <p className="text-slate-500 mt-1">
                    Paste any video URL — YouTube, TikTok, Instagram, and 1000+ more
                </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
                {/* URL Input */}
                <div className="glass-card p-6 animate-fadeIn" style={{ animationDelay: "100ms" }}>
                    <label className="block text-sm font-medium text-slate-300 mb-3">Video URL</label>
                    <div className="relative">
                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-2xl">{icon}</span>
                        <input
                            type="url"
                            id="url-input"
                            value={url}
                            onChange={(e) => setUrl(e.target.value)}
                            placeholder="https://www.youtube.com/watch?v=..."
                            className="w-full bg-white/5 border border-white/10 rounded-xl pl-14 pr-4 py-4 text-white placeholder-slate-600 focus:border-violet-500 focus:ring-0 transition-colors text-sm"
                            required
                        />
                    </div>
                    {url && platform !== "default" && (
                        <p className="mt-2 text-xs text-violet-400">
                            Detected: {platform.charAt(0).toUpperCase() + platform.slice(1)}
                        </p>
                    )}
                </div>

                {/* Quality Preset */}
                <div className="glass-card p-6 animate-fadeIn" style={{ animationDelay: "150ms" }}>
                    <label className="block text-sm font-medium text-slate-300 mb-3">Quality Preset</label>
                    <div className="grid grid-cols-3 gap-3">
                        {[
                            { value: "fast", label: "⚡ Fast", desc: "Quick processing" },
                            { value: "balanced", label: "⚖️ Balanced", desc: "Best default" },
                            { value: "high", label: "💎 High", desc: "Maximum quality" },
                        ].map((preset) => (
                            <button
                                key={preset.value}
                                type="button"
                                onClick={() => setQuality(preset.value)}
                                className={`p-4 rounded-xl border text-left transition-all ${quality === preset.value
                                        ? "border-violet-500 bg-violet-500/10 text-violet-300"
                                        : "border-white/5 bg-white/[0.02] text-slate-400 hover:bg-white/5"
                                    }`}
                            >
                                <p className="font-medium text-sm">{preset.label}</p>
                                <p className="text-xs text-slate-500 mt-1">{preset.desc}</p>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Advanced Options */}
                <div className="glass-card overflow-hidden animate-fadeIn" style={{ animationDelay: "200ms" }}>
                    <button
                        type="button"
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="w-full px-6 py-4 flex items-center justify-between text-sm font-medium text-slate-300 hover:text-white transition-colors"
                    >
                        <span>Advanced Options</span>
                        <span className={`transition-transform ${showAdvanced ? "rotate-180" : ""}`}>▾</span>
                    </button>

                    {showAdvanced && (
                        <div className="px-6 pb-6 space-y-5 border-t border-white/5 pt-5">
                            {/* Toggles */}
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                                {[
                                    { label: "Caption 9:16", checked: cropToPortrait, onChange: setCropToPortrait },
                                    { label: "Face Tracking", checked: faceTracking, onChange: setFaceTracking },
                                    { label: "Add Captions", checked: addCaptions, onChange: setAddCaptions },
                                ].map((toggle) => (
                                    <label
                                        key={toggle.label}
                                        className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5 cursor-pointer hover:bg-white/5 transition-colors"
                                    >
                                        <input
                                            type="checkbox"
                                            checked={toggle.checked}
                                            onChange={(e) => toggle.onChange(e.target.checked)}
                                            className="w-4 h-4 rounded border-slate-600 bg-transparent text-violet-500 focus:ring-violet-500"
                                        />
                                        <span className="text-sm text-slate-300">{toggle.label}</span>
                                    </label>
                                ))}
                            </div>

                            {/* Max Clips & Min Score */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1.5">Max Clips</label>
                                    <input
                                        type="number"
                                        value={maxClips}
                                        onChange={(e) => setMaxClips(parseInt(e.target.value) || 10)}
                                        min={1}
                                        max={50}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:border-violet-500 focus:ring-0"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1.5">Min Score (0-10)</label>
                                    <input
                                        type="number"
                                        value={minScore}
                                        onChange={(e) => setMinScore(parseFloat(e.target.value) || 5)}
                                        min={0}
                                        max={10}
                                        step={0.5}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:border-violet-500 focus:ring-0"
                                    />
                                </div>
                            </div>

                            {/* Aspect Ratio & Language */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1.5">Aspect Ratio</label>
                                    <select
                                        value={aspectRatio}
                                        onChange={(e) => setAspectRatio(e.target.value)}
                                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white focus:border-violet-500 focus:ring-0"
                                    >
                                        <option value="9:16">9:16 (Portrait)</option>
                                        <option value="16:9">16:9 (Landscape)</option>
                                        <option value="1:1">1:1 (Square)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-xs text-slate-500 mb-1.5">Language</label>
                                    <input
                                        type="text"
                                        value={language}
                                        onChange={(e) => setLanguage(e.target.value)}
                                        placeholder="Auto-detect"
                                        className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder-slate-600 focus:border-violet-500 focus:ring-0"
                                    />
                                </div>
                            </div>

                            {/* Notifications */}
                            <label className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={notifyTelegram}
                                    onChange={(e) => setNotifyTelegram(e.target.checked)}
                                    className="w-4 h-4 rounded border-slate-600 bg-transparent text-violet-500 focus:ring-violet-500"
                                />
                                <span className="text-sm text-slate-300">📱 Notify via Telegram</span>
                            </label>
                        </div>
                    )}
                </div>

                {/* Submit Button */}
                <button
                    type="submit"
                    disabled={submitting || !url.trim()}
                    className={`
            w-full py-4 rounded-xl font-semibold text-sm transition-all duration-300
            ${submitting || !url.trim()
                            ? "bg-slate-800 text-slate-600 cursor-not-allowed"
                            : "bg-gradient-to-r from-violet-600 to-violet-500 text-white hover:from-violet-500 hover:to-violet-400 hover:shadow-lg hover:shadow-violet-500/25 active:scale-[0.98]"
                        }
          `}
                >
                    {submitting ? (
                        <span className="flex items-center justify-center gap-2">
                            <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
                            Processing...
                        </span>
                    ) : (
                        "🚀 Start Processing"
                    )}
                </button>
            </form>
        </div>
    );
}
