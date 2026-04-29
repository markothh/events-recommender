# Kudago API client service
import requests
from datetime import datetime
from typing import List, Dict, Optional
import json

from config import KUDAGO_API, DB


class KudagoClient:
    def __init__(self, api_url: str = None):
        self._api_url = api_url or KUDAGO_API

    def fetch_events(self, location: str = "msk", category: str = None,
                 since: datetime = None, page: int = 1) -> List[Dict]:
        params = {
            "location": location,
            "page": page,
            "fields": "id,title,place,location,dates,images,tags",
            "expand": "place,location"
        }
        if category:
            params["categories"] = category
            
        try:
            r = requests.get(f"{self._api_url}/events/", params=params, timeout=10)
            r.raise_for_status()
            return r.json().get("results", [])
        except requests.exceptions.RequestException:
            return []

    def fetch_events_since(self, since: datetime) -> List[Dict]:
        if since is None:
            since = datetime.now()
        since_ts = int(since.timestamp())
        
        all_events = []
        page = 1
        
        while page <= 10:
            events = self.fetch_events(page=page)
            if not events:
                break
                
            valid_events = []
            for e in events:
                dates = e.get("dates") or []
                for d in dates:
                    start_ts = d.get("start", 0)
                    if start_ts and 0 < start_ts < 32503680000:
                        if start_ts >= since_ts:
                            valid_events.append(e)
                        break
            
            all_events.extend(valid_events)
            page += 1
            
            if len(valid_events) < len(events):
                break
                
        return all_events

    def get_event(self, event_id: int, fields: str = None) -> Optional[Dict]:
        try:
            params = {"fields": fields or "title,dates,description,place,location,images,tags"}
            r = requests.get(f"{self._api_url}/events/{event_id}/", params=params, timeout=10)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException:
            return None

    def get_event_tags(self, event_id: int) -> List[str]:
        event = self.get_event(event_id)
        return event.get("tags", []) if event else []


kudago_client = KudagoClient()