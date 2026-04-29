import sys
sys.path.insert(0, '/app')

import psycopg2
from datetime import datetime

def load_tags():
    """Загружает теги из tags.txt если таблица пустая"""
    try:
        conn = psycopg2.connect(
            host='db',
            user='postgres', 
            password='123123',
            dbname='events_db'
        )
        cur = conn.cursor()
        
        cur.execute('SELECT COUNT(*) FROM tags')
        count = cur.fetchone()[0]
        
        if count == 0:
            print('Loading tags from file...')
            with open('tags.txt', 'r', encoding='utf-8') as f:
                for line in f:
                    tag = line.strip()
                    if tag:
                        cur.execute(
                            'INSERT INTO tags (name) VALUES (%s) ON CONFLICT DO NOTHING',
                            (tag,)
                        )
            conn.commit()
            print('Tags loaded successfully')
        else:
            print(f'Tags already exist: {count}')
            
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f'Error loading tags: {e}')

def refresh_cache():
    """Обновляет materialized view events_cache"""
    try:
        print('Refreshing events_cache...')
        conn = psycopg2.connect(
            host='db',
            user='postgres',
            password='123123',
            dbname='events_db'
        )
        cur = conn.cursor()
        cur.execute('REFRESH MATERIALIZED VIEW events_cache')
        conn.commit()
        print('events_cache refreshed')
        cur.close()
        conn.close()
    except Exception as e:
        print(f'Error refreshing cache: {e}')

def update_events():
    """Загружает события из Kudago API"""
    try:
        print('Updating events from Kudago API...')
        from db import update_events_since
        count = update_events_since(datetime.now())
        print(f'Updated {count} events')
        refresh_cache()
    except Exception as e:
        print(f'Error updating events: {e}')

if __name__ == '__main__':
    load_tags()
    update_events()