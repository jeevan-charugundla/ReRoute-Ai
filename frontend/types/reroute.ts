// ============================================================
// ReRoute AI — TypeScript Types
// ============================================================
// Fully typed to match all FastAPI response shapes.
// These match the Pydantic models in backend/main.py and
// services/flight_provider.py exactly.
// ============================================================

// ------------------------------------------------------------
// DATABASE MODEL TYPES
// (match SQLAlchemy models in backend/models.py)
// ------------------------------------------------------------

export interface Trip {
  id: number;
  trip_id: string;
  traveler_name: string;
  trip_name: string;
  destination: string;
  start_date: string;
  end_date: string;
  status: TripStatus;
}

export type TripStatus =
  | "HEALTHY"
  | "DELAYED_BUT_SAFE"
  | "RECOVERY_REQUIRED"
  | "AWAITING_APPROVAL"
  | "RECOVERED"
  | "ESCALATED"
  | string;

export interface FlightSegment {
  id: number;
  trip_id: string;
  flight_number: string;
  origin: string;
  destination: string;
  scheduled_departure: string;
  scheduled_arrival: string;
  estimated_departure: string;
  estimated_arrival: string;
  actual_departure: string | null;
  actual_arrival: string | null;
  status: FlightSegmentStatus;
  // v2.1 enrichment fields
  provider: string | null;
  data_source: DataSource;
  last_status_check: string | null;
  last_provider_update: string | null;
  delay_minutes: number;
  terminal: string | null;
  gate: string | null;
  airline_name: string | null;
  origin_city: string | null;
  destination_city: string | null;
}

export type FlightSegmentStatus =
  | "CONFIRMED"
  | "DELAYED"
  | "CANCELLED"
  | "REBOOKED"
  | "CONNECTION_MISSED"
  | string;

export type DataSource = "REAL" | "CACHE" | "DEMO" | string;

export interface HotelBooking {
  id: number;
  booking_id: string;
  trip_id: string;
  hotel_name: string;
  city: string;
  check_in_date: string;
  check_out_date: string;
  expected_arrival: string;
  status: string;
}

export interface Transfer {
  id: number;
  transfer_id: string;
  trip_id: string;
  pickup_location: string;
  drop_location: string;
  pickup_time: string;
  status: string;
}

export interface PolicyRule {
  id: number;
  trip_id: string;
  auto_rebook_limit: number;
  approval_limit: number;
  hotel_limit: number;
  allowed_cabin: string;
  alternative_airport_allowed: string;
}

export interface DisruptionEvent {
  id: number;
  disruption_id: string;
  trip_id: string;
  flight_number: string;
  disruption_type: string;
  delay_minutes: number;
  original_arrival: string;
  new_estimated_arrival: string;
  affected_flight: string;
  impact: string;
  recovery_required: string;
  status: string;
}

export interface RecoveryPlan {
  id: number;
  plan_id: string;
  trip_id: string;
  disruption_id: string;
  selected_flight: string;
  recovery_score: number;
  additional_cost: number;
  policy_decision: string;
  booking_reference: string | null;
  status: string;
  explanation: string;
}

export interface RecoveryAction {
  id: number;
  action_id: string;
  plan_id: string;
  trip_id: string;
  action_type: string;
  target: string;
  status: string;
  details: string;
}

export interface Notification {
  id: number;
  notification_id: string;
  trip_id: string;
  title: string;
  message: string;
  channel: string;
  status: string;
}

export interface AuditLog {
  id: number;
  audit_id: string;
  trip_id: string;
  event_type: string;
  message: string;
  created_at: string;
}

// ------------------------------------------------------------
// API RESPONSE TYPES
// ------------------------------------------------------------

export interface TripResponse {
  trip: Trip;
  flights: FlightSegment[];
  hotel: HotelBooking | null;
  transfer: Transfer | null;
  policy: PolicyRule | null;
  disruptions: DisruptionEvent[];
  recovery_plans: RecoveryPlan[];
  recovery_actions: RecoveryAction[];
  notifications: Notification[];
  audit_logs: AuditLog[];
}

// Recovery option in disruption response
export interface ScoreBreakdown {
  cost: number;
  arrival: number;
  airline: number;
  cabin: number;
  safety: number;
}

