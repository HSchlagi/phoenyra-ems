"""
Phoenyra EMS - Strategy Manager
Verwaltet und koordiniert alle EMS-Strategien
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .strategies import (
    BaseStrategy,
    ArbitrageStrategy,
    PeakShavingStrategy,
    SelfConsumptionStrategy,
    LoadBalancingStrategy
)

logger = logging.getLogger(__name__)


class StrategyManager:
    """
    Verwaltet alle verfügbaren Strategien und wählt die optimale aus
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialisiere alle verfügbaren Strategien
        self.strategies: Dict[str, BaseStrategy] = {
            'arbitrage': ArbitrageStrategy(config),
            'peak_shaving': PeakShavingStrategy(config),
            'self_consumption': SelfConsumptionStrategy(config),
            'load_balancing': LoadBalancingStrategy(config)
        }
        
        # Strategie-Auswahl-Modus
        self.selection_mode = config.get('selection_mode', 'auto')  # 'auto' oder 'manual'
        self.manual_strategy = config.get('manual_strategy', 'arbitrage')
        
        # Schwellwert für Strategiewechsel
        self.switch_threshold = config.get('switch_threshold', 0.15)  # Min. Score-Differenz
        
        self.current_strategy_name: Optional[str] = None
        
        logger.info(f"StrategyManager initialized with {len(self.strategies)} strategies")
    
    def select_strategy(self,
                       current_state: Dict[str, Any],
                       forecast_data: Dict[str, Any]) -> str:
        """
        Wählt die optimale Strategie basierend auf aktuellen Bedingungen
        
        Args:
            current_state: Aktueller Anlagenzustand
            forecast_data: Prognosedaten
            
        Returns:
            Name der ausgewählten Strategie
        """
        
        if self.selection_mode == 'manual':
            logger.info(f"Manual strategy selection: {self.manual_strategy}")
            self.current_strategy_name = self.manual_strategy
            return self.manual_strategy
        
        # Evaluiere alle Strategien
        scores = self.evaluate_all_strategies(current_state, forecast_data)
        
        if not scores:
            logger.warning("No strategies could be evaluated, using arbitrage as default")
            self.current_strategy_name = 'arbitrage'
            return 'arbitrage'
        
        # Sortiere nach Score
        sorted_strategies = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_strategy, best_score = sorted_strategies[0]
        
        # Prüfe ob Strategiewechsel sinnvoll ist
        if self.current_strategy_name and self.current_strategy_name != best_strategy:
            current_score = scores.get(self.current_strategy_name, 0.0)
            
            # Nur wechseln wenn signifikante Verbesserung
            if best_score - current_score < self.switch_threshold:
                logger.info(f"Keeping current strategy {self.current_strategy_name} "
                           f"(score diff {best_score - current_score:.3f} < threshold)")
                return self.current_strategy_name
        
        logger.info(f"Selected strategy: {best_strategy} (score: {best_score:.3f})")
        logger.debug(f"All scores: {scores}")
        
        self.current_strategy_name = best_strategy
        return best_strategy
    
    def evaluate_all_strategies(self,
                                current_state: Dict[str, Any],
                                forecast_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Evaluiert alle Strategien und gibt Scores zurück
        
        Returns:
            Dictionary {strategy_name: score}
        """
        
        scores = {}
        
        for name, strategy in self.strategies.items():
            try:
                score = strategy.evaluate(current_state, forecast_data)
                scores[name] = score
                logger.debug(f"Strategy {name}: score={score:.3f}")
            except Exception as e:
                logger.error(f"Error evaluating strategy {name}: {e}")
                scores[name] = 0.0
        
        return scores
    
    def optimize_with_strategy(self,
                              strategy_name: str,
                              current_state: Dict[str, Any],
                              forecast_data: Dict[str, Any],
                              constraints: Optional[Dict[str, Any]] = None):
        """
        Führt Optimierung mit spezifischer Strategie durch
        
        Args:
            strategy_name: Name der Strategie
            current_state: Aktueller Zustand
            forecast_data: Prognosedaten
            constraints: Technische Constraints
            
        Returns:
            StrategyResult
        """
        
        strategy = self.strategies.get(strategy_name)
        
        if not strategy:
            logger.error(f"Unknown strategy: {strategy_name}")
            # Fallback zu Arbitrage
            strategy = self.strategies['arbitrage']
            strategy_name = 'arbitrage'
        
        logger.info(f"Optimizing with strategy: {strategy_name}")
        
        try:
            result = strategy.optimize(current_state, forecast_data, constraints)
            return result
        except Exception as e:
            logger.error(f"Error optimizing with strategy {strategy_name}: {e}", exc_info=True)
            # Return empty result
            from .strategies.base_strategy import StrategyResult
            return StrategyResult(
                schedule=[],
                strategy_name=strategy_name,
                confidence_score=0.0
            )
    
    def optimize_all_strategies(self,
                               current_state: Dict[str, Any],
                               forecast_data: Dict[str, Any],
                               constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Optimiert mit allen Strategien (für Vergleich)
        
        Returns:
            Dictionary {strategy_name: StrategyResult}
        """
        
        results = {}
        
        for name in self.strategies.keys():
            try:
                result = self.optimize_with_strategy(name, current_state, forecast_data, constraints)
                results[name] = result
            except Exception as e:
                logger.error(f"Error optimizing with {name}: {e}")
        
        return results
    
    def get_available_strategies(self) -> List[str]:
        """Gibt Liste aller verfügbaren Strategien zurück"""
        return list(self.strategies.keys())
    
    def get_current_strategy(self) -> Optional[str]:
        """Gibt aktuell aktive Strategie zurück"""
        return self.current_strategy_name
    
    def set_manual_strategy(self, strategy_name: str) -> bool:
        """
        Setzt manuelle Strategie
        
        Returns:
            True wenn erfolgreich, False wenn Strategie unbekannt
        """
        if strategy_name not in self.strategies:
            logger.error(f"Unknown strategy: {strategy_name}")
            return False
        
        self.selection_mode = 'manual'
        self.manual_strategy = strategy_name
        self.current_strategy_name = strategy_name
        
        logger.info(f"Manual strategy set to: {strategy_name}")
        return True
    
    def set_auto_mode(self):
        """Aktiviert automatische Strategiewahl"""
        self.selection_mode = 'auto'
        logger.info("Auto strategy selection enabled")


