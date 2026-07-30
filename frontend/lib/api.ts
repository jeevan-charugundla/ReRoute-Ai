import axios from "axios";
import type {
  TripResponse,
  DisruptionResponse,
  RecoveryPlanResponse,
  NotificationsResponse,
  FlightStatusResponse,
  ProviderConfig,
  TripMonitoringResponse,
  TripListItem,
  CreateTripPayload,
  AddFlightPayload,
  Trip,
  FlightSegment,
} from "@/types/reroute";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000",
});

// ============================================================
// Demo Setup
// ============================================================

export async function setupDemo(): Promise<{ message: string; trip_id: string }> {
  const res = await api.post("/api/demo/setup");
  return res.data;
}

// ============================================================
// Demo Reset
// ============================================================

export async function resetDemo(): Promise<{ message: string }> {
  const res = await api.post("/api/demo/reset");
  return res.data;
}

// ============================================================
// Get Trip
// ============================================================

export async function getTrip(tripId: string): Promise<TripResponse> {
  const res = await api.get(`/api/trips/${tripId}`);
  return res.data;
}

// ============================================================
// Trigger Disruption
// ============================================================

export async function triggerDisruption(
  tripId: string,
  flight: string,
  delayMinutes: number
): Promise<DisruptionResponse> {
  const res = await api.post("/api/demo/disruption", {
    trip_id: tripId,
    flight,
    delay_minutes: delayMinutes,
  });
  return res.data;
}

// ============================================================
// Get Recovery Plan
// ============================================================

export async function getRecoveryPlan(
  planId: string
): Promise<RecoveryPlanResponse> {
  const res = await api.get(`/api/recovery/${planId}`);
  return res.data;
}

// ============================================================
// Get Notifications
// ============================================================

export async function getNotifications(
  tripId: string
): Promise<NotificationsResponse> {
  const res = await api.get(`/api/notifications/${tripId}`);
  return res.data;
}

// ============================================================
// Get Flight Status (real or demo via backend provider layer)
// ============================================================

export async function getFlightStatus(
  flightNumber: string,
  date: string,
  carrier?: string
): Promise<FlightStatusResponse> {
  const params: Record<string, string> = {
    flight_number: flightNumber,
    date,
  };
  if (carrier) params.carrier = carrier;
  const res = await api.get("/api/flights/status", { params });
  return res.data;
}

// ============================================================
// Check Trip (real-data monitoring endpoint)
// ============================================================

export async function checkTrip(tripId: string): Promise<TripMonitoringResponse> {
  const res = await api.post(`/api/trips/${tripId}/check`);
  return res.data;
}

// ============================================================
// Get All Trips
// ============================================================

export async function getTrips(): Promise<{ trips: TripListItem[] }> {
  const res = await api.get("/api/trips");
  return res.data;
}

// ============================================================
// Create Trip
// ============================================================

export async function createTrip(
  payload: CreateTripPayload
): Promise<{ message: string; trip_id: string; trip: Trip }> {
  const res = await api.post("/api/trips", payload);
  return res.data;
}

// ============================================================
// Add Flight Segment to Trip
// ============================================================

export async function addFlightToTrip(
  tripId: string,
  payload: AddFlightPayload
): Promise<{ message: string; segment: FlightSegment }> {
  const res = await api.post(`/api/trips/${tripId}/flights`, payload);
  return res.data;
}

// ============================================================
// Remove Flight Segment
// ============================================================

export async function deleteFlightSegment(
  tripId: string,
  segmentId: number
): Promise<{ message: string }> {
  const res = await api.delete(`/api/trips/${tripId}/flights/${segmentId}`);
  return res.data;
}

// ============================================================
// Approve Recovery Plan
// ============================================================

export async function approveRecovery(
  planId: string,
  approved: boolean
): Promise<{ message: string }> {
  const res = await api.post(`/api/recovery/${planId}/approve`, { approved });
  return res.data;
}

// ============================================================
// Get Provider Config (safe — no secrets)
// ============================================================

export async function getProviderConfig(): Promise<ProviderConfig> {
  const res = await api.get("/api/config/provider");
  return res.data;
}

