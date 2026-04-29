import json
import requests
from datetime import datetime
from psycopg2.extras import execute_values, Json
import psycopg2


def get_connection():
    return psycopg2.connect(
        host='db',
        user='postgres',
        password='123123',
        dbname='events_db'
    )


KUDAGO_API = 'https://kudago.com/public-api/v1.4'


def save_events_to_db(events, dt: datetime):
    conn = get_connection()
    cur = conn.cursor()

    archive_values = []

    for e in events:
        event_id = e["id"]
        title = e.get("title")

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

        if start_date is None:
            continue

        tags = []
        try:
            r = requests.get(f"{KUDAGO_API}/events/{event_id}/", timeout=6)
            r.raise_for_status()
            tags = r.json().get("tags", [])
        except requests.exceptions.RequestException:
            pass

        thumbnail = None
        images = e.get("images") or []
        if images:
            thumbnail = images[0].get("image")

        archive_values.append((
            event_id,
            title,
            Json(place),
            Json(raw_dates),
            tags,
            thumbnail
        ))

    if archive_values:
        execute_values(cur, """
            INSERT INTO events_archive (id, title, place, dates, tags, thumbnail)
            VALUES %s
            ON CONFLICT (id) DO UPDATE SET
                title = excluded.title,
                place = excluded.place,
                dates = excluded.dates,
                tags = excluded.tags,
                thumbnail = excluded.thumbnail;
        """, archive_values)

    conn.commit()
    cur.execute("SELECT refresh_events_cache();")
    print("events_cache refreshed")
    cur.close()
    conn.close()