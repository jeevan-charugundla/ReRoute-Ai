"""
ReRoute AI — Demo Flight Provider
==================================

Returns demo data sourced from the existing database Flight inventory
and hardcoded airport/airline metadata.

This provider:
- Always works offline (no network required)
- Uses the existing recovery flight inventory from the SQLite DB
- Returns data_source = "DEMO" on all objects
- Is the guaranteed fallback for hackathon presentations
"""

import logging
from typing import Optional
from datetime import datetime

from services.flight_provider import (
    FlightProvider,
    NormalizedFlightStatus,
    NormalizedFlightOption,
    AirportInfo,
    AirlineInfo,
)

logger = logging.getLogger(__name__)


# ============================================================
# STATIC DEMO DATA
# ============================================================

DEMO_AIRPORTS: dict[str, AirportInfo] = {
    "HYD": AirportInfo(
        iata="HYD",
        name="Rajiv Gandhi International Airport",
        city="Hyderabad",
    ),
    "DXB": AirportInfo(
        iata="DXB",
        name="Dubai International Airport",
        city="Dubai",
    ),
    "LHR": AirportInfo(
        iata="LHR",
        name="London Heathrow Airport",
        city="London",
    ),
    "BOM": AirportInfo(
        iata="BOM",
        name="Chhatrapati Shivaji Maharaj International Airport",
        city="Mumbai",
    ),
    "DEL": AirportInfo(
        iata="DEL",
        name="Indira Gandhi International Airport",
        city="New Delhi",
    ),
    "SIN": AirportInfo(
        iata="SIN",
        name="Singapore Changi Airport",
        city="Singapore",
    ),
}

DEMO_AIRLINES: dict[str, AirlineInfo] = {
    "EK": AirlineInfo(code="EK", name="Emirates", callsign="EMIRATES"),
    "BA": AirlineInfo(code="BA", name="British Airways", callsign="SPEEDBIRD"),
    "AI": AirlineInfo(code="AI", name="Air India", callsign="AIR INDIA"),
    "6E": AirlineInfo(code="6E", name="IndiGo", callsign="INTERGLOBE"),
    "UK": AirlineInfo(code="UK", name="Vistara", callsign="VISTARA"),
    "SQ": AirlineInfo(code="SQ", name="Singapore Airlines", callsign="SINGAPORE"),
    "QR": AirlineInfo(code="QR", name="Qatar Airways", callsign="QATARI"),
}

# Demo flight statuses for known flights
DEMO_FLIGHT_STATUSES: dict[str, dict] = {
    "EK527": {
        "flight_number": "EK527",
        "airline_code": "EK",
        "origin_iata": "HYD",
        "destination_iata": "DXB",
        "scheduled_departure": "2026-07-24T10:00:00",
        "scheduled_arrival": "2026-07-24T12:30:00",
        "estimated_departure": "2026-07-24T10:00:00",
        "estimated_arrival": "2026-07-24T12:30:00",
        "status": "SCHEDULED",
        "delay_minutes": 0,
    },
    "EK001": {
        "flight_number": "EK001",
        "airline_code": "EK",
        "origin_iata": "DXB",
        "destination_iata": "LHR",
        "scheduled_departure": "2026-07-24T14:00:00",
        "scheduled_arrival": "2026-07-24T18:30:00",
        "estimated_departure": "2026-07-24T14:00:00",
        "estimated_arrival": "2026-07-24T18:30:00",
        "status": "SCHEDULED",
        "delay_minutes": 0,
    },
    "EK003": {
        "flight_number": "EK003",
        "airline_code": "EK",
        "origin_iata": "DXB",
        "destination_iata": "LHR",
        "scheduled_departure": "2026-07-24T16:30:00",
        "scheduled_arrival": "2026-07-24T21:10:00",
        "estimated_departure": "2026-07-24T16:30:00",
        "estimated_arrival": "2026-07-24T21:10:00",
        "status": "SCHEDULED",
        "delay_minutes": 0,
    },
    "BA106": {
        "flight_number": "BA106",
        "airline_code": "BA",
        "origin_iata": "DXB",
        "destination_iata": "LHR",
        "scheduled_departure": "2026-07-24T17:10:00",
        "scheduled_arrival": "2026-07-24T21:00:00",
        "estimated_departure": "2026-07-24T17:10:00",
        "estimated_arrival": "2026-07-24T21:00:00",
        "status": "SCHEDULED",
        "delay_minutes": 0,
    },
    "EK005": {
        "flight_number": "EK005",
        "airline_code": "EK",
        "origin_iata": "DXB",
        "destination_iata": "LHR",
        "scheduled_departure": "2026-07-24T18:00:00",
        "scheduled_arrival": "2026-07-24T22:40:00",
        "estimated_departure": "2026-07-24T18:00:00",
        "estimated_arrival": "2026-07-24T22:40:00",
        "status": "SCHEDULED",
        "delay_minutes": 0,
    },
    "EK009": {
        "flight_number": "EK009",
        "airline_code": "EK",
        "origin_iata": "DXB",
        "destination_iata": "LHR",
        "scheduled_departure": "2026-07-24T15:30:00",
        "scheduled_arrival": "2026-07-24T20:15:00",
        "estimated_departure": "2026-07-24T15:30:00",
        "estimated_arrival": "2026-07-24T20:15:00",
        "status": "SCHEDULED",
        "delay_minutes": 0,
    },
}


