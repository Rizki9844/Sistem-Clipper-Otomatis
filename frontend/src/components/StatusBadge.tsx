interface StatusBadgeProps {
    status: string;
    size?: "sm" | "md";
}

const statusStyles: Record<string, { bg: string; text: string; dot: string }> = {
    // Job statuses
    queued: { bg: "bg-slate-500/10", text: "text-slate-400", dot: "bg-slate-400" },
    processing: { bg: "bg-sky-500/10", text: "text-sky-400", dot: "bg-sky-400" },
    completed: { bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-400" },
    failed: { bg: "bg-rose-500/10", text: "text-rose-400", dot: "bg-rose-400" },
    cancelled: { bg: "bg-amber-500/10", text: "text-amber-400", dot: "bg-amber-400" },
    // Clip statuses
    pending: { bg: "bg-slate-500/10", text: "text-slate-400", dot: "bg-slate-400" },
    editing: { bg: "bg-sky-500/10", text: "text-sky-400", dot: "bg-sky-400" },
    edited: { bg: "bg-violet-500/10", text: "text-violet-400", dot: "bg-violet-400" },
    rendering: { bg: "bg-amber-500/10", text: "text-amber-400", dot: "bg-amber-400" },
    // Review statuses
    approved: { bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-400" },
    rejected: { bg: "bg-rose-500/10", text: "text-rose-400", dot: "bg-rose-400" },
    // Video statuses
    uploaded: { bg: "bg-violet-500/10", text: "text-violet-400", dot: "bg-violet-400" },
    downloading: { bg: "bg-sky-500/10", text: "text-sky-400", dot: "bg-sky-400" },
    downloaded: { bg: "bg-emerald-500/10", text: "text-emerald-400", dot: "bg-emerald-400" },
    transcribing: { bg: "bg-amber-500/10", text: "text-amber-400", dot: "bg-amber-400" },
    transcribed: { bg: "bg-violet-500/10", text: "text-violet-400", dot: "bg-violet-400" },
};

export default function StatusBadge({ status, size = "sm" }: StatusBadgeProps) {
    const s = statusStyles[status] || statusStyles.pending;
    const sizeClasses = size === "sm" ? "text-[11px] px-2.5 py-1" : "text-xs px-3 py-1.5";

    return (
        <span className={`inline-flex items-center gap-1.5 ${sizeClasses} rounded-full font-medium ${s.bg} ${s.text} border border-current/10`}>
            <span className={`w-1.5 h-1.5 rounded-full ${s.dot} ${status === "processing" || status === "rendering" || status === "downloading" ? "animate-pulse" : ""}`} />
            {status.charAt(0).toUpperCase() + status.slice(1)}
        </span>
    );
}
