"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { useEffect, useState } from "react";
import { getMyQuota, QuotaResponse } from "@/lib/api/admin";

const navItems = [
    { href: "/", label: "Dashboard", icon: "📊" },
    { href: "/submit", label: "Submit URL", icon: "🔗" },
    { href: "/videos", label: "Videos", icon: "🎬" },
    { href: "/jobs", label: "Jobs", icon: "⚙️" },
    { href: "/clips", label: "Clips", icon: "✂️" },
    { href: "/billing", label: "Billing", icon: "💳" },
];

const adminNavItems = [
    { href: "/admin", label: "Admin Dashboard", icon: "🛡️" },
    { href: "/admin/users", label: "Users", icon: "👥" },
    { href: "/admin/jobs", label: "All Jobs", icon: "📋" },
];

const PLAN_LABELS: Record<string, { label: string; emoji: string; color: string }> = {
    free: { label: "Free", emoji: "🆓", color: "text-slate-400" },
    starter: { label: "Starter", emoji: "⚡", color: "text-sky-400" },
    pro: { label: "Pro", emoji: "🚀", color: "text-violet-400" },
    business: { label: "Business", emoji: "💼", color: "text-amber-400" },
    enterprise: { label: "Enterprise", emoji: "👑", color: "text-rose-400" },
};

export default function Sidebar() {
    const pathname = usePathname();
    const router = useRouter();
    const { user, logout } = useAuth();
    const [quota, setQuota] = useState<QuotaResponse | null>(null);

    useEffect(() => {
        if (user) {
            getMyQuota().catch(() => null).then((q) => q && setQuota(q));
        }
    }, [user]);

    const quotaPct = quota && !quota.unlimited
        ? Math.min(100, (quota.used / quota.limit) * 100)
        : null;

    const planInfo = PLAN_LABELS[(quota?.plan_tier ?? user?.plan_tier ?? "free")] ?? PLAN_LABELS.free;

    return (
        <aside className="fixed left-0 top-0 h-screen flex flex-col glass z-50"
            style={{ width: "var(--sidebar-width)" }}>
            {/* Brand */}
            <div className="px-6 py-6 border-b border-white/5">
                <Link href="/" className="flex items-center gap-3 group">
                    <span className="text-2xl group-hover:scale-110 transition-transform">🎬</span>
                    <div>
                        <h1 className="text-lg font-bold bg-linear-to-r from-violet-400 to-sky-400 bg-clip-text text-transparent">
                            AutoClipperPro
                        </h1>
                        <p className="text-[10px] text-slate-500 tracking-widest uppercase">AI Video Engine</p>
                    </div>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
                {navItems.map((item) => {
                    const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`
                flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
                transition-all duration-200 group relative
                ${isActive
                                    ? "bg-violet-500/10 text-violet-300 border border-violet-500/20"
                                    : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
                                }
              `}
                        >
                            {isActive && (
                                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full bg-violet-500" />
                            )}
                            <span className="text-lg group-hover:scale-110 transition-transform">{item.icon}</span>
                            <span>{item.label}</span>
                        </Link>
                    );
                })}

                {/* Admin Section */}
                {user?.is_admin && (
                    <>
                        <div className="px-4 pt-4 pb-1">
                            <p className="text-[10px] text-slate-600 tracking-widest uppercase font-semibold">Admin</p>
                        </div>
                        {adminNavItems.map((item) => {
                            const isActive = pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
                            return (
                                <Link
                                    key={item.href}
                                    href={item.href}
                                    className={`
                    flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
                    transition-all duration-200 group relative
                    ${isActive
                                            ? "bg-amber-500/10 text-amber-300 border border-amber-500/20"
                                            : "text-slate-500 hover:text-slate-200 hover:bg-white/5"
                                        }
                  `}
                                >
                                    {isActive && (
                                        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full bg-amber-500" />
                                    )}
                                    <span className="text-lg group-hover:scale-110 transition-transform">{item.icon}</span>
                                    <span>{item.label}</span>
                                </Link>
                            );
                        })}
                    </>
                )}
            </nav>

            {/* Footer — Plan + Quota + User info + Logout */}
            <div className="px-4 py-4 border-t border-white/5 space-y-2">
                {/* Plan + Quota Card */}
                <div className="glass-card px-4 py-3 space-y-2">
                    <div className="flex items-center justify-between">
                        <span className={`text-[11px] font-semibold ${planInfo.color}`}>
                            {planInfo.emoji} {planInfo.label} Plan
                        </span>
                        {!quota?.unlimited && quota && (
                            <span className={`text-[11px] font-semibold ${(quotaPct ?? 0) >= 90 ? "text-rose-400" : (quotaPct ?? 0) >= 60 ? "text-amber-400" : "text-emerald-400"}`}>
                                {quota.used}/{quota.limit}
                            </span>
                        )}
                        {quota?.unlimited && (
                            <span className="text-[11px] text-violet-400">∞ unlimited</span>
                        )}
                    </div>
                    {!quota?.unlimited && quotaPct !== null && (
                        <div className="w-full h-1.5 rounded-full bg-white/5 overflow-hidden">
                            <div
                                className={`h-full rounded-full transition-all duration-500 ${quotaPct >= 90 ? "bg-rose-500" : quotaPct >= 60 ? "bg-amber-500" : "bg-emerald-500"}`}
                                style={{ width: `${quotaPct}%` }}
                            />
                        </div>
                    )}
                    {quota?.remaining === 0 && !quota.unlimited && (
                        <button
                            onClick={() => router.push("/pricing")}
                            className="w-full mt-1 text-[10px] text-violet-400 hover:text-violet-300 text-center transition-colors"
                        >
                            Upgrade for more →
                        </button>
                    )}
                </div>

                {user && (
                    <div className="glass-card px-4 py-3">
                        <p className="text-xs text-slate-300 font-medium truncate">{user.full_name || user.email}</p>
                        <p className="text-[10px] text-slate-500 truncate">{user.email}</p>
                        {user.is_admin && (
                            <span className="inline-block mt-1 text-[10px] text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">Admin</span>
                        )}
                    </div>
                )}
                <button
                    onClick={logout}
                    className="w-full px-4 py-2.5 rounded-xl text-sm text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-all duration-200 text-left flex items-center gap-2"
                >
                    <span>🚪</span>
                    <span>Logout</span>
                </button>
                <div className="glass-card px-4 py-2 text-center">
                    <p className="text-[11px] text-slate-500">v0.4.0 · FastAPI + Next.js</p>
                </div>
            </div>
        </aside>
    );
}
