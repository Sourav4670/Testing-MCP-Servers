"""
travel_tool.py – MCP Tool Handler: ``get_travel_advice``

This module contains the single tool that the Travel Advisor MCP server
exposes.  All advice is generated deterministically from the internal
``travel_data`` knowledge base – no external API calls, no environment
variables, no randomness.

Architecture
------------
``GetTravelAdviceToolHandler`` follows the same pattern as the weather server:

  ┌────────────────────────┐
  │  ToolHandler (abstract)│   ← toolhandler.py
  └───────────┬────────────┘
              │ inherits
  ┌───────────▼────────────┐
  │GetTravelAdviceToolHandler│  ← THIS FILE
  └───────────┬────────────┘
              │ calls
  ┌───────────▼────────────┐
  │    travel_data.py      │   ← pure-Python knowledge base
  └────────────────────────┘

Streaming note
--------------
The MCP tool itself returns a complete ``TextContent`` object.  Streaming
(chunked delivery) is handled at the transport layer:
- SSE transport sends each MCP message frame as a server-sent event.
- Streamable HTTP transport uses HTTP Transfer-Encoding: chunked.
Neither mode requires special handling inside this file.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime, date

from dateutil import parser as date_parser

from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

from .toolhandler import ToolHandler
from . import travel_data as td

logger = logging.getLogger("travel-advisor")


class GetTravelAdviceToolHandler(ToolHandler):
    """
    Handles the ``get_travel_advice`` MCP tool.

    Input
    -----
    origin       : str  – departure city / region
    destination  : str  – arrival city / region
    travel_date  : str  – ISO date (YYYY-MM-DD) OR natural language
                           e.g. "next Friday", "March 2026", "2026-04-01"

    Output
    ------
    A single ``TextContent`` item containing a richly-formatted Markdown
    string with five advisory sections:
      1. Weather Expectations
      2. Travel Safety
      3. Recommended Transport Mode
      4. Peak / Off-Peak Timing
      5. Popular Attractions
    """

    def __init__(self) -> None:
        super().__init__("get_travel_advice")

    # ------------------------------------------------------------------
    # MCP schema description (returned to clients via list_tools)
    # ------------------------------------------------------------------

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Get Travel Advice",
            description=(
                "Provide comprehensive real-time-style travel advice for a given "
                "origin, destination, and travel date. Returns weather expectations, "
                "safety guidance, recommended transport mode, peak/off-peak timing, "
                "and top attractions. All information is generated deterministically "
                "from an internal knowledge base – no external API calls required."
            ),
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "title": "GetTravelAdviceInput",
                "additionalProperties": False,
                "properties": {
                    "origin": {
                        "type": "string",
                        "title": "Origin",
                        "default": "London",
                        "description": (
                            "The city or location the traveller is departing from. "
                            "Examples: 'London', 'New York', 'Mumbai'."
                        ),
                    },
                    "destination": {
                        "type": "string",
                        "title": "Destination",
                        "default": "Paris",
                        "description": (
                            "The city or location the traveller is heading to. "
                            "Examples: 'Paris', 'Tokyo', 'Sydney'."
                        ),
                    },
                    "travel_date": {
                        "type": "string",
                        "title": "Travel Date",
                        "default": "2026-06-15",
                        "description": (
                            "When the trip is planned. Accepts ISO 8601 format "
                            "(YYYY-MM-DD), a month-year such as 'March 2026', "
                            "or relative phrases like 'next summer'. "
                            "If only a month or year is given, the first of that "
                            "month is assumed."
                        ),
                        "examples": ["2026-06-15", "June 2026", "next summer"],
                    },
                },
                "required": ["origin", "destination", "travel_date"],
            },
        )

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """
        Build and return the travel advisory for the requested trip.

        Steps
        -----
        1. Validate that all three required arguments are present.
        2. Parse the travel_date string into a Python ``date`` object.
        3. Look up city profiles, route data, and seasonal data from
           the static knowledge base.
        4. Compose a Markdown response string.
        5. Wrap it in a ``TextContent`` and return it.
        """
        try:
            self.validate_required_args(args, ["origin", "destination", "travel_date"])

            origin: str = args["origin"].strip()
            destination: str = args["destination"].strip()
            travel_date_raw: str = args["travel_date"].strip()

            logger.info(
                "get_travel_advice called: %s → %s on '%s'",
                origin,
                destination,
                travel_date_raw,
            )

            # ── Parse travel date ──────────────────────────────────────
            travel_dt = _parse_date(travel_date_raw)
            month = travel_dt.month

            # ── Data lookups ───────────────────────────────────────────
            dest_profile = td.get_city_profile(destination)
            season = td._season_from_month(month, td._normalise(destination))
            weather = td.get_weather_for_season(destination, season)
            safety = dest_profile.get("safety", "Check travel advisories")
            safety_tips = dest_profile.get("safety_tips", [])
            best_mode = dest_profile.get("best_mode", "Flying is the most practical option")
            timezone = dest_profile.get("timezone", "Verify locally")
            currency = dest_profile.get("currency", "Verify locally")
            language = dest_profile.get("language", "Verify locally")
            peak_info = td.get_peak_off_peak(month, destination)
            route = td.get_route_info(origin, destination)
            attractions = td.get_attractions(destination)
            month_profile = td.get_month_profile(month)

            # ── Compose the advisory ───────────────────────────────────
            advice = _build_advisory(
                origin=origin,
                destination=destination,
                travel_date_raw=travel_date_raw,
                travel_dt=travel_dt,
                season=season,
                weather=weather,
                dest_profile=dest_profile,
                safety=safety,
                safety_tips=safety_tips,
                best_mode=best_mode,
                timezone=timezone,
                currency=currency,
                language=language,
                peak_info=peak_info,
                route=route,
                attractions=attractions,
                month_profile=month_profile,
            )

            logger.info("get_travel_advice completed successfully for %s → %s", origin, destination)

            return [TextContent(type="text", text=advice)]

        except ValueError as exc:
            logger.error("Date parsing error: %s", exc)
            return [
                TextContent(
                    type="text",
                    text=f"⚠️ Could not parse the travel date '{args.get('travel_date')}'. "
                         f"Please use a format like '2026-06-15', 'June 2026', or 'next summer'. "
                         f"Error: {exc}",
                )
            ]
        except RuntimeError as exc:
            logger.error("Validation error: %s", exc)
            return [TextContent(type="text", text=f"⚠️ {exc}")]
        except Exception as exc:
            logger.exception("Unexpected error in get_travel_advice: %s", exc)
            return [
                TextContent(
                    type="text",
                    text=f"⚠️ An unexpected error occurred while generating travel advice: {exc}",
                )
            ]


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _parse_date(raw: str) -> date:
    """
    Convert *raw* (any reasonable date string) to a ``datetime.date``.

    Handles:
    - ISO 8601: "2026-06-15"
    - Month-year: "June 2026", "Jun 2026"
    - Season hints: "next summer", "winter 2026"
    - Partial year: "2026" → January 1 2026

    Falls back to ``dateutil.parser.parse`` for everything else,
    defaulting to the 1st of any month when only month+year is given.
    """
    raw_lower = raw.lower().strip()

    # Season-to-month mapping (northern hemisphere mid-point)
    season_to_month = {
        "spring": 4, "summer": 7, "autumn": 10, "fall": 10, "winter": 1,
    }

    # Check for season keyword + optional year
    for season_word, mid_month in season_to_month.items():
        if season_word in raw_lower:
            year = datetime.now().year
            # Look for a 4-digit year in the string
            import re
            m = re.search(r"\b(20\d{2})\b", raw)
            if m:
                year = int(m.group(1))
            return date(year, mid_month, 1)

    # Pure 4-digit year
    import re
    if re.fullmatch(r"20\d{2}", raw.strip()):
        return date(int(raw.strip()), 1, 1)

    # Delegate to dateutil with default=1st of month
    default_dt = datetime(datetime.now().year, 1, 1)
    parsed = date_parser.parse(raw, default=default_dt)
    return parsed.date()


def _build_advisory(
    *,
    origin: str,
    destination: str,
    travel_date_raw: str,
    travel_dt: date,
    season: str,
    weather: str,
    dest_profile: dict,
    safety: str,
    safety_tips: list[str],
    best_mode: str,
    timezone: str,
    currency: str,
    language: str,
    peak_info: str,
    route: dict | None,
    attractions: list[str],
    month_profile: dict,
) -> str:
    """
    Assemble the final Markdown advisory string from all collected data.

    All string interpolation is deterministic – no randomness, no I/O.
    """
    month_name  = travel_dt.strftime("%B")
    year        = travel_dt.year
    season_cap  = season.capitalize()
    month_season_note = month_profile.get("season", "")

    # ──────────────────────────────────────────────────────────────────
    lines: list[str] = []
    a = lines.append  # shorthand

    a(f"# ✈️  Real-Time Travel Advisory")
    a(f"**Route:** {origin} → {destination}")
    a(f"**Travel date:** {travel_dt.isoformat()} ({month_name} {year})")
    a(f"**Generated by:** Travel Advisor MCP Server v1.0")
    a("")

    # ── Section 1 – Weather ───────────────────────────────────────────
    a("---")
    a("## 🌤️  1. Weather Expectations")
    a(f"**Season at destination:** {season_cap}")
    a(f"**Climate type:** {dest_profile.get('climate', 'N/A')}")
    a(f"**Expected conditions ({month_name}):** {weather}")
    a("")
    a(f"> 📅 **Seasonal context:** {month_season_note}")
    a("")

    a("**Packing essentials for this season:**")
    packing = _packing_list(season, dest_profile.get("climate", ""))
    for item in packing:
        a(f"- {item}")
    a("")

    # ── Section 2 – Safety ────────────────────────────────────────────
    a("---")
    a("## 🛡️  2. Travel Safety")
    a(f"**Safety rating:** {safety}")
    if safety_tips:
        a("")
        a("**Safety tips:**")
        for tip in safety_tips:
            a(f"- {tip}")
    a("")
    a("**Essential travel documents:**")
    a("- Valid passport (6+ months remaining before expiry)")
    a("- Visa – check requirements for your nationality before booking")
    a("- Comprehensive travel insurance including medical evacuation")
    a(f"- Currency: **{currency}**  |  Language: **{language}**  |  Time zone: **{timezone}**")
    a("")

    # ── Section 3 – Transport ─────────────────────────────────────────
    a("---")
    a("## 🚆  3. Recommended Transport Mode")
    if route:
        a(f"**Best option for {origin} → {destination}:** {route['fastest_mode']}")
        a(f"**Alternatives:** {route['alternatives']}")
        if "note" in route:
            a(f"**Insider note:** {route['note']}")
        a(f"**Approximate distance:** {route.get('distance_km', 'N/A')} km")
        a(f"**Approx. direct flight time:** {route.get('direct_flight_hours', 'N/A')} h")
    else:
        a(f"**Recommended mode:** {best_mode}")
        available = [k.capitalize() for k, v in dest_profile.get("transport", {}).items() if v]
        if available:
            a(f"**Available modes at destination:** {', '.join(available)}")
    a("")
    a("**On-ground transport at destination:**")
    local_transport = _local_transport_tips(destination, dest_profile)
    for tip in local_transport:
        a(f"- {tip}")
    a("")

    # ── Section 4 – Peak / Off-Peak ───────────────────────────────────
    a("---")
    a("## 📊  4. Peak / Off-Peak Timing")
    a(f"**{month_name} {year} assessment:** {peak_info}")
    a("")
    a("**Booking strategy:**")
    booking_tips = _booking_strategy(peak_info)
    for tip in booking_tips:
        a(f"- {tip}")
    a("")

    # ── Section 5 – Attractions ───────────────────────────────────────
    a("---")
    a("## 🏛️  5. Popular Attractions in {dest}".format(dest=destination))
    for i, attraction in enumerate(attractions, 1):
        a(f"{i}. {attraction}")
    a("")
    a(f"> 💡 **Pro tip:** Many major attractions offer discounted or free entry on specific days.")
    a(f">  Check the official website before purchasing tickets.")
    a("")

    # ── Footer ────────────────────────────────────────────────────────
    a("---")
    a("*This advisory is generated from a curated internal knowledge base.*")
    a("*Always verify current conditions with your government's official travel advisory.*")

    return "\n".join(lines)


def _packing_list(season: str, climate: str) -> list[str]:
    """Return a deterministic packing checklist based on season and climate."""
    base = [
        "Travel adapter / universal power plug",
        "Medications and personal health kit",
        "Copies of travel documents (digital + paper)",
    ]
    season_items: dict[str, list[str]] = {
        "summer": [
            "Light, breathable clothing (cotton or linen)",
            "SPF 50+ sunscreen and UV-protection sunglasses",
            "Insect repellent (especially for tropical climates)",
            "Reusable water bottle – stay hydrated",
        ],
        "winter": [
            "Thermal base layers and warm mid-layer fleece",
            "Waterproof outer shell jacket",
            "Insulated gloves, hat, and thermal socks",
            "Lip balm and moisturiser – cold air dries skin",
        ],
        "spring": [
            "Light layers for variable temperatures",
            "Compact umbrella or waterproof jacket",
            "Comfortable walking shoes",
        ],
        "autumn": [
            "Medium-weight jacket or coat",
            "Comfortable walking shoes",
            "Compact umbrella – rainfall increases",
            "Camera – foliage and autumn light are spectacular",
        ],
    }
    return base + season_items.get(season, season_items["summer"])


def _local_transport_tips(city: str, profile: dict) -> list[str]:
    """Return 3–4 deterministic local transport tips for the destination."""
    transport = profile.get("transport", {})
    tips = []

    if transport.get("rail"):
        tips.append("Metro / urban rail is usually the fastest and cheapest way around the city")
    if transport.get("road"):
        tips.append("Taxis and ride-share apps (Uber, Grab, Ola, Lyft) are widely available")
    if transport.get("sea"):
        tips.append("Ferry or water-taxi services may offer scenic routes between key points")

    # City-specific overrides for deeper advice
    overrides: dict[str, list[str]] = {
        "tokyo": [
            "IC card (Suica or Pasmo) works on all trains, subways, and buses",
            "Google Maps gives accurate train times including platform numbers",
            "18-station Yamanote loop line circles most major districts",
        ],
        "london": [
            "Contactless bank card or Oyster card for all TfL transport",
            "Santander Cycles (Boris Bikes) available across central London",
            "Avoid the Tube at 08:00–09:30 and 17:00–18:30 if possible",
        ],
        "new york": [
            "MetroCard or OMNY contactless for subway and buses",
            "Avoid rush hour on the 4/5/6 and L lines",
            "CitiBike docking stations everywhere in Manhattan",
        ],
        "dubai": [
            "Dubai Metro Red and Green lines cover most tourist sites",
            "Nol card works on Metro, bus, tram, and water bus",
            "Taxis are metered and inexpensive compared to European cities",
        ],
        "singapore": [
            "Ez-link or NETS FlashPay card for MRT and buses",
            "MRT is air-conditioned and spotlessly clean",
            "Grab (super-app) for taxis, food, and delivery",
        ],
        "bangkok": [
            "BTS Skytrain Rabbit Card for easy travel above the traffic",
            "River taxi on Chao Phraya is scenic and avoids road congestion",
            "Moto-taxis (orange vests) for quick short-hops",
        ],
    }

    city_key = td._normalise(city)
    if city_key in overrides:
        return overrides[city_key]

    if not tips:
        tips.append("Verify local public transport options on arrival")
        tips.append("Hotel concierge is a reliable source for trusted taxi services")
    return tips


def _booking_strategy(peak_info: str) -> list[str]:
    """Return booking tips scaled to peak/shoulder/off-peak season."""
    peak_lower = peak_info.lower()
    if "peak" in peak_lower and "off" not in peak_lower:
        return [
            "Book flights 3–6 months in advance for best prices",
            "Reserve accommodation immediately – popular hotels sell out fast",
            "Pre-book attraction tickets online to skip long queues",
            "Consider travel insurance with cancellation cover",
            "Set price alerts on Google Flights or Skyscanner",
        ]
    elif "off-peak" in peak_lower:
        return [
            "Last-minute deals are often available – check 4–6 weeks ahead",
            "Flexible date searches can reveal savings of 30–50 %",
            "Many attractions have shorter queues and better photo opportunities",
            "Hotels are open to negotiation on price for longer stays",
        ]
    else:  # shoulder
        return [
            "Book 6–10 weeks ahead for a good balance of choice and price",
            "Shoulder season offers near-peak conditions with off-peak pricing",
            "Weekday travel is typically cheaper than weekend departures",
            "Check for local festivals that might create unexpected demand spikes",
        ]
