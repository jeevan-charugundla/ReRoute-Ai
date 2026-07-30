"""
ReRoute AI — External Flight Provider (AviationStack default)
=============================================================

Makes real HTTP calls to an external flight data API.

Default target: AviationStack (api.aviationstack.com)
  - Free tier: 500 calls/month
  - Auth: API key via `access_key` query parameter
  - Docs: https://aviationstack.com/documentation

TO SWAP PROVIDERS:
  Override the private `_parse_*` methods for your provider's JSON format.
  All other logic (caching, error handling, fallback) stays in FlightService.

CONFIGURATION (backend/.env):
  FLIGHT_PROVIDER=aviationstack
  FLIGHT_API_BASE_URL=http://api.aviationstack.com/v1
  FLIGHT_API_KEY=your_key_here
  FLIGHT_API_HOST=           # for RapidAPI-style providers
  FLIGHT_STATUS_CACHE_SECONDS=300

SECURITY:
  - Credentials are loaded from environment variables only
  - No credential is ever returned in API responses
  - Raw auth errors are caught and replaced with safe messages
"""

import logging
import os
import re
import time
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Optional

from services.flight_provider import (
    FlightProvider,
    NormalizedFlightStatus,
    NormalizedFlightOption,
    AirportInfo,
    AirlineInfo,
)

logger = logging.getLogger(__name__)

# Safe status normalization
_STATUS_MAP = {
    "scheduled": "SCHEDULED",
    "active": "ACTIVE",
    "landed": "LANDED",
    "cancelled": "CANCELLED",
    "diverted": "DIVERTED",
    "incident": "UNKNOWN",
    "redirected": "DIVERTED",
}


def _normalize_status(raw: Optional[str]) -> str:
    if not raw:
        return "UNKNOWN"
    return _STATUS_MAP.get(raw.lower(), raw.upper())


def _airline_code_from_flight(flight_number: str) -> str:
    code = ""
    for ch in flight_number:
        if ch.isalpha():
            code += ch
        else:
            break
    return code.upper()


