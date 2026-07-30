"""
ReRoute AI — Flight Service
============================

Single point of contact for all flight data in the application.

Responsibilities:
1. Select the provider from FLIGHT_PROVIDER env var
2. Cache responses (TTL = FLIGHT_STATUS_CACHE_SECONDS)
3. Fall back to DemoProvider on any real-provider failure
4. Expose clean, provider-agnostic API to main.py and recovery engine

Provider selection (FLIGHT_PROVIDER):
  aerodatabox_mcp → AeroDataBoxMCPProvider (MCP over API.market)
  demo / empty    → DemoProvider (always offline)

Data flow:
  Request
    ↓
  Cache hit → return (data_source=CACHE)
    ↓
  Real provider → normalize → cache → return (data_source=REAL)
    ↓ (failure, ENABLE_DEMO_FALLBACK=true)
  Demo provider → return (data_source=DEMO) + provider_warning
"""

import logging
import os
import time
from typing import Optional

from services.flight_provider import (
    AirlineInfo,
    AirportInfo,
    FlightProvider,
    NormalizedFlightOption,
    NormalizedFlightStatus,
)
from services.demo_provider import DemoProvider

logger = logging.getLogger(__name__)


# ============================================================
# IN-MEMORY CACHE
# ============================================================

_cache: dict[str, tuple[float, object]] = {}


def _cache_key(*parts) -> str:
    return "|".join(str(p).upper() for p in parts)


def _cache_get(key: str, ttl: int) -> Optional[object]:
    entry = _cache.get(key)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > ttl:
        del _cache[key]
        return None
    return data


def _cache_set(key: str, data: object) -> None:
    _cache[key] = (time.time(), data)


def _cache_clear() -> None:
    _cache.clear()


# ============================================================
# PROVIDER FACTORY
# ============================================================

def _create_real_provider(provider_name: str) -> Optional[FlightProvider]:
    """
    Instantiate the real provider based on FLIGHT_PROVIDER env var.
    Returns None if the provider name is unknown or instantiation fails.
    """
    name = provider_name.lower().strip()

    if name in ("", "demo"):
        return None

    if name == "aerodatabox_mcp":
        try:
            from services.aerodatabox_mcp_provider import AeroDataBoxMCPProvider
            provider = AeroDataBoxMCPProvider()
            logger.info("FlightService: using AeroDataBox MCP provider")
            return provider
        except Exception as exc:
            logger.error(
                "FlightService: failed to load AeroDataBoxMCPProvider — %s",
                exc
            )
            return None

    # Legacy support for external REST providers
    if name in ("aviationstack", "aerodatabox", "external"):
        try:
            from services.external_provider import ExternalProvider
            provider = ExternalProvider()
            logger.info(
                "FlightService: using external REST provider (%s)", name
            )
            return provider
        except Exception as exc:
            logger.error(
                "FlightService: failed to load ExternalProvider — %s", exc
            )
            return None

    logger.warning(
        "FlightService: unknown FLIGHT_PROVIDER '%s', falling back to demo",
        provider_name
    )
    return None


# ============================================================
# FLIGHT SERVICE
# ============================================================