def _get_airline_code_from_flight(flight_number: str) -> str:
    """Extract IATA airline code from flight number string."""
    code = ""
    for ch in flight_number:
        if ch.isalpha():
            code += ch
        else:
            break
    return code.upper()


class DemoProvider(FlightProvider):
    """
    Demo flight provider — always offline, always reliable.

    Uses static flight data and the existing SQLite inventory.
    Perfect for hackathon presentations when real API is unavailable.
    """

    @property
    def provider_name(self) -> str:
        return "Demo"

    def get_flight_status(
        self,
        flight_number: str,
        date: str,
        carrier: Optional[str] = None
    ) -> Optional[NormalizedFlightStatus]:
        """
        Return demo status for a known flight.
        Returns None for completely unknown flight numbers.
        """
        fn = flight_number.upper().replace(" ", "")

        raw = DEMO_FLIGHT_STATUSES.get(fn)

        if raw is None:
            # Generate a generic demo status for any unknown flight
            airline_code = carrier or _get_airline_code_from_flight(fn)
            logger.debug(
                "DemoProvider: no static data for %s, generating generic", fn
            )
            return NormalizedFlightStatus(
                flight_number=fn,
                airline_code=airline_code,
                airline_name=DEMO_AIRLINES.get(airline_code, AirlineInfo(code=airline_code)).name,
                origin=AirportInfo(iata="???"),
                destination=AirportInfo(iata="???"),
                scheduled_departure=f"{date}T10:00:00",
                estimated_departure=f"{date}T10:00:00",
                scheduled_arrival=f"{date}T14:00:00",
                estimated_arrival=f"{date}T14:00:00",
                delay_minutes=0,
                status="SCHEDULED",
                data_source="DEMO",
                last_updated=datetime.utcnow().isoformat(),
            )

        airline_code = raw["airline_code"]
        airline_info = DEMO_AIRLINES.get(airline_code)
        origin_info = DEMO_AIRPORTS.get(raw["origin_iata"], AirportInfo(iata=raw["origin_iata"]))
        dest_info = DEMO_AIRPORTS.get(raw["destination_iata"], AirportInfo(iata=raw["destination_iata"]))

        return NormalizedFlightStatus(
            flight_number=fn,
            airline_code=airline_code,
            airline_name=airline_info.name if airline_info else None,
            origin=origin_info,
            destination=dest_info,
            scheduled_departure=raw.get("scheduled_departure"),
            estimated_departure=raw.get("estimated_departure"),
            actual_departure=raw.get("actual_departure"),
            scheduled_arrival=raw.get("scheduled_arrival"),
            estimated_arrival=raw.get("estimated_arrival"),
            actual_arrival=raw.get("actual_arrival"),
            delay_minutes=raw.get("delay_minutes", 0),
            status=raw.get("status", "SCHEDULED"),
            data_source="DEMO",
            last_updated=datetime.utcnow().isoformat(),
        )

    def search_flights(
        self,
        origin: str,
        destination: str,
        date: str,
        cabin: Optional[str] = None
    ) -> list[NormalizedFlightOption]:
        """
        Return demo recovery flight options for the DXB→LHR route.
        For other routes, return a generic empty list.
        """
        results = []

        for fn, raw in DEMO_FLIGHT_STATUSES.items():
            if (
                raw.get("origin_iata") == origin.upper()
                and raw.get("destination_iata") == destination.upper()
            ):
                airline_code = raw["airline_code"]
                airline_info = DEMO_AIRLINES.get(airline_code)
                results.append(
                    NormalizedFlightOption(
                        flight_number=fn,
                        airline_code=airline_code,
                        airline_name=airline_info.name if airline_info else None,
                        origin=origin.upper(),
                        destination=destination.upper(),
                        departure=raw.get("scheduled_departure", f"{date}T12:00:00"),
                        arrival=raw.get("scheduled_arrival", f"{date}T16:00:00"),
                        available_seats=5,
                        additional_cost=0,
                        cabin=cabin or "ECONOMY",
                        status="AVAILABLE",
                        data_source="DEMO",
                    )
                )

        logger.debug(
            "DemoProvider.search_flights: %s→%s returned %d results",
            origin, destination, len(results)
        )
        return results

    def get_airport(self, iata: str) -> Optional[AirportInfo]:
        return DEMO_AIRPORTS.get(iata.upper())

    def get_airline(self, code: str) -> Optional[AirlineInfo]:
        return DEMO_AIRLINES.get(code.upper())
