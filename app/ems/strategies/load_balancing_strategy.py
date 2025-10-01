"""
Phoenyra EMS - Load Balancing Strategy
Glättet Lastschwankungen und optimiert Netzbelastung
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np

from .base_strategy import BaseStrategy, StrategyResult
import logging

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(BaseStrategy):
    """
    Load Balancing Strategie: Glättet Lastschwankungen
    
    Ziele:
    - Reduziert Volatilität der Netzlast
    - Glättet Lastprofil
    - Minimiert Lastgradienten
    - Optimiert Netzstabilität
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="Load Balancing", config=config)
        
        # Strategie-Parameter
        self.smoothing_window = config.get('smoothing_window', 3) if config else 3
        self.target_load_factor = config.get('target_load_factor', 0.8) if config else 0.8
        
    def evaluate(self, 
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any]) -> float:
        """
        Bewertet ob Load Balancing sinnvoll ist
        
        Hoher Score wenn:
        - Hohe Lastvolatilität
        - Starke Gradienten (schnelle Änderungen)
        - Mittlere bis hohe Grundlast
        """
        
        if not self.validate_forecast_data(forecast_data):
            return 0.0
        
        load_forecast = forecast_data.get('load', [])
        
        if len(load_forecast) < 3:
            return 0.0
        
        # Extrahiere Lastwerte
        load_values = np.array([l[1] for l in load_forecast])
        
        if len(load_values) < 3:
            return 0.0
        
        # Berechne Volatilität (Standardabweichung)
        load_std = np.std(load_values)
        load_mean = np.mean(load_values)
        
        if load_mean == 0:
            return 0.0
        
        # Variationskoeffizient
        cv = load_std / load_mean
        
        # Berechne Gradienten (Änderungsraten)
        gradients = np.abs(np.diff(load_values))
        avg_gradient = np.mean(gradients)
        max_gradient = np.max(gradients)
        
        # Normalisiere Gradienten
        gradient_score = min(avg_gradient / load_mean, 1.0)
        max_gradient_score = min(max_gradient / load_mean, 1.0)
        
        # Volatilitäts-Score (höher = mehr Volatilität = mehr Nutzen)
        volatility_score = min(cv * 2, 1.0)
        
        # Kombinierter Score
        # Hohe Gewichtung auf Gradienten (schnelle Änderungen)
        score = (
            volatility_score * 0.3 +
            gradient_score * 0.4 +
            max_gradient_score * 0.3
        )
        
        self.logger.info(f"Load Balancing evaluation: cv={cv:.2f}, "
                        f"avg_grad={avg_gradient:.1f}, score={score:.3f}")
        
        return min(score, 1.0)
    
    def optimize(self,
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any],
                 constraints: Optional[Dict[str, Any]] = None) -> StrategyResult:
        """
        Berechnet Load Balancing Fahrplan
        
        Algorithmus:
        1. Berechne gleitenden Durchschnitt der Last (Target)
        2. BESS kompensiert Differenz zur geglätteten Last
        3. Glättet sowohl positive als auch negative Spitzen
        """
        
        if not self.validate_forecast_data(forecast_data):
            return self._create_empty_result()
        
        load_forecast = forecast_data.get('load', [])
        pv_forecast = forecast_data.get('pv', [])
        current_soc = current_state.get('soc', 50.0)
        
        # Standard Constraints
        default_constraints = {
            'power_discharge_max_kw': 100.0,
            'power_charge_max_kw': 100.0,
            'soc_min_percent': 10.0,
            'soc_max_percent': 90.0,
            'energy_capacity_kwh': 200.0
        }
        constr = {**default_constraints, **(constraints or {})}
        
        # Extrahiere Werte
        timestamps = [l[0] for l in load_forecast]
        load_values = np.array([l[1] for l in load_forecast])
        
        # PV synchronisieren
        pv_values = np.zeros(len(load_values))
        if pv_forecast and len(pv_forecast) == len(load_forecast):
            pv_values = np.array([p[1] for p in pv_forecast])
        
        # Netto-Last (Load - PV)
        net_load = load_values - pv_values
        
        # Berechne geglättete Ziellast (gleitender Durchschnitt)
        target_load = self._moving_average(net_load, window=self.smoothing_window)
        
        # BESS-Leistung = Differenz zwischen tatsächlicher und Ziel-Last
        # Positiv = Entladen (Last ist höher als Ziel)
        # Negativ = Laden (Last ist niedriger als Ziel)
        bess_power_raw = net_load - target_load
        
        # Erstelle Fahrplan mit Constraints
        schedule = []
        soc_schedule = []
        soc_current = current_soc
        
        energy_charged = 0.0
        energy_discharged = 0.0
        load_variance_before = np.var(net_load)
        
        balanced_load = []
        
        for i, (ts, p_raw) in enumerate(zip(timestamps, bess_power_raw)):
            # Limitiere auf max Power
            p_bess = np.clip(p_raw, 
                            -constr['power_charge_max_kw'], 
                            constr['power_discharge_max_kw'])
            
            # Prüfe SoC-Grenzen
            if p_bess < 0:  # Laden
                # Prüfe ob noch Platz zum Laden
                if soc_current >= constr['soc_max_percent']:
                    p_bess = 0
                else:
                    # Limitiere um nicht über Max-SoC zu kommen
                    available_capacity = (constr['soc_max_percent'] - soc_current) / 100.0 * constr['energy_capacity_kwh']
                    max_charge_power = available_capacity  # kW (1h Annahme)
                    p_bess = max(p_bess, -max_charge_power)
            
            elif p_bess > 0:  # Entladen
                # Prüfe ob noch genug Energie
                if soc_current <= constr['soc_min_percent']:
                    p_bess = 0
                else:
                    # Limitiere um nicht unter Min-SoC zu kommen
                    available_energy = (soc_current - constr['soc_min_percent']) / 100.0 * constr['energy_capacity_kwh']
                    max_discharge_power = available_energy  # kW (1h Annahme)
                    p_bess = min(p_bess, max_discharge_power)
            
            # Update SoC (vereinfacht, 1h Zeitschritt)
            if p_bess < 0:  # Laden
                energy_charged += abs(p_bess)
                soc_current += (abs(p_bess) / constr['energy_capacity_kwh']) * 100.0
            elif p_bess > 0:  # Entladen
                energy_discharged += p_bess
                soc_current -= (p_bess / constr['energy_capacity_kwh']) * 100.0
            
            # Clamp SoC
            soc_current = np.clip(soc_current, 
                                 constr['soc_min_percent'], 
                                 constr['soc_max_percent'])
            
            # Resultierende Netzlast nach Balancing
            balanced = net_load[i] - p_bess
            balanced_load.append(balanced)
            
            schedule.append((ts, float(p_bess)))
            soc_schedule.append((ts, float(soc_current)))
        
        # Berechne Verbesserung
        balanced_load = np.array(balanced_load)
        load_variance_after = np.var(balanced_load)
        
        variance_reduction = ((load_variance_before - load_variance_after) / 
                             load_variance_before * 100) if load_variance_before > 0 else 0
        
        # Schätze Einsparungen (reduzierte Netzgebühren durch geglättete Last)
        estimated_savings = variance_reduction * 0.5  # EUR/Tag (heuristisch)
        
        result = StrategyResult(
            schedule=schedule,
            expected_revenue=0.0,
            expected_cost=0.0,
            expected_profit=estimated_savings,
            strategy_name=self.name,
            confidence_score=0.75,
            metadata={
                'soc_schedule': soc_schedule,
                'energy_charged_kwh': float(energy_charged),
                'energy_discharged_kwh': float(energy_discharged),
                'cycles': float(energy_discharged / (constr['energy_capacity_kwh'] * 2)),
                'load_variance_before': float(load_variance_before),
                'load_variance_after': float(load_variance_after),
                'variance_reduction_percent': float(variance_reduction),
                'estimated_savings_eur': float(estimated_savings),
                'smoothing_window': self.smoothing_window
            }
        )
        
        self.logger.info(f"Load Balancing: variance reduction={variance_reduction:.1f}%, "
                        f"savings={estimated_savings:.2f} EUR")
        
        return result
    
    def _moving_average(self, data: np.ndarray, window: int) -> np.ndarray:
        """Berechnet gleitenden Durchschnitt"""
        
        if len(data) < window:
            return data
        
        # Padding am Anfang und Ende
        padded = np.pad(data, (window//2, window//2), mode='edge')
        
        # Gleitender Durchschnitt
        cumsum = np.cumsum(np.insert(padded, 0, 0))
        result = (cumsum[window:] - cumsum[:-window]) / window
        
        # Trimme auf Original-Länge
        return result[:len(data)]
    
    def _create_empty_result(self) -> StrategyResult:
        return StrategyResult(
            schedule=[],
            strategy_name=self.name,
            confidence_score=0.0
        )
    
    def get_required_forecast_keys(self) -> List[str]:
        return ['load']


