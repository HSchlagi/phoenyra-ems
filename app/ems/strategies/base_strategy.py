"""
Phoenyra EMS - Base Strategy
Abstrakte Basisklasse für alle EMS-Strategien
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class StrategyResult:
    """Ergebnis einer Strategie-Berechnung"""
    
    # Geplante Setpoints (Liste von (timestamp, power_kw))
    schedule: List[tuple[datetime, float]] = field(default_factory=list)
    
    # Erwartete Metriken
    expected_revenue: float = 0.0
    expected_cost: float = 0.0
    expected_profit: float = 0.0
    
    # Zusätzliche Informationen
    strategy_name: str = ""
    confidence_score: float = 1.0  # 0.0 - 1.0
    
    # Details für Visualisierung
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert zu Dictionary für API/Serialisierung"""
        
        # Konvertiere metadata datetime-Objekte zu Strings
        serialized_metadata = {}
        for key, value in self.metadata.items():
            if key == 'soc_schedule' and isinstance(value, list):
                # SoC Schedule: Liste von (datetime, float) Tupeln
                serialized_metadata[key] = [(ts.isoformat() if hasattr(ts, 'isoformat') else ts, val) 
                                           for ts, val in value]
            elif hasattr(value, 'isoformat'):
                # Einzelnes datetime-Objekt
                serialized_metadata[key] = value.isoformat()
            else:
                serialized_metadata[key] = value
        
        return {
            'schedule': [(ts.isoformat(), power) for ts, power in self.schedule],
            'expected_revenue': round(self.expected_revenue, 2),
            'expected_cost': round(self.expected_cost, 2),
            'expected_profit': round(self.expected_profit, 2),
            'strategy_name': self.strategy_name,
            'confidence_score': round(self.confidence_score, 3),
            'metadata': serialized_metadata
        }


class BaseStrategy(ABC):
    """
    Abstrakte Basisklasse für alle EMS-Strategien
    
    Jede Strategie implementiert:
    - evaluate(): Bewertet wie gut die Strategie zur aktuellen Situation passt
    - optimize(): Berechnet den optimalen Fahrplan
    """
    
    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    @abstractmethod
    def evaluate(self, 
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any]) -> float:
        """
        Bewertet wie gut diese Strategie zur aktuellen Situation passt.
        
        Args:
            current_state: Aktueller Anlagenzustand (SoC, Power, etc.)
            forecast_data: Prognosedaten (prices, load, pv, etc.)
            
        Returns:
            Score zwischen 0.0 (ungeeignet) und 1.0 (optimal)
        """
        pass
    
    @abstractmethod
    def optimize(self,
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any],
                 constraints: Optional[Dict[str, Any]] = None) -> StrategyResult:
        """
        Berechnet den optimalen Fahrplan für diese Strategie.
        
        Args:
            current_state: Aktueller Anlagenzustand
            forecast_data: Prognosedaten
            constraints: Technische Constraints (min/max Power, SoC, etc.)
            
        Returns:
            StrategyResult mit geplantem Fahrplan und Metriken
        """
        pass
    
    def validate_forecast_data(self, forecast_data: Dict[str, Any]) -> bool:
        """Validiert ob alle benötigten Prognosedaten vorhanden sind"""
        required_keys = self.get_required_forecast_keys()
        
        for key in required_keys:
            if key not in forecast_data:
                self.logger.warning(f"Missing forecast data: {key}")
                return False
            
            if not forecast_data[key]:
                self.logger.warning(f"Empty forecast data: {key}")
                return False
                
        return True
    
    @abstractmethod
    def get_required_forecast_keys(self) -> List[str]:
        """Gibt Liste der benötigten Forecast-Keys zurück"""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
    
    def __repr__(self) -> str:
        return self.__str__()


