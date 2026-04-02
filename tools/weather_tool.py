import requests
from urllib.parse import quote
import urllib3

# Disable SSL warnings that will be generated when using verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class OpenMetoTool:

    def get_coordinates(self, city_name):
        encoded_city_name = quote(city_name)
        geocode_url = f"https://nominatim.openstreetmap.org/search?q={encoded_city_name}&format=json"
        headers = {
            'User-Agent': 'MyWeatherApp/1.0 (Geocoding and Weather Service)'
        }
        response = requests.get(geocode_url, headers=headers, verify=False)
        if response.status_code == 200:
            data = response.json()
            if data:
                latitude = data[0].get('lat')
                longitude = data[0].get('lon')
                if latitude and longitude:
                    return latitude, longitude
                else:
                    raise ValueError(f"Coordinates not found for '{city_name}'.")
            else:
                raise ValueError(f"No data returned for city '{city_name}'.")
        else:
            raise Exception(f"Nominatim API returned an error: {response.status_code}")

    def get_weather(self, city_name):
        try:
            lat, lon = self.get_coordinates(city_name)
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
            weather_response = requests.get(weather_url, verify=False)
            if weather_response.status_code == 200:
                weather_data = weather_response.json()
                current_weather = weather_data.get('current_weather')

                if current_weather:
                    response = f"Current temperature in {city_name} is {current_weather['temperature']}°C, with wind speed of {current_weather['windspeed']} m/s and it is { 'day' if current_weather['is_day'] == 1 else 'night'} time."
                    return response
                else:
                    raise Exception("Weather data not available.")
            else:
                raise Exception(f"Open-Meteo API returned an error: {weather_response.status_code}")
        except Exception as e:
            return str(e) 
        
    def weather_tool(self, city_name: str) -> str:
        return self.get_weather(city_name)