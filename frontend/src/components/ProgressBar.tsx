interface ProgressBarProps {
    value: number; // 0-100
    size?: "sm" | "md" | "lg";
    showLabel?: boolean;
    animated?: boolean;
    accent?: "violet" | "emerald" | "amber" | "sky" | "rose";
}

const gradientMap = {
    violet: "from-violet-600 to-violet-400",
    emerald: "from-emerald-600 to-emerald-400",
    amber: "from-amber-600 to-amber-400",
    sky: "from-sky-600 to-sky-400",
    rose: "from-rose-600 to-rose-400",
};

const sizeMap = {
    sm: "h-1.5",
    md: "h-2.5",
    lg: "h-4",
};

export default function ProgressBar({
    value,
    size = "md",
    showLabel = false,
    animated = true,
    accent = "violet",
}: ProgressBarProps) {
    const clamped = Math.min(100, Math.max(0, value));

    return (
        <div className="w-full">
            {showLabel && (
                <div className="flex justify-between mb-1.5">
                    <span className="text-xs text-slate-500">Progress</span>
                    <span className="text-xs font-mono text-slate-400">{clamped.toFixed(1)}%</span>
                </div>
            )}
            <div className={`w-full ${sizeMap[size]} rounded-full bg-white/5 overflow-hidden`}>
                <div
                    className={`
            ${sizeMap[size]} rounded-full bg-gradient-to-r ${gradientMap[accent]}
            transition-all duration-700 ease-out
            ${animated && clamped > 0 && clamped < 100 ? "progress-bar-animated" : ""}
          `}
                    style={{ width: `${clamped}%` }}
                />
            </div>
        </div>
    );
}
