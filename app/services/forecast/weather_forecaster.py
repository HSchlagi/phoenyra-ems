"""
Phoenyra EMS - Wetterbasierte PV-Prognosen
Verwendet Wetterdaten für präzise PV-Erzeugungsprognosen
"""

from datetime import datetime, timedelta, timezone
from typing import List, Tuple, Optional, Dict, Any
import math
import logging
import requests

logger = logging.getLogger(__name__)


class WeatherForecaster:
    """
    Wetterbasierter PV-Forecaster
    
    Integriert mit OpenWeatherMap API für:
    - Wolkenbedeckung
    - Temperatur
    - Sonneneinstrahlung (GHI)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # OpenWeatherMap API Key (optional)
        self.api_key = self.config.get('openweathermap_api_key', None)
        
        # PV-Anlage Parameter
        self.pv_peak_power_kw = self.config.get('pv_peak_power_kw', 50.0)
        self.pv_efficiency = self.config.get('pv_efficiency', 0.85)
        self.latitude = self.config.get('latitude', 48.2082)  # Wien
        self.longitude = self.config.get('longitude', 16.3738)
        
    def forecast_pv(self, hours: int = 24) -> List[Tuple[datetime, float]]:
        """
        Erstellt wetterbasierte PV-Prognose
        
        Args:
            hours: Prognosehorizont in Stunden
            
        Returns:
            Liste von (timestamp, power_kw) Tupeln
        """
        
        # Hole Wetterdaten
        weather_data = self._get_weather_forecast(hours)
        
        if weather_data:
            return self._calculate_pv_from_weather(weather_data)
        else:
            # Fallback: Clear-Sky Model
            return self._clear_sky_model(hours)
    
    def _get_weather_forecast(self, hours: int) -> Optional[List[Dict[str, Any]]]:
        """
        Holt Wetterprognose von OpenWeatherMap
        
        Returns:
            Liste mit Wetterdaten oder None bei Fehler
        """
        
        if not self.api_key:
            logger.debug("No OpenWeatherMap API key, using clear-sky model")
            return None
        
        try:
            url = "https://api.openweathermap.org/data/2.5/forecast"
            params = {
                'lat': self.latitude,
                'lon': self.longitude,
                'appid': self.api_key,
                'units': 'metric',
                'cnt': min(hours // 3, 40)  # API gibt 3h-Schritte
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse Wetterinfo
            weather_list = []
            for item in data.get('list', []):
                weather_list.append({
                    'timestamp': datetime.fromtimestamp(item['dt'], tz=timezone.utc),
                    'clouds': item['clouds']['all'],  # % Bewölkung
                    'temp': item['main']['temp'],  # °C
                    'description': item['weather'][0]['description']
                })
            
            logger.info(f"Fetched weather data: {len(weather_list)} entries")
            return weather_list
            
        except requests.RequestException as e:
            logger.warning(f"Weather API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Weather data parsing failed: {e}")
            return None
    
    def _calculate_pv_from_weather(self, weather_data: List[Dict[str, Any]]) -> List[Tuple[datetime, float]]:
        """
        Berechnet PV-Leistung aus Wetterdaten
        """
        
        result = []
        
        for weather in weather_data:
            ts = weather['timestamp']
            clouds = weather['clouds']  # 0-100%
            temp = weather['temp']
            
            # Berechne Clear-Sky Wert für diese Zeit
            clear_sky_power = self._get_clear_sky_power(ts)
            
            # Reduziere basierend auf Bewölkung
            # 0% Wolken = 100% Leistung, 100% Wolken = 20% Leistung
            cloud_factor = 1.0 - (clouds / 100.0) * 0.8
            
            # Temperatur-Effekt (PV weniger effizient bei Hitze)
            # Optimal bei 25°C, -0.4% pro °C darüber
            temp_factor = 1.0 - max(0, (temp - 25) * 0.004)
            
            # Finale Leistung
            power = clear_sky_power * cloud_factor * temp_factor
            power = max(0, power)
            
            result.append((ts, float(power)))
        
        # Interpoliere auf stündliche Werte wenn nötig
        if len(result) < 24:
            result = self._interpolate_hourly(result, 24)
        
        return result
    
    def _clear_sky_model(self, hours: int) -> List[Tuple[datetime, float]]:
        """
        Clear-Sky Model: Berechnet PV-Leistung ohne Wolken
        
        Verwendet vereinfachtes astronomisches Modell
        """
        
        base = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
        
        result = []
        
        for h in range(hours):
            ts = base + timedelta(hours=h)
            power = self._get_clear_sky_power(ts)
            result.append((ts, float(power)))
        
        return result
    
    def _get_clear_sky_power(self, timestamp: datetime) -> float:
        """
        Berechnet Clear-Sky PV-Leistung für gegebenen Zeitpunkt
        
        Verwendet Sonnenstand-Berechnung
        """
        
        # Lokalzeit (UTC + Offset)
        local_time = timestamp
        hour = local_time.hour + (local_time.minute / 60.0)
        
        # Sonnenaufgang/Untergang (vereinfacht)
        # Variiert mit Jahreszeit
        day_of_year = timestamp.timetuple().tm_yday
        
        # Näherung: Sonnenaufgang 6-8 Uhr, Untergang 18-20 Uhr
        # Variiert sinusförmig über Jahr
        sunrise_offset = math.sin((day_of_year - 80) / 365.0 * 2 * math.pi) * 2
        sunrise = 7 + sunrise_offset
        sunset = 19 - sunrise_offset
        
        # Tageslänge
        daylight_hours = sunset - sunrise
        
        if hour < sunrise or hour > sunset:
            return 0.0
        
        # Sonnenstand (0 bei Aufgang/Untergang, 1 am Mittag)
        solar_noon = (sunrise + sunset) / 2
        relative_hour = (hour - sunrise) / daylight_hours
        
        # Sinus-Kurve für Sonnenintensität
        sun_elevation = math.sin(relative_hour * math.pi)
        
        # PV-Leistung
        max_power = self.pv_peak_power_kw * self.pv_efficiency
        power = max_power * sun_elevation
        
        # Jahreszeitliche Variation (Winter schwächer)
        seasonal_factor = 0.7 + 0.3 * math.sin((day_of_year - 80) / 365.0 * 2 * math.pi)
        power *= seasonal_factor
        
        return max(0, power)
    
    def _interpolate_hourly(self, data: List[Tuple[datetime, float]], target_hours: int) -> List[Tuple[datetime, float]]:
        """Interpoliert Daten auf stündliche Werte"""
        
        if not data or len(data) >= target_hours:
            return data[:target_hours]
        
        # Einfache lineare Interpolation
        result = []
        base_time = data[0][0]
        
        for h in range(target_hours):
            target_time = base_time + timedelta(hours=h)
            
            # Finde nächste Datenpunkte
            before = None
            after = None
            
            for i, (ts, power) in enumerate(data):
                if ts <= target_time:
                    before = (ts, power)
                if ts >= target_time and after is None:
                    after = (ts, power)
                    break
            
            # Interpoliere
            if before and after and before[0] != after[0]:
                time_diff = (after[0] - before[0]).total_seconds()
                time_offset = (target_time - before[0]).total_seconds()
                ratio = time_offset / time_diff
                
                power = before[1] + (after[1] - before[1]) * ratio
            elif before:
                power = before[1]
            elif after:
                power = after[1]
            else:
                power = 0.0
            
            result.append((target_time, float(power)))
        
        return result


