"use client";

import type { HotelBooking } from "@/types/reroute";
import { formatDate } from "@/lib/formatters";

interface HotelCardProps {
  hotel: HotelBooking | null;
}

export default function HotelCard({ hotel }: HotelCardProps) {
  if (!hotel) return null;

  return (
    <div className="bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 p-6 shadow-sm">
      <h3 className="text-sm font-semibold text-zinc-500 uppercase tracking-wider mb-4">
        Hotel
      </h3>
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-semibold text-lg">{hotel.hotel_name}</span>
          <HotelStatusBadge status={hotel.status} />
        </div>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          {hotel.city}
        </p>
        <div className="text-sm text-zinc-600 dark:text-zinc-400">
          <span className="font-medium">Check-in:</span> {formatDate(hotel.check_in_date)}
        </div>
        <div className="text-sm text-zinc-600 dark:text-zinc-400">
          <span className="font-medium">Check-out:</span> {formatDate(hotel.check_out_date)}
        </div>
      </div>
    </div>
  );
}

function HotelStatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    CONFIRMED: {
      label: "CONFIRMED",
      className: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    },
    LATE_CHECKIN_CONFIRMED: {
      label: "LATE CHECK-IN CONFIRMED",
      className: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
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
