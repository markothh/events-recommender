-- Таблица тегов
CREATE TABLE IF NOT EXISTS tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255)
);

-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    interests JSONB DEFAULT '[]'::JSONB,
    geoprofiles JSONB DEFAULT '[]'::JSONB,
    active_profile_id TEXT
);

-- Архив событий
CREATE TABLE IF NOT EXISTS events_archive (
    id INT PRIMARY KEY,
    title TEXT,
    place JSONB,
    dates JSONB,
    tags TEXT[],
    thumbnail TEXT
);

-- Отслеживаемые события
CREATE TABLE IF NOT EXISTS tracked_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    event_id INTEGER REFERENCES events_archive(id),
    UNIQUE(user_id, event_id)
);

-- MATERIALIZED VIEW для кэша актуальных событий
DROP MATERIALIZED VIEW IF EXISTS events_cache;
CREATE MATERIALIZED VIEW events_cache AS
SELECT 
    e.id,
    e.title,
    e.place,
    e.tags,
    e.thumbnail,
    to_timestamp((nearest.dates->>'start')::bigint) AS start_date,
    to_timestamp((nearest.dates->>'end')::bigint) AS end_date
FROM events_archive e
CROSS JOIN LATERAL (
    SELECT d AS dates FROM jsonb_array_elements(e.dates) d
    WHERE to_timestamp((d->>'start')::bigint) > now()
    ORDER BY (d->>'start')::bigint ASC
    LIMIT 1
) AS nearest;

-- Индекс для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_events_cache_start ON events_cache(start_date);

-- Функция для обновления MATERIALIZED VIEW
DROP FUNCTION IF EXISTS refresh_events_cache();
CREATE FUNCTION refresh_events_cache()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW events_cache;
END;
$$ LANGUAGE plpgsql;