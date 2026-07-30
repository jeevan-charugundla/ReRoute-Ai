"use client";

import { useState } from "react";
import { Clock, ShieldCheck, AlertTriangle, AlertCircle, RefreshCw } from "lucide-react";
import type { FlightSegment } from "@/types/reroute";

interface ConnectionCardProps {
  segments: FlightSegment[];
  minBufferMinutes?: number;
}

export default function ConnectionCard({
  segments,
  minBufferMinutes = 75,
}: ConnectionCardProps) {
  if (!segments || segments.length < 2) {
    return (
      <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm">
        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-2">
          Upcoming Connection
        </h3>
        <p className="text-xs text-zinc-400">Direct flight — no layover connection required.</p>
      </div>
    );
  }

  const prev = segments[0];
  const next = segments[1];

  const arrStr = prev.estimated_arrival || prev.scheduled_arrival;
  const depStr = next.estimated_departure || next.scheduled_departure;

  let bufferMinutes: number | null = null;
  if (arrStr && depStr) {
    try {
      const arr = new Date(arrStr).getTime();
      const dep = new Date(depStr).getTime();
      bufferMinutes = Math.round((dep - arr) / (1000 * 60));
    } catch {
      bufferMinutes = null;
    }
  }

  const isImpossible = bufferMinutes !== null && bufferMinutes < 0;
  const isAtRisk = bufferMinutes !== null && bufferMinutes >= 0 && bufferMinutes < minBufferMinutes;
  const isHealthy = bufferMinutes !== null && bufferMinutes >= minBufferMinutes;

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">
          Upcoming Connection
        </h3>
        {isHealthy && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800">
            <ShieldCheck className="w-3.5 h-3.5" />
            Connection Safe
          </span>
        )}
        {isAtRisk && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800">
            <AlertTriangle className="w-3.5 h-3.5" />
            Connection At Risk
          </span>
        )}
        {isImpossible && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/40 dark:text-red-400 dark:border-red-800">
            <AlertCircle className="w-3.5 h-3.5" />
            Connection Missed
          </span>
        )}
      </div>

      <div className="flex items-center justify-between bg-zinc-50 dark:bg-zinc-800/50 p-3 rounded-xl">
        <div className="text-center">
          <p className="text-xs text-zinc-500">Inbound</p>
          <p className="font-bold text-sm text-zinc-900 dark:text-white">{prev.flight_number}</p>
          <p className="text-[11px] text-zinc-400">{prev.destination}</p>
        </div>

        <div className="flex flex-col items-center">
          <Clock className="w-4 h-4 text-zinc-400 mb-1" />
          <span
            className={`text-sm font-bold ${
              isImpossible
                ? "text-red-600 dark:text-red-400"
                : isAtRisk
                ? "text-amber-600 dark:text-amber-400"
                : "text-emerald-600 dark:text-emerald-400"
            }`}
          >
            {bufferMinutes !== null ? `${bufferMinutes} min` : "N/A"}
          </span>
          <span className="text-[10px] text-zinc-400">Layover Buffer</span>
        </div>

        <div className="text-center">
          <p className="text-xs text-zinc-500">Outbound</p>
          <p className="font-bold text-sm text-zinc-900 dark:text-white">{next.flight_number}</p>
          <p className="text-[11px] text-zinc-400">{next.origin}</p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-zinc-50 dark:bg-zinc-800/30 p-2 rounded-lg border border-zinc-100 dark:border-zinc-800">
          <p className="text-[10px] text-zinc-500">Safe Minimum</p>
          <p className="font-semibold text-zinc-800 dark:text-zinc-200">{minBufferMinutes} min</p>
        </div>
        <div className="bg-zinc-50 dark:bg-zinc-800/30 p-2 rounded-lg border border-zinc-100 dark:border-zinc-800">
          <p className="text-[10px] text-zinc-500">Transfer Hub</p>
          <p className="font-semibold text-zinc-800 dark:text-zinc-200">{prev.destination}</p>
        </div>
      </div>
    </div>
  );
}
