"use client";

import type { FlightSegment } from "@/types/reroute";
import FlightStatusCard from "./FlightStatusCard";

interface FlightTimelineProps {
  flights: FlightSegment[];
}

export default function FlightTimeline({ flights }: FlightTimelineProps) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
        Flight Itinerary
      </h3>
      <div className="space-y-2">
        {flights.map((flight, index) => (
          <FlightStatusCard
            key={flight.id}
            flight={flight}
            isLast={index === flights.length - 1}
          />
        ))}
      </div>
    </div>
  );
}
