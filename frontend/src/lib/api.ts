import axios from "axios";
import type {
  TripResponse,
  DisruptionResponse,
  RecoveryPlanResponse,
  NotificationsResponse,
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
