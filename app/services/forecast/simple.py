"""
Simple Forecast Service
Generiert Lastprognosen und PV-Prognosen
"""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple
import math
import logging

logger = logging.getLogger(__name__)


def pv_forecast(site_id: int, hours: int = 24, demo_mode: bool = True) -> List[Tuple[datetime, float]]:
    """
    Generiert PV-Erzeugungsprognose
    
    Args:
        site_id: Site ID
        hours: Anzahl Stunden
        demo_mode: Falls True, werden Demo-Daten generiert
        
    Returns:
        Liste von (timestamp, power_kw) Tupeln
    """
    
    if demo_mode:
        return _generate_demo_pv(hours)
    
    # TODO: Echte PV-Prognose mit Weather API in Phase 2
    return _generate_demo_pv(hours)


def load_forecast(site_id: int, hours: int = 24, demo_mode: bool = True) -> List[Tuple[datetime, float]]:
    """
    Generiert Lastprognose
    
    Args:
        site_id: Site ID
        hours: Anzahl Stunden
        demo_mode: Falls True, werden Demo-Daten generiert
        
    Returns:
        Liste von (timestamp, power_kw) Tupeln
    """
    
    if demo_mode:
        return _generate_demo_load(hours)
    
    # TODO: Echte Lastprognose mit historischen Daten in Phase 2
    return _generate_demo_load(hours)


def _generate_demo_pv(hours: int) -> List[Tuple[datetime, float]]:
    """
    Generiert realistische Demo-PV-Prognose
    
    Tageskurve mit Sonnenaufgang, Peak mittags, Sonnenuntergang
    """
    
    base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    
    forecast = []
    
    for h in range(hours):
        ts = base + timedelta(hours=h)
        hour_of_day = ts.hour
        
        # Sinus-Kurve für PV (6:00 - 20:00)
        if 6 <= hour_of_day <= 20:
            # Normalisiert auf 0-1 zwischen 6 und 20 Uhr
            t = (hour_of_day - 6) / 14.0
            # Sinus-Kurve (Peak um 13:00)
            power = 50.0 * math.sin(t * math.pi)  # Max 50 kW
        else:
            power = 0.0
        
        forecast.append((ts, round(power, 2)))
    
    logger.debug(f"Generated demo PV forecast for {hours} hours")
    
    return forecast


def _generate_demo_load(hours: int) -> List[Tuple[datetime, float]]:
    """
    Generiert realistische Demo-Lastprognose
    
    Typisches Lastprofil:
    - Niedrig nachts (5-10 kW)
    - Hoch morgens und abends (20-30 kW)
    - Mittel tagsüber (15-20 kW)
    """
    
    base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    
    # Basis-Lastprofil (Watt, typisch für Haushalt/Gewerbe)
    hourly_load = [
        # Nachts (0-6 Uhr)
        8, 7, 6, 5, 6, 8,
        # Morgens (6-12 Uhr)
        15, 25, 28, 22, 18, 16,
        # Mittag (12-18 Uhr)
        20, 22, 20, 18, 20, 24,
        # Abends (18-24 Uhr)
        30, 32, 28, 22, 15, 10
    ]
    
    forecast = []
    
    for h in range(hours):
        ts = base + timedelta(hours=h)
        hour_of_day = ts.hour
        
        # Basis-Last aus Profil
        base_load = hourly_load[hour_of_day]
        
        # Kleine Variation (+/- 10%)
        import random
        variation = random.uniform(0.9, 1.1)
        load = base_load * variation
        
        forecast.append((ts, round(load, 2)))
    
    logger.debug(f"Generated demo load forecast for {hours} hours")
    
    return forecast
