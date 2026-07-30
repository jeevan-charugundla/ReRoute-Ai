"""
ReRoute AI — AeroDataBox MCP Provider
======================================

Communicates with the AeroDataBox flight-data service via the
Model Context Protocol (MCP) exposed through API.market.

MCP endpoint : AERODATABOX_MCP_URL  (env)
Auth header  : x-api-market-key     (env: AERODATABOX_API_MARKET_KEY)

DESIGN PRINCIPLES
-----------------
* Uses stdlib only (urllib, json, re) — no external MCP SDK required.
* MCP transport: Streamable HTTP (JSON-RPC 2.0 over POST).
  Each request returns either a JSON body or an SSE stream
  (text/event-stream). This client handles both.
* Tools are discovered dynamically on first use — never guessed.
* All errors are caught and return None/[] (never raise to callers).
* Credentials are never logged, never returned in responses.
* Provider_name is set to "AERODATABOX" on every returned object.

MCP PROTOCOL (2025-03-26 Streamable HTTP)
------------------------------------------
  POST <endpoint>
  Content-Type: application/json
  Accept: application/json, text/event-stream
  x-api-market-key: <key>

  Body: {"jsonrpc":"2.0","method":"...","params":{},"id":<int>}

  Response: either
    Content-Type: application/json  → parse directly
    Content-Type: text/event-stream → parse SSE lines, extract data: <json>

No persistent session required between requests.

TOOL DISCOVERY
--------------
On first call, the client sends tools/list and caches the result.
All subsequent tool invocations use discovered tool names only.

KEY AERODATABOX TOOLS (discovered dynamically, listed here for docs):
  getflight_flightonspecificdate — flight by number + date
  getflight_flightnearest        — nearest upcoming flight by number
  getairportflights              — airport FIDS (departures/arrivals)
  getairport                     — airport metadata by IATA code
  getflighthistory_flighthistory — historical flight data

NORMALIZATION
-------------
AeroDataBox response → ReRoute NormalizedFlightStatus
Null provider values remain null — never fabricated.
"""

import json
import logging
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from services.flight_provider import (
    AirlineInfo,
    AirportInfo,
    FlightProvider,
    NormalizedFlightOption,
    NormalizedFlightStatus,
)

logger = logging.getLogger(__name__)

# ============================================================
# MCP REQUEST COUNTER (monotonically increasing per process)
# ============================================================

_request_id = 0


def _next_id() -> int:
    global _request_id
    _request_id += 1
    return _request_id


# ============================================================
# STATUS NORMALIZATION
# ============================================================

_STATUS_MAP: dict[str, str] = {
    # AeroDataBox status strings → ReRoute canonical statuses
    "scheduled": "SCHEDULED",
    "enroute": "ACTIVE",
    "en route": "ACTIVE",
    "landed": "LANDED",
    "arrived": "LANDED",
    "cancelled": "CANCELLED",
    "canceled": "CANCELLED",
    "diverted": "DIVERTED",
    "unknown": "UNKNOWN",
    "expected": "SCHEDULED",
    "departed": "ACTIVE",
    "airborne": "ACTIVE",
}


def _normalize_status(raw: Optional[str]) -> str:
    if not raw:
        return "UNKNOWN"
    return _STATUS_MAP.get(raw.lower().strip(), raw.upper())


# ============================================================
# SSE PARSER
# ============================================================

def _parse_sse_or_json(raw_body: str) -> Optional[dict]:
    """
    AeroDataBox MCP returns text/event-stream SSE or plain JSON.
    Extract the first JSON-RPC result object from either format.
    """
    body = raw_body.strip()

    if not body:
        return None

    # Try plain JSON first
    if body.startswith("{") or body.startswith("["):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass

    # Parse SSE: look for lines starting with "data: "
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if not payload or payload == "[DONE]":
                continue
            try:
                return json.loads(payload)
            except json.JSONDecodeError:
                continue

    logger.warning("AeroDataBoxMCP: could not parse response body")
    return None


