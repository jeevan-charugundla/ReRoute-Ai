// ============================================================
// FlightStatusCard — rich flight display with airline name,
// cities, scheduled vs estimated times, and data source badge
// ============================================================
"use client";

import type { FlightSegment } from "@/types/reroute";
import { formatTime } from "@/lib/formatters";
import DataSourceBadge from "./DataSourceBadge";

interface FlightStatusCardProps {
  flight: FlightSegment;
  isLast?: boolean;
}

export default function FlightStatusCard({
  flight,
  isLast = false,
}: FlightStatusCardProps) {
  const isDelayed = flight.delay_minutes > 0;
  const isCancelled = flight.status === "CANCELLED";
  const isRebooked = flight.status === "REBOOKED";
  const isMissed = flight.status === "CONNECTION_MISSED";

  const originDisplay = flight.origin_city
    ? `${flight.origin_city} (${flight.origin})`
    : flight.origin;
  const destinationDisplay = flight.destination_city
    ? `${flight.destination_city} (${flight.destination})`
    : flight.destination;

  return (
    <div
      className={`relative flex flex-col gap-3 ${
        !isLast ? "pb-4 mb-2 border-b border-zinc-100 dark:border-zinc-800" : ""
      }`}
    >
      {/* Top row: airline + flight number + status badge */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          {/* Airline name + flight number */}
          <div>
            {flight.airline_name && (
              <p className="text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
                {flight.airline_name}
              </p>
            )}
            <p className="text-base font-bold">{flight.flight_number}</p>
          </div>

          <FlightStatusChip status={flight.status} />
        </div>

        <DataSourceBadge source={flight.data_source || "DEMO"} />
      </div>

      {/* Route */}
      <div className="flex items-center gap-3">
        <div className="text-center min-w-[60px]">
          <p className="text-xl font-bold">{flight.origin}</p>
          {flight.origin_city && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {flight.origin_city}
            </p>
          )}
        </div>

        <div className="flex-1 flex items-center gap-1">
          <div className="h-px bg-zinc-300 dark:bg-zinc-600 flex-1" />
          <svg
            className="text-zinc-400 shrink-0"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z" />
          </svg>
          <div className="h-px bg-zinc-300 dark:bg-zinc-600 flex-1" />
        </div>

        <div className="text-center min-w-[60px]">
          <p className="text-xl font-bold">{flight.destination}</p>
          {flight.destination_city && (
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {flight.destination_city}
            </p>
          )}
        </div>
      </div>

      {/* Times */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-2">
          <p className="text-xs text-zinc-500 mb-0.5">Departure</p>
          <p className="font-semibold">
            {formatTime(flight.estimated_departure || flight.scheduled_departure)}
          </p>
          {flight.estimated_departure !== flight.scheduled_departure &&
            flight.scheduled_departure && (
              <p className="text-xs text-zinc-400 line-through">
                Sched: {formatTime(flight.scheduled_departure)}
              </p>
            )}
        </div>
        <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-2">
          <p className="text-xs text-zinc-500 mb-0.5">Arrival</p>
          <p
            className={`font-semibold ${
              isDelayed ? "text-amber-600 dark:text-amber-400" : ""
            }`}
          >
            {formatTime(flight.estimated_arrival || flight.scheduled_arrival)}
          </p>
          {flight.estimated_arrival !== flight.scheduled_arrival &&
            flight.scheduled_arrival && (
              <p className="text-xs text-zinc-400 line-through">
                Sched: {formatTime(flight.scheduled_arrival)}
              </p>
            )}
        </div>
      </div>

      {/* Delay banner */}
      {isDelayed && !isCancelled && (
        <div className="flex items-center gap-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg px-3 py-1.5 text-sm">
          <span className="text-amber-600 dark:text-amber-400 font-semibold">
            +{flight.delay_minutes} min delay
          </span>
        </div>
      )}

      {/* Terminal / Gate */}
      {(flight.terminal || flight.gate) && (
        <div className="flex gap-3 text-xs text-zinc-500">
          {flight.terminal && (
            <span>Terminal: <strong>{flight.terminal}</strong></span>
          )}
          {flight.gate && (
            <span>Gate: <strong>{flight.gate}</strong></span>
          )}
        </div>
      )}

      {/* Last checked */}
      {flight.last_status_check && (
        <p className="text-xs text-zinc-400">
          Last checked: {new Date(flight.last_status_check).toLocaleTimeString()}
        </p>
      )}
    </div>
  );
}

function FlightStatusChip({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    CONFIRMED: {
      label: "On Time",
      className:
        "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    },
    DELAYED: {
      label: "Delayed",
      className:
        "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
    },
    CANCELLED: {
      label: "Cancelled",
      className:
        "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
    REBOOKED: {
      label: "Rebooked",
      className:
        "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
    },
    CONNECTION_MISSED: {
      label: "Missed",
      className:
        "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
    },
    SCHEDULED: {
      label: "Scheduled",
      className:
        "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
    },
  };

  const c = config[status] || {
    label: status,
    className: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  };

  return (
    <span
      className={`px-2 py-0.5 rounded-full text-xs font-semibold ${c.className}`}
    >
      {c.label}
    </span>
  );
}
