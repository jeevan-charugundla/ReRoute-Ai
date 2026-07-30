"use client";

import type { Trip, FlightSegment } from "@/types/reroute";
import { formatDate, formatTime } from "@/lib/formatters";

interface TripHeroProps {
  trip: Trip;
  flights: FlightSegment[];
}

export default function TripHero({ trip, flights }: TripHeroProps) {
  const firstFlight = flights[0];
  const lastFlight = flights[flights.length - 1];

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">{trip.trip_name}</h2>
          <p className="text-zinc-500 mt-1">
            {formatDate(trip.start_date)} — {formatDate(trip.end_date)}
          </p>
        </div>
        <TripStatusBadge status={trip.status} />
      </div>

      {firstFlight && lastFlight && (
        <div className="flex items-center gap-4 overflow-x-auto pb-2">
          <div className="flex flex-col items-center min-w-[80px]">
            <span className="text-lg font-semibold">{firstFlight.origin}</span>
            <span className="text-xs text-zinc-500">
              {formatTime(firstFlight.scheduled_departure)}
            </span>
          </div>

          <div className="flex-1 flex items-center gap-2 min-w-[200px]">
            <div className="h-px bg-zinc-300 dark:bg-zinc-700 flex-1" />
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-zinc-400"
            >
              <path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z" />
            </svg>
            <div className="h-px bg-zinc-300 dark:bg-zinc-700 flex-1" />
          </div>

          <div className="flex flex-col items-center min-w-[80px]">
            <span className="text-lg font-semibold">{lastFlight.destination}</span>
            <span className="text-xs text-zinc-500">
              {formatTime(lastFlight.scheduled_arrival)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function TripStatusBadge({ status }: { status: string }) {
  const config: Record<
    string,
    { label: string; className: string }
  > = {
    HEALTHY: {
      label: "HEALTHY",
      className:
        "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    },
    DELAYED_BUT_SAFE: {
      label: "DELAYED",
      className:
        "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    },
    RECOVERY_REQUIRED: {
      label: "DISRUPTION DETECTED",
      className:
        "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
    RECOVERED: {
      label: "RECOVERED",
      className:
        "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    },
    AWAITING_APPROVAL: {
      label: "AWAITING APPROVAL",
      className:
        "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    },
    ESCALATED: {
      label: "ESCALATED",
      className:
        "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
  };

  const c = config[status] || config.HEALTHY;

  return (
    <span
      className={`px-3 py-1 rounded-full text-xs font-semibold ${c.className}`}
    >
      {c.label}
    </span>
  );
}
