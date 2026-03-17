"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { getSubscriptionStatus, openBillingPortal } from "@/lib/api/billing";
import { getConnectedAccounts, getConnectUrl, disconnectAccount } from "@/lib/api/publish";
import type { SubscriptionStatus, SocialAccount } from "@/lib/api/types";

const PLAN_COLORS: Record<string, string> = {
  free: "from-slate-500 to-slate-600",
  starter: "from-sky-500 to-blue-600",
  pro: "from-violet-500 to-purple-600",
  business: "from-amber-500 to-orange-600",
  enterprise: "from-rose-500 to-pink-600",
};

const PLATFORM_ICONS: Record<string, string> = {
  tiktok: "🎵",
  instagram: "📸",
  youtube: "▶️",
};

function BillingContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const [sub, setSub] = useState<SubscriptionStatus | null>(null);
  const [accounts, setAccounts] = useState<SocialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const successMsg = searchParams.get("success");
  const cancelMsg = searchParams.get("canceled");

  useEffect(() => {
    if (!user) { router.push("/login?redirect=/billing"); return; }
    Promise.all([getSubscriptionStatus(), getConnectedAccounts()]).then(([s, a]) => {
      setSub(s);
      setAccounts(a.accounts);
      setLoading(false);
    });
  }, [user, router]);

  async function handlePortal() {
    setPortalLoading(true);
    try {
      const { portal_url } = await openBillingPortal();
      window.location.href = portal_url;
    } catch {
      alert("No active subscription found.");
    } finally {
      setPortalLoading(false);
    }
  }

  async function handleConnect(platform: string) {
    try {
      const { oauth_url } = await getConnectUrl(platform);
      window.location.href = oauth_url;
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: { code?: string; message?: string } | string } } };
      const detail = err?.response?.data?.detail;
      if (typeof detail === "object" && detail?.code === "FEATURE_LOCKED") {
        router.push("/pricing");
      } else {
        alert(typeof detail === "string" ? detail : detail?.message || "Failed to connect");
      }
    }
  }

  async function handleDisconnect(id: string) {
    await disconnectAccount(id);
    setAccounts((prev) => prev.filter((a) => a.id !== id));
  }

  if (loading || !sub) {
    return (
      <div className="space-y-6 max-w-3xl">
        <div className="animate-pulse glass-card h-48 rounded-2xl" />
        <div className="animate-pulse glass-card h-64 rounded-2xl" />
      </div>
    );
  }

  const gradientClass = PLAN_COLORS[sub.plan_tier] ?? PLAN_COLORS.free;
  const quota_pct =
    sub.monthly_quota === 0 ? 100 : Math.min(100, (sub.used_quota / sub.monthly_quota) * 100);
  const daysLeft = sub.trial_end_date
    ? Math.max(0, Math.ceil((new Date(sub.trial_end_date).getTime() - Date.now()) / 86400000))
    : null;

  return (
    <div className="space-y-8 max-w-3xl animate-fadeIn">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Billing &amp; Subscription</h1>
        <p className="text-slate-500">Manage your plan, payment, and connected social accounts.</p>
      </div>

      {successMsg && (
        <div className="p-4 border border-emerald-500/20 bg-emerald-500/5 text-emerald-400 text-sm rounded-xl">
          ✅ Subscription updated successfully!
        </div>
      )}
      {cancelMsg && (
        <div className="p-4 border border-amber-500/20 bg-amber-500/5 text-amber-400 text-sm rounded-xl">
          ℹ️ Checkout canceled. No charges were made.
        </div>
      )}

      {/* Current Plan Card */}
      <div className="glass-card p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Current Plan</h2>
          <div className={`px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r ${gradientClass} text-white`}>
            {sub.plan_tier.toUpperCase()}
          </div>
        </div>

        {sub.is_trial && daysLeft !== null && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-300 text-sm">
            <span>⏳</span>
            <span>
              Pro trial ends in <strong>{daysLeft} day{daysLeft !== 1 ? "s" : ""}</strong> — upgrade to keep Pro features.
            </span>
          </div>
        )}

        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Videos this month</span>
            <span className="text-slate-300 font-medium">
              {sub.monthly_quota === 0 ? "Unlimited" : `${sub.used_quota} / ${sub.monthly_quota}`}
            </span>
          </div>
          {sub.monthly_quota > 0 && (
            <div className="w-full h-2 rounded-full bg-white/5">
              <div
                className={`h-full rounded-full transition-all bg-gradient-to-r ${
                  quota_pct >= 90
                    ? "from-rose-500 to-red-400"
                    : quota_pct >= 70
                    ? "from-amber-500 to-yellow-400"
                    : "from-violet-500 to-purple-400"
                }`}
                style={{ width: `${quota_pct}%` }}
              />
            </div>
          )}
        </div>

        <div className="flex gap-3 pt-2">
          <button
            onClick={() => router.push("/pricing")}
            className="px-4 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white transition-all"
          >
            {sub.plan_tier === "free" ? "Upgrade Plan" : "Change Plan"}
          </button>
          {sub.subscription_status === "active" && (
            <button
              onClick={handlePortal}
              disabled={portalLoading}
              className="px-4 py-2 rounded-xl text-sm font-semibold bg-white/5 hover:bg-white/10 text-slate-300 transition-colors disabled:opacity-50"
            >
              {portalLoading ? "Loading..." : "Manage / Cancel"}
            </button>
          )}
        </div>
      </div>

      {/* Connected Social Accounts */}
      <div className="glass-card p-6 space-y-4">
        <div>
          <h2 className="text-lg font-semibold text-white mb-1">Connected Accounts</h2>
          <p className="text-sm text-slate-500">Connect social accounts to publish clips directly.</p>
        </div>

        {(["tiktok", "instagram", "youtube"] as const).map((platform) => {
          const connected = accounts.find((a) => a.platform === platform);
          return (
            <div
              key={platform}
              className="flex items-center justify-between py-3 border-b border-white/5 last:border-0"
            >
              <div className="flex items-center gap-3">
                <span className="text-2xl">{PLATFORM_ICONS[platform]}</span>
                <div>
                  <p className="text-sm font-medium text-slate-200 capitalize">{platform}</p>
                  {connected ? (
                    <p className="text-xs text-slate-500">@{connected.username}</p>
                  ) : (
                    <p className="text-xs text-slate-600">Not connected</p>
                  )}
                </div>
              </div>
              {connected ? (
                <button
                  onClick={() => handleDisconnect(connected.id)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors"
                >
                  Disconnect
                </button>
              ) : (
                <button
                  onClick={() => handleConnect(platform)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20 hover:bg-violet-500/20 transition-colors"
                >
                  Connect
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function BillingPage() {
  return (
    <Suspense fallback={<div className="animate-pulse glass-card h-48 rounded-2xl" />}>
      <BillingContent />
    </Suspense>
  );
}
