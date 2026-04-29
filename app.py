import os
import time
import json
from functools import wraps
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash, check_password_hash
import requests

from services.database import db_service
from recommendations import get_recommendations
from services.recommender import recommender_service
from config import SECRET, DB, KUDAGO_API, YANDEX_API


app = Flask(__name__)
app.secret_key = SECRET

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = db_service.get_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT id, password_hash FROM users WHERE username=%s", (username,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row or not check_password_hash(row["password_hash"], password):
            return render_template("login.html", error="Неправильный логин или пароль")
        session["user_id"] = row["id"]
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        pw_hash = generate_password_hash(password)
        conn = db_service.get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id",
                        (username, pw_hash))
            user_id = cur.fetchone()[0]
            conn.commit()
        except psycopg2.IntegrityError:
            conn.rollback()
            cur.close()
            conn.close()
            return render_template("register.html", error="Имя пользователя занято")
        cur.close()
        conn.close()
        session["user_id"] = user_id
        return redirect(url_for("select_interests"))
    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --- Tags & Interests ---
@app.route("/api/tags")
@login_required
def api_tags():
    conn = db_service.get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, name FROM tags ORDER BY name")
    tags = [{"id": r["id"], "name": r["name"]} for r in cur.fetchall()]
    cur.close()
    conn.close()
    return jsonify(tags)

@app.route("/select-interests", methods=["GET", "POST"])
@login_required
def select_interests():
    if request.method == "POST":
        data = request.json or {}
        selected_ids = data.get("selected", [])  # список id выбранных тегов

        # Загружаем имена тегов по id
        conn = db_service.get_connection()
        cur = conn.cursor()

        if selected_ids:
            # Получаем имена тегов
            sql = "SELECT name FROM tags WHERE id = ANY(%s)"
            cur.execute(sql, (selected_ids,))
            tag_names = [row[0] for row in cur.fetchall()]

            # Формируем словарь {tag_name: 0.5}
            interests_vector = {name: 0.5 for name in tag_names}
        else:
            # Пустой вектор
            interests_vector = {}

        # Обновляем профиль пользователя
        cur.execute(
            "UPDATE users SET interests=%s WHERE id=%s",
            (json.dumps(interests_vector), session["user_id"])
        )
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({"status": "ok"})

    return render_template("interests.html")

# --- Main / recommendations ---
@app.route("/")
@login_required
def index():
    return render_template("index.html", yandex_api_key=YANDEX_API)

@app.route("/api/recommendations", methods=["POST"])
@login_required
def api_recommendations():
    data = request.get_json()
    user_id = session["user_id"]

    page = int(data.get("page", 1))
    page_size = 32
    offset = (page - 1) * page_size

    active_profile = db_service.get_active_geoprofile(user_id)
    
    lat = lon = None
    if active_profile:
        lat = active_profile.get("lat")
        lon = active_profile.get("lon")
    else:
        try:
            lat = float(data.get("lat"))
            lon = float(data.get("lon"))
        except (TypeError, ValueError):
            pass

    search_mode = db_service.get_user_search_mode(user_id)
    user_interests = db_service.get_user_interests(user_id)

    events = get_recommendations(
        user_id=user_id,
        latitude=lat,
        longitude=lon,
        search_mode=search_mode
    )

    total = len(events)
    page_events = events[offset: offset + page_size]

    result = []
    for e in page_events:
        matched = [t for t in e.get("tags", []) if t in user_interests]
        matched_sorted = sorted(
            matched,
            key=lambda t: user_interests.get(t, 0),
            reverse=True
        )[:4]

        result.append({
            "id": e.get("id"),
            "title": e.get("title"),
            "place": e.get("place"),
            "thumbnail": e.get("thumbnail"),
            "matched_tags": matched_sorted
        })

    return jsonify({
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size
    })

