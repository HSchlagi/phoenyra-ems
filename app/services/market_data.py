"""
Phoenyra EMS - Market Data Service
Berechnet Marktdaten wie Preis-Trends und Volatilität
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import logging
import numpy as np

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Berechnet Marktdaten aus Preis-Historie:
    - Preis-Trend (steigend/fallend)
    - Preis-Volatilität
    - Preis-Prognosen
    """
    
    def __init__(self):
        self.price_history: List[Dict[str, Any]] = []
        self.max_history_hours = 168  # 7 Tage
    
    def update_price_history(self, timestamp: datetime, price: float):
        """Aktualisiert Preis-Historie"""
        self.price_history.append({
            'timestamp': timestamp,
            'price': price
        })
        
        # Halte Historie auf max_history_hours begrenzt
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.max_history_hours)
        self.price_history = [
            p for p in self.price_history 
            if p['timestamp'] >= cutoff
        ]
    
    def get_price_trend(self, hours: int = 6) -> float:
        """
        Berechnet Preis-Trend der letzten N Stunden
        Returns: -1.0 (fallend) bis +1.0 (steigend)
        """
        if len(self.price_history) < 2:
            return 0.0
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_prices = [
            p['price'] for p in self.price_history 
            if p['timestamp'] >= cutoff
        ]
        
        if len(recent_prices) < 2:
            return 0.0
        
        # Linear Regression für Trend
        x = np.arange(len(recent_prices))
        y = np.array(recent_prices)
        
        # Normalisiere auf -1 bis +1
        if len(y) > 1:
            slope = np.polyfit(x, y, 1)[0]
            # Normalisiere: max slope = 1.0, min slope = -1.0
            # Annahme: max Preisänderung = 50 EUR/MWh pro Stunde
            normalized_slope = np.clip(slope / 50.0, -1.0, 1.0)
            return float(normalized_slope)
        
        return 0.0
    
    def get_price_volatility(self, hours: int = 24) -> float:
        """
        Berechnet Preis-Volatilität (Standardabweichung)
        Returns: 0.0 (stabil) bis 1.0 (sehr volatil)
        """
        if len(self.price_history) < 2:
            return 0.0
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        recent_prices = [
            p['price'] for p in self.price_history 
            if p['timestamp'] >= cutoff
        ]
        
        if len(recent_prices) < 2:
            return 0.0
        
        # Berechne Standardabweichung
        prices_array = np.array(recent_prices)
        std_dev = np.std(prices_array)
        
        # Normalisiere auf 0-1 (Annahme: max StdDev = 100 EUR/MWh)
        normalized_volatility = min(std_dev / 100.0, 1.0)
        return float(normalized_volatility)
    
    def get_current_price(self) -> Optional[float]:
        """Gibt aktuellsten Preis zurück"""
        if not self.price_history:
            return None
        return self.price_history[-1]['price']
    
    def get_market_data(self) -> Dict[str, Any]:
        """
        Gibt vollständige Marktdaten zurück
        """
        return {
            'current_price': self.get_current_price(),
            'price_trend': self.get_price_trend(hours=6),
            'price_volatility': self.get_price_volatility(hours=24),
            'price_history_count': len(self.price_history)
        }
    
    def get_price_forecast_6h_avg(self, forecast_data: Dict[str, Any]) -> float:
        """
        Berechnet Durchschnittspreis der nächsten 6 Stunden aus Forecast
        """
        prices = forecast_data.get('prices', [])
        if not prices:
            return 0.0
        
        # Nimm nächste 6 Stunden
        next_6h = prices[:6] if len(prices) >= 6 else prices
        if not next_6h:
            return 0.0
        
        # Extrahiere Preise (kann Dict oder List sein)
        price_values = []
        for p in next_6h:
            if isinstance(p, dict):
                price_values.append(p.get('price', p.get('value', 0.0)))
            elif isinstance(p, (int, float)):
                price_values.append(float(p))
        
        if not price_values:
            return 0.0
        
        return float(np.mean(price_values))

