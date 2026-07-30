from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from datetime import datetime, timedelta
from typing import Optional
import uuid
import json
import os
import logging
import re


def _load_dotenv(path: str = ".env") -> None:
    """
    Minimal stdlib-only .env loader.
    Reads KEY=VALUE pairs from the .env file and sets them as environment
    variables if they are not already set by the shell.
    Does not require python-dotenv.
    """
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=(.*)$', line)
                if match:
                    key, val = match.group(1), match.group(2).strip()
                    # Strip surrounding quotes
                    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
                        val = val[1:-1]
                    # Only set if not already set by the environment
                    if key not in os.environ:
                        os.environ[key] = val
    except Exception:
        pass


# Load environment variables from backend/.env before anything else
_load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from database import engine, SessionLocal
import models
from services.flight_service import get_flight_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

# Minimum connection buffer in minutes — used throughout the recovery engine
DEFAULT_MIN_CONNECTION_MINUTES: int = int(
    os.getenv("DEFAULT_MIN_CONNECTION_MINUTES", "75")
)


# ============================================================
# DATABASE
# ============================================================

models.Base.metadata.create_all(bind=engine)


# ============================================================
# SAFE SCHEMA MIGRATION
#
# Adds new columns to existing tables without dropping data.
# Each ALTER TABLE is idempotent — safe to run on every startup.
# ============================================================

