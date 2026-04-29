import json
from typing import Dict

import requests
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values, Json, RealDictCursor
from config import DB, KUDAGO_API
from kudago_client import fetch_events_since


def get_conn():
    """Создает соединение с БД, используя объект DB из config.py"""
    return psycopg2.connect(
        host=DB["host"],
        port=DB["port"],
        dbname=DB["dbname"],
        user=DB["user"],
        password=DB["password"]
    )

def save_events_to_db(events, dt: datetime):
    conn = get_conn()
    cur = conn.cursor()

    archive_values = []

    for e in events:
        print(e["id"])
        event_id = e["id"]
        title = e.get("title")

        # ---------- place ----------
        place = None
        location = e.get("location")
        place_raw = e.get("place")

        if location:
            slug = location.get("slug")
            city = location.get("name")

            if place_raw and place_raw.get("coords"):
                coords = {
                    "lat": place_raw["coords"]["lat"],
                    "lon": place_raw["coords"]["lon"]
                }
                name = place_raw.get("title")
            else:
                coords = {
                    "lat": location["coords"]["lat"],
                    "lon": location["coords"]["lon"]
                }
                name = None

            place = {
                "slug": slug,
                "city": city,
                "name": name,
                "coords": coords
            }

        # ---------- dates ----------
        start_date = None
        end_date = None

        raw_dates = e.get("dates") or []

        for d in raw_dates:
            start_ts = d.get("start")
            end_ts = d.get("end")

            if start_ts and 0 < start_ts < 32503680000:
                candidate = datetime.fromtimestamp(start_ts)
                if candidate >= dt:
                    start_date = candidate
                    if end_ts and 0 < end_ts < 32503680000:
                        end_date = datetime.fromtimestamp(end_ts)
                    break

        # если нет ни одной актуальной даты — в cache не пишем
        if start_date is None:
            continue

        # ---------- tags ----------
        tags = []
        try:
            r = requests.get(f"{KUDAGO_API}/events/{event_id}/", timeout=6)
            r.raise_for_status()
            tags = r.json().get("tags", [])
        except requests.exceptions.RequestException:
            pass

        # ---------- thumbnail ----------
        thumbnail = None
        images = e.get("images") or []
        if images:
            thumbnail = images[0].get("image")

        # ---------- events_archive ----------
        archive_values.append((
            event_id,
            title,
            Json(place),
            Json(raw_dates),   # ВСЕ даты целиком
            tags,
            thumbnail
        ))

# ---------- INSERT events_archive ----------
    archive_sql = """
        INSERT INTO events_archive (id, title, place, dates, tags, thumbnail)
        VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            title = excluded.title,
            place = excluded.place,
            dates = excluded.dates,
            tags = excluded.tags,
            thumbnail = excluded.thumbnail;
    """

    if archive_values:
        execute_values(cur, archive_sql, archive_values)

    conn.commit()

    cur.execute("SELECT refresh_events_cache();")
    print("events_cache refreshed")

    cur.close()
    conn.close()

def update_events_since(dt: datetime):
    """Главная функция: берёт события из API, позже date dt, и сохраняет в БД."""
    events = fetch_events_since(dt)
    if events:
        save_events_to_db(events, dt)
    return len(events)


def delete_old_events(before_dt: datetime):
    """Удаляет из БД все события, у которых start_date < before_dt."""
    conn = get_conn()
    cur = conn.cursor()

    sql = """
        DELETE FROM events_archive
        WHERE start_date < %s or start_date is null;
    """

    cur.execute(sql, (before_dt,))
    deleted = cur.rowcount

    conn.commit()
    cur.close()
    conn.close()

    # Обновляем кэш
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT refresh_events_cache();")
    conn.commit()
    cur.close()
    conn.close()

    return deleted

