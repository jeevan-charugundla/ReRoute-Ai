"use client";

import type { RecoveryOption } from "@/types/reroute";
import { formatCurrency } from "@/lib/formatters";
import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";

interface PolicyDecisionProps {
  decision: string;
  reason: string;
  option: RecoveryOption;
  autoLimit: number;
}

export default function PolicyDecision({
  decision,
  reason,
  option,
  autoLimit,
}: PolicyDecisionProps) {
  const config: Record<
    string,
    {
      icon: typeof ShieldCheck;
      label: string;
      className: string;
      badgeClassName: string;
    }
  > = {
    AUTO: {
      icon: ShieldCheck,
      label: "AUTO AUTHORIZED",
      className: "text-emerald-600 dark:text-emerald-400",
      badgeClassName:
        "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    },
    APPROVAL_REQUIRED: {
      icon: ShieldAlert,
      label: "APPROVAL REQUIRED",
      className: "text-amber-600 dark:text-amber-400",
      badgeClassName:
        "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    },
    ESCALATE: {
      icon: ShieldX,
      label: "ESCALATE",
      className: "text-red-600 dark:text-red-400",
      badgeClassName:
        "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
  };

  const c = config[decision] || config.AUTO;
  const Icon = c.icon;

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-4">
        <Icon className={`w-6 h-6 ${c.className}`} />
        <h3 className="font-semibold">Policy Check</h3>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm text-zinc-600 dark:text-zinc-400">
            Selected Flight
          </span>
          <span className="font-semibold">{option.flight_number}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-zinc-600 dark:text-zinc-400">
            Additional Cost
          </span>
          <span className="font-semibold">{formatCurrency(option.additional_cost)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-zinc-600 dark:text-zinc-400">
            Auto Rebook Limit
          </span>
          <span className="font-semibold">{formatCurrency(autoLimit)}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-zinc-600 dark:text-zinc-400">Cabin</span>
          <span className="font-semibold">{option.cabin}</span>
        </div>
        <div className="pt-3 border-t border-zinc-200 dark:border-zinc-700">
          <div className="flex items-center justify-between">
            <span className="text-sm text-zinc-600 dark:text-zinc-400">Decision</span>
            <span className={`px-3 py-1 rounded-full text-sm font-bold ${c.badgeClassName}`}>
              {c.label}
            </span>
          </div>
          <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-2">{reason}</p>
        </div>
      </div>
    </div>
  );
}