class ExternalProvider(FlightProvider):
    """
    Generic external flight provider.

    Default format: AviationStack JSON.
    To adapt for another provider, override the `_parse_*` methods.
    """

    def __init__(self) -> None:
        self._api_key: str = os.getenv("FLIGHT_API_KEY", "")
        self._api_secret: str = os.getenv("FLIGHT_API_SECRET", "")
        self._base_url: str = os.getenv(
            "FLIGHT_API_BASE_URL", "http://api.aviationstack.com/v1"
        ).rstrip("/")
        self._api_host: str = os.getenv("FLIGHT_API_HOST", "")
        self._api_token: str = os.getenv("FLIGHT_API_TOKEN", "")
        self._timeout: float = 10.0

    @property
    def provider_name(self) -> str:
        provider = os.getenv("FLIGHT_PROVIDER", "external")
        return provider.capitalize() if provider else "External"

    # --------------------------------------------------------
    # INTERNAL HTTP HELPER
    # --------------------------------------------------------

    def _make_request(
        self,
        path: str,
        params: dict
    ) -> Optional[dict]:
        """
        Make a GET request to the provider using stdlib urllib.
        Returns parsed JSON dict or None on any failure.
        Never raises; never logs credentials.
        """
        safe_params = dict(params)

        headers: dict[str, str] = {
            "Accept": "application/json",
        }

        # AviationStack / query-param-key style
        if self._api_key:
            safe_params["access_key"] = self._api_key

        # RapidAPI style
        if self._api_host:
            headers["X-RapidAPI-Host"] = self._api_host
            if self._api_key:
                headers["X-RapidAPI-Key"] = self._api_key

        # Bearer token style
        if self._api_token:
            headers["Authorization"] = f"Bearer {self._api_token}"

        url = f"{self._base_url}/{path.lstrip('/')}"
        full_url = f"{url}?{urllib.parse.urlencode(safe_params)}"

        req = urllib.request.Request(full_url, headers=headers, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as response:
                status_code = response.status
                body = response.read().decode("utf-8")

        except urllib.error.HTTPError as e:
            status_code = e.code
            body = None

            if status_code == 401:
                logger.warning(
                    "ExternalProvider: authentication failed (401). "
                    "Check FLIGHT_API_KEY configuration."
                )
                return None

            if status_code == 403:
                logger.warning(
                    "ExternalProvider: access forbidden (403). "
                    "Check API plan or IP restrictions."
                )
                return None

            if status_code == 404:
                logger.info("ExternalProvider: resource not found (404) for %s", path)
                return None

            if status_code == 429:
                logger.warning(
                    "ExternalProvider: rate limit exceeded (429). "
                    "Consider increasing FLIGHT_STATUS_CACHE_SECONDS."
                )
                return None

            if status_code >= 500:
                logger.warning(
                    "ExternalProvider: provider returned server error %d", status_code
                )
                return None

            logger.warning("ExternalProvider: unexpected HTTP error %d", status_code)
            return None

        except urllib.error.URLError as e:
            reason = str(e.reason) if hasattr(e, 'reason') else str(e)
            if 'timed out' in reason.lower() or 'timeout' in reason.lower():
                logger.warning("ExternalProvider: request timed out (%ss)", self._timeout)
            else:
                logger.warning("ExternalProvider: network error — %s", type(e).__name__)
            return None

        except Exception as e:
            logger.error("ExternalProvider: unexpected error — %s", type(e).__name__)
            return None

        if body is None:
            return None

        try:
            data = json.loads(body)
        except Exception:
            logger.warning("ExternalProvider: failed to parse JSON response")
            return None

        # AviationStack wraps errors in the JSON body
        if isinstance(data, dict) and "error" in data:
            err = data["error"]
            code = err.get("code", "unknown") if isinstance(err, dict) else "unknown"
            logger.warning("ExternalProvider: API error code=%s", code)
            return None

        return data

    # --------------------------------------------------------
    # FLIGHT STATUS
    # --------------------------------------------------------

    def get_flight_status(
        self,
        flight_number: str,
        date: str,
        carrier: Optional[str] = None
    ) -> Optional[NormalizedFlightStatus]:
        """
        AviationStack: GET /flights?flight_iata=EK527&flight_date=2026-07-25
        """
        fn = flight_number.upper().replace(" ", "")

        params: dict = {
            "flight_iata": fn,
        }

        if date:
            params["flight_date"] = date

        data = self._make_request("flights", params)

        if data is None:
            return None

        # AviationStack wraps in {"pagination": {...}, "data": [...]}
        flights = data.get("data", [])
        if not flights:
            logger.info("ExternalProvider: no flights found for %s on %s", fn, date)
            return None

        raw = flights[0]
        return self._parse_flight_status(raw, fn)

    def _parse_flight_status(
        self,
        raw: dict,
        flight_number: str
    ) -> Optional[NormalizedFlightStatus]:
        """
        Parse AviationStack flight object into NormalizedFlightStatus.

        AviationStack structure (key fields):
        {
          "flight_date": "2026-07-25",
          "flight_status": "scheduled",
          "departure": {
            "airport": "Rajiv Gandhi International Airport",
            "iata": "HYD",
            "terminal": null,
            "gate": null,
            "scheduled": "2026-07-25T10:00:00+00:00",
            "estimated": "2026-07-25T10:00:00+00:00",
            "actual": null,
            "delay": 0
          },
          "arrival": {
            "airport": "Dubai International Airport",
            "iata": "DXB",
            "terminal": "3",
            "gate": null,
            "scheduled": "2026-07-25T12:30:00+00:00",
            "estimated": "2026-07-25T12:30:00+00:00",
            "actual": null,
            "delay": null
          },
          "airline": {
            "name": "Emirates",
            "iata": "EK"
          },
          "flight": {
            "number": "527",
            "iata": "EK527",
            "icao": "UAE527"
          }
        }
        """
        try:
            dep_raw = raw.get("departure", {}) or {}
            arr_raw = raw.get("arrival", {}) or {}
            airline_raw = raw.get("airline", {}) or {}
            flight_raw = raw.get("flight", {}) or {}

            airline_code = (
                airline_raw.get("iata")
                or _airline_code_from_flight(flight_number)
            )
            airline_name = airline_raw.get("name")

            origin = AirportInfo(
                iata=dep_raw.get("iata") or "???",
                name=dep_raw.get("airport"),
                city=dep_raw.get("city"),
                terminal=dep_raw.get("terminal"),
                gate=dep_raw.get("gate"),
            )

            destination = AirportInfo(
                iata=arr_raw.get("iata") or "???",
                name=arr_raw.get("airport"),
                city=arr_raw.get("city"),
                terminal=arr_raw.get("terminal"),
                gate=arr_raw.get("gate"),
            )

            # AviationStack delay is in minutes (int or None)
            dep_delay = dep_raw.get("delay") or 0
            arr_delay = arr_raw.get("delay") or 0
            delay_minutes = max(int(dep_delay), int(arr_delay), 0)

            status = _normalize_status(raw.get("flight_status"))

            fn = flight_raw.get("iata") or flight_number

            return NormalizedFlightStatus(
                flight_number=fn,
                airline_code=airline_code,
                airline_name=airline_name,
                origin=origin,
                destination=destination,
                scheduled_departure=dep_raw.get("scheduled"),
                estimated_departure=dep_raw.get("estimated"),
                actual_departure=dep_raw.get("actual"),
                scheduled_arrival=arr_raw.get("scheduled"),
                estimated_arrival=arr_raw.get("estimated"),
                actual_arrival=arr_raw.get("actual"),
                delay_minutes=delay_minutes,
                status=status,
                data_source="REAL",
                last_updated=time.strftime("%Y-%m-%dT%H:%M:%S"),
            )

        except Exception as e:
            logger.warning("ExternalProvider: failed to parse flight status — %s", e)
            return None

    # --------------------------------------------------------
    # FLIGHT SEARCH
    # --------------------------------------------------------

    def search_flights(
        self,
        origin: str,
        destination: str,
        date: str,
        cabin: Optional[str] = None
    ) -> list[NormalizedFlightOption]:
        """
        AviationStack: GET /flights?dep_iata=DXB&arr_iata=LHR&flight_date=...

        NOTE: AviationStack free tier does NOT support flight search with
        seat availability or pricing. If your provider supports it, adapt
        _parse_flight_option() accordingly.
        """
        params: dict = {
            "dep_iata": origin.upper(),
            "arr_iata": destination.upper(),
        }
        if date:
            params["flight_date"] = date

        data = self._make_request("flights", params)

        if data is None:
            return []

        flights_raw = data.get("data", [])
        if not flights_raw:
            return []

        results = []
        for raw in flights_raw:
            option = self._parse_flight_option(raw, cabin)
            if option:
                results.append(option)

        logger.info(
            "ExternalProvider.search_flights: %s→%s on %s returned %d options",
            origin, destination, date, len(results)
        )
        return results

    def _parse_flight_option(
        self,
        raw: dict,
        cabin: Optional[str]
    ) -> Optional[NormalizedFlightOption]:
        """
        Parse AviationStack flight into NormalizedFlightOption.

        IMPORTANT: AviationStack does NOT provide seat availability or
        rebooking cost. additional_cost is left as None, which causes the
        policy engine to require APPROVAL_REQUIRED rather than guessing.
        """
        try:
            dep_raw = raw.get("departure", {}) or {}
            arr_raw = raw.get("arrival", {}) or {}
            airline_raw = raw.get("airline", {}) or {}
            flight_raw = raw.get("flight", {}) or {}

            fn = flight_raw.get("iata") or ""
            if not fn:
                return None

            airline_code = airline_raw.get("iata") or _airline_code_from_flight(fn)
            airline_name = airline_raw.get("name")

            departure = dep_raw.get("estimated") or dep_raw.get("scheduled") or ""
            arrival = arr_raw.get("estimated") or arr_raw.get("scheduled") or ""

            if not departure or not arrival:
                return None

            flight_status = _normalize_status(raw.get("flight_status"))
            if flight_status in ("CANCELLED",):
                return None

            return NormalizedFlightOption(
                flight_number=fn,
                airline_code=airline_code,
                airline_name=airline_name,
                origin=dep_raw.get("iata") or "",
                destination=arr_raw.get("iata") or "",
                departure=departure,
                arrival=arrival,
                available_seats=None,    # AviationStack doesn't provide this
                market_price=None,       # AviationStack doesn't provide this
                additional_cost=None,    # Cannot determine rebooking cost from search API
                cabin=cabin or "ECONOMY",
                status="AVAILABLE",
                data_source="REAL",
            )

        except Exception as e:
            logger.warning("ExternalProvider: failed to parse flight option — %s", e)
            return None

    # --------------------------------------------------------
    # AIRPORT / AIRLINE LOOKUP
    # --------------------------------------------------------

    def get_airport(self, iata: str) -> Optional[AirportInfo]:
        """
        AviationStack: GET /airports?iata_code=HYD
        Only available on paid plans. Falls back gracefully.
        """
        data = self._make_request("airports", {"iata_code": iata.upper()})

        if not data:
            return None

        airports = data.get("data", [])
        if not airports:
            return None

        raw = airports[0]
        try:
            return AirportInfo(
                iata=raw.get("iata_code") or iata,
                name=raw.get("airport_name"),
                city=raw.get("city_iata_code") or raw.get("city"),
            )
        except Exception:
            return None

    def get_airline(self, code: str) -> Optional[AirlineInfo]:
        """
        AviationStack: GET /airlines?iata_code=EK
        Only available on paid plans. Falls back gracefully.
        """
        data = self._make_request("airlines", {"iata_code": code.upper()})

        if not data:
            return None

        airlines = data.get("data", [])
        if not airlines:
            return None

        raw = airlines[0]
        try:
            return AirlineInfo(
                code=raw.get("iata_code") or code,
                name=raw.get("airline_name"),
                callsign=raw.get("callsign"),
            )
        except Exception:
            return None
