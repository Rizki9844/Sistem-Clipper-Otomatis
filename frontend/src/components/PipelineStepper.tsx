import { JobStep } from "@/lib/api/types";

interface PipelineStepperProps {
    steps: JobStep[];
}

const stepIcons: Record<string, string> = {
    download: "📥",
    transcribe: "🎙️",
    analyze: "🧠",
    edit: "✂️",
    render: "🎨",
};

const stepColors: Record<string, string> = {
    pending: "border-slate-700 bg-slate-800/50 text-slate-500",
    running: "border-violet-500 bg-violet-500/15 text-violet-400 animate-pulse-glow",
    completed: "border-emerald-500 bg-emerald-500/15 text-emerald-400",
    failed: "border-rose-500 bg-rose-500/15 text-rose-400",
    skipped: "border-slate-700 bg-slate-800/30 text-slate-600",
};

const lineColors: Record<string, string> = {
    pending: "bg-slate-700/50",
    running: "bg-violet-500/30",
    completed: "bg-emerald-500/50",
    failed: "bg-rose-500/50",
    skipped: "bg-slate-700/30",
};

export default function PipelineStepper({ steps }: PipelineStepperProps) {
    return (
        <div className="flex items-center justify-between w-full gap-1">
            {steps.map((step, index) => (
                <div key={step.name} className="flex items-center flex-1 last:flex-none">
                    {/* Step Circle */}
                    <div className="flex flex-col items-center gap-2 min-w-[80px]">
                        <div
                            className={`
                w-12 h-12 rounded-2xl border-2 flex items-center justify-center text-xl
                transition-all duration-500 ${stepColors[step.status]}
              `}
                        >
                            {step.status === "completed" ? "✓" : stepIcons[step.name] || "●"}
                        </div>
                        <div className="text-center">
                            <p className={`text-[11px] font-medium ${step.status === "running" ? "text-violet-300" :
                                    step.status === "completed" ? "text-emerald-300" :
                                        step.status === "failed" ? "text-rose-300" : "text-slate-500"
                                }`}>
                                {step.display.replace(/^[^\s]+\s/, "")}
                            </p>
                            {step.status === "running" && (
                                <p className="text-[10px] text-violet-400/70 font-mono mt-0.5">
                                    {step.progress.toFixed(0)}%
                                </p>
                            )}
                            {step.status === "failed" && step.error && (
                                <p className="text-[10px] text-rose-400/70 mt-0.5 line-clamp-2 max-w-[100px]">
                                    {step.error}
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Connector Line */}
                    {index < steps.length - 1 && (
                        <div className={`flex-1 h-0.5 mx-1 rounded-full ${lineColors[step.status]} transition-all duration-500`} />
                    )}
                </div>
            ))}
        </div>
    );
}
