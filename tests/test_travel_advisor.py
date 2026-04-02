"""
Tests for the Travel Advisor MCP Server.

Run with:
  cd travel-advisor-mcp
  pip install -e ".[dev]"
  pytest tests/ -v

All tests are deterministic – no network calls, no randomness.
"""

from __future__ import annotations

import pytest

# ── Travel data unit tests ──────────────────────────────────────────────────

from src.travel_advisor.tools.travel_data import (
    get_city_profile,
    get_attractions,
    get_route_info,
    get_month_profile,
    get_weather_for_season,
    get_peak_off_peak,
    _normalise,
    _season_from_month,
)


class TestNormalise:
    def test_lowercase(self):
        assert _normalise("London") == "london"

    def test_strips_whitespace(self):
        assert _normalise("  Tokyo  ") == "tokyo"

    def test_mixed_case(self):
        assert _normalise("New York") == "new york"


class TestGetCityProfile:
    def test_known_city_exact(self):
        profile = get_city_profile("Paris")
        assert profile["country"] == "France"
        assert "climate" in profile

    def test_known_city_case_insensitive(self):
        assert get_city_profile("TOKYO")["country"] == "Japan"

    def test_partial_match(self):
        # "new york city" should match "new york"
        profile = get_city_profile("New York City")
        assert profile["country"] == "USA"

    def test_unknown_city_returns_fallback(self):
        profile = get_city_profile("Atlantis")
        assert profile["country"] == "Unknown"
        assert "climate" in profile

    def test_all_known_cities_have_required_keys(self):
        from src.travel_advisor.tools.travel_data import CITY_DATA
        required = {"country", "climate", "summer", "winter", "spring", "autumn",
                    "safety", "safety_tips", "transport", "best_mode", "timezone",
                    "currency", "language"}
        for city, data in CITY_DATA.items():
            missing = required - data.keys()
            assert not missing, f"{city} is missing keys: {missing}"


class TestGetAttractions:
    def test_known_city(self):
        attractions = get_attractions("london")
        assert len(attractions) == 5
        assert any("British Museum" in s for s in attractions)

    def test_case_insensitive(self):
        assert get_attractions("TOKYO") == get_attractions("tokyo")

    def test_unknown_city_fallback(self):
        attractions = get_attractions("Atlantis")
        assert len(attractions) > 0  # generic list


class TestGetRouteInfo:
    def test_known_route(self):
        route = get_route_info("London", "Paris")
        assert route is not None
        assert "Eurostar" in route["fastest_mode"]

    def test_known_route_reversed(self):
        # Route lookup is order-independent
        assert get_route_info("Paris", "London") == get_route_info("London", "Paris")

    def test_unknown_route_returns_none(self):
        assert get_route_info("London", "Atlantis") is None


class TestGetMonthProfile:
    def test_known_month(self):
        profile = get_month_profile(7)
        assert profile["name"] == "July"

    def test_all_months_present(self):
        for m in range(1, 13):
            p = get_month_profile(m)
            assert "name" in p


class TestSeasonFromMonth:
    def test_northern_summer(self):
        assert _season_from_month(7, "london") == "summer"

    def test_northern_winter(self):
        assert _season_from_month(1, "london") == "winter"

    def test_southern_hemisphere_flip(self):
        # July in Sydney → winter (Australia)
        assert _season_from_month(7, "sydney") == "winter"
        # December in Sydney → summer
        assert _season_from_month(12, "sydney") == "summer"


class TestGetPeakOffPeak:
    def test_peak_august_london(self):
        result = get_peak_off_peak(8, "London")
        assert "PEAK" in result

    def test_off_peak_november_london(self):
        result = get_peak_off_peak(11, "London")
        assert "OFF-PEAK" in result

    def test_shoulder_october(self):
        result = get_peak_off_peak(10, "London")
        assert "SHOULDER" in result


class TestGetWeatherForSeason:
    def test_summer_london(self):
        weather = get_weather_for_season("london", "summer")
        assert "°C" in weather or len(weather) > 5  # contains meaningful text

    def test_winter_tokyo(self):
        weather = get_weather_for_season("tokyo", "winter")
        assert len(weather) > 5


# ── Travel tool integration tests ──────────────────────────────────────────

import asyncio
from src.travel_advisor.tools.travel_tool import GetTravelAdviceToolHandler
from mcp.types import TextContent


