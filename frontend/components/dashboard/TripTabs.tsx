"use client";

import { useState } from "react";
import { Plus } from "lucide-react";
import type { TripListItem } from "@/types/reroute";
import DataSourceBadge from "./DataSourceBadge";

interface TripTabsProps {
  tripsList: TripListItem[];
  selectedTripId: string;
  onSelectTrip: (tripId: string) => void;
  onCreateTripClick: () => void;
}

export default function TripTabs({
  tripsList,
  selectedTripId,
  onSelectTrip,
  onCreateTripClick,
}: TripTabsProps) {
  const [tabFilter, setTabFilter] = useState<"all" | "active" | "past">("all");

  const nowStr = new Date().toISOString().split("T")[0];

  const filteredTrips = tripsList.filter((item) => {
    if (tabFilter === "active") {
      return item.trip.end_date >= nowStr || item.trip.status !== "RECOVERED";
    }
    if (tabFilter === "past") {
      return item.trip.end_date < nowStr && item.trip.status === "RECOVERED";
    }
    return true;
  });

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-5 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center gap-1 bg-zinc-100 dark:bg-zinc-800 p-1 rounded-xl w-fit">
          <button
            onClick={() => setTabFilter("all")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              tabFilter === "all"
                ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white shadow-sm"
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
            }`}
          >
            My Trips ({tripsList.length})
          </button>
          <button
            onClick={() => setTabFilter("active")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              tabFilter === "active"
                ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white shadow-sm"
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
            }`}
          >
            Upcoming Flights
          </button>
          <button
            onClick={() => setTabFilter("past")}
            className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              tabFilter === "past"
                ? "bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white shadow-sm"
                : "text-zinc-500 hover:text-zinc-900 dark:hover:text-white"
            }`}
          >
            Past Trips
          </button>
        </div>

        <button
          onClick={onCreateTripClick}
          className="flex items-center justify-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          Create New Trip
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filteredTrips.map(({ trip, segments_count, flights }) => {
          const isSelected = trip.trip_id === selectedTripId;
          const firstFlight = flights[0];
          const lastFlight = flights[flights.length - 1];

          return (
            <div
              key={trip.trip_id}
              onClick={() => onSelectTrip(trip.trip_id)}
              className={`cursor-pointer p-4 rounded-xl border transition-all ${
                isSelected
                  ? "bg-indigo-50/60 dark:bg-indigo-950/20 border-indigo-500/50 shadow-sm"
                  : "bg-zinc-50/50 dark:bg-zinc-800/40 border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div>
                  <h4 className="font-bold text-sm text-zinc-900 dark:text-white">{trip.trip_name}</h4>
                  <p className="text-xs text-zinc-500">
                    {trip.start_date} → {trip.end_date} • ID: {trip.trip_id}
                  </p>
                </div>
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                    trip.status === "HEALTHY"
                      ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400"
                      : trip.status === "RECOVERED"
                      ? "bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-400"
                      : "bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400"
                  }`}
                >
                  {trip.status}
                </span>
              </div>

              {flights.length > 0 && (
                <div className="mt-3 pt-2 border-t border-zinc-200/60 dark:border-zinc-800/60 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2 font-semibold">
                    <span>{firstFlight.origin}</span>
                    <span className="text-zinc-400">→</span>
                    {flights.length > 1 && (
                      <>
                        <span className="text-zinc-500 text-[10px]">({flights.length - 1} layover)</span>
                        <span className="text-zinc-400">→</span>
                      </>
                    )}
                    <span>{lastFlight.destination}</span>
                  </div>
                  <DataSourceBadge source={firstFlight.data_source || "DEMO"} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
