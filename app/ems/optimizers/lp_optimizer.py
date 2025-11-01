"""
Phoenyra EMS - Linear Programming Optimizer
Optimiert Batterie-Fahrpläne mit linearer Programmierung (CVXPY)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import logging

try:
    import cvxpy as cp
    CVXPY_AVAILABLE = True
except ImportError:
    CVXPY_AVAILABLE = False
    logging.warning("CVXPY not available, falling back to simple optimization")

logger = logging.getLogger(__name__)


class LinearProgrammingOptimizer:
    """
    Linear Programming Optimierer für BESS-Fahrplanung
    
    Optimiert den Batterie-Fahrplan über einen Zeithorizont unter
    Berücksichtigung von Preisen, Prognosen und technischen Constraints.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Standard-Constraints (können überschrieben werden)
        self.default_constraints = {
            'power_charge_max_kw': 100.0,
            'power_discharge_max_kw': 100.0,
            'energy_capacity_kwh': 200.0,
            'soc_min_percent': 10.0,
            'soc_max_percent': 90.0,
            'efficiency_charge': 0.95,
            'efficiency_discharge': 0.95,
            'timestep_hours': 1.0
        }
        
    def optimize_arbitrage(self,
                          prices: List[Tuple[datetime, float]],
                          current_soc: float,
                          constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Optimiert Batterie-Fahrplan für Arbitrage (kaufe billig, verkaufe teuer)
        
        Args:
            prices: Liste von (timestamp, price_per_mwh) Tupeln
            current_soc: Aktueller SoC in Prozent (0-100)
            constraints: Technische Constraints
            
        Returns:
            Dictionary mit Optimierungsergebnis
        """
        
        # Merge constraints
        constr = {**self.default_constraints, **(constraints or {})}
        
        if not CVXPY_AVAILABLE:
            return self._fallback_arbitrage(prices, current_soc, constr)
        
        try:
            return self._cvxpy_arbitrage(prices, current_soc, constr)
        except Exception as e:
            logger.error(f"CVXPY optimization failed: {e}, using fallback")
            return self._fallback_arbitrage(prices, current_soc, constr)
    
    def _cvxpy_arbitrage(self,
                        prices: List[Tuple[datetime, float]],
                        current_soc: float,
                        constr: Dict[str, Any]) -> Dict[str, Any]:
        """Optimierung mit CVXPY (optimal)"""
        
        n_steps = len(prices)
        
        # Prüfe ob Preisdaten vorhanden
        if n_steps == 0:
            logger.warning("No price data available for CVXPY optimization")
            return self._fallback_arbitrage(prices, current_soc, constr)
        
        timestamps = [p[0] for p in prices]
        price_values = np.array([p[1] for p in prices])  # EUR/MWh
        
        # Konvertiere Preise zu EUR/kWh
        prices_kwh = price_values / 1000.0
        
        # Extrahiere Constraints
        P_charge_max = constr['power_charge_max_kw']
        P_discharge_max = constr['power_discharge_max_kw']
        E_capacity = constr['energy_capacity_kwh']
        soc_min = constr['soc_min_percent'] / 100.0
        soc_max = constr['soc_max_percent'] / 100.0
        eta_c = constr['efficiency_charge']
        eta_d = constr['efficiency_discharge']
        dt = constr['timestep_hours']
        
        # Initiale Energie (in kWh)
        E_init = (current_soc / 100.0) * E_capacity
        
        # Variablen
        P_charge = cp.Variable(n_steps, nonneg=True)    # Ladeleistung (kW)
        P_discharge = cp.Variable(n_steps, nonneg=True)  # Entladeleistung (kW)
        E = cp.Variable(n_steps + 1)                     # Energieinhalt (kWh)
        
        # Zielfunktion: Maximiere Gewinn
        # Gewinn = Einnahmen (Verkauf) - Ausgaben (Kauf)
        revenue = cp.sum(cp.multiply(P_discharge * dt, prices_kwh))
        cost = cp.sum(cp.multiply(P_charge * dt, prices_kwh))
        profit = revenue - cost
        
        objective = cp.Maximize(profit)
        
        # Constraints
        constraints = []
        
        # Initiale Energie
        constraints.append(E[0] == E_init)
        
        # Energiebilanz für jeden Zeitschritt
        for t in range(n_steps):
            constraints.append(
                E[t+1] == E[t] + (eta_c * P_charge[t] - P_discharge[t] / eta_d) * dt
            )
        
        # Leistungs-Limits
        constraints.append(P_charge <= P_charge_max)
        constraints.append(P_discharge <= P_discharge_max)
        
        # SoC-Limits
        constraints.append(E >= soc_min * E_capacity)
        constraints.append(E <= soc_max * E_capacity)
        
        # Problem lösen (CVXPY wählt automatisch den besten Solver)
        problem = cp.Problem(objective, constraints)
        result = problem.solve(verbose=False)
        
        if problem.status not in ["optimal", "optimal_inaccurate"]:
            logger.warning(f"Optimization status: {problem.status}, using fallback")
            return self._fallback_arbitrage([(timestamps[i], price_values[i]) for i in range(n_steps)], 
                                           current_soc, constr)
        
        # Extrahiere Ergebnisse
        p_charge = P_charge.value
        p_discharge = P_discharge.value
        energy = E.value
        
        # Berechne netto Leistung (positiv = entladen/verkaufen, negativ = laden/kaufen)
        p_net = p_discharge - p_charge
        
        # SoC über Zeit
        soc_schedule = (energy / E_capacity) * 100.0
        
        # Erstelle Schedule
        schedule = []
        for i in range(n_steps):
            schedule.append((timestamps[i], float(p_net[i])))
        
        # Berechne Metriken
        total_revenue = float(np.sum(p_discharge * dt * prices_kwh))
        total_cost = float(np.sum(p_charge * dt * prices_kwh))
        total_profit = total_revenue - total_cost
        
        # Energie-Statistiken
        energy_charged = float(np.sum(p_charge * dt))
        energy_discharged = float(np.sum(p_discharge * dt))
        
        return {
            'schedule': schedule,
            'soc_schedule': [(timestamps[i], float(soc_schedule[i])) for i in range(len(soc_schedule))],
            'expected_revenue': total_revenue,
            'expected_cost': total_cost,
            'expected_profit': total_profit,
            'energy_charged_kwh': energy_charged,
            'energy_discharged_kwh': energy_discharged,
            'cycles': energy_discharged / (E_capacity * 2),  # Vollzyklen
            'optimization_status': problem.status,
            'solver': 'cvxpy'
        }
    
    def _fallback_arbitrage(self,
                           prices: List[Tuple[datetime, float]],
                           current_soc: float,
                           constr: Dict[str, Any]) -> Dict[str, Any]:
        """
        Einfache Heuristik für Arbitrage (fallback wenn CVXPY nicht verfügbar)
        
        Regel: Lade bei niedrigen Preisen, entlade bei hohen Preisen
        """
        
        logger.info("Using fallback heuristic optimization")
        
        timestamps = [p[0] for p in prices]
        price_values = [p[1] for p in prices]
        
        # Prüfe ob Preisdaten vorhanden
        if len(price_values) == 0:
            logger.warning("No price data available for fallback optimization")
            return {
                'schedule': [],
                'soc_schedule': [],
                'expected_revenue': 0.0,
                'expected_cost': 0.0,
                'expected_profit': 0.0,
                'energy_charged_kwh': 0.0,
                'energy_discharged_kwh': 0.0,
                'cycles': 0.0,
                'optimization_status': 'no_data',
                'solver': 'fallback'
            }
        
        # Finde Preis-Quantile
        prices_sorted = sorted(price_values)
        n = len(prices_sorted)
        low_threshold = prices_sorted[n // 4] if n >= 4 else prices_sorted[0]  # 25% Quantil
        high_threshold = prices_sorted[3 * n // 4] if n >= 4 else prices_sorted[-1]  # 75% Quantil
        
        P_charge_max = constr['power_charge_max_kw']
        P_discharge_max = constr['power_discharge_max_kw']
        E_capacity = constr['energy_capacity_kwh']
        soc_min = constr['soc_min_percent']
        soc_max = constr['soc_max_percent']
        dt = constr['timestep_hours']
        eta_c = constr['efficiency_charge']
        eta_d = constr['efficiency_discharge']
        
        schedule = []
        soc_schedule = []
        current_soc_val = current_soc
        
        total_revenue = 0.0
        total_cost = 0.0
        energy_charged = 0.0
        energy_discharged = 0.0
        
        for ts, price in zip(timestamps, price_values):
            p_net = 0.0
            
            # Entscheide basierend auf Preis und SoC
            if price <= low_threshold and current_soc_val < soc_max:
                # Niedrige Preise -> Laden
                p_charge = min(P_charge_max, (soc_max - current_soc_val) / 100.0 * E_capacity / dt)
                p_net = -p_charge
                
                # Update SoC
                energy_added = p_charge * eta_c * dt
                current_soc_val += (energy_added / E_capacity) * 100.0
                
                # Kosten
                total_cost += (p_charge * dt) * (price / 1000.0)
                energy_charged += p_charge * dt
                
            elif price >= high_threshold and current_soc_val > soc_min:
                # Hohe Preise -> Entladen
                p_discharge = min(P_discharge_max, (current_soc_val - soc_min) / 100.0 * E_capacity / dt)
                p_net = p_discharge
                
                # Update SoC
                energy_removed = p_discharge / eta_d * dt
                current_soc_val -= (energy_removed / E_capacity) * 100.0
                
                # Erlöse
                total_revenue += (p_discharge * dt) * (price / 1000.0)
                energy_discharged += p_discharge * dt
            
            # Clamp SoC
            current_soc_val = max(soc_min, min(soc_max, current_soc_val))
            
            schedule.append((ts, p_net))
            soc_schedule.append((ts, current_soc_val))
        
        return {
            'schedule': schedule,
            'soc_schedule': soc_schedule,
            'expected_revenue': total_revenue,
            'expected_cost': total_cost,
            'expected_profit': total_revenue - total_cost,
            'energy_charged_kwh': energy_charged,
            'energy_discharged_kwh': energy_discharged,
            'cycles': energy_discharged / (E_capacity * 2),
            'optimization_status': 'heuristic',
            'solver': 'fallback'
        }
    
    def optimize_self_consumption(self,
                                  pv_forecast: List[Tuple[datetime, float]],
                                  load_forecast: List[Tuple[datetime, float]],
                                  prices: List[Tuple[datetime, float]],
                                  current_soc: float,
                                  constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Optimiert für maximalen Eigenverbrauch (mit PV-Anlage)
        
        Ziel: Maximiere PV-Eigenverbrauch, minimiere Netzbezug
        """
        
        # TODO: Implementierung in Phase 2
        logger.info("Self-consumption optimization not yet implemented, using arbitrage")
        return self.optimize_arbitrage(prices, current_soc, constraints)