def _run_safe_migrations():
    """
    Add new columns introduced in v2.1 to existing SQLite databases.
    SQLite does not support multiple ADD COLUMN in one statement.
    Each migration is wrapped in a try/except so it silently skips
    columns that already exist.
    """
    new_columns = [
        ("flight_segments", "actual_departure", "TEXT"),
        ("flight_segments", "actual_arrival", "TEXT"),
        ("flight_segments", "provider", "TEXT"),
        ("flight_segments", "data_source", "TEXT DEFAULT 'DEMO'"),
        ("flight_segments", "last_status_check", "TEXT"),
        ("flight_segments", "last_provider_update", "TEXT"),
        ("flight_segments", "delay_minutes", "INTEGER DEFAULT 0"),
        ("flight_segments", "terminal", "TEXT"),
        ("flight_segments", "gate", "TEXT"),
        ("flight_segments", "airline_name", "TEXT"),
        ("flight_segments", "origin_city", "TEXT"),
        ("flight_segments", "destination_city", "TEXT"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in new_columns:
            try:
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                )
                conn.commit()
                logger.info("Migration: added column %s.%s", table, column)
            except Exception:
                # Column already exists — safe to ignore
                pass


_run_safe_migrations()


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="ReRoute AI",
    description="Autonomous Travel Disruption Recovery Backend",
    version="2.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE SESSION
# ============================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# REQUEST MODELS
# ============================================================

class DisruptionRequest(BaseModel):

    trip_id: str

    flight: str

    delay_minutes: int


class ApprovalRequest(BaseModel):

    approved: bool


# ============================================================
# ADDITIONAL REQUEST / RESPONSE MODELS
# ============================================================

class FlightStatusResponse(BaseModel):
    """Safe response wrapping a normalized flight status."""
    flight_number: str
    airline_code: str
    airline_name: Optional[str] = None
    origin_iata: str
    origin_name: Optional[str] = None
    origin_city: Optional[str] = None
    origin_terminal: Optional[str] = None
    origin_gate: Optional[str] = None
    destination_iata: str
    destination_name: Optional[str] = None
    destination_city: Optional[str] = None
    destination_terminal: Optional[str] = None
    destination_gate: Optional[str] = None
    scheduled_departure: Optional[str] = None
    estimated_departure: Optional[str] = None
    actual_departure: Optional[str] = None
    scheduled_arrival: Optional[str] = None
    estimated_arrival: Optional[str] = None
    actual_arrival: Optional[str] = None
    delay_minutes: int = 0
    status: str = "UNKNOWN"
    data_source: str = "DEMO"
    last_updated: Optional[str] = None
    provider_warning: Optional[str] = None


class ProviderConfigResponse(BaseModel):
    """Non-sensitive provider configuration info."""
    provider_name: str
    real_data_enabled: bool
    demo_fallback_enabled: bool
    cache_ttl_seconds: int
    min_connection_minutes: int


# ============================================================
# HELPERS
# ============================================================

def make_id(prefix):

    return (
        prefix
        + "-"
        + uuid.uuid4().hex[:8].upper()
    )


def now_iso():

    return datetime.now().isoformat()


def date_from_iso(iso_string: str) -> str:
    """Extract YYYY-MM-DD date from an ISO datetime string."""
    if not iso_string:
        return datetime.now().strftime("%Y-%m-%d")
    return iso_string[:10]


def parse_iso_flexible(iso_string: str) -> datetime:
    """
    Parse an ISO datetime string that may or may not have timezone info.

    Strips timezone offset and returns a naive datetime for comparison.
    Used for connection buffer calculations where we compare same-timezone
    airport times (both in UTC from provider).
    """
    if not iso_string:
        raise ValueError("Empty datetime string")
    # Remove timezone offset (+HH:MM or Z) for naive comparison
    # This is safe because AviationStack returns UTC times
    clean = iso_string
    if clean.endswith("Z"):
        clean = clean[:-1]
    elif "+" in clean[10:]:
        clean = clean[:clean.rindex("+", 10)]
    elif clean.count("-") > 2:
        # Negative timezone offset like 2026-07-25T10:00:00-05:30
        last_dash = clean.rfind("-", 10)
        clean = clean[:last_dash]
    return datetime.fromisoformat(clean)


def get_airline_code(flight_number):

    code = ""

    for character in flight_number:

        if character.isalpha():
            code += character

        else:
            break

    return code.upper()


# ============================================================
# AUDIT LOG
# ============================================================

def add_audit(
    db,
    trip_id,
    event_type,
    message
):

    audit = models.AuditLog(

        audit_id=make_id("AUD"),

        trip_id=trip_id,

        event_type=event_type,

        message=message,

        created_at=now_iso()

    )

    db.add(audit)


# ============================================================
# HOME
# ============================================================

@app.get("/")
def home():

    return {

        "name": "ReRoute AI",

        "status": "ONLINE",

        "version": "2.1.0",

        "message":
            "Autonomous Travel Recovery Backend Running"

    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {

        "status": "healthy",

        "service": "reroute-backend"

    }


# ============================================================
# DEMO RESET
# ============================================================

@app.post("/api/demo/reset")
def reset_demo(
    db: Session = Depends(get_db)
):

    tables = [

        models.Notification,
        models.RecoveryAction,
        models.RecoveryPlan,
        models.DisruptionEvent,
        models.PolicyRule,
        models.Transfer,
        models.HotelBooking,
        models.FlightSegment,
        models.Trip,
        models.Flight,
        models.AuditLog

    ]

    for table in tables:

        db.query(table).delete()

    db.commit()

    return {
        "message": "Demo database reset successfully"
    }


# ============================================================
# DEMO SETUP
# ============================================================

@app.post("/api/demo/setup")
def setup_demo(
    db: Session = Depends(get_db)
):

    existing = db.query(
        models.Trip
    ).filter(
        models.Trip.trip_id == "TRIP001"
    ).first()


    if existing:

        return {
            "message": "Demo already exists",
            "trip_id": "TRIP001"
        }


    # --------------------------------------------------------
    # TRIP
    # --------------------------------------------------------

    trip = models.Trip(

        trip_id="TRIP001",

        traveler_name="Jeevan",

        trip_name="London Trip",

        destination="London",

        start_date="2026-07-24",

        end_date="2026-07-30",

        status="HEALTHY"

    )

    db.add(trip)


    # --------------------------------------------------------
    # ORIGINAL FLIGHT 1
    # --------------------------------------------------------

    db.add(

        models.FlightSegment(

            trip_id="TRIP001",

            flight_number="EK527",

            origin="HYD",

            destination="DXB",

            scheduled_departure=
                "2026-07-24T10:00:00",

            scheduled_arrival=
                "2026-07-24T12:30:00",

            estimated_departure=
                "2026-07-24T10:00:00",

            estimated_arrival=
                "2026-07-24T12:30:00",

            status="CONFIRMED"

        )

    )


    # --------------------------------------------------------
    # ORIGINAL CONNECTION
    # --------------------------------------------------------

    db.add(

        models.FlightSegment(

            trip_id="TRIP001",

            flight_number="EK001",

            origin="DXB",

            destination="LHR",

            scheduled_departure=
                "2026-07-24T14:00:00",

            scheduled_arrival=
                "2026-07-24T18:30:00",

            estimated_departure=
                "2026-07-24T14:00:00",

            estimated_arrival=
                "2026-07-24T18:30:00",

            status="CONFIRMED"

        )

    )


    # --------------------------------------------------------
    # HOTEL
    # --------------------------------------------------------

    db.add(

        models.HotelBooking(

            booking_id="HOTEL001",

            trip_id="TRIP001",

            hotel_name="London Marriott",

            city="London",

            check_in_date="2026-07-24",

            check_out_date="2026-07-30",

            expected_arrival=
                "2026-07-24T20:00:00",

            status="CONFIRMED"

        )

    )


    # --------------------------------------------------------
    # TRANSFER
    # --------------------------------------------------------

    db.add(

        models.Transfer(

            transfer_id="TRANSFER001",

            trip_id="TRIP001",

            pickup_location="LHR Airport",

            drop_location="London Marriott",

            pickup_time=
                "2026-07-24T19:15:00",

            status="CONFIRMED"

        )

    )


    # --------------------------------------------------------
    # POLICY
    # --------------------------------------------------------

    db.add(

        models.PolicyRule(

            trip_id="TRIP001",

            auto_rebook_limit=15000,

            approval_limit=40000,

            hotel_limit=10000,

            allowed_cabin="ECONOMY",

            alternative_airport_allowed="NO"

        )

    )


    # --------------------------------------------------------
    # RECOVERY FLIGHTS
    # --------------------------------------------------------

    recovery_flights = [

        models.Flight(

            flight_number="EK003",

            origin="DXB",

            destination="LHR",

            departure=
                "2026-07-24T16:30:00",

            arrival=
                "2026-07-24T21:10:00",

            available_seats=7,

            additional_cost=0,

            cabin="ECONOMY",

            status="AVAILABLE"

        ),


        models.Flight(

            flight_number="BA106",

            origin="DXB",

            destination="LHR",

            departure=
                "2026-07-24T17:10:00",

            arrival=
                "2026-07-24T21:00:00",

            available_seats=2,

            additional_cost=7500,

            cabin="ECONOMY",

            status="AVAILABLE"

        ),


        models.Flight(

            flight_number="EK005",

            origin="DXB",

            destination="LHR",

            departure=
                "2026-07-24T18:00:00",

            arrival=
                "2026-07-24T22:40:00",

            available_seats=0,

            additional_cost=2000,

            cabin="ECONOMY",

            status="AVAILABLE"

        ),


        models.Flight(

            flight_number="EK009",

            origin="DXB",

            destination="LHR",

            departure=
                "2026-07-24T15:30:00",

            arrival=
                "2026-07-24T20:15:00",

            available_seats=5,

            additional_cost=1000,

            cabin="ECONOMY",

            status="AVAILABLE"

        )

    ]


    for flight in recovery_flights:

        db.add(flight)


    add_audit(
        db,
        "TRIP001",
        "TRIP_CREATED",
        "Demo London trip created."
    )


    db.commit()


    return {

        "message":
            "Complete ReRoute demo environment created",

        "trip_id":
            "TRIP001",

        "status":
            "HEALTHY"

    }


# ============================================================
# SCORE RECOVERY OPTION
# ============================================================

def score_flight(
    flight,
    original_flight,
    traveler_available_at
):

    score = 0

    reasons = []

    penalties = []


    # --------------------------------------------------------
    # COST — 35
    # --------------------------------------------------------

    if flight.additional_cost == 0:

        cost_score = 35

        reasons.append(
            "No additional cost"
        )

    elif flight.additional_cost <= 5000:

        cost_score = 30

        reasons.append(
            "Low additional cost"
        )

    elif flight.additional_cost <= 10000:

        cost_score = 22

        reasons.append(
            "Moderate additional cost"
        )

    elif flight.additional_cost <= 15000:

        cost_score = 15

        penalties.append(
            "Higher additional cost"
        )

    else:

        cost_score = 5

        penalties.append(
            "Expensive option"
        )


    score += cost_score


    # --------------------------------------------------------
    # ARRIVAL — 25
    # --------------------------------------------------------

    arrival = datetime.fromisoformat(
        flight.arrival
    )


    recovery_minutes = int(

        (
            arrival
            - traveler_available_at
        ).total_seconds()

        / 60

    )


    if recovery_minutes <= 300:

        arrival_score = 25

        reasons.append(
            "Fast arrival"
        )

    elif recovery_minutes <= 360:

        arrival_score = 22

        reasons.append(
            "Good arrival time"
        )

    elif recovery_minutes <= 420:

        arrival_score = 18

        reasons.append(
            "Reasonable arrival time"
        )

    else:

        arrival_score = 10

        penalties.append(
            "Later arrival"
        )


    score += arrival_score


    # --------------------------------------------------------
    # AIRLINE — 15
    # --------------------------------------------------------

    if (
        get_airline_code(flight.flight_number)
        ==
        get_airline_code(original_flight)
    ):

        airline_score = 15

        reasons.append(
            "Same airline"
        )

    else:

        airline_score = 8

        penalties.append(
            "Different airline"
        )


    score += airline_score


    # --------------------------------------------------------
    # CABIN — 15
    # --------------------------------------------------------

    if flight.cabin == "ECONOMY":

        cabin_score = 15

        reasons.append(
            "Same cabin class"
        )

    else:

        cabin_score = 5

        penalties.append(
            "Different cabin"
        )


    score += cabin_score


    # --------------------------------------------------------
    # CONNECTION BUFFER — 10
    # --------------------------------------------------------

    departure = datetime.fromisoformat(
        flight.departure
    )


    buffer_minutes = int(

        (
            departure
            - traveler_available_at
        ).total_seconds()

        / 60

    )


    if buffer_minutes >= 120:

        buffer_score = 10

        reasons.append(
            "Comfortable connection buffer"
        )

    elif buffer_minutes >= 90:

        buffer_score = 9

        reasons.append(
            "Good connection buffer"
        )

    else:

        buffer_score = 7

        reasons.append(
            "Safe connection buffer"
        )


    score += buffer_score


    return {

        "score": score,

        "reasons": reasons,

        "penalties": penalties,

        "buffer_minutes":
            buffer_minutes,

        "breakdown": {

            "cost":
                cost_score,

            "arrival":
                arrival_score,

            "airline":
                airline_score,

            "cabin":
                cabin_score,

            "safety":
                buffer_score

        }

    }


# ============================================================
# SEARCH + RANK RECOVERY FLIGHTS
# ============================================================

def find_recovery_options(
    db,
    origin,
    destination,
    traveler_available_at,
    original_flight
):

    minimum_buffer = DEFAULT_MIN_CONNECTION_MINUTES


    earliest_departure = (

        traveler_available_at

        + timedelta(
            minutes=minimum_buffer
        )

    )


    flights = db.query(
        models.Flight
    ).filter(

        models.Flight.origin == origin,

        models.Flight.destination == destination

    ).all()


    valid = []

    rejected = []


    for flight in flights:

        reasons = []


        if flight.status != "AVAILABLE":

            reasons.append(
                "Flight unavailable"
            )


        if flight.available_seats <= 0:

            reasons.append(
                "No seats available"
            )


        departure = datetime.fromisoformat(
            flight.departure
        )


        if departure < earliest_departure:

            reasons.append(
                "Departure too soon"
            )


        if reasons:

            rejected.append({

                "flight_number":
                    flight.flight_number,

                "reasons":
                    reasons

            })

            continue


        scoring = score_flight(

            flight,

            original_flight,

            traveler_available_at

        )


        valid.append({

            "flight_number":
                flight.flight_number,

            "origin":
                flight.origin,

            "destination":
                flight.destination,

            "departure":
                flight.departure,

            "arrival":
                flight.arrival,

            "additional_cost":
                flight.additional_cost,

            "available_seats":
                flight.available_seats,

            "cabin":
                flight.cabin,

            "recovery_score":
                scoring["score"],

            "score_breakdown":
                scoring["breakdown"],

            "why":
                scoring["reasons"],

            "penalties":
                scoring["penalties"],

            "connection_buffer_minutes":
                scoring["buffer_minutes"]

        })


    valid.sort(
        key=lambda x: x["recovery_score"],
        reverse=True
    )


    for index, item in enumerate(
        valid,
        start=1
    ):

        item["rank"] = index


    return {

        "valid_options":
            valid,

        "rejected_options":
            rejected,

        "best_option":
            valid[0] if valid else None

    }


# ============================================================
# POLICY ENGINE
# ============================================================

def evaluate_policy(
    policy,
    option
):

    cost = option["additional_cost"]


    # --------------------------------------------------------
    # CABIN RULE
    # --------------------------------------------------------

    if (
        option["cabin"]
        != policy.allowed_cabin
    ):

        return {

            "decision":
                "ESCALATE",

            "reason":
                "Cabin violates travel policy"

        }


    # --------------------------------------------------------
    # AUTO
    # --------------------------------------------------------

    if cost <= policy.auto_rebook_limit:

        return {

            "decision":
                "AUTO",

            "reason":
                (
                    f"₹{cost} is within "
                    f"₹{policy.auto_rebook_limit} "
                    "automatic rebooking limit"
                )

        }


    # --------------------------------------------------------
    # APPROVAL
    # --------------------------------------------------------

    if cost <= policy.approval_limit:

        return {

            "decision":
                "APPROVAL_REQUIRED",

            "reason":
                (
                    f"₹{cost} exceeds automatic limit "
                    "but is within customer approval limit"
                )

        }


    # --------------------------------------------------------
    # ESCALATE
    # --------------------------------------------------------

    return {

        "decision":
            "ESCALATE",

        "reason":
            (
                f"₹{cost} exceeds "
                f"₹{policy.approval_limit} limit"
            )

    }


# ============================================================
# EXECUTE FLIGHT REBOOKING
# ============================================================

def execute_rebooking(
    db,
    trip,
    missed_segment,
    replacement
):

    inventory = db.query(
        models.Flight
    ).filter(
        models.Flight.flight_number
        == replacement["flight_number"]
    ).first()


    if not inventory:

        raise HTTPException(
            status_code=404,
            detail="Recovery flight disappeared"
        )


    if inventory.available_seats <= 0:

        raise HTTPException(
            status_code=409,
            detail="Recovery flight sold out"
        )


    # --------------------------------------------------------
    # REDUCE INVENTORY
    # --------------------------------------------------------

    inventory.available_seats -= 1


    booking_reference = make_id("RR")


    # --------------------------------------------------------
    # REPLACE ITINERARY SEGMENT
    # --------------------------------------------------------

    old_flight = missed_segment.flight_number


    missed_segment.flight_number = (
        inventory.flight_number
    )

    missed_segment.scheduled_departure = (
        inventory.departure
    )

    missed_segment.scheduled_arrival = (
        inventory.arrival
    )

    missed_segment.estimated_departure = (
        inventory.departure
    )

    missed_segment.estimated_arrival = (
        inventory.arrival
    )

    missed_segment.status = "REBOOKED"


    add_audit(

        db,

        trip.trip_id,

        "FLIGHT_REBOOKED",

        (
            f"{old_flight} replaced with "
            f"{inventory.flight_number}. "
            f"Booking {booking_reference}."
        )

    )


    return booking_reference


# ============================================================
# HOTEL RECOVERY
# ============================================================

def update_hotel(
    db,
    trip_id,
    new_arrival
):

    hotel = db.query(
        models.HotelBooking
    ).filter(
        models.HotelBooking.trip_id
        == trip_id
    ).first()


    if not hotel:

        return None


    hotel.expected_arrival = (
        new_arrival.isoformat()
    )


    hotel.status = (
        "LATE_CHECKIN_CONFIRMED"
    )


    return {

        "hotel":
            hotel.hotel_name,

        "status":
            hotel.status,

        "new_expected_arrival":
            hotel.expected_arrival

    }


# ============================================================
# TRANSFER RECOVERY
# ============================================================

def update_transfer(
    db,
    trip_id,
    flight_arrival
):

    transfer = db.query(
        models.Transfer
    ).filter(
        models.Transfer.trip_id
        == trip_id
    ).first()


    if not transfer:

        return None


    # Demo assumption:
    # airport pickup = 45 min after arrival

    pickup = (

        flight_arrival

        + timedelta(minutes=45)

    )


    transfer.pickup_time = (
        pickup.isoformat()
    )


    transfer.status = (
        "RESCHEDULED"
    )


    return {

        "transfer_id":
            transfer.transfer_id,

        "status":
            transfer.status,

        "new_pickup_time":
            transfer.pickup_time

    }


# ============================================================
# CREATE NOTIFICATION
# ============================================================

def create_notification(
    db,
    trip_id,
    flight,
    booking_reference,
    extra_cost
):

    notification = models.Notification(

        notification_id=
            make_id("NOT"),

        trip_id=
            trip_id,

        title=
            "Trip recovered",

        message=(

            f"Your missed connection has been recovered. "
            f"You are now booked on {flight}. "
            f"Booking reference: {booking_reference}. "
            f"Additional cost: ₹{extra_cost}."

        ),

        channel=
            "APP",

        status=
            "SENT"

    )


    db.add(notification)


    return notification


# ============================================================
# CREATE RECOVERY ACTION
# ============================================================

def add_recovery_action(
    db,
    plan_id,
    trip_id,
    action_type,
    target,
    status,
    details
):

    action = models.RecoveryAction(

        action_id=
            make_id("ACT"),

        plan_id=
            plan_id,

        trip_id=
            trip_id,

        action_type=
            action_type,

        target=
            target,

        status=
            status,

        details=
            details

    )


    db.add(action)


# ============================================================
# MAIN AUTONOMOUS DISRUPTION ENDPOINT
# ============================================================

@app.post("/api/demo/disruption")
def disruption(
    request: DisruptionRequest,
    db: Session = Depends(get_db)
):

    # --------------------------------------------------------
    # VALIDATE DELAY
    # --------------------------------------------------------

    if request.delay_minutes < 0:

        raise HTTPException(
            status_code=400,
            detail="Delay cannot be negative"
        )


    # --------------------------------------------------------
    # FIND TRIP
    # --------------------------------------------------------

    trip = db.query(
        models.Trip
    ).filter(
        models.Trip.trip_id
        == request.trip_id
    ).first()


    if not trip:

        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )


    # --------------------------------------------------------
    # IDEMPOTENCY
    #
    # Don't execute the same recovery twice.
    # --------------------------------------------------------

    existing_plan = db.query(
        models.RecoveryPlan
    ).filter(
        models.RecoveryPlan.trip_id
        == request.trip_id,
        models.RecoveryPlan.status
        == "COMPLETED"
    ).first()


    if existing_plan:

        return {

            "message":
                "Trip was already recovered",

            "plan_id":
                existing_plan.plan_id,

            "selected_flight":
                existing_plan.selected_flight,

            "booking_reference":
                existing_plan.booking_reference,

            "trip_status":
                trip.status

        }


    # --------------------------------------------------------
    # FIND DELAYED SEGMENT
    # --------------------------------------------------------

    delayed = db.query(
        models.FlightSegment
    ).filter(

        models.FlightSegment.trip_id
        == request.trip_id,

        models.FlightSegment.flight_number
        == request.flight

    ).first()


    if not delayed:

        raise HTTPException(
            status_code=404,
            detail="Flight not found in trip"
        )


    original_arrival = datetime.fromisoformat(
        delayed.scheduled_arrival
    )


    new_arrival = (

        original_arrival

        + timedelta(
            minutes=request.delay_minutes
        )

    )


    delayed.estimated_arrival = (
        new_arrival.isoformat()
    )


    delayed.status = "DELAYED"


    # --------------------------------------------------------
    # FIND NEXT SEGMENT
    # --------------------------------------------------------

    next_segment = db.query(
        models.FlightSegment
    ).filter(

        models.FlightSegment.trip_id
        == request.trip_id,

        models.FlightSegment.origin
        == delayed.destination,

        models.FlightSegment.id
        != delayed.id

    ).first()


    if not next_segment:

        db.commit()

        return {

            "disruption_detected":
                True,

            "impact":
                "NO_CONNECTION",

            "recovery_required":
                False

        }


    next_departure = datetime.fromisoformat(
        next_segment.estimated_departure
    )


    connection_buffer = int(

        (
            next_departure
            - new_arrival
        ).total_seconds()

        / 60

    )


    # --------------------------------------------------------
    # CONNECTION STILL SAFE
    # --------------------------------------------------------

    if connection_buffer >= DEFAULT_MIN_CONNECTION_MINUTES:

        trip.status = "DELAYED_BUT_SAFE"

        db.commit()


        return {

            "disruption_detected":
                True,

            "delay_minutes":
                request.delay_minutes,

            "connection_buffer_minutes":
                connection_buffer,

            "impact":
                "CONNECTION_SAFE",

            "recovery_required":
                False,

            "trip_status":
                trip.status

        }


    # ========================================================
    # MISSED CONNECTION
    # ========================================================

    trip.status = "RECOVERY_REQUIRED"

    next_segment.status = (
        "CONNECTION_MISSED"
    )


    disruption_id = make_id("DIS")


    disruption_event = models.DisruptionEvent(

        disruption_id=
            disruption_id,

        trip_id=
            request.trip_id,

        flight_number=
            request.flight,

        disruption_type=
            "DELAY",

        delay_minutes=
            request.delay_minutes,

        original_arrival=
            original_arrival.isoformat(),

        new_estimated_arrival=
            new_arrival.isoformat(),

        affected_flight=
            next_segment.flight_number,

        impact=
            "MISSED_CONNECTION",

        recovery_required=
            "True",

        status=
            "DETECTED"

    )


    db.add(disruption_event)


    add_audit(

        db,

        trip.trip_id,

        "DISRUPTION_DETECTED",

        (
            f"{request.flight} delayed "
            f"{request.delay_minutes} minutes. "
            f"{next_segment.flight_number} "
            "connection cannot be reached."
        )

    )


    # ========================================================
    # SEARCH RECOVERY OPTIONS
    # ========================================================

    options = find_recovery_options(

        db,

        next_segment.origin,

        next_segment.destination,

        new_arrival,

        next_segment.flight_number

    )


    best = options["best_option"]


    # --------------------------------------------------------
    # NO RECOVERY FOUND
    # --------------------------------------------------------

    if not best:

        trip.status = "ESCALATED"

        db.commit()


        return {

            "disruption_detected":
                True,

            "impact":
                "MISSED_CONNECTION",

            "recovery_required":
                True,

            "recovery_status":
                "ESCALATED",

            "reason":
                "No valid replacement flights found"

        }


    # ========================================================
    # POLICY
    # ========================================================

    policy = db.query(
        models.PolicyRule
    ).filter(
        models.PolicyRule.trip_id
        == request.trip_id
    ).first()


    if not policy:

        raise HTTPException(
            status_code=500,
            detail="Travel policy not configured"
        )


    policy_result = evaluate_policy(
        policy,
        best
    )


    # ========================================================
    # CREATE RECOVERY PLAN
    # ========================================================

    plan_id = make_id("PLAN")


    explanation = (

        f"{best['flight_number']} selected with "
        f"recovery score {best['recovery_score']}. "
        + "; ".join(best["why"])

    )


    plan = models.RecoveryPlan(

        plan_id=
            plan_id,

        trip_id=
            request.trip_id,

        disruption_id=
            disruption_id,

        selected_flight=
            best["flight_number"],

        recovery_score=
            best["recovery_score"],

        additional_cost=
            best["additional_cost"],

        policy_decision=
            policy_result["decision"],

        booking_reference=
            None,

        status=
            "PLANNED",

        explanation=
            explanation

    )


    db.add(plan)


    add_recovery_action(

        db,

        plan_id,

        request.trip_id,

        "FLIGHT_SELECTION",

        best["flight_number"],

        "COMPLETE",

        explanation

    )


    # ========================================================
    # APPROVAL REQUIRED
    # ========================================================

    if (
        policy_result["decision"]
        == "APPROVAL_REQUIRED"
    ):

        plan.status = "WAITING_FOR_APPROVAL"

        trip.status = "AWAITING_APPROVAL"

        db.commit()


        return {

            "disruption_detected":
                True,

            "impact":
                "MISSED_CONNECTION",

            "recovery_required":
                True,

            "selected_recovery":
                best,

            "policy":
                policy_result,

            "plan_id":
                plan_id,

            "execution":
                "WAITING_FOR_USER_APPROVAL",

            "trip_status":
                trip.status

        }


    # ========================================================
    # HUMAN ESCALATION
    # ========================================================

    if (
        policy_result["decision"]
        == "ESCALATE"
    ):

        plan.status = "ESCALATED"

        trip.status = "ESCALATED"


        add_recovery_action(

            db,

            plan_id,

            request.trip_id,

            "ESCALATION",

            "HUMAN_AGENT",

            "REQUIRED",

            policy_result["reason"]

        )


        db.commit()


        return {

            "disruption_detected":
                True,

            "selected_recovery":
                best,

            "policy":
                policy_result,

            "execution":
                "HUMAN_ESCALATION",

            "trip_status":
                trip.status

        }


    # ========================================================
    # AUTO AUTHORIZED
    # ========================================================

    booking_reference = execute_rebooking(

        db,

        trip,

        next_segment,

        best

    )


    plan.booking_reference = (
        booking_reference
    )


    add_recovery_action(

        db,

        plan_id,

        request.trip_id,

        "FLIGHT_REBOOK",

        best["flight_number"],

        "COMPLETE",

        (
            f"Booking confirmed: "
            f"{booking_reference}"
        )

    )


    # ========================================================
    # HOTEL UPDATE
    # ========================================================

    replacement_arrival = (
        datetime.fromisoformat(
            best["arrival"]
        )
    )


    hotel_result = update_hotel(

        db,

        request.trip_id,

        replacement_arrival

    )


    if hotel_result:

        add_recovery_action(

            db,

            plan_id,

            request.trip_id,

            "HOTEL_UPDATE",

            hotel_result["hotel"],

            "COMPLETE",

            json.dumps(hotel_result)

        )


    # ========================================================
    # TRANSFER UPDATE
    # ========================================================

    transfer_result = update_transfer(

        db,

        request.trip_id,

        replacement_arrival

    )


    if transfer_result:

        add_recovery_action(

            db,

            plan_id,

            request.trip_id,

            "TRANSFER_RESCHEDULE",

            transfer_result["transfer_id"],

            "COMPLETE",

            json.dumps(transfer_result)

        )


    # ========================================================
    # NOTIFICATION
    # ========================================================

    notification = create_notification(

        db,

        request.trip_id,

        best["flight_number"],

        booking_reference,

        best["additional_cost"]

    )


    add_recovery_action(

        db,

        plan_id,

        request.trip_id,

        "NOTIFICATION",

        notification.notification_id,

        "COMPLETE",

        "Traveler notified"

    )


    # ========================================================
    # COMPLETE RECOVERY
    # ========================================================

    plan.status = "COMPLETED"

    trip.status = "RECOVERED"


    add_audit(

        db,

        request.trip_id,

        "TRIP_RECOVERED",

        (
            f"Trip recovered automatically "
            f"using {best['flight_number']}."
        )

    )


    db.commit()


    # ========================================================
    # FINAL RESPONSE
    # ========================================================

    return {

        "disruption": {

            "detected":
                True,

            "flight":
                request.flight,

            "delay_minutes":
                request.delay_minutes,

            "new_arrival":
                new_arrival.isoformat()

        },


        "impact_analysis": {

            "affected_flight":
                disruption_event.affected_flight,

            "connection_buffer_minutes":
                connection_buffer,

            "impact":
                "MISSED_CONNECTION",

            "recovery_required":
                True

        },


        "alternatives": {

            "valid":
                options["valid_options"],

            "rejected":
                options["rejected_options"]

        },


        "decision": {

            "selected_flight":
                best["flight_number"],

            "recovery_score":
                best["recovery_score"],

            "additional_cost":
                best["additional_cost"],

            "why":
                best["why"]

        },


        "policy": {

            "decision":
                policy_result["decision"],

            "reason":
                policy_result["reason"]

        },


        "execution": {

            "flight_rebooking":
                "CONFIRMED",

            "booking_reference":
                booking_reference,

            "booking_mode":
                "SIMULATED",

            "hotel":
                hotel_result,

            "transfer":
                transfer_result,

            "notification":
                "SENT"

        },


        "recovery_plan": {

            "plan_id":
                plan_id,

            "status":
                "COMPLETED"

        },


        "trip_status":
            "RECOVERED"

    }


# ============================================================
# PROVIDER HEALTH (safe — no secrets)
# ============================================================

@app.get("/api/provider/health")
def get_provider_health():
    """
    Return provider connection health status and discovered tool counts.
    Never returns API keys, secrets, headers, or tokens.
    """
    fs = get_flight_service()
    return fs.health_check()


# ============================================================
# PROVIDER CONFIG (safe — no secrets)
# ============================================================

@app.get("/api/config/provider", response_model=ProviderConfigResponse)
def get_provider_config():
    """
    Return non-sensitive provider configuration.
    Never returns API keys, secrets, or tokens.
    """
    fs = get_flight_service()
    return ProviderConfigResponse(
        provider_name=fs.active_provider_name,
        real_data_enabled=fs.real_enabled,
        demo_fallback_enabled=(
            os.getenv("ENABLE_DEMO_FALLBACK", "true").lower() == "true"
        ),
        cache_ttl_seconds=int(os.getenv("FLIGHT_STATUS_CACHE_SECONDS", "300")),
        min_connection_minutes=DEFAULT_MIN_CONNECTION_MINUTES,
    )


# ============================================================
# FLIGHT STATUS (real or demo via provider layer)
# ============================================================

@app.get("/api/flights/status", response_model=FlightStatusResponse)
def get_flight_status(
    flight_number: str = Query(..., description="Full flight number e.g. EK527"),
    date: str = Query(..., description="Travel date YYYY-MM-DD e.g. 2026-07-25"),
    carrier: Optional[str] = Query(None, description="Optional 2-letter IATA airline code"),
):
    """
    Fetch real-time flight status via the configured flight provider.

    Flow:
      Cache hit → return cached result
      Real provider → normalize → cache → return (data_source=REAL)
      Provider failure → demo data (data_source=DEMO) + provider_warning

    Never returns provider credentials or raw auth errors.
    """
    # Basic input validation
    flight_number = flight_number.upper().strip()
    date = date.strip()

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid date format. Use YYYY-MM-DD."
        )

    if not flight_number or len(flight_number) < 3:
        raise HTTPException(
            status_code=400,
            detail="Invalid flight number."
        )

    fs = get_flight_service()
    status = fs.get_flight_status(flight_number, date, carrier)

    return FlightStatusResponse(
        flight_number=status.flight_number,
        airline_code=status.airline_code,
        airline_name=status.airline_name,
        origin_iata=status.origin.iata,
        origin_name=status.origin.name,
        origin_city=status.origin.city,
        origin_terminal=status.origin.terminal,
        origin_gate=status.origin.gate,
        destination_iata=status.destination.iata,
        destination_name=status.destination.name,
        destination_city=status.destination.city,
        destination_terminal=status.destination.terminal,
        destination_gate=status.destination.gate,
        scheduled_departure=status.scheduled_departure,
        estimated_departure=status.estimated_departure,
        actual_departure=status.actual_departure,
        scheduled_arrival=status.scheduled_arrival,
        estimated_arrival=status.estimated_arrival,
        actual_arrival=status.actual_arrival,
        delay_minutes=status.delay_minutes,
        status=status.status,
        data_source=status.data_source,
        last_updated=status.last_updated,
        provider_warning=status.provider_warning,
    )


