import requests
from datetime import datetime
from typing import Dict, Any, Optional
import config

BASE = config.KUDAGO_API

def get_event(event_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить одно событие по id. Возвращает dict с ключами:
    - 'id', 'title', 'city', 'location' {'lat', 'lon'}, 'tags' -> list[str]
    """
    url = f"{BASE}/events/{event_id}/"
    params = {}
    try:
        r = requests.get(url, params=params, timeout=5)
        r.raise_for_status()
        data = r.json()
        # структура зависит от API версии; делаем устойчивый парсинг
        loc = data.get('location') or {}
        # tags могут быть списком объектов {'name': ...} или строк
        raw_tags = data.get('tags') or []
        tags = []
        for t in raw_tags:
            if isinstance(t, dict):
                tags.append(t.get('name') or t.get('slug') or '')
            else:
                tags.append(str(t))
        return {
            "id": data.get('id'),
            "title": data.get('title'),
            "city": data.get('place', {}).get('city') or data.get('location', {}).get('city') or data.get('city'),
            "lat": float(loc.get('lat')) if loc.get('lat') else None,
            "lon": float(loc.get('lon')) if loc.get('lon') else None,
            "tags": [t for t in tags if t]
        }
    except Exception as e:
        print("KudaGo fetch error:", e)
        return None

def search_events(city: str = None, lat: float = None, lon: float = None, radius_km: int = 50, page_size: int = 100):
    """
    Минимальный search: возвращает генератор/список событий (с тем же форматом, как get_event).
    Использует /events/ endpoint с параметрами location/lat/long/radius.
    """
    url = f"{BASE}/events/"
    params = {"page_size": page_size}
    if city:
        params['text_format'] = 'plain'
        params['place_city'] = city
    if lat and lon:
        params['lat'] = lat
        params['lon'] = lon
        params['radius'] = radius_km * 1000  # API может ожидать в метрах
    try:
        r = requests.get(url, params=params, timeout=6)
        r.raise_for_status()
        data = r.json()
        results = data.get('results', data)
        out = []
        for item in results:
            loc = item.get('location') or {}
            raw_tags = item.get('tags') or []
            tags = []
            for t in raw_tags:
                if isinstance(t, dict):
                    tags.append(t.get('name') or t.get('slug') or '')
                else:
                    tags.append(str(t))
            out.append({
                "id": item.get('id'),
                "title": item.get('title'),
                "city": item.get('place', {}).get('city') or item.get('location', {}).get('city') or item.get('city'),
                "lat": float(loc.get('lat')) if loc.get('lat') else None,
                "lon": float(loc.get('lon')) if loc.get('lon') else None,
                "tags": [t for t in tags if t]
            })
        return out
    except Exception as e:
        print("KudaGo search error:", e)
        return []

def fetch_events_since(dt: datetime):
    """
    Загружает ВСЕ события позже указанной даты.
    Проходит постранично, пока API не вернёт 404 (что означает 'страниц больше нет').
    """
    timestamp = int(dt.timestamp())
    page = 1
    events = []

    while True:
        params = {
            "page": page,
            "page_size": 100,
            "actual_since": timestamp,
            "fields": "id,title,location,dates,place,images",
            "expand": "location,place"
        }

        r = requests.get(f'{BASE}/events', params=params)

        if r.status_code == 404:
            break

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            raise

        data = r.json()

        results = data.get("results", [])
        if not results:
            break

        events.extend(results)
        page += 1

    return events
