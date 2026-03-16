const fs = require('fs');
const path = require('path');

const BASE = 'r:\\All Projek Saya\\Sistem Clipper Otomatis\\frontend\\src\\app';

// ---- Create directories ----
const directories = [
  path.join(BASE, 'pricing'),
  path.join(BASE, 'billing'),
];
directories.forEach(dir => {
  fs.mkdirSync(dir, { recursive: true });
  console.log(`✓ Dir: ${dir}`);
});

// ---- /pricing/page.tsx ----
fs.writeFileSync(path.join(BASE, 'pricing', 'page.tsx'), `"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { getPlans, createCheckout } from "@/lib/api/billing";
import type { PricingPlan } from "@/lib/api/types";

const TIER_BADGE_COLORS: Record<string, string> = {
  free: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  starter: "bg-sky-500/10 text-sky-400 border-sky-500/20",
  pro: "bg-violet-500/10 text-violet-400 border-violet-500/20",
  business: "bg-amber-500/10 text-amber-400 border-amber-500/20",
};

export default function PricingPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [plans, setPlans] = useState<PricingPlan[]>([]);
  const [prices, setPrices] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [upgrading, setUpgrading] = useState<string | null>(null);

  useEffect(() => {
    getPlans().then((data) => {
      setPlans(data.plans);
      setPrices(data.prices);
      setLoading(false);
    });
  }, []);

  async function handleUpgrade(tier: string) {
    if (!user) { router.push("/login?redirect=/pricing"); return; }
    if (tier === "free") return;
    setUpgrading(tier);
    try {
      const { checkout_url } = await createCheckout(tier);
      window.location.href = checkout_url;
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } };
      alert(err?.response?.data?.detail || "Failed to start checkout");
    } finally { setUpgrading(null); }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white px-4 py-16">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-4">
            Simple,{" "}
            <span className="bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
              Transparent
            </span>{" "}
            Pricing
          </h1>
          <p className="text-slate-400 text-xl max-w-2xl mx-auto">
            Turn long videos into viral clips. Start free, upgrade when you need more.
          </p>
        </div>
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {Array.from({ length: 4 }).map((_, i) => <div key={i} className="h-96 rounded-2xl bg-white/5 animate-pulse" />)}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {plans.map((plan) => {
              const isCurrent = (user as { plan_tier?: string } | null)?.plan_tier === plan.tier;
              const isMostPopular = plan.badge === "Most Popular";
              const price = prices[plan.tier] ?? 0;
              return (
                <div key={plan.tier} className={\`relative rounded-2xl border p-6 flex flex-col gap-5 transition-all \${isMostPopular ? "border-violet-500/40 bg-violet-500/5 shadow-xl shadow-violet-500/10 scale-105" : "border-white/10 bg-white/[0.03] hover:border-white/20"}\`}>
                  {plan.badge && <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold bg-violet-500 text-white">{plan.badge}</div>}
                  {isCurrent && <div className="absolute -top-3 right-4 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500 text-white">Current Plan</div>}
                  <div>
                    <div className={\`inline-flex px-3 py-1 rounded-lg text-xs font-bold border mb-3 \${TIER_BADGE_COLORS[plan.tier] ?? ""}\`}>{plan.tier.toUpperCase()}</div>
                    <div className="flex items-end gap-1">
                      <span className="text-4xl font-bold">{price === 0 ? "Free" : \`\$\${price}\`}</span>
                      {price > 0 && <span className="text-slate-500 mb-1">/month</span>}
                    </div>
                  </div>
                  <ul className="space-y-2 flex-1">
                    {plan.features.map((f: string, i: number) => <li key={i} className="flex items-start gap-2 text-sm text-slate-300"><span className="text-emerald-400 mt-0.5">✓</span>{f}</li>)}
                    {plan.not_included.map((f: string, i: number) => <li key={i} className="flex items-start gap-2 text-sm text-slate-600"><span className="mt-0.5">✗</span>{f}</li>)}
                  </ul>
                  <button onClick={() => handleUpgrade(plan.tier)} disabled={isCurrent || plan.tier === "free" || upgrading === plan.tier}
                    className={\`w-full py-3 rounded-xl font-semibold text-sm transition-all \${isCurrent ? "bg-white/5 text-slate-500 cursor-default" : plan.tier === "free" ? "bg-white/5 text-slate-400 cursor-default" : isMostPopular ? "bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white shadow-lg shadow-violet-500/20" : "bg-white/10 hover:bg-white/20 text-white"}\`}>
                    {upgrading === plan.tier ? "Redirecting..." : isCurrent ? "Current Plan" : plan.cta}
                  </button>
                </div>
              );
            })}
          </div>
        )}
        <div className="mt-20 text-center">
          <p className="text-slate-500 text-sm">All plans include a 7-day Pro trial for new users. Cancel anytime. <a href="mailto:support@autoclipperpro.com" className="text-violet-400 hover:underline">Questions? Contact us</a></p>
        </div>
      </div>
    </div>
  );
}
`);
console.log('✓ Created: pricing/page.tsx');

