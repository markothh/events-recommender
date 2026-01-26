# run.py
from datetime import datetime

from db import get_user_interest_vector, search_events_from_db
from geoloc import reverse_geocode
from kudago_client import search_events
from recommender import rank_events

def recsys(user_id: int, latitude: float, longitude: float):
    user_vec = get_user_interest_vector(user_id)
    if not user_vec:
        return []

    city = reverse_geocode(latitude, longitude) if latitude and longitude else None

    events = search_events_from_db(user_id, datetime.now())
    if not events:
        return []

    ranked = rank_events(
        user_vec,
        {"lat": latitude, "lon": longitude, "city": city},
        events,
        top_n=500
    )

    user_tags = set(user_vec.keys())

    filtered = []
    for e in ranked:
        event_tags = set(e.get("tags", []))
        if user_tags & event_tags:
            filtered.append(e)

    return filtered
