from datetime import datetime

from services.database import db_service
from services.recommender import recommender_service
from core.geolocation import geolocation_service


def get_recommendations(user_id: int, latitude: float, longitude: float, search_mode: str = "balanced"):
    user_vec = recommender_service.get_user_vector(user_id)
    if not user_vec:
        return []

    city = geolocation_service.reverse_geocode(latitude, longitude) if latitude and longitude else None

    events = db_service.get_events_for_user(user_id, datetime.now())
    if not events:
        return []

    user_geo = {"lat": latitude, "lon": longitude, "city": city}
    ranked = recommender_service.rank_events(user_vec, user_geo, events, search_mode)

    user_tags = set(user_vec.keys())
    filtered = [e for e in ranked if set(e.get("tags", [])) & user_tags]

    return filtered