"use client";

import { Plane, AlertTriangle, ShieldCheck, CheckCircle2 } from "lucide-react";
import type { TripListItem } from "@/types/reroute";

interface DashboardMetricsProps {
  tripsList: TripListItem[];
}

export default function DashboardMetrics({ tripsList }: DashboardMetricsProps) {
  const totalTrips = tripsList.length;
  const activeTrips = tripsList.filter((t) => t.trip.status === "HEALTHY" || t.trip.status === "MONITORING").length;
  const tripsAtRisk = tripsList.filter((t) => t.trip.status === "DELAYED_BUT_SAFE" || t.trip.status === "AT_RISK" || t.trip.status === "RECOVERY_REQUIRED").length;
  const recoveredTrips = tripsList.filter((t) => t.trip.status === "RECOVERED").length;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4 shadow-sm flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center shrink-0">
          <Plane className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-zinc-900 dark:text-white">{totalTrips}</p>
          <p className="text-xs text-zinc-500 font-medium">Total Trips</p>
        </div>
      </div>

      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4 shadow-sm flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
          <ShieldCheck className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-zinc-900 dark:text-white">{activeTrips}</p>
          <p className="text-xs text-zinc-500 font-medium">Active Monitoring</p>
        </div>
      </div>

      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4 shadow-sm flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-amber-50 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-zinc-900 dark:text-white">{tripsAtRisk}</p>
          <p className="text-xs text-zinc-500 font-medium">Trips At Risk</p>
        </div>
      </div>

      <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl p-4 shadow-sm flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0">
          <CheckCircle2 className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-zinc-900 dark:text-white">{recoveredTrips}</p>
          <p className="text-xs text-zinc-500 font-medium">Recoveries Done</p>
        </div>
      </div>
    </div>
  );
}
