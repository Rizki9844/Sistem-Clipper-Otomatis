"use client";

import { useRouter } from "next/navigation";

interface UpgradePromptProps {
    /** The feature name being blocked */
    feature?: string;
    /** Minimum plan required */
    requiredPlan?: "starter" | "pro" | "business";
    /** User's current plan */
    currentPlan?: string;
    /** Custom message override */
    message?: string;
    /** Show as inline card (default) or full-screen overlay */
    variant?: "card" | "banner" | "inline";
}

const PLAN_LABELS: Record<string, string> = {
    starter: "Starter ($12/mo)",
    pro: "Pro ($29/mo)",
    business: "Business ($79/mo)",
};

const PLAN_EMOJIS: Record<string, string> = {
    starter: "⚡",
    pro: "🚀",
    business: "💼",
};

export default function UpgradePrompt({
    feature,
    requiredPlan = "starter",
    currentPlan,
    message,
    variant = "card",
}: UpgradePromptProps) {
    const router = useRouter();

    const label = PLAN_LABELS[requiredPlan] ?? requiredPlan;
    const emoji = PLAN_EMOJIS[requiredPlan] ?? "🔒";
    const defaultMsg = feature
        ? `${feature} requires the ${label} plan or higher.`
        : `This feature requires the ${label} plan.`;

    const handleUpgrade = () => {
        router.push(`/pricing?highlight=${requiredPlan}`);
    };

    if (variant === "banner") {
        return (
            <div className="flex items-center justify-between px-4 py-3 rounded-xl bg-violet-500/10 border border-violet-500/20 animate-fadeIn">
                <div className="flex items-center gap-3">
                    <span className="text-xl">{emoji}</span>
                    <p className="text-sm text-slate-300">{message || defaultMsg}</p>
                </div>
                <button
                    onClick={handleUpgrade}
                    className="ml-4 shrink-0 px-4 py-1.5 rounded-lg text-xs font-semibold bg-violet-500 hover:bg-violet-400 text-white transition-colors"
                >
                    Upgrade
                </button>
            </div>
        );
    }

    if (variant === "inline") {
        return (
            <span className="inline-flex items-center gap-1.5 text-xs text-amber-400 font-medium">
                <span>🔒</span>
                <span>{label}</span>
            </span>
        );
    }

    // Default: card
    return (
        <div className="glass-card p-8 text-center space-y-4 animate-fadeIn">
            <div className="w-16 h-16 rounded-2xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center mx-auto">
                <span className="text-3xl">{emoji}</span>
            </div>
            <div>
                <h3 className="text-lg font-semibold text-white mb-1">
                    Upgrade to {label}
                </h3>
                <p className="text-sm text-slate-400 max-w-xs mx-auto">
                    {message || defaultMsg}
                </p>
                {currentPlan && (
                    <p className="text-xs text-slate-600 mt-1">
                        You&apos;re currently on the{" "}
                        <span className="text-slate-400 font-medium capitalize">{currentPlan}</span> plan.
                    </p>
                )}
            </div>
            <div className="flex gap-3 justify-center">
                <button
                    onClick={handleUpgrade}
                    className="px-6 py-2.5 rounded-xl font-semibold text-sm bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white transition-all shadow-lg shadow-violet-500/20"
                >
                    View Plans →
                </button>
                <button
                    onClick={() => router.back()}
                    className="px-6 py-2.5 rounded-xl font-semibold text-sm bg-white/5 hover:bg-white/10 text-slate-300 transition-colors"
                >
                    Go Back
                </button>
            </div>
        </div>
    );
}
