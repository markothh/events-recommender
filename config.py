import os
import urllib.parse

db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:123123@db:5432/events_db')
parsed = urllib.parse.urlparse(db_url)

DB = {
    "host": parsed.hostname or "db",
    "port": parsed.port or 5432,
    "dbname": parsed.path.lstrip('/') if parsed.path else "events_db",
    "user": parsed.username or "postgres",
    "password": parsed.password or "123123"
}

KUDAGO_API = os.environ.get('KUDAGO_API', 'https://kudago.com/public-api/v1.4')
YANDEX_API = os.environ.get('YANDEX_API', '31329796-880c-441b-b0e1-2b6fc0b9cdea')

SECRET = os.environ.get('SECRET', 'tarasova_sofya_iuk4-82b_programm_engineering_diploma')


SEARCH_MODES = {
    "nearby": 0.3,      # Рядом - больше вес геолокации
    "balanced": 0.6,    # Сбалансированный
    "interests": 0.85   # По интересам - больше вес похожести
}

CITY_CHANGE_PENALTY = 0.3
SAME_CITY_GRADE = 1.0
GEOSCORE_DESCEND = 50.0
LEARNING_RATE_GRADE = 0.05
LEARNING_RATE_WATCH = 0.01
DECAY_RATE = 0.01
NEW_TAG_INIT_WATCH = 0.2
NEW_TAG_INIT_GRADE = 0.4
