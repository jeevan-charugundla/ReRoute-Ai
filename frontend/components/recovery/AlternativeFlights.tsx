"use client";

import type { RecoveryOption, RejectedOption } from "@/types/reroute";
import { formatTime, formatCurrency } from "@/lib/formatters";
import { CheckCircle2 } from "lucide-react";

interface AlternativeFlightsProps {
  validOptions: RecoveryOption[];
  rejectedOptions: RejectedOption[];
}

export default function AlternativeFlights({
  validOptions,
  rejectedOptions,
}: AlternativeFlightsProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider">
        Alternative Flights
      </h3>

      {/* Valid Options */}
      <div className="grid gap-4">
        {validOptions.map((option) => (
          <div
            key={option.flight_number}
            className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm"
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold">{option.flight_number}</span>
                  {option.rank === 1 && (
                    <span className="px-2 py-0.5 bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded text-xs font-semibold">
                      BEST OPTION
                    </span>
                  )}
                </div>
                <p className="text-sm text-zinc-600 dark:text-zinc-400 mt-1">
                  {option.origin} ? {option.destination}
                </p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {option.recovery_score}
                </p>
                <p className="text-xs text-zinc-500">recovery score</p>
              </div>
            </div>

            <div className="flex items-center gap-6 text-sm mb-4">
              <div>
                <span className="text-zinc-500">Departure</span>
                <p className="font-medium">{formatTime(option.departure)}</p>
              </div>
              <div>
                <span className="text-zinc-500">Arrival</span>
                <p className="font-medium">{formatTime(option.arrival)}</p>
              </div>
              <div>
                <span className="text-zinc-500">Extra Cost</span>
                <p className="font-medium">
                  {option.additional_cost === 0 ? (
                    <span className="text-emerald-600">?0</span>
                  ) : (
                    formatCurrency(option.additional_cost)
                  )}
                </p>
              </div>
              <div>
                <span className="text-zinc-500">Cabin</span>
                <p className="font-medium">{option.cabin}</p>
              </div>
            </div>

            {option.why.length > 0 && (
              <div className="space-y-1">
                {option.why.map((reason, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                    <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    {reason}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Rejected Options */}
      {rejectedOptions.length > 0 && (
        <details className="bg-zinc-50 dark:bg-zinc-800/50 rounded-2xl border border-zinc-200 dark:border-zinc-700 p-4">
          <summary className="cursor-pointer text-sm font-medium text-zinc-600 dark:text-zinc-400">
            {rejectedOptions.length} alternatives rejected
          </summary>
          <div className="mt-3 space-y-2">
            {rejectedOptions.map((opt) => (
              <div
                key={opt.flight_number}
                className="flex items-center justify-between text-sm"
              >
                <span className="font-medium">{opt.flight_number}</span>
                <span className="text-zinc-500">{opt.reasons.join(", ")}</span>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