class TestGetTravelAdviceToolHandler:
    """Integration tests that exercise the full run_tool path."""

    @pytest.fixture
    def handler(self):
        return GetTravelAdviceToolHandler()

    def _run(self, coro):
        """Helper to run a coroutine in pytest (no async native needed for 3.10+)."""
        return asyncio.get_event_loop().run_until_complete(coro)

    # ── Schema tests ───────────────────────────────────────────────────

    def test_tool_description_name(self, handler):
        desc = handler.get_tool_description()
        assert desc.name == "get_travel_advice"

    def test_tool_description_required_params(self, handler):
        schema = handler.get_tool_description().inputSchema
        assert "origin" in schema["properties"]
        assert "destination" in schema["properties"]
        assert "travel_date" in schema["properties"]
        assert set(schema["required"]) == {"origin", "destination", "travel_date"}

    # ── Execution tests ────────────────────────────────────────────────

    def test_known_route_london_paris(self, handler):
        result = self._run(handler.run_tool({
            "origin": "London",
            "destination": "Paris",
            "travel_date": "2026-07-15",
        }))
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        text = result[0].text
        assert "Paris" in text
        assert "London" in text
        assert "Weather" in text
        assert "Safety" in text
        assert "Transport" in text
        assert "Attraction" in text

    def test_unknown_city_returns_fallback_content(self, handler):
        result = self._run(handler.run_tool({
            "origin": "Westeros",
            "destination": "Narnia",
            "travel_date": "2026-03-01",
        }))
        assert len(result) == 1
        text = result[0].text
        assert "Narnia" in text  # destination name always appears
        assert "Travel Advisor" in text

    def test_determinism(self, handler):
        """Same inputs must always produce identical outputs."""
        args = {"origin": "Tokyo", "destination": "Singapore", "travel_date": "2026-10-01"}
        r1 = self._run(handler.run_tool(args))
        r2 = self._run(handler.run_tool(args))
        assert r1[0].text == r2[0].text

    def test_missing_origin_returns_error_text(self, handler):
        result = self._run(handler.run_tool({
            "destination": "Paris",
            "travel_date": "2026-05-01",
        }))
        assert len(result) == 1
        assert "⚠️" in result[0].text

    def test_missing_destination_returns_error_text(self, handler):
        result = self._run(handler.run_tool({
            "origin": "London",
            "travel_date": "2026-05-01",
        }))
        assert len(result) == 1
        assert "⚠️" in result[0].text

    def test_natural_language_date_next_summer(self, handler):
        result = self._run(handler.run_tool({
            "origin": "New York",
            "destination": "Sydney",
            "travel_date": "next summer",
        }))
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Sydney" in result[0].text

    def test_month_year_date(self, handler):
        result = self._run(handler.run_tool({
            "origin": "Delhi",
            "destination": "Mumbai",
            "travel_date": "December 2026",
        }))
        assert "December" in result[0].text

    def test_iso_date(self, handler):
        result = self._run(handler.run_tool({
            "origin": "Berlin",
            "destination": "Amsterdam",
            "travel_date": "2026-04-20",
        }))
        assert "Amsterdam" in result[0].text

    def test_all_five_sections_present(self, handler):
        result = self._run(handler.run_tool({
            "origin": "Dubai",
            "destination": "Bangkok",
            "travel_date": "2026-11-10",
        }))
        text = result[0].text
        for section_head in [
            "Weather Expectations",
            "Travel Safety",
            "Recommended Transport",
            "Peak / Off-Peak",
            "Popular Attractions",
        ]:
            assert section_head in text, f"Missing section: {section_head}"

    def test_peak_season_booking_advice_in_july(self, handler):
        result = self._run(handler.run_tool({
            "origin": "Chicago",
            "destination": "London",
            "travel_date": "2026-07-01",
        }))
        text = result[0].text
        assert "PEAK" in text

    def test_off_peak_season_in_february(self, handler):
        result = self._run(handler.run_tool({
            "origin": "Los Angeles",
            "destination": "London",
            "travel_date": "2026-02-01",
        }))
        text = result[0].text
        assert "OFF-PEAK" in text

    def test_attractions_count_five(self, handler):
        """Top attractions list should have exactly 5 entries for a known city."""
        result = self._run(handler.run_tool({
            "origin": "London",
            "destination": "Rome",
            "travel_date": "2026-05-01",
        }))
        text = result[0].text
        # Look for numbered list items 1–5
        for n in range(1, 6):
            assert f"{n}. " in text
