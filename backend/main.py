from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from datetime import datetime, timedelta
import uuid
import json

from database import engine, SessionLocal
import models


# ============================================================
# DATABASE
# ============================================================

models.Base.metadata.create_all(bind=engine)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="ReRoute AI",
    description="Autonomous Travel Disruption Recovery Backend",
    version="2.0.0"
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

        "version": "2.0.0",

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

    minimum_buffer = 75


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

    if connection_buffer >= 75:

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