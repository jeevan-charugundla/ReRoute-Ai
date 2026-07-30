"use client";

import type { FlightSegment } from "@/types/reroute";
import { formatTime } from "@/lib/formatters";

interface FlightTimelineProps {
  flights: FlightSegment[];
}

export default function FlightTimeline({ flights }: FlightTimelineProps) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
        Flight Itinerary
      </h3>
      <div className="space-y-4">
        {flights.map((flight, index) => (
          <div
            key={flight.id}
            className={`flex items-center gap-4 ${
              index !== flights.length - 1 ? "pb-4 border-b border-zinc-100 dark:border-zinc-800" : ""
            }`}
          >
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <span className="text-lg font-semibold">{flight.flight_number}</span>
                <FlightStatusBadge status={flight.status} />
              </div>
              <div className="flex items-center gap-4 mt-1 text-sm text-zinc-600 dark:text-zinc-400">
                <span className="font-medium">{flight.origin}</span>
                <span className="text-zinc-400">?</span>
                <span className="font-medium">{flight.destination}</span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium">
                {formatTime(flight.estimated_departure)}
              </div>
              <div className="text-xs text-zinc-500">departure</div>
            </div>
            <div className="text-right">
              <div className="text-sm font-medium">
                {formatTime(flight.estimated_arrival)}
              </div>
              <div className="text-xs text-zinc-500">arrival</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FlightStatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    CONFIRMED: {
      label: "CONFIRMED",
      className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    },
    DELAYED: {
      label: "DELAYED",
      className: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    },
    REBOOKED: {
      label: "REBOOKED",
      className: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    },
    CONNECTION_MISSED: {
      label: "MISSED",
      className: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
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
