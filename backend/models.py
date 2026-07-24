from sqlalchemy import Column, Integer, String, Text

from database import Base


# ============================================================
# FLIGHT INVENTORY
# ============================================================

class Flight(Base):

    __tablename__ = "flights"

    id = Column(Integer, primary_key=True, index=True)

    flight_number = Column(
        String,
        unique=True,
        index=True
    )

    origin = Column(String)
    destination = Column(String)

    departure = Column(String)
    arrival = Column(String)

    available_seats = Column(Integer)

    additional_cost = Column(Integer)

    cabin = Column(
        String,
        default="ECONOMY"
    )

    status = Column(
        String,
        default="AVAILABLE"
    )


# ============================================================
# TRIPS
# ============================================================

class Trip(Base):

    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)

    trip_id = Column(
        String,
        unique=True,
        index=True
    )

    traveler_name = Column(String)

    trip_name = Column(String)

    destination = Column(String)

    start_date = Column(String)
    end_date = Column(String)

    status = Column(
        String,
        default="HEALTHY"
    )


# ============================================================
# BOOKED FLIGHT SEGMENTS
# ============================================================

class FlightSegment(Base):

    __tablename__ = "flight_segments"

    id = Column(Integer, primary_key=True, index=True)

    trip_id = Column(String)

    flight_number = Column(String)

    origin = Column(String)
    destination = Column(String)

    scheduled_departure = Column(String)
    scheduled_arrival = Column(String)

    estimated_departure = Column(String)
    estimated_arrival = Column(String)

    status = Column(
        String,
        default="CONFIRMED"
    )


# ============================================================
# HOTEL
# ============================================================

class HotelBooking(Base):

    __tablename__ = "hotel_bookings"

    id = Column(Integer, primary_key=True, index=True)

    booking_id = Column(
        String,
        unique=True,
        index=True
    )

    trip_id = Column(String)

    hotel_name = Column(String)
    city = Column(String)

    check_in_date = Column(String)
    check_out_date = Column(String)

    expected_arrival = Column(String)

    status = Column(
        String,
        default="CONFIRMED"
    )


# ============================================================
# TRANSFER
# ============================================================

class Transfer(Base):

    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)

    transfer_id = Column(
        String,
        unique=True,
        index=True
    )

    trip_id = Column(String)

    pickup_location = Column(String)
    drop_location = Column(String)

    pickup_time = Column(String)

    status = Column(
        String,
        default="CONFIRMED"
    )


# ============================================================
# DISRUPTION EVENTS
# ============================================================

class DisruptionEvent(Base):

    __tablename__ = "disruption_events"

    id = Column(Integer, primary_key=True, index=True)

    disruption_id = Column(
        String,
        unique=True,
        index=True
    )

    trip_id = Column(String)

    flight_number = Column(String)

    disruption_type = Column(String)

    delay_minutes = Column(Integer)

    original_arrival = Column(String)

    new_estimated_arrival = Column(String)

    affected_flight = Column(String)

    impact = Column(String)

    recovery_required = Column(String)

    status = Column(
        String,
        default="DETECTED"
    )


# ============================================================
# TRAVEL POLICY
# ============================================================

class PolicyRule(Base):

    __tablename__ = "policy_rules"

    id = Column(Integer, primary_key=True, index=True)

    trip_id = Column(
        String,
        unique=True,
        index=True
    )

    auto_rebook_limit = Column(Integer)

    approval_limit = Column(Integer)

    hotel_limit = Column(Integer)

    allowed_cabin = Column(String)

    alternative_airport_allowed = Column(
        String,
        default="NO"
    )


# ============================================================
# RECOVERY PLAN
# ============================================================

class RecoveryPlan(Base):

    __tablename__ = "recovery_plans"

    id = Column(Integer, primary_key=True, index=True)

    plan_id = Column(
        String,
        unique=True,
        index=True
    )

    trip_id = Column(String)

    disruption_id = Column(String)

    selected_flight = Column(String)

    recovery_score = Column(Integer)

    additional_cost = Column(Integer)

    policy_decision = Column(String)

    booking_reference = Column(String)

    status = Column(String)

    explanation = Column(Text)


# ============================================================
# RECOVERY ACTIONS
# ============================================================

class RecoveryAction(Base):

    __tablename__ = "recovery_actions"

    id = Column(Integer, primary_key=True, index=True)

    action_id = Column(
        String,
        unique=True,
        index=True
    )

    plan_id = Column(String)

    trip_id = Column(String)

    action_type = Column(String)

    target = Column(String)

    status = Column(String)

    details = Column(Text)


# ============================================================
# NOTIFICATIONS
# ============================================================

class Notification(Base):

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)

    notification_id = Column(
        String,
        unique=True,
        index=True
    )

    trip_id = Column(String)

    title = Column(String)

    message = Column(Text)

    channel = Column(String)

    status = Column(String)


# ============================================================
# AUDIT LOG
# ============================================================

class AuditLog(Base):

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    audit_id = Column(
        String,
        unique=True,
        index=True
    )

    trip_id = Column(String)

    event_type = Column(String)

    message = Column(Text)

    created_at = Column(String)