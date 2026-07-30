"use client";

import type { Transfer } from "@/types/reroute";
import { formatTime } from "@/lib/formatters";

interface TransferCardProps {
  transfer: Transfer | null;
}

export default function TransferCard({ transfer }: TransferCardProps) {
  if (!transfer) return null;

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
        Airport Transfer
      </h3>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-lg">
            {transfer.pickup_location} ? {transfer.drop_location}
          </span>
          <TransferStatusBadge status={transfer.status} />
        </div>
        <div className="text-sm text-zinc-600 dark:text-zinc-400">
          <span className="font-medium">Pickup:</span> {formatTime(transfer.pickup_time)}
        </div>
      </div>
    </div>
  );
}

function TransferStatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    CONFIRMED: {
      label: "CONFIRMED",
      className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    },
    RESCHEDULED: {
      label: "RESCHEDULED",
      className: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    },
  };

  const c = config[status] || {
    label: status,
    className: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  };

  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${c.className}`}>
      {c.label}
    </span>
  );
}