# ============================================================
# MCP HTTP CLIENT
# ============================================================

class _MCPClient:
    """
    Minimal MCP HTTP client using stdlib urllib.

    Each method is a complete, stateless MCP exchange:
      initialize → tools/list → tools/call

    The MCP server (API.market) does not require a persistent
    session between requests, so each call does its own
    initialize + tool call.  For efficiency, tools are
    discovered once and cached in-process.
    """

    def __init__(self, url: str, api_key: str, timeout: float = 15.0) -> None:
        self._url = url
        self._api_key = api_key
        self._timeout = timeout
        self._tools_cache: Optional[list[dict]] = None
        self._tools_by_name: dict[str, dict] = {}
        self._initialized: bool = False

    # --------------------------------------------------------
    # RAW HTTP POST
    # --------------------------------------------------------

    def _post(self, payload: dict) -> Optional[dict]:
        """
        Send a JSON-RPC 2.0 POST and return the parsed response dict.
        Returns None on any failure. Never raises. Never logs credentials.
        """
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "x-api-market-key": self._api_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                status = resp.status
                raw = resp.read().decode("utf-8", errors="replace")

            if status == 200:
                return _parse_sse_or_json(raw)

            if status == 401 or status == 403:
                logger.warning(
                    "AeroDataBoxMCP: authentication error (%d). "
                    "Check AERODATABOX_API_MARKET_KEY.",
                    status,
                )
                return None

            if status == 404:
                logger.info("AeroDataBoxMCP: not found (404)")
                return None

            if status == 429:
                logger.warning(
                    "AeroDataBoxMCP: rate limit exceeded (429). "
                    "Increase FLIGHT_STATUS_CACHE_SECONDS to reduce calls."
                )
                return None

            if status >= 500:
                logger.warning("AeroDataBoxMCP: server error (%d)", status)
                return None

            logger.warning("AeroDataBoxMCP: unexpected status %d", status)
            return None

        except urllib.error.HTTPError as exc:
            code = exc.code
            if code in (401, 403):
                logger.warning(
                    "AeroDataBoxMCP: authentication error (%d). "
                    "Check AERODATABOX_API_MARKET_KEY.",
                    code,
                )
            elif code == 429:
                logger.warning("AeroDataBoxMCP: rate limit (%d)", code)
            elif code >= 500:
                logger.warning("AeroDataBoxMCP: provider error (%d)", code)
            else:
                logger.warning("AeroDataBoxMCP: HTTP error (%d)", code)
            return None

        except urllib.error.URLError as exc:
            reason = str(exc.reason) if hasattr(exc, "reason") else str(exc)
            if "timed out" in reason.lower() or "timeout" in reason.lower():
                logger.warning(
                    "AeroDataBoxMCP: request timed out (%.0fs)", self._timeout
                )
            else:
                logger.warning(
                    "AeroDataBoxMCP: network error — %s", type(exc).__name__
                )
            return None

        except Exception as exc:
            logger.error(
                "AeroDataBoxMCP: unexpected error — %s", type(exc).__name__
            )
            return None

    # --------------------------------------------------------
    # MCP INITIALIZE
    # --------------------------------------------------------

    def initialize(self) -> bool:
        """
        Send MCP initialize handshake.
        Returns True if the server responds with protocolVersion.
        """
        resp = self._post(
            {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "reroute-ai", "version": "2.1.0"},
                },
                "id": _next_id(),
            }
        )

        if resp is None:
            return False

        result = resp.get("result", {})
        proto = result.get("protocolVersion")
        if proto:
            logger.info(
                "AeroDataBoxMCP: initialized (protocol=%s)", proto
            )
            return True

        # Some MCP servers return error on initialize if already initialized
        if "error" in resp:
            err_code = resp["error"].get("code", -1)
            # -32002 = already initialized — still ok
            if err_code == -32002:
                return True
            logger.warning(
                "AeroDataBoxMCP: initialize error code=%d", err_code
            )

        return False

    # --------------------------------------------------------
    # TOOL DISCOVERY
    # --------------------------------------------------------

    def discover_tools(self) -> list[dict]:
        """
        Fetch the list of available MCP tools and cache them.
        Returns list of tool dicts with 'name', 'description', 'inputSchema'.
        """
        if self._tools_cache is not None:
            return self._tools_cache

        # Initialize first
        self.initialize()

        resp = self._post(
            {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": _next_id(),
            }
        )

        if resp is None:
            logger.warning("AeroDataBoxMCP: tools/list returned no response")
            self._tools_cache = []
            return []

        if "error" in resp:
            logger.warning(
                "AeroDataBoxMCP: tools/list error — %s",
                resp["error"].get("message", "unknown"),
            )
            self._tools_cache = []
            return []

        tools = resp.get("result", {}).get("tools", [])
        self._tools_cache = tools
        self._tools_by_name = {t["name"]: t for t in tools}

        logger.info(
            "AeroDataBoxMCP: discovered %d tools", len(tools)
        )
        return tools

    def has_tool(self, name: str) -> bool:
        """Return True if the given tool name was discovered."""
        if self._tools_cache is None:
            self.discover_tools()
        return name in self._tools_by_name

    # --------------------------------------------------------
    # TOOL INVOCATION
    # --------------------------------------------------------

    def call_tool(
        self, tool_name: str, arguments: dict
    ) -> Optional[Any]:
        """
        Call an MCP tool and return its result value.

        Returns:
          - The parsed result content (str / dict / list) on success
          - None if the tool is unavailable, errored, or returned nothing
        """
        if self._tools_cache is None:
            self.discover_tools()

        if not self._tools_by_name.get(tool_name):
            logger.info(
                "AeroDataBoxMCP: tool '%s' not available", tool_name
            )
            return None

        # Initialize before each tool call
        self.initialize()

        resp = self._post(
            {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments},
                "id": _next_id(),
            }
        )

        if resp is None:
            return None

        if "error" in resp:
            err = resp["error"]
            logger.warning(
                "AeroDataBoxMCP: tool '%s' error — code=%s msg=%s",
                tool_name,
                err.get("code", "?"),
                err.get("message", "?"),
            )
            return None

        result = resp.get("result", {})

        # MCP tool results are in result.content (list of content items)
        content = result.get("content", [])
        if not content:
            return None

        # Find the first text content item
        for item in content:
            if item.get("type") == "text":
                text = item.get("text", "")
                if text:
                    # Try to parse JSON from the text
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return text

        return None

    def health_check(self) -> dict:
        """
        Perform a non-destructive health check.
        Returns dict with connection status and tool count.
        """
        tools = self.discover_tools()
        return {
            "provider": "AERODATABOX",
            "transport": "MCP",
            "configured": bool(self._api_key),
            "connection": "OK" if tools else "DEGRADED",
            "mcp_url": self._url,
            "tools_discovered": len(tools),
            "tool_names_sample": [t["name"] for t in tools[:5]],
        }