@app.route("/api/event/<int:event_id>")
@login_required
def api_event(event_id):
    # 1. Запрос в KuDaGo
    r = requests.get(
        f"{KUDAGO_API}/events/{event_id}/",
        params={
            "fields": "title,dates,description,place,location,images,tags",
            "expand": "place,location"
        },
        timeout=10
    )
    r.raise_for_status()
    data = r.json()

    # 2. Актуальные даты
    now = datetime.now().timestamp()
    future_dates = [
        {"start": d["start"], "end": d["end"]}
        for d in data.get("dates", [])
        if d.get("end", 0) >= now
    ]

    # 3. Интересы пользователя
    conn = db_service.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT interests FROM users WHERE id = %s", (session["user_id"],))
    interests = cur.fetchone()[0] or {}
    cur.close()
    conn.close()

    event_tags = data.get("tags", [])
    matched_tags = [t for t in event_tags if t in interests]

    place = data.get("place") or {}
    location = data.get("location") or {}

    return jsonify({
        "id": event_id,
        "title": data.get("title"),
        "description": data.get("description"),
        "dates": future_dates,
        "images": [img["image"] for img in data.get("images", [])],
        "place_name": place.get("title") or location.get("name"),
        "address": place.get("address"),
        "lat": place.get("coords", {}).get("lat"),
        "lon": place.get("coords", {}).get("lon"),
        "matched_tags": matched_tags
    })

@app.route("/event/<int:event_id>")
@login_required
def event_page(event_id):
    return render_template(
        "event.html",
        event_id=event_id,
        yandex_api_key=YANDEX_API
    )

# --- Tracked events page ---
@app.route("/tracked")
@login_required
def tracked():
    return render_template("tracked.html")

@app.route("/api/tracked-events")
@login_required
def api_tracked_events():
    now = datetime.now()

    conn = db_service.get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute("""
        SELECT 
            e.id,
            e.title,
            e.thumbnail,
            e.dates
        FROM tracked_events t
        JOIN events_archive e ON e.id = t.event_id
        WHERE t.user_id = %s
    """, (session["user_id"],))

    now_ts = int(datetime.now(tz=timezone.utc).timestamp())

    actual = []
    archive = []

    for ev in cur.fetchall():
        dates = ev["dates"] or []

        has_future = any(
            d.get("end", 0) >= now_ts
            for d in dates
            if isinstance(d, dict)
        )

        card = {
            "id": ev["id"],
            "title": ev["title"],
            "image": ev["thumbnail"],
        }

        if has_future:
            actual.append(card)
        else:
            archive.append(card)

    return jsonify({
        "actual": actual,
        "archive": archive
    })

@app.route("/api/track/<int:event_id>", methods=["POST"])
@login_required
def api_track_event(event_id):
    conn = db_service.get_connection()
    cur = conn.cursor()

    try:
        # 1. Добавляем в tracked_events
        cur.execute(
            """
            INSERT INTO tracked_events (user_id, event_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, event_id) DO NOTHING
            """,
            (session["user_id"], event_id)
        )

        # 2. Получаем текущие интересы пользователя
        cur.execute(
            "SELECT interests FROM users WHERE id = %s",
            (session["user_id"],)
        )
        interests = cur.fetchone()[0] or {}

        # 3. Получаем теги события
        cur.execute(
            "SELECT tags FROM events_archive WHERE id = %s",
            (event_id,)
        )
        row = cur.fetchone()
        event_tags = row[0] if row else []

        # 4. Обновляем вектор интересов
        new_interests = recommender_service.update_interests_on_watch(
            interests,
            event_tags
        )

        # 5. Сохраняем
        cur.execute(
            "UPDATE users SET interests = %s WHERE id = %s",
            (json.dumps(new_interests), session["user_id"])
        )

        conn.commit()

    finally:
        cur.close()
        conn.close()

    return jsonify({"status": "ok"})

