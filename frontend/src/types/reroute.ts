// ============================================================
// ReRoute AI - TypeScript interfaces matching FastAPI backend
// ============================================================

export interface Trip {
  id: number;
  trip_id: string;
  traveler_name: string;
  trip_name: string;
  destination: string;
  start_date: string;
  end_date: string;
  status: string;
}

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
  status: string;
}

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

// ============================================================
// API Response shapes
// ============================================================

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

export interface DisruptionResponse {
  disruption: {
    detected: boolean;
    flight: string;
    delay_minutes: number;
    new_arrival: string;
  };
  impact_analysis: {
    affected_flight: string;
    connection_buffer_minutes: number;
    impact: string;
    recovery_required: boolean;
  };
  alternatives: {
    valid: RecoveryOption[];
    rejected: RejectedOption[];
  };
  decision: {
    selected_flight: string;
    recovery_score: number;
    additional_cost: number;
    why: string[];
  };
  policy: {
    decision: string;
    reason: string;
  };
  execution: {
    flight_rebooking: string;
    booking_reference: string;
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
  };
  recovery_plan: {
    plan_id: string;
    status: string;
  };
  trip_status: string;
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
  score_breakdown: {
    cost: number;
    arrival: number;
    airline: number;
    cabin: number;
    safety: number;
  };
  why: string[];
  penalties: string[];
  connection_buffer_minutes: number;
  rank: number;
}

export interface RejectedOption {
  flight_number: string;
  reasons: string[];
}

export interface RecoveryPlanResponse {
  plan: RecoveryPlan;
  actions: RecoveryAction[];
}

export interface NotificationsResponse {
  count: number;
  notifications: Notification[];
}
