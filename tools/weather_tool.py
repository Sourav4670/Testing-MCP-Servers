"""weather_tool.py - MCP tool handler for ``get_weather``.

This module exposes a single tool that fetches current weather data for a city
using OpenStreetMap Nominatim (geocoding) and Open-Meteo (weather).
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from urllib.parse import quote

import requests
import urllib3
from mcp.types import EmbeddedResource, ImageContent, TextContent, Tool

from .toolhandler import ToolHandler

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("weather-advisor")


class OpenMeteoTool:
    """Small client wrapper around Nominatim + Open-Meteo HTTP APIs."""

    def get_coordinates(self, city_name: str) -> tuple[str, str]:
        encoded_city_name = quote(city_name)
        geocode_url = (
            "https://nominatim.openstreetmap.org/search"
            f"?q={encoded_city_name}&format=json"
        )
        headers = {"User-Agent": "WeatherAdvisorMCP/1.0"}
        response = requests.get(geocode_url, headers=headers, verify=False, timeout=20)

        if response.status_code != 200:
            raise RuntimeError(f"Nominatim API returned status {response.status_code}")

        data = response.json()
        if not data:
            raise ValueError(f"No geocoding data returned for city '{city_name}'")

        latitude = data[0].get("lat")
        longitude = data[0].get("lon")
        if not latitude or not longitude:
            raise ValueError(f"Coordinates not found for city '{city_name}'")

        return latitude, longitude

    def get_weather(self, city_name: str) -> str:
        lat, lon = self.get_coordinates(city_name)
        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current_weather=true"
        )
        weather_response = requests.get(weather_url, verify=False, timeout=20)

        if weather_response.status_code != 200:
            raise RuntimeError(f"Open-Meteo API returned status {weather_response.status_code}")

        weather_data = weather_response.json()
        current_weather = weather_data.get("current_weather")
        if not current_weather:
            raise RuntimeError("Weather data not available from Open-Meteo")

        day_or_night = "day" if current_weather.get("is_day") == 1 else "night"
        return (
            f"Current temperature in {city_name} is {current_weather.get('temperature')} C, "
            f"with wind speed of {current_weather.get('windspeed')} m/s and it is "
            f"{day_or_night} time."
        )

    def weather_tool(self, city_name: str) -> str:
        """Compatibility helper used by handler execution."""
        return self.get_weather(city_name)


class GetWeatherToolHandler(ToolHandler):
    """
    MCP ToolHandler for the ``get_weather`` tool.

    Wraps ``OpenMeteoTool`` to fit the standard ToolHandler interface used
    throughout this server.  Adding this handler to the registry in
    ``server.py::register_all_tools()`` is all that is needed to
    expose the tool to MCP clients.
    """

    def __init__(self) -> None:
        super().__init__("get_weather")
        self._client = OpenMeteoTool()

    # ------------------------------------------------------------------
    # MCP schema description
    # ------------------------------------------------------------------

    def get_tool_description(self) -> Tool:
        return Tool(
            name=self.name,
            title="Get Weather",
            description=(
                "Retrieve the current weather for a given city using the "
                "Open-Meteo API and Nominatim geocoding. Returns the current "
                "temperature (°C), wind speed (m/s), and whether it is day or "
                "night at the location. No API key required."
            ),
            inputSchema={
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "title": "GetWeatherInput",
                "additionalProperties": False,
                "properties": {
                    "city_name": {
                        "type": "string",
                        "title": "City Name",
                        "description": (
                            "The name of the city for which to retrieve current "
                            "weather data. Examples: 'London', 'Tokyo', 'New York'."
                        ),
                        "examples": ["London", "Tokyo", "New York"],
                    }
                },
                "required": ["city_name"],
            },
        )

    # ------------------------------------------------------------------
    # Tool execution
    # ------------------------------------------------------------------

    async def run_tool(
        self, args: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Execute ``get_weather`` and return MCP TextContent output."""
        self.validate_required_args(args, ["city_name"])
        city_name: str = args["city_name"].strip()

        logger.info("get_weather called for city: %s", city_name)
        try:
            result = self._client.weather_tool(city_name)
            logger.info("get_weather completed for city: %s", city_name)
            return [TextContent(type="text", text=result)]
        except Exception as exc:
            logger.exception("Unexpected error in get_weather: %s", exc)
            return [
                TextContent(
                    type="text",
                    text=f"Error while retrieving weather for '{city_name}': {exc}",
                )
            ]