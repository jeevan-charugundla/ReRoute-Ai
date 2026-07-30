"use client";

import type { RecoveryOption } from "@/types/reroute";
import { formatTime, formatCurrency } from "@/lib/formatters";

interface SelectedFlightProps {
  option: RecoveryOption;
  bookingReference?: string;
}

export default function SelectedFlight({ option, bookingReference }: SelectedFlightProps) {
  return (
    <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-2xl p-6">
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-300 uppercase tracking-wider mb-4">
        Selected Recovery Flight
      </h3>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-3xl font-bold">{option.flight_number}</p>
          <p className="text-blue-600 dark:text-blue-400 mt-1">
            {option.origin} ? {option.destination}
          </p>
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold">
            {formatTime(option.departure)} ? {formatTime(option.arrival)}
          </p>
          <p className="text-sm text-blue-600 dark:text-blue-400 mt-1">
            Recovery Score: {option.recovery_score}/100
          </p>
        </div>
      </div>
      {bookingReference && (
        <div className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-800">
          <p className="text-sm text-blue-600 dark:text-blue-400">
            Booking Reference
          </p>
          <p className="font-mono font-semibold">{bookingReference}</p>
        </div>
      )}
    </div>
  );
}
