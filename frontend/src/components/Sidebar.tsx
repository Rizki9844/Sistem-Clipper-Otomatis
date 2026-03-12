"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
    { href: "/", label: "Dashboard", icon: "📊" },
    { href: "/submit", label: "Submit URL", icon: "🔗" },
    { href: "/videos", label: "Videos", icon: "🎬" },
    { href: "/jobs", label: "Jobs", icon: "⚙️" },
    { href: "/clips", label: "Clips", icon: "✂️" },
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <aside className="fixed left-0 top-0 h-screen flex flex-col glass z-50"
            style={{ width: "var(--sidebar-width)" }}>
            {/* Brand */}
            <div className="px-6 py-6 border-b border-white/5">
                <Link href="/" className="flex items-center gap-3 group">
                    <span className="text-2xl group-hover:scale-110 transition-transform">🎬</span>
                    <div>
                        <h1 className="text-lg font-bold bg-gradient-to-r from-violet-400 to-sky-400 bg-clip-text text-transparent">
                            AutoClipperPro
                        </h1>
                        <p className="text-[10px] text-slate-500 tracking-widest uppercase">AI Video Engine</p>
                    </div>
                </Link>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-3 py-4 space-y-1">
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
            </nav>

            {/* Footer */}
            <div className="px-4 py-4 border-t border-white/5">
                <div className="glass-card px-4 py-3 text-center">
                    <p className="text-[11px] text-slate-500">v0.2.0 · FastAPI + Next.js</p>
                </div>
            </div>
        </aside>
    );
}
