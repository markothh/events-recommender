from math import radians, sin, cos, sqrt, atan2
from typing import Dict
import numpy as np

def cosine_similarity(vec_a: Dict[str, float], vec_b: Dict[str, float]) -> float:
    """
    Косинусная похожесть между двумя разреженными векторами (dicts).
    Возвращает значение в [0,1] (если негативные значения не используются).
    """
    if not vec_a or not vec_b:
        return 0.0
    # общий набор тегов
    keys = set(vec_a.keys()) | set(vec_b.keys())
    a = np.array([vec_a.get(k, 0.0) for k in keys], dtype=float)
    b = np.array([vec_b.get(k, 0.0) for k in keys], dtype=float)
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    cos = float(np.dot(a, b) / denom)
    # косинус может быть -1..1; для наших скорингов возьмём max(0, cos)
    return max(0.0, cos)

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371  # радиус Земли в км
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c
