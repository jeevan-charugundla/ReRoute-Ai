// ============================================================
// RefreshButton — calls /api/trips/{id}/check on the backend
// Includes cooldown to prevent rapid re-requests
// ============================================================
"use client";

import { useState, useCallback } from "react";
import { RefreshCw } from "lucide-react";
import type { TripMonitoringResponse } from "@/types/reroute";

interface RefreshButtonProps {
  tripId: string;
  onRefreshed?: (data: TripMonitoringResponse) => void;
  /** Minimum seconds between refreshes (default: 10) */
  cooldownSeconds?: number;
}

export default function RefreshButton({
  tripId,
  onRefreshed,
  cooldownSeconds = 10,
}: RefreshButtonProps) {
  const [loading, setLoading] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [cooldownUntil, setCooldownUntil] = useState<number>(0);
  const [warning, setWarning] = useState<string | null>(null);

  const secondsLeft = Math.max(
    0,
    Math.ceil((cooldownUntil - Date.now()) / 1000)
  );
  const isOnCooldown = secondsLeft > 0;

  const handleRefresh = useCallback(async () => {
    if (isOnCooldown || loading) return;

    setLoading(true);
    setWarning(null);

    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}/api/trips/${tripId}/check`,
        { method: "POST" }
      );

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const data: TripMonitoringResponse = await res.json();
      setLastChecked(new Date());
      setCooldownUntil(Date.now() + cooldownSeconds * 1000);

      // Show provider warning if demo fallback is active
      const warnings = data.flight_updates
        .map((u) => u.provider_warning)
        .filter(Boolean);
      if (warnings.length > 0) {
        setWarning(warnings[0] || null);
      }

      if (onRefreshed) {
        onRefreshed(data);
      }
    } catch (err) {
      console.error("Refresh failed:", err);
      setWarning("Status refresh failed. Check your connection.");
    } finally {
      setLoading(false);
    }
  }, [tripId, isOnCooldown, loading, cooldownSeconds, onRefreshed]);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-3">
        <button
          onClick={handleRefresh}
          disabled={loading || isOnCooldown}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-blue-50 text-blue-700 border border-blue-200 rounded-lg hover:bg-blue-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800 dark:hover:bg-blue-900/30"
        >
          <RefreshCw
            className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`}
          />
          {loading
            ? "Checking..."
            : isOnCooldown
            ? `Refresh (${secondsLeft}s)`
            : "Refresh Status"}
        </button>

        {lastChecked && (
          <span className="text-xs text-zinc-400">
            Last updated: {lastChecked.toLocaleTimeString()}
          </span>
        )}
      </div>

      {warning && (
        <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1">
          <span>⚠</span> {warning}
        </p>
      )}
    </div>
  );
}