@app.route("/api/tracked-events/<int:event_id>/grade", methods=["POST"])
@login_required
def grade_tracked_event(event_id):
    data = request.json
    liked = data.get("liked")
    user_id = session["user_id"]
    
    interests = db_service.get_user_interests(user_id)
    event_tags = db_service.get_event_tags(event_id)
    
    new_interests = recommender_service.update_interests_on_grade(interests, event_tags, liked)
    db_service.update_user_interests(user_id, new_interests)
    
    conn = db_service.get_connection()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM tracked_events
        WHERE user_id = %s AND event_id = %s
    """, (user_id, event_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({"ok": True})

# --- Profile and geoprofiles ---
@app.route("/profile")
@login_required
def profile():
    return render_template("geoprofiles.html", yandex_api_key=YANDEX_API)

# Получение всех профилей
@app.route("/api/geoprofiles", methods=["GET", "POST"])
@login_required
def geoprofiles_api():
    conn = db_service.get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "GET":
        cur.execute("SELECT geoprofiles FROM users WHERE id=%s", (session["user_id"],))
        profiles = cur.fetchone()["geoprofiles"] or []
        return jsonify(profiles)

    # POST = добавление нового профиля
    data = request.json
    new_profile = {
        "id": f"p{int(time.time()*1000)}",
        "name": data["name"],
        "lat": data["lat"],
        "lon": data["lon"]
    }

    cur.execute("""
        UPDATE users
        SET geoprofiles = COALESCE(geoprofiles, '[]'::jsonb) || %s::jsonb
        WHERE id = %s
    """, (json.dumps([new_profile]), session["user_id"]))

    conn.commit()
    return jsonify({"status": "ok"})

# Удаление профиля
@app.route("/api/geoprofiles/<profile_id>", methods=["DELETE"])
@login_required
def geoprofiles_delete(profile_id):
    conn = db_service.get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Получаем текущие профили
    cur.execute("SELECT geoprofiles, active_profile_id FROM users WHERE id=%s", (session["user_id"],))
    user_row = cur.fetchone()
    profiles = user_row.get("geoprofiles") or []
    active_id = user_row.get("active_profile_id")

    # Удаляем профиль по ID
    profiles = [p for p in profiles if str(p.get("id")) != str(profile_id)]

    # Если удаляемый профиль был активным, сбрасываем active_profile_id
    new_active = active_id if str(active_id) in [str(p.get("id")) for p in profiles] else None

    cur.execute("""
        UPDATE users
        SET geoprofiles = %s::jsonb, active_profile_id = %s
        WHERE id = %s
    """, (json.dumps(profiles), new_active, session["user_id"]))

    conn.commit()
    return jsonify({"status": "ok"})

# Получение активного профиля
@app.route("/api/geoprofiles/active", methods=["GET", "POST"])
@login_required
def geoprofiles_active():
    conn = db_service.get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "GET":
        cur.execute("SELECT active_profile_id FROM users WHERE id=%s", (session["user_id"],))
        row = cur.fetchone()
        active = row["active_profile_id"] if row else None
        cur.close()
        conn.close()
        return jsonify(active)

    # POST = установка активного профиля
    data = request.json
    active_id = data.get("active_profile_id")
    cur.execute("UPDATE users SET active_profile_id=%s WHERE id=%s",
                (active_id, session["user_id"]))
    conn.commit()
    return jsonify({"status": "ok"})

# Получение/установка режима поиска
@app.route("/api/search-mode", methods=["GET", "POST"])
@login_required
def search_mode_api():
    conn = db_service.get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    if request.method == "GET":
        cur.execute("SELECT active_search_mode FROM users WHERE id=%s", (session["user_id"],))
        row = cur.fetchone()
        mode = row["active_search_mode"] if row and row["active_search_mode"] else "balanced"
        cur.close()
        conn.close()
        return jsonify(mode)

    # POST = установка режима
    data = request.json
    mode = data.get("mode", "balanced")
    if mode not in ("nearby", "balanced", "interests"):
        mode = "balanced"
    cur.execute("UPDATE users SET active_search_mode=%s WHERE id=%s",
                (mode, session["user_id"]))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/api/search", methods=["POST"])
@login_required
def api_search():
    data = request.get_json()
    query = (data.get("query") or "").strip()
    page = int(data.get("page", 1))
    page_size = 32
    offset = (page - 1) * page_size

    if not query:
        return jsonify({"items": [], "total": 0, "page": page, "page_size": page_size})

    events = search_events_from_db_by_query(query)

    total = len(events)
    page_events = events[offset:offset+page_size]

    result = []
    for e in page_events:
        result.append({
            "id": e.get("id"),
            "title": e.get("title"),
            "place": e.get("place"),
            "thumbnail": e.get("thumbnail"),
            "matched_tags": e.get("tags")[:4] or []
        })

    return jsonify({
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size
    })

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