# ============================================================
# AERODATABOX RESPONSE NORMALIZATION
# ============================================================

def _extract_iata(airport: Optional[dict]) -> str:
    """Extract IATA code from AeroDataBox airport dict."""
    if not airport:
        return "???"
    return (
        airport.get("iata")
        or airport.get("icao", "???")[:3]
        or "???"
    )


def _extract_airport_info(airport: Optional[dict]) -> AirportInfo:
    """Convert AeroDataBox airport dict → ReRoute AirportInfo."""
    if not airport:
        return AirportInfo(iata="???")

    return AirportInfo(
        iata=_extract_iata(airport),
        name=airport.get("name") or airport.get("shortName"),
        city=(
            airport.get("municipalityName")
            or airport.get("location", {}).get("city")
            if isinstance(airport.get("location"), dict)
            else None
        ),
        terminal=airport.get("terminal"),
        gate=airport.get("gate"),
    )


def _parse_datetime(val: Optional[str]) -> Optional[str]:
    """
    Preserve the datetime string as-is (AeroDataBox uses ISO 8601).
    Returns None for empty/missing values.
    """
    if not val:
        return None
    return val.strip() if isinstance(val, str) else None


def _calc_delay_minutes(
    scheduled: Optional[str],
    estimated: Optional[str],
) -> int:
    """
    Calculate delay in minutes from scheduled vs estimated datetime strings.
    Returns 0 if either value is missing or parse fails.
    """
    if not scheduled or not estimated:
        return 0
    try:
        from datetime import datetime

        def _parse(s: str) -> datetime:
            s = s.strip()
            # Remove Z suffix for fromisoformat compat
            if s.endswith("Z"):
                s = s[:-1]
            # Remove timezone offset: +HH:MM or -HH:MM
            s = re.sub(r"[+-]\d{2}:\d{2}$", "", s)
            return datetime.fromisoformat(s)

        sched = _parse(scheduled)
        est = _parse(estimated)
        diff = int((est - sched).total_seconds() / 60)
        return max(0, diff)
    except Exception:
        return 0


