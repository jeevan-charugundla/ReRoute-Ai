// ============================================================
// DataSourceBadge — shows REAL / CACHE / DEMO data source
// ============================================================
"use client";

import type { DataSource } from "@/types/reroute";

interface DataSourceBadgeProps {
  source: DataSource;
  className?: string;
}

export default function DataSourceBadge({
  source,
  className = "",
}: DataSourceBadgeProps) {
  const config: Record<string, { dot: string; label: string; bg: string }> = {
    REAL: {
      dot: "bg-emerald-500 animate-pulse",
      label: "Live Data",
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
    },
    CACHE: {
      dot: "bg-amber-400",
      label: "Cached",
      bg: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
    },
    DEMO: {
      dot: "bg-zinc-400",
      label: "Demo Data",
      bg: "bg-zinc-100 text-zinc-600 border-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:border-zinc-700",
    },
  };

  const c = config[source] || config.DEMO;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${c.bg} ${className}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  );
}
