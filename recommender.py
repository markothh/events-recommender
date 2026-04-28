from typing import Dict, Any

import psycopg2
import psycopg2.extras

import config
from db import get_conn
from utils import cosine_similarity, haversine_km
from config import *

def event_tags_to_vector(event_tags: list, user_tags_all: list = None) -> Dict[str, float]:
    """
    Простая стратегия: если у события есть тег -> 1.0, иначе 0.
    Можно улучшить: учитывать веса тегов события, TF-IDF и т.д.
    """
    return {t: 1.0 for t in event_tags}

def compute_geoscore(user_city: str, user_lat: float, user_lon: float,
                     event_city: str, event_lat: float, event_lon: float) -> float:
    """
    geoscore = alpha * exp(-d/tau), alpha=1 if same city else gamma
    Возвращает значение в [0, alpha]
    """
    if event_lat is None or event_lon is None:
        # если нет координат у события, даём небольшой базовый балл, зависящий только от города
        return SAME_CITY_GRADE if (user_city and event_city and user_city.lower() == event_city.lower()) else CITY_CHANGE_PENALTY * 0.5

    same_city = (user_city and event_city and user_city.lower() == event_city.lower())
    alpha = SAME_CITY_GRADE if same_city else CITY_CHANGE_PENALTY
    d = haversine_km(user_lat, user_lon, event_lat, event_lon)
    geoscore = alpha * (2.718281828459045 ** (-d / GEOSCORE_DESCEND))

    return float(geoscore)

def compute_simscore(user_vec: Dict[str, float], event_vec: Dict[str, float]) -> float:
    return float(cosine_similarity(user_vec, event_vec))

def compute_recommendation_score(user_vec: Dict[str, float],
                                 user_city: str, user_lat: float, user_lon: float,
                                 event: Dict[str, Any],
                                 beta: float = SIMILARITY_CONTRIBUTION) -> float:
    event_vec = event_tags_to_vector(event.get('tags', []))
    simscore = compute_simscore(user_vec, event_vec)
    if user_lon and user_lat:
        geoscore = compute_geoscore(user_city, user_lat, user_lon,
                                event.get('city'), event.get('lat'), event.get('lon'))
        score = beta * simscore + (1.0 - beta) * geoscore
    else:
        score = simscore
    return float(score)

def rank_events(user_vec, user_geo, events, top_n=10):
    """
    Возвращает отсортированный список event по убыванию score.
    user_geo: dict with lat, lon, city
    """
    scored = [
        (e, compute_recommendation_score(user_vec, user_geo.get('city'), user_geo['lat'], user_geo['lon'], e))
        for e in events
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    top_events = [e for e, s in scored[:top_n]]
    return top_events

def update_user_interests_on_watch(
    user_interests: dict,
    event_tags: list[str]
) -> dict:
    """
    user_interests: {tag: weight}
    event_tags: список тегов события
    """

    updated = {}

    event_tags_set = set(event_tags)

    # 1. Проходим по существующим интересам
    for tag, value in user_interests.items():
        if tag in event_tags_set:
            new_value = value * (1 + LEARNING_RATE_WATCH)
        else:
            new_value = value * (1 - DECAY_RATE)

        updated[tag] = max(0, min(1, new_value))

    # 2. Добавляем новые теги события
    for tag in event_tags_set:
        if tag not in updated:
            updated[tag] = NEW_TAG_INIT_WATCH

    return updated

def update_user_vector_after_grade(user_id: int, event_id: int, liked: bool):
    conn = get_conn()
    cur = conn.cursor()

    # блокируем строку пользователя
    cur.execute("""
        SELECT interests
        FROM users
        WHERE id = %s
        FOR UPDATE
    """, (user_id,))
    row = cur.fetchone()
    interests = row[0] if row and row[0] else {}

    # получаем теги события
    cur.execute("""
        SELECT tags
        FROM events_archive
        WHERE id = %s
    """, (event_id,))
    row = cur.fetchone()
    event_tags = set(row[0]) if row and row[0] else set()

    # вычисляем коэффициент изменения
    factor = 1 + LEARNING_RATE_GRADE if liked else 1 - LEARNING_RATE_GRADE

    # обновляем вектор интересов
    for tag in event_tags:
        if tag not in interests:
            interests[tag] = NEW_TAG_INIT_GRADE
        interests[tag] *= factor

    # сохраняем обратно
    cur.execute("""
        UPDATE users
        SET interests = %s
        WHERE id = %s
    """, (psycopg2.extras.Json(interests), user_id))

    conn.commit()
    cur.close()
    conn.close()


