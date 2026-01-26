import psycopg2
import json
from config import DB


def load_events():
    conn = psycopg2.connect(**DB)
    cursor = conn.cursor()

    cursor.execute("SELECT tags FROM events")
    rows = cursor.fetchall()

    conn.close()
    return rows


def extract_unique_tags(rows):
    tag_set = set()

    for (tags_raw,) in rows:
        if tags_raw is None:
            continue

        # jsonb[]
        if isinstance(tags_raw, list):
            tag_set.update(tags_raw)
            continue

        # json string
        try:
            parsed = json.loads(tags_raw)
            if isinstance(parsed, list):
                tag_set.update(parsed)
                continue
        except:
            pass

        # string "tag1,tag2"
        if isinstance(tags_raw, str):
            parts = [t.strip() for t in tags_raw.split(",") if t.strip()]
            tag_set.update(parts)

    return tag_set


def save_tags(tag_set):
    conn = psycopg2.connect(**DB)
    cursor = conn.cursor()

    for tag in tag_set:
        try:
            cursor.execute("INSERT INTO tags (name) VALUES (%s)", (tag,))
        except Exception as e:
            print(f"Ошибка при вставке тега {tag}: {e}")

    conn.commit()
    conn.close()


def main():
    rows = load_events()
    unique_tags = extract_unique_tags(rows)
    save_tags(unique_tags)
    print(f"Загружено {len(unique_tags)} уникальных тегов")


if __name__ == "__main__":
    main()
