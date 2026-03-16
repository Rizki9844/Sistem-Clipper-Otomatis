"use client";

import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { useAuth } from "@/components/AuthProvider";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();

  // Show full-screen loading while checking auth
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <span className="text-5xl animate-pulse">🎬</span>
          <p className="mt-4 text-slate-500 text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  // Login page — no sidebar
  if (pathname === "/login") {
    return <main className="min-h-screen">{children}</main>;
  }

  // Authenticated pages — sidebar + content
  if (isAuthenticated) {
    return (
      <>
        <Sidebar />
        <main
          className="min-h-screen transition-all duration-300"
          style={{ marginLeft: "var(--sidebar-width)" }}
        >
          <div className="p-6 lg:p-8 max-w-[1400px] mx-auto">{children}</div>
        </main>
      </>
    );
  }

  // Fallback (redirecting to login)
  return null;
}
