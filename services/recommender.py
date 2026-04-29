# Recommender service
from typing import Dict, List, Any, Optional
import numpy as np
from math import radians, sin, cos, sqrt, atan2

from config import SEARCH_MODES, CITY_CHANGE_PENALTY, SAME_CITY_GRADE, GEOSCORE_DESCEND, LEARNING_RATE_GRADE, LEARNING_RATE_WATCH, DECAY_RATE, NEW_TAG_INIT_WATCH, NEW_TAG_INIT_GRADE
from services.database import DatabaseService


class RecommenderService:
    def __init__(self, db_service: DatabaseService = None):
        self._db = db_service or DatabaseService()

    def get_user_vector(self, user_id: int) -> Dict[str, float]:
        return self._db.get_user_interests(user_id)

    def event_tags_to_vector(self, event_tags: List[str]) -> Dict[str, float]:
        return {t: 1.0 for t in event_tags}

    def cosine_similarity(self, vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
        if not vec_a or not vec_b:
            return 0.0
        keys = set(vec_a.keys()) | set(vec_b.keys())
        a = np.array([vec_a.get(k, 0.0) for k in keys], dtype=float)
        b = np.array([vec_b.get(k, 0.0) for k in keys], dtype=float)
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return max(0.0, float(np.dot(a, b) / denom))

    def haversine_km(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    def compute_geoscore(self, user_city: str, user_lat: float, user_lon: float,
                           event_city: str, event_lat: float, event_lon: float) -> float:
        if event_lat is None or event_lon is None:
            return SAME_CITY_GRADE if (user_city and event_city and user_city.lower() == event_city.lower()) else CITY_CHANGE_PENALTY * 0.5
        same_city = (user_city and event_city and user_city.lower() == event_city.lower())
        alpha = SAME_CITY_GRADE if same_city else CITY_CHANGE_PENALTY
        d = self.haversine_km(user_lat, user_lon, event_lat, event_lon)
        return float(alpha * (2.718281828459045 ** (-d / GEOSCORE_DESCEND)))

    def compute_recommendation_score(self, user_vector: Dict[str, float], user_geo: Dict,
                                 event: Dict[str, Any], beta: float) -> float:
        event_vector = self.event_tags_to_vector(event.get("tags", []))
        simscore = self.cosine_similarity(user_vector, event_vector)
        
        if user_geo.get("lat") and user_geo.get("lon"):
            geoscore = self.compute_geoscore(
                user_geo.get("city"), user_geo.get("lat"), user_geo.get("lon"),
                event.get("city"), event.get("lat"), event.get("lon")
            )
            score = beta * simscore + (1.0 - beta) * geoscore
        else:
            score = simscore
        return float(score)

    def rank_events(self, user_vector: Dict[str, float], user_geo: Dict,
                        events: List[Dict], search_mode: str = "balanced", top_n: int = 500) -> List[Dict]:
        beta = SEARCH_MODES.get(search_mode, SEARCH_MODES["balanced"])
        scored = [
            (e, self.compute_recommendation_score(user_vector, user_geo, e, beta))
            for e in events
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [e for e, s in scored[:top_n]]

    def update_interests_on_watch(self, user_interests: Dict[str, float], event_tags: List[str]) -> Dict[str, float]:
        updated = {}
        event_tags_set = set(event_tags)

        for tag, value in user_interests.items():
            if tag in event_tags_set:
                new_value = value * (1 + LEARNING_RATE_WATCH)
            else:
                new_value = value * (1 - DECAY_RATE)
            updated[tag] = max(0, min(1, new_value))

        for tag in event_tags_set:
            if tag not in updated:
                updated[tag] = NEW_TAG_INIT_WATCH

        return updated

    def update_interests_on_grade(self, user_interests: Dict[str, float], event_tags: List[str], liked: bool) -> Dict[str, float]:
        factor = 1 + LEARNING_RATE_GRADE if liked else 1 - LEARNING_RATE_GRADE
        updated = dict(user_interests)

        for tag in event_tags:
            if tag not in updated:
                updated[tag] = NEW_TAG_INIT_GRADE
            updated[tag] *= factor

        return {tag: max(0, min(1, val)) for tag, val in updated.items()}

    def get_recommendations(self, user_id: int, latitude: Optional[float] = None, longitude: Optional[float] = None,
                          search_mode: str = "balanced") -> List[Dict]:
        user_vector = self.get_user_vector(user_id)
        if not user_vector:
            return []

        user_geo = {"lat": latitude, "lon": longitude, "city": None}
        
        events = self._db.get_events_for_user(user_id)
        if not events:
            return []

        ranked = self.rank_events(user_vector, user_geo, events, search_mode)

        user_tags = set(user_vector.keys())
        filtered = [e for e in ranked if set(e.get("tags", [])) & user_tags]
        
        return filtered


recommender_service = RecommenderService()