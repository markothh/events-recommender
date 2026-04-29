# Geolocation service
import requests
from typing import Optional

from config import YANDEX_API


class GeolocationService:
    def __init__(self, api_key: str = None):
        self._api_key = api_key or YANDEX_API

    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        try:
            url = "https://geocode-maps.yandex.ru/1.x/"
            params = {
                "apikey": self._api_key,
                "format": "json",
                "geocode": f"{lon},{lat}",
                "kind": "locality"
            }
            r = requests.get(url, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
                if features:
                    return features[0]["GeoObject"]["name"]
        except Exception:
            pass
        return None


geolocation_service = GeolocationService()