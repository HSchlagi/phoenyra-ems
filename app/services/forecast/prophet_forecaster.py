"""
Phoenyra EMS - Prophet-basiertes Forecasting
Verwendet Facebook Prophet für zeitreihenbasierte Prognosen
"""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Prophet Import (optional)
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logger.warning("Prophet not available, using fallback forecasting")


class ProphetForecaster:
    """
    Prophet-basierter Forecaster für Last und Preise
    
    Features:
    - Automatische Saisonalität (täglich, wöchentlich, jährlich)
    - Trend-Erkennung
    - Holiday Effects
    - Uncertainty Intervals
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.models = {}  # Cache für trainierte Modelle
        
    def forecast_load(self, 
                     historical_data: Optional[pd.DataFrame] = None,
                     hours: int = 24) -> List[Tuple[datetime, float]]:
        """
        Erstellt Lastprognose mit Prophet
        
        Args:
            historical_data: DataFrame mit Spalten ['ds', 'y'] (timestamp, load)
            hours: Prognosehorizont in Stunden
            
        Returns:
            Liste von (timestamp, load_kw) Tupeln
        """
        
        if not PROPHET_AVAILABLE or historical_data is None:
            return self._fallback_load_forecast(hours)
        
        try:
            # Prophet-Modell trainieren/laden
            if 'load' not in self.models:
                self.models['load'] = self._train_load_model(historical_data)
            
            model = self.models['load']
            
            # Future DataFrame erstellen
            future = model.make_future_dataframe(periods=hours, freq='H')
            
            # Prognose erstellen
            forecast = model.predict(future)
            
            # Letzte N Stunden extrahieren
            forecast_data = forecast.tail(hours)
            
            # Konvertiere zu Liste von Tupeln
            result = []
            for _, row in forecast_data.iterrows():
                ts = row['ds'].to_pydatetime()
                load = max(0, row['yhat'])  # Keine negativen Lasten
                result.append((ts, float(load)))
            
            logger.info(f"Prophet load forecast: {len(result)} hours")
            return result
            
        except Exception as e:
            logger.error(f"Prophet load forecast failed: {e}, using fallback")
            return self._fallback_load_forecast(hours)
    
    def forecast_price(self,
                      historical_data: Optional[pd.DataFrame] = None,
                      hours: int = 24) -> List[Tuple[datetime, float]]:
        """
        Erstellt Preisprognose mit Prophet
        
        Args:
            historical_data: DataFrame mit Spalten ['ds', 'y'] (timestamp, price)
            hours: Prognosehorizont in Stunden
            
        Returns:
            Liste von (timestamp, price_eur_per_mwh) Tupeln
        """
        
        if not PROPHET_AVAILABLE or historical_data is None:
            return self._fallback_price_forecast(hours)
        
        try:
            # Prophet-Modell trainieren/laden
            if 'price' not in self.models:
                self.models['price'] = self._train_price_model(historical_data)
            
            model = self.models['price']
            
            # Future DataFrame erstellen
            future = model.make_future_dataframe(periods=hours, freq='H')
            
            # Prognose erstellen
            forecast = model.predict(future)
            
            # Letzte N Stunden extrahieren
            forecast_data = forecast.tail(hours)
            
            # Konvertiere zu Liste von Tupeln
            result = []
            for _, row in forecast_data.iterrows():
                ts = row['ds'].to_pydatetime()
                price = max(0, row['yhat'])  # Keine negativen Preise
                result.append((ts, float(price)))
            
            logger.info(f"Prophet price forecast: {len(result)} hours")
            return result
            
        except Exception as e:
            logger.error(f"Prophet price forecast failed: {e}, using fallback")
            return self._fallback_price_forecast(hours)
    
    def _train_load_model(self, data: pd.DataFrame) -> Prophet:
        """Trainiert Prophet-Modell für Last"""
        
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True,
            changepoint_prior_scale=0.05,
            seasonality_mode='multiplicative'
        )
        
        # Fit Modell
        model.fit(data)
        
        logger.info("Prophet load model trained")
        return model
    
    def _train_price_model(self, data: pd.DataFrame) -> Prophet:
        """Trainiert Prophet-Modell für Preise"""
        
        model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=False,  # Preise haben keine jährliche Saisonalität
            changepoint_prior_scale=0.1,
            seasonality_mode='additive'
        )
        
        # Fit Modell
        model.fit(data)
        
        logger.info("Prophet price model trained")
        return model
    
    def _fallback_load_forecast(self, hours: int) -> List[Tuple[datetime, float]]:
        """Fallback: Pattern-basierte Lastprognose"""
        
        base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        
        # Typisches Lastprofil (24h Muster)
        hourly_pattern = [
            8, 7, 6, 5, 6, 8,  # 0-5: Nacht
            15, 25, 28, 22, 18, 16,  # 6-11: Morgen
            20, 22, 20, 18, 20, 24,  # 12-17: Tag
            30, 32, 28, 22, 15, 10   # 18-23: Abend
        ]
        
        result = []
        for h in range(hours):
            ts = base + timedelta(hours=h)
            hour_of_day = ts.hour
            base_load = hourly_pattern[hour_of_day]
            
            # Kleine Variation
            variation = np.random.uniform(0.9, 1.1)
            load = base_load * variation
            
            result.append((ts, float(load)))
        
        return result
    
    def _fallback_price_forecast(self, hours: int) -> List[Tuple[datetime, float]]:
        """Fallback: Pattern-basierte Preisprognose"""
        
        base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        
        # Typisches Preisprofil (24h)
        hourly_prices = [
            65, 60, 55, 50, 52, 58,  # Nacht: niedrig
            85, 110, 135, 130, 120, 115,  # Morgen: steigend
            105, 95, 90, 100, 110, 125,  # Tag: mittel
            145, 150, 140, 120, 95, 75   # Abend: Peak
        ]
        
        result = []
        for h in range(hours):
            ts = base + timedelta(hours=h)
            hour_of_day = ts.hour
            price = hourly_prices[hour_of_day]
            
            # Kleine Variation
            variation = np.random.uniform(0.95, 1.05)
            price = price * variation
            
            result.append((ts, float(price)))
        
        return result
    
    def generate_synthetic_history(self, days: int = 30) -> dict:
        """
        Generiert synthetische historische Daten für Training
        
        Returns:
            Dictionary mit 'load' und 'price' DataFrames
        """
        
        start = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Load History
        load_data = []
        for day in range(days):
            for hour in range(24):
                ts = start + timedelta(days=day, hours=hour)
                
                # Basis-Last mit Wochentag-Effekt
                is_weekend = ts.weekday() >= 5
                weekday_factor = 0.7 if is_weekend else 1.0
                
                hour_of_day = ts.hour
                hourly_pattern = [8,7,6,5,6,8,15,25,28,22,18,16,20,22,20,18,20,24,30,32,28,22,15,10]
                base_load = hourly_pattern[hour_of_day] * weekday_factor
                
                # Trend und Noise
                trend = day * 0.05  # Leichter Anstieg
                noise = np.random.normal(0, 2)
                load = max(0, base_load + trend + noise)
                
                load_data.append({'ds': ts, 'y': load})
        
        # Price History
        price_data = []
        for day in range(days):
            for hour in range(24):
                ts = start + timedelta(days=day, hours=hour)
                
                hour_of_day = ts.hour
                hourly_prices = [65,60,55,50,52,58,85,110,135,130,120,115,105,95,90,100,110,125,145,150,140,120,95,75]
                base_price = hourly_prices[hour_of_day]
                
                # Wochenend-Effekt
                is_weekend = ts.weekday() >= 5
                weekend_factor = 0.85 if is_weekend else 1.0
                
                # Noise
                noise = np.random.normal(0, 10)
                price = max(20, base_price * weekend_factor + noise)
                
                price_data.append({'ds': ts, 'y': price})
        
        return {
            'load': pd.DataFrame(load_data),
            'price': pd.DataFrame(price_data)
        }


