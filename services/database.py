# Database service
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import psycopg2
import psycopg2.extras
from psycopg2.extras import RealDictCursor
import requests

from config import DB, KUDAGO_API


class DatabaseService:
    def __init__(self, connection_params: Dict = None):
        self._params = connection_params or DB

    def get_connection(self):
        return psycopg2.connect(
            host=self._params["host"],
            port=self._params["port"],
            dbname=self._params["dbname"],
            user=self._params["user"],
            password=self._params["password"]
        )

    def get_user_interests(self, user_id: int) -> Dict[str, float]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT interests FROM users WHERE id = %s;", (user_id,))
                row = cur.fetchone()
                if not row or not row.get("interests"):
                    return {}
                interests = row["interests"]
                if isinstance(interests, str):
                    interests = json.loads(interests)
                return {tag: float(score) for tag, score in interests.items()}
        finally:
            conn.close()

    def get_user_search_mode(self, user_id: int) -> str:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT active_search_mode FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                return row["active_search_mode"] if row and row["active_search_mode"] else "balanced"
        finally:
            conn.close()

    def set_user_search_mode(self, user_id: int, mode: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET active_search_mode = %s WHERE id = %s",
                (mode, user_id)
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def get_active_geoprofile(self, user_id: int) -> Optional[Dict]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT geoprofiles, active_profile_id FROM users WHERE id = %s",
                    (user_id,)
                )
                row = cur.fetchone()
                if not row:
                    return None
                profiles = row.get("geoprofiles") or []
                active_id = row.get("active_profile_id")
                if not active_id:
                    return None
                return next((p for p in profiles if p.get("id") == active_id), None)
        finally:
            conn.close()

    def get_user_geoprofiles(self, user_id: int) -> List[Dict]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT geoprofiles FROM users WHERE id = %s", (user_id,))
                row = cur.fetchone()
                return row.get("geoprofiles") or [] if row else []
        finally:
            conn.close()

    def set_active_geoprofile(self, user_id: int, profile_id: Optional[str]):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET active_profile_id = %s WHERE id = %s",
                (profile_id, user_id)
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def add_geoprofile(self, user_id: int, profile: Dict):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE users
                SET geoprofiles = COALESCE(geoprofiles, '[]'::jsonb) || %s::jsonb
                WHERE id = %s
            """, (json.dumps([profile]), user_id))
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def delete_geoprofile(self, user_id: int, profile_id: str):
        conn = self.get_connection()
        try:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(
                "SELECT geoprofiles, active_profile_id FROM users WHERE id = %s",
                (user_id,)
            )
            row = cur.fetchone()
            profiles = [p for p in (row.get("geoprofiles") or []) if str(p.get("id")) != str(profile_id)]
            active_id = row.get("active_profile_id")
            new_active = active_id if str(active_id) in [str(p.get("id")) for p in profiles] else None

            cur.execute("""
                UPDATE users SET geoprofiles = %s::jsonb, active_profile_id = %s WHERE id = %s
            """, (json.dumps(profiles), new_active, user_id))
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def update_user_interests(self, user_id: int, interests: Dict[str, float]):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE users SET interests = %s WHERE id = %s",
                (json.dumps(interests), user_id)
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def get_events_for_user(self, user_id: int, since: datetime = None) -> List[Dict]:
        conn = self.get_connection()
        cur = conn.cursor()

        query = """
            SELECT e.id, e.title, e.place, e.start_date, e.end_date, e.tags, e.thumbnail
            FROM events_cache e
            WHERE NOT EXISTS (
                SELECT 1 FROM tracked_events t
                WHERE t.user_id = %s AND t.event_id = e.id
            )
        """
        params = [user_id]

        if since:
            query += " AND e.start_date >= %s"
            params.append(since)

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

    def get_user_tracked_events(self, user_id: int) -> List[Dict]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT e.id, e.title, e.thumbnail, e.dates
                    FROM tracked_events t
                    JOIN events_archive e ON e.id = t.event_id
                    WHERE t.user_id = %s
                """, (user_id,))
                return list(cur.fetchall())
        finally:
            conn.close()

    def track_event(self, user_id: int, event_id: int):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO tracked_events (user_id, event_id) VALUES (%s, %s)
                ON CONFLICT (user_id, event_id) DO NOTHING
            """, (user_id, event_id))
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def untrack_event(self, user_id: int, event_id: int):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM tracked_events WHERE user_id = %s AND event_id = %s
            """, (user_id, event_id))
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def get_event_tags(self, event_id: int) -> List[str]:
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT tags FROM events_archive WHERE id = %s", (event_id,))
                row = cur.fetchone()
                return row[0] if row and row[0] else []
        finally:
            conn.close()

    def save_tags(self, tags: List[str]):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.executemany(
                "INSERT INTO tags (name) VALUES (%s) ON CONFLICT DO NOTHING",
                [(tag,) for tag in tags if tag]
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def get_all_tags(self) -> List[Dict]:
        conn = self.get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name FROM tags ORDER BY name")
                return [{"id": r["id"], "name": r["name"]} for r in cur.fetchall()]
        finally:
            conn.close()

    def get_last_sync_date(self) -> datetime:
        conn = self.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM sync_state WHERE key = 'last_event_update'")
                row = cur.fetchone()
                if row:
                    return datetime.fromisoformat(row[0])
        finally:
            conn.close()
        return datetime.now() - timedelta(days=30)

    def update_last_sync_date(self, dt: datetime):
        conn = self.get_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO sync_state (key, value, updated_at) VALUES ('last_event_update', %s, NOW())
                ON CONFLICT (key) DO UPDATE SET value = %s, updated_at = NOW()
            """, (dt.isoformat(), dt.isoformat()))
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def search_events(self, query: str) -> List[Dict]:
        conn = self.get_connection()
        cur = conn.cursor()
        query_lower = query.lower()

        cur.execute("SELECT id, title, place, tags, thumbnail FROM events_cache")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        out = []
        for r in rows:
            place = r[2] or {}
            coords = place.get("coords") or {}
            tags = r[3] or []
            title_match = query_lower in (r[1] or "").lower()
            tags_match = any(query_lower in t.lower() for t in tags)
            if title_match or tags_match:
                out.append({
                    "id": r[0],
                    "title": r[1],
                    "place": place.get("name") or place.get("city"),
                    "city": place.get("city"),
                    "lat": coords.get("lat"),
                    "lon": coords.get("lon"),
                    "tags": tags,
                    "thumbnail": r[4]
                })
        return out


db_service = DatabaseService()