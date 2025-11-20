"""
Grid Tariff Service - Verwaltung dynamischer Netzentgelte

Unterstützt:
- NE5 / NE7 Tarifstrukturen
- Zeitvariable Netzentgelte (Hochlastzeitfenster)
- Integration in Optimierungslogik
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TariffWindow:
    """Zeitfenster mit speziellem Tarif"""
    start_time: time
    end_time: time
    multiplier: float  # Multiplikator für Basis-Tarif


@dataclass
class GridTariffConfig:
    """Konfiguration für Netzentgelte"""
    enabled: bool = False
    tariff_structure: str = "NE7"  # 'NE5', 'NE7', 'custom'
    time_variable: bool = True
    base_tariff_eur_per_kw: float = 0.15  # Basis-Tarif in EUR/kW
    high_load_windows: List[Dict[str, any]] = None  # Zeitfenster mit erhöhtem Tarif
    
    def __post_init__(self):
        if self.high_load_windows is None:
            self.high_load_windows = []


class GridTariffService:
    """
    Service zur Berechnung von Netzentgelten
    
    Unterstützt:
    - Statische Tarife (NE5/NE7)
    - Zeitvariable Tarife mit Hochlastzeitfenstern
    - Berechnung der monatlichen/jährlichen Netzgebühren
    """
    
    def __init__(self, config: Dict[str, any]):
        """
        Initialisiert den Grid Tariff Service
        
        Args:
            config: Konfiguration aus ems.yaml (grid_tariffs Sektion)
        """
        self.config = GridTariffConfig(
            enabled=config.get('enabled', False),
            tariff_structure=config.get('tariff_structure', 'NE7'),
            time_variable=config.get('time_variable', True),
            base_tariff_eur_per_kw=config.get('base_tariff_eur_per_kw', 0.15),
            high_load_windows=config.get('high_load_windows', [])
        )
        
        # Parse Zeitfenster
        self._windows: List[TariffWindow] = []
        if self.config.high_load_windows:
            for window in self.config.high_load_windows:
                try:
                    start_str = window.get('start', '00:00')
                    end_str = window.get('end', '23:59')
                    multiplier = float(window.get('multiplier', 1.0))
                    
                    start_time = datetime.strptime(start_str, '%H:%M').time()
                    end_time = datetime.strptime(end_str, '%H:%M').time()
                    
                    self._windows.append(TariffWindow(
                        start_time=start_time,
                        end_time=end_time,
                        multiplier=multiplier
                    ))
                except Exception as e:
                    logger.warning(f"Fehler beim Parsen des Zeitfensters {window}: {e}")
        
        # Standard-Tarife für NE5/NE7 (vereinfacht)
        self._standard_tariffs = {
            'NE5': 0.12,  # EUR/kW (vereinfacht)
            'NE7': 0.15,  # EUR/kW (vereinfacht)
        }
        
        if self.config.enabled:
            logger.info(f"Grid Tariff Service aktiviert: {self.config.tariff_structure}, "
                       f"Basis-Tarif: {self.config.base_tariff_eur_per_kw} EUR/kW, "
                       f"{len(self._windows)} Hochlastzeitfenster")
    
    def get_tariff_at_time(self, timestamp: datetime) -> float:
        """
        Gibt den aktuellen Tarif für einen Zeitpunkt zurück
        
        Args:
            timestamp: Zeitpunkt für Tarifberechnung
            
        Returns:
            Tarif in EUR/kW
        """
        if not self.config.enabled:
            return 0.0
        
        # Basis-Tarif
        if self.config.tariff_structure in self._standard_tariffs:
            base_tariff = self._standard_tariffs[self.config.tariff_structure]
        else:
            base_tariff = self.config.base_tariff_eur_per_kw
        
        # Zeitvariable Anpassung
        if self.config.time_variable:
            current_time = timestamp.time()
            multiplier = 1.0
            
            # Prüfe ob Zeitpunkt in einem Hochlastzeitfenster liegt
            for window in self._windows:
                if self._is_time_in_window(current_time, window):
                    multiplier = max(multiplier, window.multiplier)
            
            return base_tariff * multiplier
        
        return base_tariff
    
    def _is_time_in_window(self, current_time: time, window: TariffWindow) -> bool:
        """Prüft ob Zeitpunkt in Zeitfenster liegt (unterstützt Über-Mitternacht)"""
        if window.start_time <= window.end_time:
            # Normales Zeitfenster (z.B. 09:00-17:00)
            return window.start_time <= current_time <= window.end_time
        else:
            # Über-Mitternacht (z.B. 22:00-06:00)
            return current_time >= window.start_time or current_time <= window.end_time
    
    def calculate_grid_cost(self, 
                           power_kw: float, 
                           timestamp: datetime,
                           duration_hours: float = 1.0) -> float:
        """
        Berechnet die Netzgebühren für eine bestimmte Leistung
        
        Args:
            power_kw: Leistung am Netzanschlusspunkt (kW)
            timestamp: Zeitpunkt
            duration_hours: Dauer in Stunden (Standard: 1h)
            
        Returns:
            Kosten in EUR
        """
        if not self.config.enabled or power_kw <= 0:
            return 0.0
        
        tariff = self.get_tariff_at_time(timestamp)
        
        # Netzgebühren basieren auf der maximalen Leistung (Leistungspreis)
        # Vereinfacht: Kosten = Tarif * Leistung * Dauer
        # In der Realität würde hier die maximale Leistung über einen Zeitraum verwendet
        cost = tariff * power_kw * duration_hours
        
        return cost
    
    def calculate_monthly_cost(self, 
                              peak_power_kw: float,
                              base_power_kw: Optional[float] = None) -> float:
        """
        Berechnet die monatlichen Netzgebühren basierend auf der Spitzenleistung
        
        Args:
            peak_power_kw: Maximale Leistung im Monat (kW)
            base_power_kw: Basis-Leistung (optional, falls unterschiedlich)
            
        Returns:
            Monatliche Kosten in EUR
        """
        if not self.config.enabled:
            return 0.0
        
        # Basis-Tarif
        if self.config.tariff_structure in self._standard_tariffs:
            base_tariff = self._standard_tariffs[self.config.tariff_structure]
        else:
            base_tariff = self.config.base_tariff_eur_per_kw
        
        # Monatliche Gebühren = Tarif * Spitzenleistung
        # (vereinfacht, in Realität könnte es komplexer sein)
        monthly_cost = base_tariff * peak_power_kw
        
        return monthly_cost
    
    def get_tariff_info(self) -> Dict[str, any]:
        """Gibt Informationen über die aktuelle Tarifkonfiguration zurück"""
        return {
            'enabled': self.config.enabled,
            'tariff_structure': self.config.tariff_structure,
            'time_variable': self.config.time_variable,
            'base_tariff_eur_per_kw': self.config.base_tariff_eur_per_kw,
            'high_load_windows': [
                {
                    'start': w.start_time.strftime('%H:%M'),
                    'end': w.end_time.strftime('%H:%M'),
                    'multiplier': w.multiplier
                }
                for w in self._windows
            ],
            'current_tariff_eur_per_kw': self.get_tariff_at_time(datetime.now()) if self.config.enabled else 0.0
        }

