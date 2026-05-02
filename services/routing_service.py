import requests
import polyline
from django.core.cache import cache
from django.conf import settings


class RoutingService:
    GOOGLE_DIRECTIONS_URL = "https://maps.googleapis.com/maps/api/directions/json"

    def get_route(self, start: str, finish: str) -> dict:
        cache_key = f"route:{start.lower().strip()}:{finish.lower().strip()}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        params = {
            "origin": start.strip(),
            "destination": finish.strip(),
            "key": settings.GOOGLE_MAPS_API_KEY,
        }

        try:
            response = requests.get(self.GOOGLE_DIRECTIONS_URL, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            raise ValueError("Google Maps request timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise ValueError("Could not connect to Google Maps. Check your internet connection.")
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Google Maps request failed: {str(e)}")

        data = response.json()

        if data.get("status") != "OK":
            raise ValueError(
                f"Google Maps could not find a route from '{start}' to '{finish}'. "
                f"Status: {data.get('status')}. "
                f"Check the location names and try again."
            )

        try:
            leg = data["routes"][0]["legs"][0]
            encoded = data["routes"][0]["overview_polyline"]["points"]
            distance_meters = leg["distance"]["value"]
        except (KeyError, IndexError) as e:
            raise ValueError(
                f"Unexpected response from Google Maps. Could not parse route data: {str(e)}"
            )

        coords = polyline.decode(encoded)  # list of (lat, lon)
        distance_miles = distance_meters / 1609.344

        result = {
            "polyline": encoded,
            "coords": coords,
            "distance_miles": round(distance_miles, 2),
        }

        cache.set(cache_key, result, timeout=None)
        return result
