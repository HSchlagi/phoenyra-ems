"""
Phoenyra EMS - Self Consumption Strategy
Maximiert Eigenverbrauch von PV-Strom
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np

from .base_strategy import BaseStrategy, StrategyResult
import logging

logger = logging.getLogger(__name__)


class SelfConsumptionStrategy(BaseStrategy):
    """
    Eigenverbrauchs-Strategie: Maximiert PV-Eigenverbrauch
    
    - Lädt Batterie mit PV-Überschuss
    - Entlädt Batterie wenn PV < Last
    - Minimiert Netzbezug und Netzeinspeisung
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="Self Consumption", config=config)
        
        # Feed-in Tarif vs. Grid Tarif
        self.feedin_tariff = config.get('feedin_tariff', 0.08) if config else 0.08  # EUR/kWh
        self.grid_tariff = config.get('grid_tariff', 0.30) if config else 0.30  # EUR/kWh
        
    def evaluate(self, 
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any]) -> float:
        """
        Bewertet ob Self-Consumption sinnvoll ist
        
        Hoher Score wenn:
        - PV-Erzeugung vorhanden
        - Große Spreizung zwischen Bezug und Einspeisung
        """
        
        if not self.validate_forecast_data(forecast_data):
            return 0.0
        
        pv_forecast = forecast_data.get('pv', [])
        load_forecast = forecast_data.get('load', [])
        
        if len(pv_forecast) < 2 or len(load_forecast) < 2:
            return 0.0
        
        # Extrahiere Werte
        pv_values = [p[1] for p in pv_forecast]
        load_values = [l[1] for l in load_forecast]
        
        # Durchschnittliche PV-Erzeugung
        avg_pv = np.mean(pv_values)
        max_pv = max(pv_values)
        
        if max_pv < 1.0:  # Keine nennenswerte PV-Erzeugung
            return 0.0
        
        # Berechne Überschuss/Defizit
        n = min(len(pv_values), len(load_values))
        surplus = [max(0, pv_values[i] - load_values[i]) for i in range(n)]
        deficit = [max(0, load_values[i] - pv_values[i]) for i in range(n)]
        
        avg_surplus = np.mean(surplus)
        avg_deficit = np.mean(deficit)
        
        # Score basierend auf PV-Erzeugung und Balance
        pv_score = min(avg_pv / 10.0, 1.0)  # Normalisiert auf ~10kW
        balance_score = min((avg_surplus + avg_deficit) / 10.0, 1.0)
        
        score = pv_score * 0.6 + balance_score * 0.4
        
        self.logger.info(f"Self-Consumption evaluation: avg_pv={avg_pv:.1f}kW, score={score:.3f}")
        
        return score
    
    def optimize(self,
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any],
                 constraints: Optional[Dict[str, Any]] = None) -> StrategyResult:
        """
        Berechnet Self-Consumption Fahrplan
        
        Einfache Regel:
        - PV > Last: Lade Batterie mit Überschuss
        - PV < Last: Entlade Batterie für Last
        """
        
        if not self.validate_forecast_data(forecast_data):
            return self._create_empty_result()
        
        pv_forecast = forecast_data.get('pv', [])
        load_forecast = forecast_data.get('load', [])
        current_soc = current_state.get('soc', 50.0)
        
        # Standard Constraints
        default_constraints = {
            'power_discharge_max_kw': 100.0,
            'power_charge_max_kw': 100.0,
            'soc_min_percent': 10.0,
            'soc_max_percent': 90.0,
            'efficiency_charge': 0.95,
            'efficiency_discharge': 0.95
        }
        constr = {**default_constraints, **(constraints or {})}
        
        # Synchronisiere Zeitstempel
        n = min(len(pv_forecast), len(load_forecast))
        
        schedule = []
        soc_current = current_soc
        
        grid_import = 0.0
        grid_export = 0.0
        battery_charge = 0.0
        battery_discharge = 0.0
        
        for i in range(n):
            ts_pv, pv = pv_forecast[i]
            ts_load, load = load_forecast[i]
            
            # Verwende PV-Zeitstempel (sollten identisch sein)
            ts = ts_pv
            
            # Netto-Leistung (PV - Last)
            net = pv - load
            
            p_bess = 0.0
            
            if net > 0 and soc_current < constr['soc_max_percent']:
                # Überschuss: Lade Batterie
                p_charge = min(net, constr['power_charge_max_kw'])
                p_bess = -p_charge  # Negativ = Laden
                
                battery_charge += p_charge
                soc_current += 1.0  # Vereinfacht
                
            elif net < 0 and soc_current > constr['soc_min_percent']:
                # Defizit: Entlade Batterie
                p_discharge = min(abs(net), constr['power_discharge_max_kw'])
                p_bess = p_discharge  # Positiv = Entladen
                
                battery_discharge += p_discharge
                soc_current -= 1.0  # Vereinfacht
            
            # Clamp SoC
            soc_current = max(constr['soc_min_percent'], 
                            min(constr['soc_max_percent'], soc_current))
            
            # Berechne verbleibenden Netzbezug/-einspeisung
            remaining = net + p_bess  # Nach Batterie
            if remaining > 0:
                grid_export += remaining
            else:
                grid_import += abs(remaining)
            
            schedule.append((ts, p_bess))
        
        # Berechne Einsparungen
        # Ohne Batterie: Netzbezug und Einspeisung direkt
        total_pv = sum(p[1] for p in pv_forecast[:n])
        total_load = sum(l[1] for l in load_forecast[:n])
        
        without_battery_import = max(0, total_load - total_pv)
        without_battery_export = max(0, total_pv - total_load)
        
        cost_without = (without_battery_import * self.grid_tariff - 
                       without_battery_export * self.feedin_tariff)
        
        cost_with = (grid_import * self.grid_tariff - 
                    grid_export * self.feedin_tariff)
        
        savings = cost_without - cost_with
        
        result = StrategyResult(
            schedule=schedule,
            expected_revenue=0.0,
            expected_cost=cost_with,
            expected_profit=savings,
            strategy_name=self.name,
            confidence_score=0.75,
            metadata={
                'total_pv_kwh': float(total_pv),
                'total_load_kwh': float(total_load),
                'grid_import_kwh': float(grid_import),
                'grid_export_kwh': float(grid_export),
                'battery_charge_kwh': float(battery_charge),
                'battery_discharge_kwh': float(battery_discharge),
                'savings_eur': float(savings),
                'self_consumption_rate': float((total_pv - grid_export) / total_pv * 100) if total_pv > 0 else 0.0
            }
        )
        
        self.logger.info(f"Self-Consumption: savings={savings:.2f} EUR, "
                        f"self_consumption={result.metadata['self_consumption_rate']:.1f}%")
        
        return result
    
    def _create_empty_result(self) -> StrategyResult:
        return StrategyResult(
            schedule=[],
            strategy_name=self.name,
            confidence_score=0.0
        )
    
    def get_required_forecast_keys(self) -> List[str]:
        return ['pv', 'load']