# ============================================================
# TRIP MONITORING (main real-data monitoring endpoint)
# ============================================================

@app.post("/api/trips/{trip_id}/check")
def check_trip(
    trip_id: str,
    db: Session = Depends(get_db)
):
    """
    Refresh flight status for all segments in a trip.

    Flow:
      1. Load trip + segments
      2. For each active segment, fetch latest status from provider
      3. Update segment with new estimated times, delay, data_source
      4. Detect disruptions (DELAY, CANCELLATION)
      5. Analyze connection impact
      6. If connection missed → trigger recovery
      7. Return full monitoring response

    The frontend must NOT calculate disruption logic.
    All calculations happen here in FastAPI.
    """
    # --------------------------------------------------------
    # LOAD TRIP
    # --------------------------------------------------------

    trip = db.query(models.Trip).filter(
        models.Trip.trip_id == trip_id
    ).first()

    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    segments = db.query(models.FlightSegment).filter(
        models.FlightSegment.trip_id == trip_id
    ).all()

    if not segments:
        return {
            "trip_id": trip_id,
            "monitoring": {
                "status": "NO_SEGMENTS",
                "data_source": "DEMO",
                "checked_at": now_iso(),
            },
            "flight_updates": [],
            "disruption": {"detected": False},
            "trip_status": trip.status,
        }

    fs = get_flight_service()
    now = now_iso()

    flight_updates = []
    disruptions_detected = []

    # --------------------------------------------------------
    # UPDATE EACH SEGMENT
    # --------------------------------------------------------

    for segment in segments:
        # Skip already-resolved segments
        if segment.status in ("REBOOKED", "CONNECTION_MISSED"):
            flight_updates.append({
                "flight_number": segment.flight_number,
                "status": segment.status,
                "data_source": segment.data_source or "DEMO",
                "note": "Segment already resolved — skipping status check",
            })
            continue

        # Determine date from scheduled departure
        travel_date = date_from_iso(segment.scheduled_departure)

        flight_status = fs.get_flight_status(
            segment.flight_number,
            travel_date,
        )

        # Detect changes
        old_estimated_arrival = segment.estimated_arrival
        old_status = segment.status
        old_delay = segment.delay_minutes or 0

        new_delay = flight_status.delay_minutes or 0
        status_changed = (new_delay != old_delay)

        # Update segment with fresh data
        segment.estimated_departure = (
            flight_status.estimated_departure
            or segment.scheduled_departure
        )
        segment.estimated_arrival = (
            flight_status.estimated_arrival
            or segment.scheduled_arrival
        )
        segment.actual_departure = flight_status.actual_departure
        segment.actual_arrival = flight_status.actual_arrival
        segment.delay_minutes = new_delay
        segment.data_source = flight_status.data_source
        segment.last_status_check = now
        segment.airline_name = flight_status.airline_name
        segment.origin_city = flight_status.origin.city
        segment.destination_city = flight_status.destination.city
        segment.terminal = flight_status.destination.terminal
        segment.gate = flight_status.destination.gate

        # Map provider status to segment status
        if flight_status.status == "CANCELLED":
            segment.status = "CANCELLED"
        elif new_delay > 0 and segment.status == "CONFIRMED":
            segment.status = "DELAYED"
        # Don't reset DELAYED back to CONFIRMED if delay cleared
        elif segment.status not in ("DELAYED", "CANCELLED"):
            segment.status = "CONFIRMED"

        provider_warning = flight_status.provider_warning

        update_record = {
            "flight_number": segment.flight_number,
            "airline_name": segment.airline_name,
            "origin": segment.origin,
            "destination": segment.destination,
            "scheduled_departure": segment.scheduled_departure,
            "estimated_departure": segment.estimated_departure,
            "scheduled_arrival": segment.scheduled_arrival,
            "estimated_arrival": segment.estimated_arrival,
            "delay_minutes": new_delay,
            "status": segment.status,
            "data_source": segment.data_source,
            "last_updated": flight_status.last_updated,
        }
        if provider_warning:
            update_record["provider_warning"] = provider_warning

        flight_updates.append(update_record)

        if status_changed and new_delay > 0:
            disruptions_detected.append({
                "flight_number": segment.flight_number,
                "type": "DELAY",
                "delay_minutes": new_delay,
                "previous_delay": old_delay,
            })

        add_audit(
            db,
            trip_id,
            "FLIGHT_STATUS_CHECKED",
            (
                f"{segment.flight_number}: {segment.status}, "
                f"delay={new_delay}min, source={segment.data_source}"
            )
        )

    # --------------------------------------------------------
    # CONNECTION ANALYSIS
    # --------------------------------------------------------

    connection_status = "HEALTHY"
    connection_buffer_minutes = None
    recovery_required = False

    if len(segments) >= 2:
        # Sort segments by scheduled departure to find ordered connections
        sorted_segments = sorted(
            segments,
            key=lambda s: s.scheduled_departure or ""
        )

        for i in range(len(sorted_segments) - 1):
            prev = sorted_segments[i]
            nxt = sorted_segments[i + 1]

            try:
                prev_arrival_str = prev.estimated_arrival or prev.scheduled_arrival
                next_departure_str = nxt.estimated_departure or nxt.scheduled_departure

                if prev_arrival_str and next_departure_str:
                    prev_arr = parse_iso_flexible(prev_arrival_str)
                    next_dep = parse_iso_flexible(next_departure_str)

                    buffer = int(
                        (next_dep - prev_arr).total_seconds() / 60
                    )
                    connection_buffer_minutes = buffer

                    if buffer < DEFAULT_MIN_CONNECTION_MINUTES:
                        connection_status = "MISSED_CONNECTION"
                        recovery_required = True
                        add_audit(
                            db,
                            trip_id,
                            "MISSED_CONNECTION",
                            (
                                f"Connection {prev.flight_number}→{nxt.flight_number} "
                                f"buffer={buffer}min (min={DEFAULT_MIN_CONNECTION_MINUTES}min)"
                            )
                        )
                    elif buffer < DEFAULT_MIN_CONNECTION_MINUTES + 30:
                        connection_status = "AT_RISK"
                        add_audit(
                            db,
                            trip_id,
                            "CONNECTION_AT_RISK",
                            (
                                f"Connection {prev.flight_number}→{nxt.flight_number} "
                                f"only {buffer}min buffer"
                            )
                        )
            except Exception as e:
                logger.warning(
                    "check_trip: connection analysis failed — %s", e
                )

    db.commit()

    # --------------------------------------------------------
    # DETERMINE DATA SOURCE FOR MONITORING SUMMARY
    # --------------------------------------------------------

    sources = [u.get("data_source", "DEMO") for u in flight_updates]
    monitoring_source = "REAL" if "REAL" in sources else (
        "CACHE" if "CACHE" in sources else "DEMO"
    )

    return {
        "trip_id": trip_id,

        "monitoring": {
            "status": "CHECKED",
            "data_source": monitoring_source,
            "checked_at": now,
            "provider": fs.active_provider_name,
        },

        "flight_updates": flight_updates,

        "disruption": {
            "detected": len(disruptions_detected) > 0
            or connection_status in ("MISSED_CONNECTION", "AT_RISK"),
            "events": disruptions_detected,
        },

        "impact_analysis": {
            "connection_status": connection_status,
            "connection_buffer_minutes": connection_buffer_minutes,
            "recovery_required": recovery_required,
        },

        "trip_status": trip.status,
    }


