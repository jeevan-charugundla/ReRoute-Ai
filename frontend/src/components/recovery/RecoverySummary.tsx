"use client";

import type { DisruptionResponse } from "@/types/reroute";
import { formatCurrency } from "@/lib/formatters";
import { CheckCircle2 } from "lucide-react";

interface RecoverySummaryProps {
  data: DisruptionResponse;
}

export default function RecoverySummary({ data }: RecoverySummaryProps) {
  return (
    <div className="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <CheckCircle2 className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
        <div>
          <h3 className="text-xl font-bold text-emerald-900 dark:text-emerald-100">
            Trip Recovered
          </h3>
          <p className="text-sm text-emerald-700 dark:text-emerald-300">
            ReRoute automatically repaired your itinerary.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div className="bg-white/50 dark:bg-emerald-900/20 rounded-xl p-4">
          <p className="text-sm text-emerald-600 dark:text-emerald-400 mb-1">
            New Flight
          </p>
          <p className="text-2xl font-bold">{data.decision.selected_flight}</p>
        </div>
        <div className="bg-white/50 dark:bg-emerald-900/20 rounded-xl p-4">
          <p className="text-sm text-emerald-600 dark:text-emerald-400 mb-1">
            Additional Cost
          </p>
          <p className="text-2xl font-bold">
            {formatCurrency(data.decision.additional_cost)}
          </p>
        </div>
      </div>

      <div className="space-y-2">
        <ExecutionRow
          label="Flight"
          value={`${data.execution.flight_rebooking} — ${data.decision.selected_flight}`}
        />
        <ExecutionRow
          label="Hotel"
          value={data.execution.hotel?.status || "Updated"}
        />
        <ExecutionRow
          label="Airport Transfer"
          value={data.execution.transfer?.status || "Rescheduled"}
        />
        <ExecutionRow
          label="Traveler"
          value={data.execution.notification}
        />
      </div>

      {data.execution.booking_reference && (
        <div className="mt-4 pt-4 border-t border-emerald-200 dark:border-emerald-800">
          <p className="text-sm text-emerald-600 dark:text-emerald-400">
            Booking Reference
          </p>
          <p className="font-mono font-semibold text-lg">
            {data.execution.booking_reference}
          </p>
        </div>
      )}
    </div>
  );
}

function ExecutionRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-emerald-700 dark:text-emerald-300">{label}</span>
      <span className="font-medium text-emerald-900 dark:text-emerald-100">{value}</span>
    </div>
  );
}
