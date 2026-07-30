"use client";

import type { RecoveryOption } from "@/types/reroute";
import { CheckCircle2 } from "lucide-react";

interface DecisionExplanationProps {
  option: RecoveryOption;
}

export default function DecisionExplanation({ option }: DecisionExplanationProps) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
        Why ReRoute selected {option.flight_number}
      </h3>
      <div className="space-y-2">
        {option.why.map((reason, index) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            <span className="text-zinc-700 dark:text-zinc-300">{reason}</span>
          </div>
        ))}
      </div>

      {option.penalties.length > 0 && (
        <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-700">
          <p className="text-sm font-medium text-zinc-500 mb-2">Considerations</p>
          <div className="space-y-1">
            {option.penalties.map((penalty, index) => (
              <p key={index} className="text-sm text-zinc-600 dark:text-zinc-400">
                {penalty}
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="mt-4 pt-4 border-t border-zinc-200 dark:border-zinc-700">
        <p className="text-sm text-zinc-500 mb-1">Recovery Score</p>
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-zinc-200 dark:bg-zinc-700 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full"
              style={{ width: `${option.recovery_score}%` }}
            />
          </div>
          <span className="text-2xl font-bold text-blue-600 dark:text-blue-400">
            {option.recovery_score}
          </span>
        </div>
      </div>
    </div>
  );
}
