"use client";

import { useState } from "react";
import { Search, Loader2, Plane, Plus, CheckCircle2, AlertCircle } from "lucide-react";
import { getFlightStatus, addFlightToTrip } from "@/lib/api";
import type { FlightStatusResponse, FlightSegment } from "@/types/reroute";
import DataSourceBadge from "./DataSourceBadge";

interface AddFlightCardProps {
  tripId: string;
  onFlightAdded?: (segment: FlightSegment) => void;
}

export default function AddFlightCard({ tripId, onFlightAdded }: AddFlightCardProps) {
  const [flightNumber, setFlightNumber] = useState("");
  const [travelDate, setTravelDate] = useState(new Date().toISOString().split("T")[0]);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<FlightStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!flightNumber.trim()) return;

    setLoading(true);
    setError(null);
    setPreview(null);

    try {
      const res = await getFlightStatus(flightNumber.trim(), travelDate);
      setPreview(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to fetch live flight details.");
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!preview) return;
    setAdding(true);
    try {
      const res = await addFlightToTrip(tripId, {
        flight_number: preview.flight_number,
        travel_date: travelDate,
      });
      if (onFlightAdded) {
        onFlightAdded(res.segment);
      }
      setPreview(null);
      setFlightNumber("");
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to add flight segment to trip.");
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-bold text-zinc-900 dark:text-white flex items-center gap-2">
            <Plane className="w-4 h-4 text-indigo-500" />
            Add Flight to Monitor
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            Query live AeroDataBox flight data and attach segment to active trip.
          </p>
        </div>
      </div>

      <form onSubmit={handleSearch} className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
        <div>
          <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">
            Flight Number
          </label>
          <input
            type="text"
            placeholder="e.g. EK527"
            value={flightNumber}
            onChange={(e) => setFlightNumber(e.target.value.toUpperCase())}
            className="w-full px-3.5 py-2 text-sm bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 uppercase font-mono font-bold"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-1">
            Travel Date
          </label>
          <input
            type="date"
            value={travelDate}
            onChange={(e) => setTravelDate(e.target.value)}
            className="w-full px-3.5 py-2 text-sm bg-zinc-50 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        <div className="flex items-end">
          <button
            type="submit"
            disabled={loading || !flightNumber.trim()}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? "Fetching..." : "Find Flight"}
          </button>
        </div>
      </form>

      {error && (
        <div className="flex items-center gap-2 text-xs text-red-600 bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 p-3 rounded-xl mb-4">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Flight Lookup Preview Confirmation Card */}
      {preview && (
        <div className="bg-indigo-50/50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800/60 rounded-xl p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                {preview.airline_name || preview.airline_code}
              </span>
              <span className="text-base font-bold text-zinc-900 dark:text-white font-mono">
                {preview.flight_number}
              </span>
            </div>
            <DataSourceBadge source={preview.data_source} />
          </div>

          <div className="flex items-center justify-between text-sm py-1">
            <div>
              <p className="text-lg font-bold text-zinc-900 dark:text-white">{preview.origin_iata}</p>
              <p className="text-xs text-zinc-500">{preview.origin_city || preview.origin_name || "Origin"}</p>
            </div>
            <div className="text-center">
              <Plane className="w-4 h-4 text-zinc-400 mx-auto" />
              <span className="text-[10px] text-zinc-400 font-medium">Direct</span>
            </div>
            <div className="text-right">
              <p className="text-lg font-bold text-zinc-900 dark:text-white">{preview.destination_iata}</p>
              <p className="text-xs text-zinc-500">{preview.destination_city || preview.destination_name || "Destination"}</p>
            </div>
          </div>

          <div className="flex items-center justify-between text-xs text-zinc-500 pt-2 border-t border-indigo-100 dark:border-indigo-900/40">
            <span>Dep: <strong>{preview.scheduled_departure ? new Date(preview.scheduled_departure).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "TBD"}</strong></span>
            <span>Arr: <strong>{preview.scheduled_arrival ? new Date(preview.scheduled_arrival).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "TBD"}</strong></span>
            <span className="px-2 py-0.5 bg-zinc-200 dark:bg-zinc-800 rounded font-semibold text-[10px] uppercase text-zinc-700 dark:text-zinc-300">
              {preview.status}
            </span>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              onClick={() => setPreview(null)}
              className="px-3 py-1.5 text-xs text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-white"
            >
              Cancel
            </button>
            <button
              onClick={handleAdd}
              disabled={adding}
              className="flex items-center gap-1.5 px-4 py-1.5 text-xs font-semibold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              {adding ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Plus className="w-3.5 h-3.5" />}
              {adding ? "Adding..." : "Add to Trip"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
