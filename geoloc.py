import requests

YANDEX_API_KEY = "31329796-880c-441b-b0e1-2b6fc0b9cdea"

def reverse_geocode(lat: float, lon: float) -> str:
    try:
        url = "https://geocode-maps.yandex.ru/1.x/"
        params = {
            "apikey": YANDEX_API_KEY,
            "format": "json",
            "geocode": f"{lon},{lat}",
            "kind": "locality"
        }
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            data = r.json()
            features = data.get("response", {}).get("GeoObjectCollection", {}).get("featureMember", [])
            if features:
                city_name = features[0]["GeoObject"]["name"]
                return city_name
    except Exception as e:
        print("Yandex reverse geocode error:", e)
    return None
