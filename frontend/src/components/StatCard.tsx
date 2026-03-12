"use client";

interface StatCardProps {
    icon: string;
    label: string;
    value: number | string;
    suffix?: string;
    accent?: "violet" | "amber" | "emerald" | "rose" | "sky";
    delay?: number;
}

const accentMap = {
    violet: { bg: "bg-violet-500/10", text: "text-violet-400", border: "border-violet-500/20", glow: "shadow-violet-500/10" },
    amber: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/20", glow: "shadow-amber-500/10" },
    emerald: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20", glow: "shadow-emerald-500/10" },
    rose: { bg: "bg-rose-500/10", text: "text-rose-400", border: "border-rose-500/20", glow: "shadow-rose-500/10" },
    sky: { bg: "bg-sky-500/10", text: "text-sky-400", border: "border-sky-500/20", glow: "shadow-sky-500/10" },
};

export default function StatCard({ icon, label, value, suffix, accent = "violet", delay = 0 }: StatCardProps) {
    const colors = accentMap[accent];

    return (
        <div
            className={`glass-card p-5 animate-fadeIn`}
            style={{ animationDelay: `${delay}ms` }}
        >
            <div className="flex items-start justify-between">
                <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wider font-medium mb-2">{label}</p>
                    <div className="flex items-baseline gap-1.5">
                        <span className={`text-3xl font-bold ${colors.text} animate-countUp`}>
                            {value}
                        </span>
                        {suffix && <span className="text-sm text-slate-500">{suffix}</span>}
                    </div>
                </div>
                <div className={`w-10 h-10 rounded-xl ${colors.bg} border ${colors.border} flex items-center justify-center text-lg`}>
                    {icon}
                </div>
            </div>
        </div>
    );
}
