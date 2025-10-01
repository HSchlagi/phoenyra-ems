"""
Phoenyra EMS - Peak Shaving Strategy
Reduziert Lastspitzen durch gezielten Batterieentladung
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np

from .base_strategy import BaseStrategy, StrategyResult
import logging

logger = logging.getLogger(__name__)


class PeakShavingStrategy(BaseStrategy):
    """
    Peak Shaving Strategie: Reduziert Lastspitzen
    
    - Analysiert Lastprognose
    - Identifiziert Spitzen
    - Entlädt Batterie während Spitzenzeiten
    - Lädt in Nebenzeiten
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="Peak Shaving", config=config)
        
        # Strategie-Parameter
        self.peak_threshold_percentile = config.get('peak_threshold_percentile', 75) if config else 75
        self.target_peak_reduction_percent = config.get('target_peak_reduction', 20) if config else 20
        
    def evaluate(self, 
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any]) -> float:
        """
        Bewertet ob Peak Shaving sinnvoll ist
        
        Hoher Score wenn:
        - Signifikante Lastspitzen vorhanden
        - Genug SoC verfügbar
        """
        
        if not self.validate_forecast_data(forecast_data):
            return 0.0
        
        load_forecast = forecast_data.get('load', [])
        
        if len(load_forecast) < 2:
            return 0.0
        
        # Extrahiere Lastwerte
        load_values = [l[1] for l in load_forecast]
        
        # Berechne Variabilität
        load_mean = np.mean(load_values)
        load_max = max(load_values)
        load_std = np.std(load_values)
        
        if load_mean == 0:
            return 0.0
        
        # Peak-Intensität
        peak_ratio = (load_max - load_mean) / load_mean if load_mean > 0 else 0
        
        # Volatilität
        cv = load_std / load_mean if load_mean > 0 else 0
        
        # Score: Hoch wenn große Peaks und hohe Volatilität
        score = min(peak_ratio * 2, 1.0) * 0.6 + min(cv * 3, 1.0) * 0.4
        
        self.logger.info(f"Peak Shaving evaluation: peak_ratio={peak_ratio:.2f}, cv={cv:.2f}, score={score:.3f}")
        
        return min(score, 1.0)
    
    def optimize(self,
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any],
                 constraints: Optional[Dict[str, Any]] = None) -> StrategyResult:
        """
        Berechnet Peak Shaving Fahrplan
        
        Einfache Heuristik:
        1. Identifiziere Lastspitzen
        2. Entlade Batterie während Spitzen
        3. Lade in Schwachlastzeiten
        """
        
        if not self.validate_forecast_data(forecast_data):
            return self._create_empty_result()
        
        load_forecast = forecast_data.get('load', [])
        prices = forecast_data.get('prices', [])
        current_soc = current_state.get('soc', 50.0)
        
        # Standard Constraints
        default_constraints = {
            'power_discharge_max_kw': 100.0,
            'power_charge_max_kw': 100.0,
            'soc_min_percent': 10.0,
            'soc_max_percent': 90.0
        }
        constr = {**default_constraints, **(constraints or {})}
        
        # Extrahiere Werte
        timestamps = [l[0] for l in load_forecast]
        load_values = np.array([l[1] for l in load_forecast])
        
        # Bestimme Peak-Schwelle
        peak_threshold = np.percentile(load_values, self.peak_threshold_percentile)
        
        # Erstelle Fahrplan
        schedule = []
        soc_current = current_soc
        
        for i, (ts, load) in enumerate(zip(timestamps, load_values)):
            p_net = 0.0
            
            if load > peak_threshold and soc_current > constr['soc_min_percent']:
                # Peak: Entladen
                p_net = min(constr['power_discharge_max_kw'], 
                           (load - peak_threshold))
                soc_current -= 2.0  # Vereinfachte SoC-Änderung
                
            elif load < peak_threshold * 0.7 and soc_current < constr['soc_max_percent']:
                # Schwachlast: Laden
                p_net = -min(constr['power_charge_max_kw'], 
                            peak_threshold * 0.5)
                soc_current += 2.0
            
            # Clamp SoC
            soc_current = max(constr['soc_min_percent'], 
                            min(constr['soc_max_percent'], soc_current))
            
            schedule.append((ts, p_net))
        
        # Schätze Einsparungen (vereinfacht)
        peak_reduction = max(load_values) - peak_threshold
        estimated_savings = peak_reduction * 0.15 * len(load_forecast) / 24  # EUR/Tag
        
        result = StrategyResult(
            schedule=schedule,
            expected_revenue=0.0,
            expected_cost=0.0,
            expected_profit=estimated_savings,
            strategy_name=self.name,
            confidence_score=0.7,
            metadata={
                'peak_threshold_kw': float(peak_threshold),
                'max_load_kw': float(max(load_values)),
                'estimated_peak_reduction_kw': float(peak_reduction),
                'estimated_savings_eur': float(estimated_savings)
            }
        )
        
        self.logger.info(f"Peak Shaving: threshold={peak_threshold:.1f}kW, "
                        f"reduction={peak_reduction:.1f}kW")
        
        return result
    
    def _create_empty_result(self) -> StrategyResult:
        return StrategyResult(
            schedule=[],
            strategy_name=self.name,
            confidence_score=0.0
        )
    
    def get_required_forecast_keys(self) -> List[str]:
        return ['load']



