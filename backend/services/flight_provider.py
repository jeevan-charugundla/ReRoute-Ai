"""
ReRoute AI — Flight Provider Abstract Interface
===============================================

Defines the contract that every flight provider must implement.
Also defines all shared Pydantic schemas for normalized flight data.

The recovery engine, trip monitoring, and all API routes communicate
ONLY through these normalized schemas — never through raw provider data.
"""

from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel


# ============================================================
# NORMALIZED SCHEMAS
# These are the internal representations ReRoute works with.
# Providers must map their raw API responses to these models.
# ============================================================


class AirportInfo(BaseModel):
    """Normalized airport data."""

    iata: str
    name: Optional[str] = None
    city: Optional[str] = None
    terminal: Optional[str] = None
    gate: Optional[str] = None


class AirlineInfo(BaseModel):
    """Normalized airline data."""

    code: str
    name: Optional[str] = None
    callsign: Optional[str] = None


class NormalizedFlightStatus(BaseModel):
    """
    Normalized real-time flight status.

    Fields that the provider cannot supply are left as None.
    Never fabricate real-world data for None fields.
    """

    flight_number: str
    airline_code: str
    airline_name: Optional[str] = None

    origin: AirportInfo
    destination: AirportInfo

    scheduled_departure: Optional[str] = None
    estimated_departure: Optional[str] = None
    actual_departure: Optional[str] = None

    scheduled_arrival: Optional[str] = None
    estimated_arrival: Optional[str] = None
    actual_arrival: Optional[str] = None

    delay_minutes: int = 0

    # SCHEDULED | ACTIVE | LANDED | CANCELLED | DIVERTED | UNKNOWN
    status: str = "UNKNOWN"

    # REAL | CACHE | DEMO
    data_source: str = "DEMO"

    last_updated: Optional[str] = None

    # Non-sensitive warning shown when falling back to demo
    provider_warning: Optional[str] = None


class NormalizedFlightOption(BaseModel):
    """
    Normalized recovery flight search result.

    IMPORTANT: price/additional_cost from a search API represents
    a market fare, NOT a guaranteed rebooking cost.
    If rebooking cost cannot be reliably determined, leave additional_cost=None
    and let the policy engine require approval.
    """

    flight_number: str
    airline_code: str
    airline_name: Optional[str] = None

    origin: str
    destination: str

    departure: str
    arrival: str

    available_seats: Optional[int] = None

    # Market price from provider (not necessarily rebooking cost)
    market_price: Optional[float] = None
    currency: Optional[str] = None

    # Used by policy engine — None means cost is unknown → APPROVAL_REQUIRED
    additional_cost: Optional[int] = None

    cabin: str = "ECONOMY"

    # AVAILABLE | UNKNOWN
    status: str = "AVAILABLE"

    # REAL | DEMO
    data_source: str = "DEMO"


# ============================================================
# ABSTRACT PROVIDER CONTRACT
# ============================================================


class FlightProvider(ABC):
    """
    Abstract base class that every flight data provider must implement.

    Providers must:
    - Return None (not raise) when data is unavailable or the flight is not found
    - Raise exceptions only for unexpected/unrecoverable errors
    - Never log or return credentials
    - Set data_source correctly on every returned object
    """

    @abstractmethod
    def get_flight_status(
        self,
        flight_number: str,
        date: str,
        carrier: Optional[str] = None
    ) -> Optional[NormalizedFlightStatus]:
        """
        Fetch real-time status for a single flight.

        Parameters
        ----------
        flight_number : str
            Full flight number, e.g. "EK527"
        date : str
            Travel date in YYYY-MM-DD format
        carrier : str, optional
            2-letter IATA airline code if needed separately by the provider

        Returns
        -------
        NormalizedFlightStatus | None
            Normalized status, or None if not found / unavailable
        """
        ...

    @abstractmethod
    def search_flights(
        self,
        origin: str,
        destination: str,
        date: str,
        cabin: Optional[str] = None
    ) -> list[NormalizedFlightOption]:
        """
        Search for available flights on a given route and date.

        Parameters
        ----------
        origin : str
            Origin IATA airport code
        destination : str
            Destination IATA airport code
        date : str
            Travel date in YYYY-MM-DD format
        cabin : str, optional
            Cabin class preference, e.g. "ECONOMY"

        Returns
        -------
        list[NormalizedFlightOption]
            List of available flights (may be empty)
        """
        ...

    @abstractmethod
    def get_airport(self, iata: str) -> Optional[AirportInfo]:
        """
        Look up airport metadata by IATA code.

        Returns None if the provider doesn't support airport lookup
        or the airport is not found.
        """
        ...

    @abstractmethod
    def get_airline(self, code: str) -> Optional[AirlineInfo]:
        """
        Look up airline metadata by IATA code.

        Returns None if the provider doesn't support airline lookup
        or the airline is not found.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name for this provider, e.g. 'AviationStack'."""
        ...
