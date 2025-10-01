"""
aWATTar Price Service
Holt Day-Ahead Strompreise von aWATTar API
"""

import requests
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


def get_day_ahead(region='AT', currency='EUR', demo_mode=True) -> List[Tuple[datetime, float]]:
    """
    Holt Day-Ahead Strompreise von aWATTar
    
    Args:
        region: 'AT' oder 'DE'
        currency: 'EUR'
        demo_mode: Falls True, werden Demo-Daten zurückgegeben
        
    Returns:
        Liste von (timestamp, price_eur_per_mwh) Tupeln
    """
    
    if demo_mode:
        return _get_demo_prices()
    
    try:
        return _fetch_real_prices(region)
    except Exception as e:
        logger.error(f"Failed to fetch real prices: {e}, falling back to demo")
        return _get_demo_prices()


def _fetch_real_prices(region='AT') -> List[Tuple[datetime, float]]:
    """Holt echte Preise von aWATTar API"""
    
    # aWATTar API Endpoint
    if region == 'AT':
        url = 'https://api.awattar.at/v1/marketdata'
    elif region == 'DE':
        url = 'https://api.awattar.de/v1/marketdata'
    else:
        raise ValueError(f"Unknown region: {region}")
    
    # Zeitbereich: Nächste 24-48 Stunden
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(hours=48)
    
    params = {
        'start': int(start.timestamp() * 1000),  # Millisekunden
        'end': int(end.timestamp() * 1000)
    }
    
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    
    # Parse Daten
    prices = []
    for entry in data.get('data', []):
        ts = datetime.fromtimestamp(entry['start_timestamp'] / 1000, tz=timezone.utc)
        # aWATTar gibt Preise in EUR/MWh (bereits richtig)
        price = entry['marketprice']  # EUR/MWh
        prices.append((ts, price))
    
    logger.info(f"Fetched {len(prices)} price points from aWATTar {region}")
    
    return prices


def _get_demo_prices() -> List[Tuple[datetime, float]]:
    """
    Generiert realistische Demo-Preise
    
    Basierend auf typischen Day-Ahead Mustern:
    - Niedrig nachts (50-80 EUR/MWh)
    - Hoch morgens und abends (100-150 EUR/MWh)
    - Mittel tagsüber (80-120 EUR/MWh)
    """
    
    base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    
    # Realistisches Preisprofil (24h)
    hourly_prices = [
        # Nachts (0-6 Uhr): Niedrig
        65, 60, 55, 50, 52, 58,
        # Morgens (6-12 Uhr): Steigend
        85, 110, 135, 130, 120, 115,
        # Mittag (12-18 Uhr): Hoch, aber schwankend
        105, 95, 90, 100, 110, 125,
        # Abends (18-24 Uhr): Peak, dann fallend
        145, 150, 140, 120, 95, 75
    ]
    
    prices = []
    for h in range(24):
        ts = base + timedelta(hours=h)
        price = hourly_prices[h]
        prices.append((ts, float(price)))
    
    logger.debug(f"Generated {len(prices)} demo price points")
    
    return prices