// ---- /billing/page.tsx ----
fs.writeFileSync(path.join(BASE, 'billing', 'page.tsx'), `"use client";

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
    Promise.all([getSubscriptionStatus(), getConnectedAccounts()]).then(([s, a]) => {
      setSub(s); setAccounts(a.accounts); setLoading(false);
    });
  }, []);

  async function handlePortal() {
    setPortalLoading(true);
    try { const { portal_url } = await openBillingPortal(); window.location.href = portal_url; }
    catch { alert("No active subscription found."); }
    finally { setPortalLoading(false); }
  }

  async function handleConnect(platform: string) {
    try {
      const { oauth_url } = await getConnectUrl(platform);
      window.location.href = oauth_url;
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: { code?: string; message?: string } | string } } };
      const detail = err?.response?.data?.detail;
      if (typeof detail === "object" && detail?.code === "FEATURE_LOCKED") { router.push("/pricing"); }
      else { alert(typeof detail === "string" ? detail : detail?.message || "Failed to connect"); }
    }
  }

  async function handleDisconnect(id: string) {
    await disconnectAccount(id);
    setAccounts((prev) => prev.filter((a) => a.id !== id));
  }

  if (loading || !sub) return <div className="animate-pulse glass-card h-48 rounded-2xl" />;

  const gradientClass = PLAN_COLORS[sub.plan_tier] ?? PLAN_COLORS.free;
  const quota_pct = sub.monthly_quota === 0 ? 100 : Math.min(100, (sub.used_quota / sub.monthly_quota) * 100);
  const daysLeft = sub.trial_end_date
    ? Math.max(0, Math.ceil((new Date(sub.trial_end_date).getTime() - Date.now()) / 86400000))
    : null;

  return (
    <div className="space-y-8 max-w-3xl animate-fadeIn">
      <div>
        <h1 className="text-3xl font-bold text-white mb-1">Billing & Subscription</h1>
        <p className="text-slate-500">Manage your plan, payment, and connected social accounts.</p>
      </div>

      {successMsg && <div className="glass-card p-4 border-emerald-500/20 bg-emerald-500/5 text-emerald-400 text-sm rounded-xl">✅ Subscription updated successfully!</div>}
      {cancelMsg && <div className="glass-card p-4 border-amber-500/20 bg-amber-500/5 text-amber-400 text-sm rounded-xl">ℹ️ Checkout canceled. No charges were made.</div>}

      <div className="glass-card p-6 space-y-5">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Current Plan</h2>
          <div className={\`px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r \${gradientClass} text-white\`}>{sub.plan_tier.toUpperCase()}</div>
        </div>
        {sub.is_trial && daysLeft !== null && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-violet-500/10 border border-violet-500/20 text-violet-300 text-sm">
            <span>⏳</span>
            <span>Pro trial ends in <strong>{daysLeft} day{daysLeft !== 1 ? "s" : ""}</strong> — upgrade to keep Pro features.</span>
          </div>
        )}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-slate-400">Videos this month</span>
            <span className="text-slate-300 font-medium">{sub.monthly_quota === 0 ? "Unlimited" : \`\${sub.used_quota} / \${sub.monthly_quota}\`}</span>
          </div>
          {sub.monthly_quota > 0 && (
            <div className="w-full h-2 rounded-full bg-white/5">
              <div className={\`h-full rounded-full transition-all bg-gradient-to-r \${quota_pct >= 90 ? "from-rose-500 to-red-400" : quota_pct >= 70 ? "from-amber-500 to-yellow-400" : "from-violet-500 to-purple-400"}\`} style={{ width: \`\${quota_pct}%\` }} />
            </div>
          )}
        </div>
        <div className="flex gap-3 pt-2">
          <button onClick={() => router.push("/pricing")} className="px-4 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white transition-all">Upgrade Plan</button>
          {sub.subscription_status === "active" && (
            <button onClick={handlePortal} disabled={portalLoading} className="px-4 py-2 rounded-xl text-sm font-semibold bg-white/5 hover:bg-white/10 text-slate-300 transition-colors">{portalLoading ? "Loading..." : "Manage / Cancel"}</button>
          )}
        </div>
      </div>

      <div className="glass-card p-6 space-y-5">
        <div>
          <h2 className="text-lg font-semibold text-white mb-1">Connected Accounts</h2>
          <p className="text-sm text-slate-500">Connect social accounts to publish clips directly.</p>
        </div>
        {(["tiktok", "instagram", "youtube"] as const).map((platform) => {
          const connected = accounts.find((a) => a.platform === platform);
          return (
            <div key={platform} className="flex items-center justify-between py-3 border-b border-white/5 last:border-0">
              <div className="flex items-center gap-3">
                <span className="text-2xl">{PLATFORM_ICONS[platform]}</span>
                <div>
                  <p className="text-sm font-medium text-slate-200 capitalize">{platform}</p>
                  {connected ? <p className="text-xs text-slate-500">@{connected.username}</p> : <p className="text-xs text-slate-600">Not connected</p>}
                </div>
              </div>
              {connected ? (
                <button onClick={() => handleDisconnect(connected.id)} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors">Disconnect</button>
              ) : (
                <button onClick={() => handleConnect(platform)} className="px-3 py-1.5 rounded-lg text-xs font-medium bg-violet-500/10 text-violet-400 border border-violet-500/20 hover:bg-violet-500/20 transition-colors">Connect</button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function BillingPage() {
  return <Suspense fallback={<div className="animate-pulse glass-card h-48 rounded-2xl" />}><BillingContent /></Suspense>;
}
`);
console.log('✓ Created: billing/page.tsx');

console.log('\n✅ All done! Run: cd frontend && npm run dev to test.');