class FlightService:
    """
    Unified flight data service — provider-agnostic interface.

    Instantiate once at app startup and reuse for all requests.
    """

    def __init__(self) -> None:
        self._real_enabled: bool = (
            os.getenv("ENABLE_REAL_FLIGHT_DATA", "false").lower() == "true"
        )
        self._demo_fallback: bool = (
            os.getenv("ENABLE_DEMO_FALLBACK", "true").lower() == "true"
        )
        self._cache_ttl: int = int(
            os.getenv("FLIGHT_STATUS_CACHE_SECONDS", "300")
        )
        self._provider_name_cfg: str = os.getenv("FLIGHT_PROVIDER", "demo")

        self._demo: DemoProvider = DemoProvider()
        self._real: Optional[FlightProvider] = None

        if self._real_enabled:
            self._real = _create_real_provider(self._provider_name_cfg)

        if self._real:
            logger.info(
                "FlightService: real provider = %s, cache TTL = %ds",
                self._real.provider_name,
                self._cache_ttl,
            )
        else:
            logger.info(
                "FlightService: no real provider active, using demo"
            )

    @property
    def real_enabled(self) -> bool:
        return self._real_enabled and self._real is not None

    @property
    def active_provider_name(self) -> str:
        if self.real_enabled and self._real:
            return self._real.provider_name
        return "Demo"

    # --------------------------------------------------------
    # FLIGHT STATUS
    # --------------------------------------------------------

    def get_flight_status(
        self,
        flight_number: str,
        date: str,
        carrier: Optional[str] = None,
    ) -> NormalizedFlightStatus:
        """
        Get real-time flight status.

        data_source on returned object:
          REAL  — from live provider
          CACHE — recently fetched real data
          DEMO  — demo provider (by config or fallback)
        """
        key = _cache_key("status", flight_number, date)

        # Cache check
        cached = _cache_get(key, self._cache_ttl)
        if cached is not None and isinstance(cached, NormalizedFlightStatus):
            result = NormalizedFlightStatus(**cached.model_dump())
            result.data_source = "CACHE"
            logger.debug(
                "FlightService: cache hit for %s/%s", flight_number, date
            )
            return result

        # Real provider
        if self.real_enabled and self._real:
            try:
                result = self._real.get_flight_status(
                    flight_number, date, carrier
                )
                if result is not None:
                    _cache_set(key, result)
                    logger.info(
                        "FlightService: real status fetched for %s", flight_number
                    )
                    return result
                else:
                    logger.info(
                        "FlightService: real provider returned None for %s, "
                        "using fallback",
                        flight_number,
                    )
            except Exception as exc:
                logger.warning(
                    "FlightService: real provider error (%s) — using demo fallback",
                    type(exc).__name__,
                )

        # Demo fallback
        if self._demo_fallback or not self.real_enabled:
            result = self._demo.get_flight_status(flight_number, date, carrier)
            if result is None:
                result = NormalizedFlightStatus(
                    flight_number=flight_number,
                    airline_code=carrier or flight_number[:2].upper(),
                    origin=AirportInfo(iata="???"),
                    destination=AirportInfo(iata="???"),
                    status="UNKNOWN",
                    data_source="DEMO",
                )

            if self.real_enabled:
                result.provider_warning = (
                    "Real-time data unavailable. Demo fallback active."
                )
            return result

        return NormalizedFlightStatus(
            flight_number=flight_number,
            airline_code=carrier or "??",
            origin=AirportInfo(iata="???"),
            destination=AirportInfo(iata="???"),
            status="UNKNOWN",
            data_source="DEMO",
            provider_warning="No flight data available.",
        )

    # --------------------------------------------------------
    # FLIGHT SEARCH
    # --------------------------------------------------------

    def search_flights(
        self,
        origin: str,
        destination: str,
        date: str,
        cabin: Optional[str] = None,
    ) -> list[NormalizedFlightOption]:
        """
        Search for flights on a route (for recovery alternatives).
        """
        key = _cache_key("search", origin, destination, date, cabin or "")

        cached = _cache_get(key, self._cache_ttl)
        if cached is not None and isinstance(cached, list):
            results = []
            for item in cached:
                if isinstance(item, NormalizedFlightOption):
                    r = NormalizedFlightOption(**item.model_dump())
                    r.data_source = "CACHE"
                    results.append(r)
            if results:
                return results

        if self.real_enabled and self._real:
            try:
                results = self._real.search_flights(
                    origin, destination, date, cabin
                )
                if results:
                    _cache_set(key, results)
                    return results
            except Exception as exc:
                logger.warning(
                    "FlightService.search_flights: real error (%s)",
                    type(exc).__name__,
                )

        return self._demo.search_flights(origin, destination, date, cabin)

    # --------------------------------------------------------
    # AIRPORT
    # --------------------------------------------------------

    def get_airport(self, iata: str) -> Optional[AirportInfo]:
        key = _cache_key("airport", iata)
        # Airports change rarely — use longer TTL
        cached = _cache_get(key, self._cache_ttl * 24)
        if cached is not None:
            return cached

        if self.real_enabled and self._real:
            try:
                result = self._real.get_airport(iata)
                if result:
                    _cache_set(key, result)
                    return result
            except Exception:
                pass

        return self._demo.get_airport(iata)

    # --------------------------------------------------------
    # AIRLINE
    # --------------------------------------------------------

    def get_airline(self, code: str) -> Optional[AirlineInfo]:
        key = _cache_key("airline", code)
        cached = _cache_get(key, self._cache_ttl * 24)
        if cached is not None:
            return cached

        if self.real_enabled and self._real:
            try:
                result = self._real.get_airline(code)
                if result:
                    _cache_set(key, result)
                    return result
            except Exception:
                pass

        return self._demo.get_airline(code)

    # --------------------------------------------------------
    # HEALTH CHECK
    # --------------------------------------------------------

    def health_check(self) -> dict:
        """
        Return provider health info. Safe to expose from API.
        Never includes credentials.
        """
        base = {
            "real_data_enabled": self.real_enabled,
            "demo_fallback_enabled": self._demo_fallback,
            "cache_ttl_seconds": self._cache_ttl,
            "active_provider": self.active_provider_name,
        }

        if self.real_enabled and self._real and hasattr(self._real, "health_check"):
            try:
                provider_health = self._real.health_check()
                base.update(provider_health)
            except Exception:
                base["connection"] = "ERROR"
        elif not self.real_enabled:
            base["provider"] = "DEMO"
            base["connection"] = "OK"
            base["configured"] = True

        return base

    # --------------------------------------------------------
    # CACHE MANAGEMENT
    # --------------------------------------------------------

    def clear_cache(self) -> None:
        _cache_clear()
        logger.info("FlightService: cache cleared")

    def get_cache_info(self) -> dict:
        now = time.time()
        entries = []
        for key, (ts, _) in _cache.items():
            age = int(now - ts)
            entries.append({
                "key": key,
                "age_seconds": age,
                "expires_in": max(0, self._cache_ttl - age),
            })
        return {
            "count": len(_cache),
            "ttl_seconds": self._cache_ttl,
            "entries": entries,
        }


# ============================================================
# SINGLETON
# ============================================================

_flight_service: Optional[FlightService] = None


def get_flight_service() -> FlightService:
    """Return the process-wide singleton FlightService."""
    global _flight_service
    if _flight_service is None:
        _flight_service = FlightService()
    return _flight_service


def reset_flight_service() -> None:
    """Reset the singleton (useful after config changes in tests)."""
    global _flight_service
    _flight_service = None
