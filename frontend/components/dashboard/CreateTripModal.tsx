"use client";

import { useState } from "react";
import { Plus, X, Calendar, MapPin, Building, Car, Loader2 } from "lucide-react";
import { createTrip } from "@/lib/api";
import type { Trip } from "@/types/reroute";

interface CreateTripModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTripCreated: (trip: Trip) => void;
}

export default function CreateTripModal({ isOpen, onClose, onTripCreated }: CreateTripModalProps) {
  const [tripName, setTripName] = useState("");
  const [destination, setDestination] = useState("");
  const [startDate, setStartDate] = useState(new Date().toISOString().split("T")[0]);
  const [endDate, setEndDate] = useState(
    new Date(Date.now() + 6 * 24 * 3600 * 1000).toISOString().split("T")[0]
  );
  const [hotelName, setHotelName] = useState("");
  const [transferPickup, setTransferPickup] = useState("");
  const [transferDrop, setTransferDrop] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tripName.trim() || !destination.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const res = await createTrip({
        trip_name: tripName.trim(),
        destination: destination.trim(),
        start_date: startDate,
        end_date: endDate,
        hotel_name: hotelName.trim() || undefined,
        transfer_pickup: transferPickup.trim() || undefined,
        transfer_drop: transferDrop.trim() || undefined,
      });

      onTripCreated(res.trip);
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.detail || "Failed to create trip.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg p-6 text-white shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-zinc-400 hover:text-white p-1 rounded-lg transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h2 className="text-lg font-bold text-white mb-1 flex items-center gap-2">
          <Plus className="w-5 h-5 text-indigo-400" />
          Create New Trip
        </h2>
        <p className="text-xs text-zinc-400 mb-5">
          Define itinerary dates and optional hotel/transfer details.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-950/40 border border-red-800 rounded-xl text-xs text-red-400">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
              Trip Name *
            </label>
            <input
              type="text"
              placeholder="e.g. Business Summit in Singapore"
              value={tripName}
              onChange={(e) => setTripName(e.target.value)}
              className="w-full px-3.5 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                Destination *
              </label>
              <div className="relative">
                <MapPin className="w-4 h-4 text-zinc-500 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Singapore"
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  className="w-full pl-9 pr-3.5 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
                Start Date *
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3.5 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-1">
              End Date *
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-3.5 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>

          <div className="pt-2 border-t border-zinc-800 space-y-3">
            <p className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
              Optional Recovery Integrations
            </p>

            <div>
              <label className="block text-xs font-medium text-zinc-400 mb-1 flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-zinc-400" />
                Hotel Name
              </label>
              <input
                type="text"
                placeholder="e.g. Marina Bay Sands"
                value={hotelName}
                onChange={(e) => setHotelName(e.target.value)}
                className="w-full px-3.5 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1 flex items-center gap-1.5">
                  <Car className="w-3.5 h-3.5 text-zinc-400" />
                  Pickup Point
                </label>
                <input
                  type="text"
                  placeholder="Changi Airport T3"
                  value={transferPickup}
                  onChange={(e) => setTransferPickup(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-zinc-400 mb-1">Dropoff Location</label>
                <input
                  type="text"
                  placeholder="Hotel Lobby"
                  value={transferDrop}
                  onChange={(e) => setTransferDrop(e.target.value)}
                  className="w-full px-3.5 py-2 text-sm bg-zinc-800 border border-zinc-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-zinc-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 px-5 py-2 text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl transition-colors disabled:opacity-50"
            >
              {loading && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {loading ? "Creating..." : "Save Trip"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