# ============================================================
# GET COMPLETE TRIP
# ============================================================

@app.get("/api/trips/{trip_id}")
def get_trip(
    trip_id: str,
    db: Session = Depends(get_db)
):

    trip = db.query(
        models.Trip
    ).filter(
        models.Trip.trip_id == trip_id
    ).first()


    if not trip:

        raise HTTPException(
            status_code=404,
            detail="Trip not found"
        )


    return {

        "trip":
            trip,

        "flights":
            db.query(
                models.FlightSegment
            ).filter(
                models.FlightSegment.trip_id
                == trip_id
            ).all(),

        "hotel":
            db.query(
                models.HotelBooking
            ).filter(
                models.HotelBooking.trip_id
                == trip_id
            ).first(),

        "transfer":
            db.query(
                models.Transfer
            ).filter(
                models.Transfer.trip_id
                == trip_id
            ).first(),

        "policy":
            db.query(
                models.PolicyRule
            ).filter(
                models.PolicyRule.trip_id
                == trip_id
            ).first(),

        "disruptions":
            db.query(
                models.DisruptionEvent
            ).filter(
                models.DisruptionEvent.trip_id
                == trip_id
            ).all(),

        "recovery_plans":
            db.query(
                models.RecoveryPlan
            ).filter(
                models.RecoveryPlan.trip_id
                == trip_id
            ).all(),

        "recovery_actions":
            db.query(
                models.RecoveryAction
            ).filter(
                models.RecoveryAction.trip_id
                == trip_id
            ).all(),

        "notifications":
            db.query(
                models.Notification
            ).filter(
                models.Notification.trip_id
                == trip_id
            ).all(),

        "audit_logs":
            db.query(
                models.AuditLog
            ).filter(
                models.AuditLog.trip_id
                == trip_id
            ).all()

    }


