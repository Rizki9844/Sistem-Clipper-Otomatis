// Pricing page content - ready to paste into /pricing/page.tsx after running node create_directories.js

/*
FILE: frontend/src/app/pricing/page.tsx
USAGE: After running `node create_directories.js`, save this as page.tsx in that folder
*/

export const PRICING_PAGE_CONTENT = `
"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";
import { getPlans, createCheckout } from "@/lib/api/billing";
import type { PricingPlan } from "@/lib/api/types";

const TIER_COLORS: Record<string, string> = {
  free: "from-slate-500 to-slate-600",
  starter: "from-sky-500 to-blue-600",
  pro: "from-violet-500 to-purple-600",
  business: "from-amber-500 to-orange-600",
};

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
    if (!user) {
      router.push("/login?redirect=/pricing");
      return;
    }
    if (tier === "free") return;

    setUpgrading(tier);
    try {
      const { checkout_url } = await createCheckout(tier);
      window.location.href = checkout_url;
    } catch (e: any) {
      alert(e?.response?.data?.detail || "Failed to start checkout");
    } finally {
      setUpgrading(null);
    }
  }

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-white px-4 py-16">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
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

        {/* Plans Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-96 rounded-2xl bg-white/5 animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {plans.map((plan) => {
              const isCurrent = user?.plan_tier === plan.tier;
              const isMostPopular = plan.badge === "Most Popular";
              const price = prices[plan.tier] ?? 0;

              return (
                <div
                  key={plan.tier}
                  className={\`relative rounded-2xl border p-6 flex flex-col gap-5 transition-all \${
                    isMostPopular
                      ? "border-violet-500/40 bg-violet-500/5 shadow-xl shadow-violet-500/10 scale-105"
                      : "border-white/10 bg-white/3 hover:border-white/20"
                  }\`}
                >
                  {/* Badge */}
                  {plan.badge && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold bg-violet-500 text-white">
                      {plan.badge}
                    </div>
                  )}
                  {isCurrent && (
                    <div className="absolute -top-3 right-4 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500 text-white">
                      Current Plan
                    </div>
                  )}

                  {/* Plan Name */}
                  <div>
                    <div className={\`inline-flex px-3 py-1 rounded-lg text-xs font-bold border mb-3 \${TIER_BADGE_COLORS[plan.tier] ?? ""}\`}>
                      {plan.tier.toUpperCase()}
                    </div>
                    <div className="flex items-end gap-1">
                      <span className="text-4xl font-bold">
                        {price === 0 ? "Free" : \`\$\${price}\`}
                      </span>
                      {price > 0 && <span className="text-slate-500 mb-1">/month</span>}
                    </div>
                  </div>

                  {/* Features */}
                  <ul className="space-y-2 flex-1">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-300">
                        <span className="text-emerald-400 mt-0.5">✓</span>
                        {f}
                      </li>
                    ))}
                    {plan.not_included.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-slate-600">
                        <span className="mt-0.5">✗</span>
                        {f}
                      </li>
                    ))}
                  </ul>

                  {/* CTA */}
                  <button
                    onClick={() => handleUpgrade(plan.tier)}
                    disabled={isCurrent || plan.tier === "free" || upgrading === plan.tier}
                    className={\`w-full py-3 rounded-xl font-semibold text-sm transition-all \${
                      isCurrent
                        ? "bg-white/5 text-slate-500 cursor-default"
                        : plan.tier === "free"
                        ? "bg-white/5 text-slate-400 cursor-default"
                        : isMostPopular
                        ? "bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-400 hover:to-purple-500 text-white shadow-lg shadow-violet-500/20"
                        : "bg-white/10 hover:bg-white/20 text-white"
                    }\`}
                  >
                    {upgrading === plan.tier
                      ? "Redirecting..."
                      : isCurrent
                      ? "Current Plan"
                      : plan.cta}
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {/* FAQ */}
        <div className="mt-20 text-center">
          <p className="text-slate-500 text-sm">
            All plans include a 7-day Pro trial for new users. Cancel anytime.{" "}
            <a href="mailto:support@autoclipperpro.com" className="text-violet-400 hover:underline">
              Questions? Contact us
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
`;