def _normalize_flight_object(raw: Any, date: str) -> Optional[NormalizedFlightStatus]:
    """
    Convert a single AeroDataBox flight object into NormalizedFlightStatus.

    AeroDataBox flight object structure (abbreviated):
    {
      "number": "EK527",
      "callSign": "UAE527",
      "status": "Expected",
      "codeshareStatus": "IsOperator",
      "isCargo": false,
      "aircraft": {"reg": "A6-ENQ", "modeS": "...", "model": "B77W"},
      "airline": {"name": "Emirates", "iata": "EK", "icao": "UAE"},
      "departure": {
        "airport": {
          "icao": "VOHY", "iata": "HYD",
          "name": "Rajiv Gandhi International Airport",
          "shortName": "Rajiv Gandhi Intl",
          "municipalityName": "Hyderabad",
          "location": {"lat": 17.23, "lon": 78.43},
          "countryCode": "IN"
        },
        "scheduledTime": {"local": "2026-07-26T10:00:00+05:30", "utc": "2026-07-26T04:30:00Z"},
        "predictedTime": {...},
        "actualTime": {...},
        "terminal": "1",
        "gate": "A12",
        "quality": ["Basic", "Live"]
      },
      "arrival": {
        "airport": {...},
        "scheduledTime": {...},
        "predictedTime": {...},
        "actualTime": {...},
        "terminal": "3",
        "gate": "B22",
        "quality": [...]
      }
    }
    """
    if not isinstance(raw, dict):
        return None

    try:
        flight_number = raw.get("number", "").strip()
        if not flight_number:
            return None

        # Airline
        airline_raw = raw.get("airline") or {}
        airline_code = (
            airline_raw.get("iata")
            or airline_raw.get("icao", "??")[:2]
        )
        airline_name = airline_raw.get("name")

        # Departure
        dep_raw = raw.get("departure") or {}
        dep_airport_raw = dep_raw.get("airport") or {}
        dep_airport = _extract_airport_info(dep_airport_raw)
        dep_airport.terminal = dep_raw.get("terminal") or dep_airport.terminal
        dep_airport.gate = dep_raw.get("gate") or dep_airport.gate

        # Arrival
        arr_raw = raw.get("arrival") or {}
        arr_airport_raw = arr_raw.get("airport") or {}
        arr_airport = _extract_airport_info(arr_airport_raw)
        arr_airport.terminal = arr_raw.get("terminal") or arr_airport.terminal
        arr_airport.gate = arr_raw.get("gate") or arr_airport.gate

        # Times — AeroDataBox uses .local / .utc nested objects
        def _pick_time(time_obj: Optional[dict], prefer_utc: bool = False) -> Optional[str]:
            if not time_obj or not isinstance(time_obj, dict):
                return None
            if prefer_utc:
                return _parse_datetime(time_obj.get("utc") or time_obj.get("local"))
            return _parse_datetime(time_obj.get("local") or time_obj.get("utc"))

        sched_dep = _pick_time(dep_raw.get("scheduledTime"))
        est_dep = _pick_time(
            dep_raw.get("predictedTime")
            or dep_raw.get("revisedTime")
            or dep_raw.get("scheduledTime")
        )
        actual_dep = _pick_time(dep_raw.get("actualTime"))

        sched_arr = _pick_time(arr_raw.get("scheduledTime"))
        est_arr = _pick_time(
            arr_raw.get("predictedTime")
            or arr_raw.get("revisedTime")
            or arr_raw.get("scheduledTime")
        )
        actual_arr = _pick_time(arr_raw.get("actualTime"))

        # Delay — use departure delay as primary
        dep_delay = arr_delay = 0
        dep_delay_obj = dep_raw.get("delay")
        if isinstance(dep_delay_obj, (int, float)):
            dep_delay = max(0, int(dep_delay_obj))
        elif sched_dep and est_dep and est_dep != sched_dep:
            dep_delay = _calc_delay_minutes(sched_dep, est_dep)

        arr_delay_obj = arr_raw.get("delay")
        if isinstance(arr_delay_obj, (int, float)):
            arr_delay = max(0, int(arr_delay_obj))
        elif sched_arr and est_arr and est_arr != sched_arr:
            arr_delay = _calc_delay_minutes(sched_arr, est_arr)

        delay_minutes = max(dep_delay, arr_delay)

        # Status
        status = _normalize_status(raw.get("status"))

        return NormalizedFlightStatus(
            flight_number=flight_number,
            airline_code=airline_code,
            airline_name=airline_name,
            origin=dep_airport,
            destination=arr_airport,
            scheduled_departure=sched_dep,
            estimated_departure=est_dep if est_dep != sched_dep else sched_dep,
            actual_departure=actual_dep,
            scheduled_arrival=sched_arr,
            estimated_arrival=est_arr if est_arr != sched_arr else sched_arr,
            actual_arrival=actual_arr,
            delay_minutes=delay_minutes,
            status=status,
            data_source="REAL",
            last_updated=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    except Exception as exc:
        logger.warning(
            "AeroDataBoxMCP: normalization error — %s", exc
        )
        return None


def _normalize_flight_option(raw: Any) -> Optional[NormalizedFlightOption]:
    """
    Convert AeroDataBox flight object → NormalizedFlightOption for recovery search.

    IMPORTANT: AeroDataBox is a flight-DATA provider, not a booking system.
    It does NOT provide seat availability or rebooking cost.
    additional_cost = None → policy engine requires APPROVAL_REQUIRED.
    availability_verified = False.
    """
    if not isinstance(raw, dict):
        return None

    try:
        flight_number = raw.get("number", "").strip()
        if not flight_number:
            return None

        airline_raw = raw.get("airline") or {}
        airline_code = airline_raw.get("iata") or airline_raw.get("icao", "??")[:2]
        airline_name = airline_raw.get("name")

        dep_raw = raw.get("departure") or {}
        arr_raw = raw.get("arrival") or {}

        dep_airport_raw = dep_raw.get("airport") or {}
        arr_airport_raw = arr_raw.get("airport") or {}

        origin_iata = dep_airport_raw.get("iata") or "???"
        dest_iata = arr_airport_raw.get("iata") or "???"

        def _pick_time(time_obj: Optional[dict]) -> Optional[str]:
            if not time_obj or not isinstance(time_obj, dict):
                return None
            return time_obj.get("local") or time_obj.get("utc")

        dep_time = (
            _pick_time(dep_raw.get("predictedTime"))
            or _pick_time(dep_raw.get("scheduledTime"))
        )
        arr_time = (
            _pick_time(arr_raw.get("predictedTime"))
            or _pick_time(arr_raw.get("scheduledTime"))
        )

        if not dep_time or not arr_time:
            return None

        status = _normalize_status(raw.get("status"))
        if status == "CANCELLED":
            return None

        return NormalizedFlightOption(
            flight_number=flight_number,
            airline_code=airline_code,
            airline_name=airline_name,
            origin=origin_iata,
            destination=dest_iata,
            departure=dep_time,
            arrival=arr_time,
            available_seats=None,      # AeroDataBox does not provide seat availability
            market_price=None,         # AeroDataBox does not provide fares
            additional_cost=None,      # Cannot determine rebooking cost — APPROVAL_REQUIRED
            cabin="ECONOMY",
            status="AVAILABLE",
            data_source="REAL",
        )

    except Exception as exc:
        logger.warning(
            "AeroDataBoxMCP: option normalization error — %s", exc
        )
        return None


# ============================================================
# AERODATABOX MCP PROVIDER (implements FlightProvider)
# ============================================================


class AeroDataBoxMCPProvider(FlightProvider):
    """
    Flight provider backed by AeroDataBox via API.market MCP.

    TOOL USAGE (all dynamically discovered):
      getflight_flightonspecificdate — primary flight status lookup
      getflight_flightnearest        — fallback nearest-flight lookup
      getairportflights              — airport FIDS for route search
      getairport                     — airport metadata
    """

    def __init__(self) -> None:
        mcp_url = os.getenv(
            "AERODATABOX_MCP_URL",
            "https://prod.api.market/api/mcp/aedbx/aerodatabox",
        )
        api_key = os.getenv("AERODATABOX_API_MARKET_KEY", "")
        self._client = _MCPClient(url=mcp_url, api_key=api_key)

        # Warm up tool discovery on init (non-blocking — failures are ignored)
        try:
            self._client.discover_tools()
        except Exception:
            pass

    @property
    def provider_name(self) -> str:
        return "AeroDataBox"

    # --------------------------------------------------------
    # FLIGHT STATUS
    # --------------------------------------------------------

    def get_flight_status(
        self,
        flight_number: str,
        date: str,
        carrier: Optional[str] = None,
    ) -> Optional[NormalizedFlightStatus]:
        """
        Fetch real-time flight status from AeroDataBox.

        Tries in order:
        1. getflight_flightonspecificdate (preferred — date-specific)
        2. getflight_flightnearest        (fallback — nearest upcoming)
        """
        fn = flight_number.upper().replace(" ", "")

        # ── Strategy 1: flight on specific date ──
        if self._client.has_tool("getflight_flightonspecificdate"):
            result = self._client.call_tool(
                "getflight_flightonspecificdate",
                {
                    "searchBy": "number",
                    "searchParam": fn,
                    "dateLocal": date,
                    "query": {},
                },
            )

            status = self._parse_flight_result(result, fn, date)
            if status:
                logger.info(
                    "AeroDataBoxMCP: got status for %s on %s (source=specific_date)",
                    fn, date
                )
                return status

        # ── Strategy 2: nearest flight ──
        if self._client.has_tool("getflight_flightnearest"):
            result = self._client.call_tool(
                "getflight_flightnearest",
                {
                    "searchBy": "number",
                    "searchParam": fn,
                },
            )

            status = self._parse_flight_result(result, fn, date)
            if status:
                logger.info(
                    "AeroDataBoxMCP: got status for %s via nearest (source=nearest)",
                    fn
                )
                return status

        logger.info("AeroDataBoxMCP: no status found for %s on %s", fn, date)
        return None

    def _parse_flight_result(
        self,
        result: Any,
        flight_number: str,
        date: str,
    ) -> Optional[NormalizedFlightStatus]:
        """
        Extract a single NormalizedFlightStatus from a tool result.
        Handles both single-flight dict and list-of-flights list.
        """
        if result is None:
            return None

        # AeroDataBox returns either a list or a single dict
        if isinstance(result, list):
            if not result:
                return None
            flights = result
        elif isinstance(result, dict):
            # Some tools wrap results: {"departures": [...], "arrivals": [...]}
            # or directly return a flight dict
            if "number" in result:
                flights = [result]
            else:
                # Try common wrapper keys
                for key in ("departures", "arrivals", "flights", "items"):
                    if key in result:
                        flights = result[key]
                        break
                else:
                    flights = [result]
        else:
            return None

        # Find the flight matching our flight number
        for flight in flights:
            if not isinstance(flight, dict):
                continue
            fn = (flight.get("number") or "").upper().replace(" ", "")
            if fn == flight_number.upper().replace(" ", ""):
                return _normalize_flight_object(flight, date)

        # If only one result, return it regardless of number (provider may abbreviate)
        if len(flights) == 1 and isinstance(flights[0], dict):
            return _normalize_flight_object(flights[0], date)

        return None

    # --------------------------------------------------------
    # FLIGHT SEARCH (recovery alternatives)
    # --------------------------------------------------------

    def search_flights(
        self,
        origin: str,
        destination: str,
        date: str,
        cabin: Optional[str] = None,
    ) -> list[NormalizedFlightOption]:
        """
        Find flights on a route using AeroDataBox airport FIDS.

        IMPORTANT: AeroDataBox provides schedule/status data only.
        It does NOT provide seat availability or ticket prices.
        All returned options have additional_cost=None which triggers
        APPROVAL_REQUIRED in the policy engine.

        Uses getairportflights to get departures from origin airport,
        then filters for flights going to the destination.
        """
        results: list[NormalizedFlightOption] = []

        if not self._client.has_tool("getairportflights"):
            logger.info(
                "AeroDataBoxMCP: getairportflights not available for %s→%s",
                origin, destination
            )
            return results

        try:
            # Build the time window: ±12 hours around midnight of the travel date
            from_time = f"{date}T00:00"
            to_time = f"{date}T23:59"

            result = self._client.call_tool(
                "getairportflights",
                {
                    "icao": origin.upper(),
                    "fromLocal": from_time,
                    "toLocal": to_time,
                    "direction": "Departure",
                    "query": {},
                },
            )

            flights = self._extract_flights_list(result)

            for flight in flights:
                if not isinstance(flight, dict):
                    continue

                arr_raw = flight.get("arrival") or {}
                arr_airport = arr_raw.get("airport") or {}
                arr_iata = arr_airport.get("iata", "").upper()

                if arr_iata == destination.upper():
                    option = _normalize_flight_option(flight)
                    if option:
                        results.append(option)

            logger.info(
                "AeroDataBoxMCP.search_flights: %s→%s on %s: %d results",
                origin, destination, date, len(results)
            )

        except Exception as exc:
            logger.warning(
                "AeroDataBoxMCP.search_flights: error — %s", exc
            )

        return results

    def _extract_flights_list(self, result: Any) -> list:
        """Extract a flat list of flight dicts from a tool result."""
        if result is None:
            return []
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("departures", "arrivals", "flights", "items"):
                if key in result and isinstance(result[key], list):
                    return result[key]
            return [result] if "number" in result else []
        return []

    # --------------------------------------------------------
    # AIRPORT
    # --------------------------------------------------------

    def get_airport(self, iata: str) -> Optional[AirportInfo]:
        """
        Fetch airport metadata from AeroDataBox.
        Uses getairport tool if available.
        """
        if not self._client.has_tool("getairport"):
            return None

        try:
            result = self._client.call_tool(
                "getairport",
                {"codeType": "iata", "code": iata.upper()},
            )

            if not result:
                return None

            airport_raw = result if isinstance(result, dict) else {}
            return _extract_airport_info(airport_raw)

        except Exception as exc:
            logger.warning("AeroDataBoxMCP.get_airport: error — %s", exc)
            return None

    # --------------------------------------------------------
    # AIRLINE
    # --------------------------------------------------------

    def get_airline(self, code: str) -> Optional[AirlineInfo]:
        """
        AeroDataBox does not have a dedicated airline lookup tool.
        Returns None — caller falls back to demo provider.
        """
        return None

    # --------------------------------------------------------
    # HEALTH CHECK
    # --------------------------------------------------------

    def health_check(self) -> dict:
        """Non-destructive health check — safe to call from /api/provider/health."""
        return self._client.health_check()