export interface RecoveryOption {
  flight_number: string;
  origin: string;
  destination: string;
  departure: string;
  arrival: string;
  additional_cost: number;
  available_seats: number;
  cabin: string;
  recovery_score: number;
  score_breakdown: ScoreBreakdown;
  why: string[];
  penalties: string[];
  connection_buffer_minutes: number;
  rank: number;
  // v2.1 fields
  airline_name?: string | null;
  data_source?: DataSource;
}

export interface RejectedOption {
  flight_number: string;
  reasons: string[];
}

export interface DisruptionInfo {
  detected: boolean;
  flight: string;
  delay_minutes: number;
  new_arrival: string;
}

export interface ImpactAnalysis {
  affected_flight: string;
  connection_buffer_minutes: number;
  impact: string;
  recovery_required: boolean;
}

export interface PolicyDecisionInfo {
  decision: "AUTO" | "APPROVAL_REQUIRED" | "ESCALATE" | string;
  reason: string;
}

export interface DecisionInfo {
  selected_flight: string;
  recovery_score: number;
  additional_cost: number;
  why: string[];
}

export interface ExecutionInfo {
  flight_rebooking: string;
  booking_reference: string | null;
  booking_mode: "SIMULATED" | string;
  hotel: {
    hotel: string;
    status: string;
    new_expected_arrival: string;
  } | null;
  transfer: {
    transfer_id: string;
    status: string;
    new_pickup_time: string;
  } | null;
  notification: string;
}

export interface DisruptionResponse {
  disruption: DisruptionInfo;
  impact_analysis: ImpactAnalysis;
  alternatives: {
    valid: RecoveryOption[];
    rejected: RejectedOption[];
  };
  decision: DecisionInfo;
  policy: PolicyDecisionInfo;
  execution: ExecutionInfo;
  recovery_plan: {
    plan_id: string;
    status: string;
  };
  trip_status: string;
}

export interface RecoveryPlanResponse {
  plan: RecoveryPlan;
  actions: RecoveryAction[];
}

export interface NotificationsResponse {
  count: number;
  notifications: Notification[];
}

// ------------------------------------------------------------
// FLIGHT PROVIDER TYPES (v2.1)
// ------------------------------------------------------------

export interface FlightStatusResponse {
  flight_number: string;
  airline_code: string;
  airline_name: string | null;
  origin_iata: string;
  origin_name: string | null;
  origin_city: string | null;
  origin_terminal: string | null;
  origin_gate: string | null;
  destination_iata: string;
  destination_name: string | null;
  destination_city: string | null;
  destination_terminal: string | null;
  destination_gate: string | null;
  scheduled_departure: string | null;
  estimated_departure: string | null;
  actual_departure: string | null;
  scheduled_arrival: string | null;
  estimated_arrival: string | null;
  actual_arrival: string | null;
  delay_minutes: number;
  status: string;
  data_source: DataSource;
  last_updated: string | null;
  provider_warning: string | null;
}

export interface ProviderConfig {
  provider_name: string;
  real_data_enabled: boolean;
  demo_fallback_enabled: boolean;
  cache_ttl_seconds: number;
  min_connection_minutes: number;
}

export interface TripMonitoringResponse {
  trip_id: string;
  monitoring: {
    status: string;
    data_source: DataSource;
    checked_at: string;
    provider: string;
  };
  flight_updates: Array<{
    flight_number: string;
    airline_name: string | null;
    origin: string;
    destination: string;
    scheduled_departure: string;
    estimated_departure: string;
    scheduled_arrival: string;
    estimated_arrival: string;
    delay_minutes: number;
    status: string;
    data_source: DataSource;
    last_updated: string | null;
    provider_warning?: string;
    note?: string;
  }>;
  disruption: {
    detected: boolean;
    events: Array<{
      flight_number: string;
      type: string;
      delay_minutes: number;
      previous_delay: number;
    }>;
  };
  impact_analysis: {
    connection_status: "HEALTHY" | "AT_RISK" | "MISSED_CONNECTION" | string;
    connection_buffer_minutes: number | null;
    recovery_required: boolean;
  };
  trip_status: string;
}

export interface TripListItem {
  trip: Trip;
  segments_count: number;
  flights: FlightSegment[];
}

export interface CreateTripPayload {
  trip_name: string;
  traveler_name?: string;
  destination: string;
  start_date: string;
  end_date: string;
  hotel_name?: string;
  hotel_city?: string;
  transfer_pickup?: string;
  transfer_drop?: string;
}

export interface AddFlightPayload {
  flight_number: string;
  travel_date: string;
}