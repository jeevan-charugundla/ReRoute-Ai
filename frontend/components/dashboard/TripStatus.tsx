"use client";

import type { TripResponse } from "@/types/reroute";

interface TripStatusProps {
  tripData: TripResponse | null;
  loading: boolean;
}

export default function TripStatus({ tripData, loading }: TripStatusProps) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    );
  }

  if (!tripData) {
    return (
      <div className="flex items-center justify-center py-12 text-zinc-500">
        No trip data available
      </div>
    );
  }

  const hasRecovery = tripData.recovery_plans.length > 0;
  const latestPlan = tripData.recovery_plans[0];

  return (
    <div className="space-y-6">
      {/* Recovery Plan Summary */}
      {hasRecovery && latestPlan && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-2xl p-6">
          <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-300 uppercase tracking-wider mb-2">
            Recovery Plan
          </h3>
          <div className="flex items-center gap-4">
            <div>
              <p className="text-sm text-blue-600 dark:text-blue-400">Plan ID</p>
              <p className="font-mono text-sm">{latestPlan.plan_id}</p>
            </div>
            <div>
              <p className="text-sm text-blue-600 dark:text-blue-400">Selected Flight</p>
              <p className="font-semibold">{latestPlan.selected_flight}</p>
            </div>
            <div>
              <p className="text-sm text-blue-600 dark:text-blue-400">Recovery Score</p>
              <p className="font-semibold">{latestPlan.recovery_score}/100</p>
            </div>
            <div>
              <p className="text-sm text-blue-600 dark:text-blue-400">Additional Cost</p>
              <p className="font-semibold">?{latestPlan.additional_cost.toLocaleString()}</p>
            </div>
          </div>
        </div>
      )}

      {/* Audit Logs */}
      {tripData.audit_logs.length > 0 && (
        <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
          <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
            Activity Log
          </h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {tripData.audit_logs.map((log) => (
              <div key={log.id} className="text-sm border-b border-zinc-100 dark:border-zinc-800 pb-2 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-zinc-700 dark:text-zinc-300">
                    {log.event_type}
                  </span>
                  <span className="text-xs text-zinc-400">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-zinc-600 dark:text-zinc-400 mt-1">{log.message}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
