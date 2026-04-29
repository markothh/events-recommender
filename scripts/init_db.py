import sys
sys.path.insert(0, '/app')

import psycopg2
from datetime import datetime


def get_connection():
    return psycopg2.connect(
        host='db',
        user='postgres',
        password='123123',
        dbname='events_db'
    )


def get_connection():
    return psycopg2.connect(
        host='db',
        user='postgres',
        password='123123',
        dbname='events_db'
    )


def load_tags():
    try:
        conn = get_connection()
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
    try:
        print('Refreshing events_cache...')
        conn = get_connection()
        cur = conn.cursor()
        cur.execute('REFRESH MATERIALIZED VIEW events_cache')
        conn.commit()
        print('events_cache refreshed')
        cur.close()
        conn.close()
    except Exception as e:
        print(f'Error refreshing cache: {e}')


def update_events():
    try:
        print('Updating events from Kudago API...')
        from services.kudago_client import kudago_client
        
        events = kudago_client.fetch_events_since(datetime.now())
        if events:
            from scripts.kudago_sync import save_events_to_db
            save_events_to_db(events, datetime.now())
            refresh_cache()
            print(f'Updated {len(events)} events')
        else:
            print('No new events')
    except Exception as e:
        print(f'Error updating events: {e}')


if __name__ == '__main__':
    load_tags()
    update_events()