# ============================================================
# GET RECOVERY PLAN
# ============================================================

@app.get("/api/recovery/{plan_id}")
def get_recovery_plan(
    plan_id: str,
    db: Session = Depends(get_db)
):

    plan = db.query(
        models.RecoveryPlan
    ).filter(
        models.RecoveryPlan.plan_id
        == plan_id
    ).first()


    if not plan:

        raise HTTPException(
            status_code=404,
            detail="Recovery plan not found"
        )


    actions = db.query(
        models.RecoveryAction
    ).filter(
        models.RecoveryAction.plan_id
        == plan_id
    ).all()


    return {

        "plan":
            plan,

        "actions":
            actions

    }


# ============================================================
# TRIP MANAGEMENT ENDPOINTS
# ============================================================

class CreateTripRequest(BaseModel):
    trip_name: str
    traveler_name: Optional[str] = "Traveler"
    destination: str
    start_date: str
    end_date: str
    hotel_name: Optional[str] = None
    hotel_city: Optional[str] = None
    transfer_pickup: Optional[str] = None
    transfer_drop: Optional[str] = None


class AddFlightSegmentRequest(BaseModel):
    flight_number: str
    travel_date: str


@app.get("/api/trips")
def list_trips(db: Session = Depends(get_db)):
    """List all trips in the system."""
    trips = db.query(models.Trip).all()
    results = []
    for trip in trips:
        segments = db.query(models.FlightSegment).filter(
            models.FlightSegment.trip_id == trip.trip_id
        ).all()
        results.append({
            "trip": trip,
            "segments_count": len(segments),
            "flights": segments
        })
    return {"trips": results}


