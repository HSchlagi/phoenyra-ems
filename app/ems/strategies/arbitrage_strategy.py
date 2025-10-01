"""
Phoenyra EMS - Arbitrage Strategy
Kaufe Strom bei niedrigen Preisen, verkaufe bei hohen Preisen
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np

from .base_strategy import BaseStrategy, StrategyResult
from ..optimizers.lp_optimizer import LinearProgrammingOptimizer
import logging

logger = logging.getLogger(__name__)


class ArbitrageStrategy(BaseStrategy):
    """
    Arbitrage-Strategie: Nutzt Preisunterschiede am Strommarkt
    
    - Lädt die Batterie bei niedrigen Preisen
    - Entlädt die Batterie bei hohen Preisen
    - Maximiert den Gewinn durch optimale Planung
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(name="Arbitrage", config=config)
        self.optimizer = LinearProgrammingOptimizer(config)
        
        # Strategie-spezifische Parameter
        self.min_price_spread = config.get('min_price_spread', 20.0) if config else 20.0  # EUR/MWh
        self.min_profit_threshold = config.get('min_profit_threshold', 5.0) if config else 5.0  # EUR
        
    def evaluate(self, 
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any]) -> float:
        """
        Bewertet ob Arbitrage sinnvoll ist basierend auf Preisvolatilität
        
        Hoher Score wenn:
        - Große Preisunterschiede vorhanden
        - Genug Zeit für Lade-/Entladezyklen
        """
        
        if not self.validate_forecast_data(forecast_data):
            return 0.0
        
        prices = forecast_data.get('prices', [])
        
        if len(prices) < 4:  # Mindestens 4 Stunden für sinnvolle Arbitrage
            return 0.1
        
        # Extrahiere Preiswerte
        price_values = [p[1] for p in prices]
        
        # Berechne Preisvolatilität
        price_min = min(price_values)
        price_max = max(price_values)
        price_spread = price_max - price_min
        
        # Normalisiere Spread (0-100 EUR/MWh -> 0-1)
        spread_score = min(price_spread / 100.0, 1.0)
        
        # Höhere Bewertung wenn Spread über Mindest-Schwelle
        if price_spread < self.min_price_spread:
            spread_score *= 0.5
        
        # Berücksichtige auch Standardabweichung (Volatilität)
        price_std = np.std(price_values)
        volatility_score = min(price_std / 30.0, 1.0)
        
        # Kombinierter Score
        score = (spread_score * 0.7 + volatility_score * 0.3)
        
        self.logger.info(f"Arbitrage evaluation: spread={price_spread:.1f} EUR/MWh, score={score:.3f}")
        
        return score
    
    def optimize(self,
                 current_state: Dict[str, Any],
                 forecast_data: Dict[str, Any],
                 constraints: Optional[Dict[str, Any]] = None) -> StrategyResult:
        """
        Berechnet optimalen Arbitrage-Fahrplan
        """
        
        if not self.validate_forecast_data(forecast_data):
            return self._create_empty_result()
        
        prices = forecast_data.get('prices', [])
        current_soc = current_state.get('soc', 50.0)
        
        # Optimiere mit Linear Programming
        opt_result = self.optimizer.optimize_arbitrage(
            prices=prices,
            current_soc=current_soc,
            constraints=constraints
        )
        
        # Konvertiere zu StrategyResult
        result = StrategyResult(
            schedule=opt_result['schedule'],
            expected_revenue=opt_result['expected_revenue'],
            expected_cost=opt_result['expected_cost'],
            expected_profit=opt_result['expected_profit'],
            strategy_name=self.name,
            confidence_score=self._calculate_confidence(opt_result),
            metadata={
                'soc_schedule': opt_result['soc_schedule'],
                'energy_charged_kwh': opt_result['energy_charged_kwh'],
                'energy_discharged_kwh': opt_result['energy_discharged_kwh'],
                'cycles': opt_result['cycles'],
                'optimization_status': opt_result['optimization_status'],
                'solver': opt_result['solver'],
                'price_spread': self._calculate_price_spread(prices)
            }
        )
        
        self.logger.info(f"Arbitrage optimization: profit={result.expected_profit:.2f} EUR, "
                        f"cycles={result.metadata['cycles']:.3f}")
        
        return result
    
    def _calculate_confidence(self, opt_result: Dict[str, Any]) -> float:
        """
        Berechnet Konfidenz-Score basierend auf Optimierungsergebnis
        """
        
        # Basis-Konfidenz
        if opt_result['solver'] == 'cvxpy' and opt_result['optimization_status'] == 'optimal':
            base_confidence = 1.0
        elif opt_result['solver'] == 'cvxpy':
            base_confidence = 0.85
        else:
            base_confidence = 0.7  # Heuristik
        
        # Reduziere Konfidenz wenn Gewinn gering
        if opt_result['expected_profit'] < self.min_profit_threshold:
            base_confidence *= 0.6
        
        return base_confidence
    
    def _calculate_price_spread(self, prices: List[tuple]) -> float:
        """Berechnet Preisspanne"""
        price_values = [p[1] for p in prices]
        return max(price_values) - min(price_values)
    
    def _create_empty_result(self) -> StrategyResult:
        """Erstellt leeres Ergebnis bei Fehler"""
        return StrategyResult(
            schedule=[],
            strategy_name=self.name,
            confidence_score=0.0
        )
    
    def get_required_forecast_keys(self) -> List[str]:
        """Arbitrage benötigt nur Preise"""
        return ['prices']