def search_events_from_db(user_id: int, since_dt: datetime = None):
    """
    Загружает события из БД, которые НЕ отслеживаются пользователем.
    - user_id: id пользователя
    - since_dt: datetime, фильтр по start_date >= since_dt
    - Возвращает список словарей:
      id, title, city, place, lat, lon, tags, thumbnail
    """
    conn = get_conn()
    cur = conn.cursor()

    query = """
        SELECT
            e.id,
            e.title,
            e.place,
            e.start_date,
            e.end_date,
            e.tags,
            e.thumbnail
        FROM events_cache e
        WHERE NOT EXISTS (
            SELECT 1
            FROM tracked_events t
            WHERE t.user_id = %s
              AND t.event_id = e.id
        )
    """
    params = [user_id]

    if since_dt:
        query += " AND e.start_date >= %s"
        params.append(since_dt)

    cur.execute(query, params)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    out = []
    for r in rows:
        place = r[2] or {}
        coords = place.get("coords") or {}

        out.append({
            "id": r[0],
            "title": r[1],
            "city": place.get("city"),
            "place": place.get("name") or place.get("city"),
            "lat": coords.get("lat"),
            "lon": coords.get("lon"),
            "tags": r[5] or [],
            "thumbnail": r[6]
        })

    return out


def search_events_from_db_by_query(query_input, since_dt=None):
    """
    Ищет события в БД по названию и тегам.
    - query: строка поиска (по title или тегам)
    - since_dt: datetime, фильтр по start_date >= since_dt
    - Возвращает список словарей с ключами: id, title, place, city, lat, lon, tags, thumbnail
    """
    conn = get_conn()
    cur = conn.cursor()
    query_lower = query_input.lower()

    sql = "SELECT id, title, place, start_date, end_date, tags, thumbnail FROM events_cache"
    params = []
    if since_dt:
        sql += " WHERE start_date >= %s"
        params.append(since_dt)

    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    out = []
    for r in rows:
        place = r[2] or {}
        coords = place.get("coords") or {}
        tags = r[5] or []

        # фильтрация по названию и тегам
        title_match = query_lower in (r[1] or "").lower()
        tags_match = any(query_lower in t.lower() for t in tags)
        if not (title_match or tags_match):
            continue

        out.append({
            "id": r[0],
            "title": r[1],
            "city": place.get("city"),
            "place": place.get("name") if place.get("name") else place.get("city"),
            "lat": coords.get("lat"),
            "lon": coords.get("lon"),
            "tags": tags,
            "thumbnail": r[6]
        })
    return out

def get_user_interest_vector(user_id: int) -> Dict[str, float]:
    """
    Возвращает словарь интересов {tag: score} из поля users.interests (JSONB).
    Если поле пусто → возвращаем {}.
    """
    conn = psycopg2.connect(**DB)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT interests FROM users WHERE id = %s;", (user_id,))
            row = cur.fetchone()
            if not row or not row.get("interests"):
                return {}

            # interests — JSONB, приводим к dict
            interests = row["interests"]
            # Если вернулось как строка, десериализуем
            if isinstance(interests, str):
                interests = json.loads(interests)

            # Приводим значения к float
            return {tag: float(score) for tag, score in interests.items()}
    finally:
        conn.close()

def load_tags_from_file(filepath: str):
    """Загружает теги из файла (один тег - одна строка)"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Читаем теги из файла
    with open(filepath, 'r', encoding='utf-8') as f:
        tags = [line.strip().strip('"') for line in f if line.strip() and line.strip() != '"']
    
    # Вставляем теги
    tag_values = [(tag,) for tag in tags if tag]
    
    if tag_values:
        cur.executemany(
            "INSERT INTO tags (name) VALUES (%s) ON CONFLICT DO NOTHING",
            tag_values
        )
        conn.commit()
    
    cur.close()
    conn.close()
    return len(tag_values)

def get_last_sync_date() -> datetime:
    """Получает дату последней синхронизации событий"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT value FROM sync_state WHERE key = 'last_event_update'")
    row = cur.fetchone()
    cur.close()
    conn.close()
    
    if row:
        return datetime.fromisoformat(row[0])
    return datetime.now() - timedelta(days=30)

def update_last_sync_date(dt: datetime):
    """Обновляет дату последней синхронизации"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO sync_state (key, value, updated_at) VALUES ('last_event_update', %s, NOW()) "
        "ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = NOW()",
        (dt.isoformat(), dt.isoformat())
    )
    conn.commit()
    cur.close()
    conn.close()

if __name__ == '__main__':
    update_events_since(datetime.now())
    #delete_old_events(datetime.now())