@app.post("/api/trips")
def create_trip(payload: CreateTripRequest, db: Session = Depends(get_db)):
    """Create a new trip with optional default policy, hotel, and transfer."""
    trip_id = f"TRIP-{uuid.uuid4().hex[:6].upper()}"
    
    trip = models.Trip(
        trip_id=trip_id,
        traveler_name=payload.traveler_name or "Traveler",
        trip_name=payload.trip_name,
        destination=payload.destination,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status="HEALTHY"
    )
    db.add(trip)

    # Default policy
    policy = models.PolicyRule(
        trip_id=trip_id,
        auto_rebook_limit=15000,
        approval_limit=40000,
        hotel_limit=10000,
        allowed_cabin="ECONOMY",
        alternative_airport_allowed="ALLOWED"
    )
    db.add(policy)

    # Optional hotel
    if payload.hotel_name:
        hotel = models.HotelBooking(
            booking_id=f"HTL-{uuid.uuid4().hex[:6].upper()}",
            trip_id=trip_id,
            hotel_name=payload.hotel_name,
            city=payload.hotel_city or payload.destination,
            check_in_date=payload.start_date,
            check_out_date=payload.end_date,
            expected_arrival=f"{payload.start_date}T18:00:00",
            status="CONFIRMED"
        )
        db.add(hotel)

    # Optional transfer
    if payload.transfer_pickup and payload.transfer_drop:
        transfer = models.Transfer(
            transfer_id=f"TRF-{uuid.uuid4().hex[:6].upper()}",
            trip_id=trip_id,
            pickup_location=payload.transfer_pickup,
            drop_location=payload.transfer_drop,
            pickup_time=f"{payload.start_date}T19:00:00",
            status="CONFIRMED"
        )
        db.add(transfer)

    db.commit()
    db.refresh(trip)
    return {"message": "Trip created successfully", "trip_id": trip_id, "trip": trip}


