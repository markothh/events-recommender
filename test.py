from db import search_events_from_db, get_user_interest_vector
from recommender import compute_geoscore
from utils import haversine_km

events = search_events_from_db()
print(events[0])

# geoscore=0.0737389329
print(haversine_km(54.493184, 36.2217472, 59.939095, 30.315868))
print(compute_geoscore("Калуга", 54.493184, 36.2217472, "Санкт-Петербург",
                       59.939095, 30.315868))
#geoscore=0.0025196011
print(haversine_km(54.493184, 36.2217472, 37.6171875, 55.7518493917353))
print(compute_geoscore("Калуга", 54.493184, 36.2217472, "Москва",
                       37.6171875, 55.7518493917353))