@app.post("/api/trips/{trip_id}/flights")
def add_flight_to_trip(
    trip_id: str,
    payload: AddFlightSegmentRequest,
    db: Session = Depends(get_db)
):
    """
    Fetch real/demo flight data for a given flight number & date,
    then save the segment under the specified trip.
    """
    trip = db.query(models.Trip).filter(models.Trip.trip_id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    fs = get_flight_service()
    status = fs.get_flight_status(payload.flight_number, payload.travel_date)

    segment = models.FlightSegment(
        trip_id=trip_id,
        flight_number=status.flight_number,
        origin=status.origin.iata,
        destination=status.destination.iata,
        scheduled_departure=status.scheduled_departure or f"{payload.travel_date}T10:00:00",
        scheduled_arrival=status.scheduled_arrival or f"{payload.travel_date}T14:00:00",
        estimated_departure=status.estimated_departure or status.scheduled_departure or f"{payload.travel_date}T10:00:00",
        estimated_arrival=status.estimated_arrival or status.scheduled_arrival or f"{payload.travel_date}T14:00:00",
        actual_departure=status.actual_departure,
        actual_arrival=status.actual_arrival,
        status="CONFIRMED" if status.status not in ("CANCELLED", "DELAYED") else status.status,
        provider=fs.active_provider_name,
        data_source=status.data_source,
        last_status_check=now_iso(),
        delay_minutes=status.delay_minutes,
        terminal=status.destination.terminal,
        gate=status.destination.gate,
        airline_name=status.airline_name,
        origin_city=status.origin.city,
        destination_city=status.destination.city
    )

    db.add(segment)
    db.commit()
    db.refresh(segment)

    return {"message": "Flight segment added successfully", "segment": segment}


@app.delete("/api/trips/{trip_id}/flights/{segment_id}")
def remove_flight_segment(
    trip_id: str,
    segment_id: int,
    db: Session = Depends(get_db)
):
    """Remove a flight segment from a trip."""
    segment = db.query(models.FlightSegment).filter(
        models.FlightSegment.id == segment_id,
        models.FlightSegment.trip_id == trip_id
    ).first()

    if not segment:
        raise HTTPException(status_code=404, detail="Flight segment not found")

    db.delete(segment)
    db.commit()
    return {"message": "Flight segment deleted", "segment_id": segment_id}


@app.post("/api/recovery/{plan_id}/approve")
def approve_recovery_plan(
    plan_id: str,
    approval: ApprovalRequest,
    db: Session = Depends(get_db)
):
    """Approve or reject a pending recovery plan."""
    plan = db.query(models.RecoveryPlan).filter(
        models.RecoveryPlan.plan_id == plan_id
    ).first()

    if not plan:
        raise HTTPException(status_code=404, detail="Recovery plan not found")

    trip = db.query(models.Trip).filter(models.Trip.trip_id == plan.trip_id).first()

    if approval.approved:
        plan.status = "COMPLETED"
        if trip:
            trip.status = "RECOVERED"
        add_audit(db, plan.trip_id, "RECOVERY_APPROVED", f"Recovery plan {plan_id} approved by user")
    else:
        plan.status = "REJECTED"
        if trip:
            trip.status = "ESCALATED"
        add_audit(db, plan.trip_id, "RECOVERY_REJECTED", f"Recovery plan {plan_id} rejected by user")

    db.commit()
    return {"message": f"Recovery plan {'approved' if approval.approved else 'rejected'}", "plan": plan}


# ============================================================
# GET NOTIFICATIONS
# ============================================================

@app.get("/api/notifications/{trip_id}")
def get_notifications(
    trip_id: str,
    db: Session = Depends(get_db)
):

    notifications = db.query(
        models.Notification
    ).filter(
        models.Notification.trip_id
        == trip_id
    ).all()


    return {

        "count":
            len(notifications),

        "notifications":
            notifications

    }