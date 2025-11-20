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
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, history_db=None, market_data_service=None):
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
        
        # AI Strategy Selector
        self.ai_selector = None
        self.history_db = history_db
        self.market_data_service = market_data_service
        
        ai_config = config.get('ai_selection', {})
        if ai_config.get('enabled', False):
            try:
                from .strategies.ai_strategy_selector import AIStrategySelector
                model_path = ai_config.get('model_path', 'data/ai_strategy_model.pkl')
                self.ai_selector = AIStrategySelector(model_path=model_path)
                logger.info("AI Strategy Selector initialized")
                
                # Trainiere mit historischen Daten falls verfügbar
                if self.history_db:
                    self._train_ai_selector()
            except Exception as e:
                logger.error(f"Failed to initialize AI Strategy Selector: {e}", exc_info=True)
                self.ai_selector = None
        
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
        
        # AI-basierte Auswahl falls aktiviert und trainiert
        if self.ai_selector and self.ai_selector.is_trained:
            try:
                # Hole Marktdaten
                market_data = {}
                if self.market_data_service:
                    market_data = self.market_data_service.get_market_data()
                    # Ergänze Forecast-Daten für Market Data
                    market_data['price_6h_avg'] = self.market_data_service.get_price_forecast_6h_avg(forecast_data)
                
                # Ergänze Forecast-Daten
                forecast_enhanced = forecast_data.copy()
                forecast_enhanced['pv_6h_avg'] = self._calculate_6h_avg(forecast_data.get('pv', []))
                forecast_enhanced['load_6h_avg'] = self._calculate_6h_avg(forecast_data.get('load', []))
                forecast_enhanced['price_6h_avg'] = market_data.get('price_6h_avg', 0.0)
                
                # State erweitern
                state_enhanced = current_state.copy()
                state_enhanced['current_strategy_score'] = scores.get(self.current_strategy_name, 0.0) if self.current_strategy_name else 0.0
                
                # AI-Auswahl
                ai_selected = self.ai_selector.select_strategy(
                    state_enhanced,
                    forecast_enhanced,
                    market_data,
                    scores
                )
                
                # Prüfe ob Strategiewechsel sinnvoll ist
                if self.current_strategy_name and self.current_strategy_name != ai_selected:
                    current_score = scores.get(self.current_strategy_name, 0.0)
                    ai_score = scores.get(ai_selected, 0.0)
                    
                    # Nur wechseln wenn signifikante Verbesserung
                    if ai_score - current_score < self.switch_threshold:
                        logger.info(f"AI suggested {ai_selected}, but keeping {self.current_strategy_name} "
                                   f"(score diff {ai_score - current_score:.3f} < threshold)")
                        return self.current_strategy_name
                
                logger.info(f"AI selected strategy: {ai_selected} (scores: {scores})")
                self.current_strategy_name = ai_selected
                return ai_selected
            except Exception as e:
                logger.error(f"Error in AI strategy selection: {e}", exc_info=True)
                # Fallback zu Score-basierter Auswahl
        
        # Fallback: Score-basierte Auswahl
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
    
    def _calculate_6h_avg(self, data_list: List[Any]) -> float:
        """Berechnet Durchschnitt der nächsten 6 Stunden"""
        if not data_list:
            return 0.0
        
        next_6h = data_list[:6] if len(data_list) >= 6 else data_list
        
        values = []
        for item in next_6h:
            if isinstance(item, dict):
                values.append(item.get('value', item.get('power', 0.0)))
            elif isinstance(item, (int, float)):
                values.append(float(item))
        
        if not values:
            return 0.0
        
        return sum(values) / len(values)
    
    def _train_ai_selector(self):
        """Trainiert AI-Selector mit historischen Daten"""
        if not self.ai_selector or not self.history_db:
            return
        
        try:
            # Hole historische Optimierungen (letzte 30 Tage)
            optimization_history = self.history_db.get_optimization_history(days=30)
            
            if len(optimization_history) < 100:
                logger.info(f"Insufficient optimization history for AI training: {len(optimization_history)} records")
                return
            
            # Hole State History für Kontext
            state_history = self.history_db.get_state_history(hours=24 * 30)
            
            # Erstelle Training-Daten
            training_data = []
            
            for opt in optimization_history:
                # Finde passenden State
                opt_timestamp = datetime.fromisoformat(opt['timestamp'].replace('Z', '+00:00'))
                
                # Finde nähesten State
                closest_state = None
                min_diff = float('inf')
                for state in state_history:
                    state_timestamp = datetime.fromisoformat(state['timestamp'].replace('Z', '+00:00'))
                    diff = abs((opt_timestamp - state_timestamp).total_seconds())
                    if diff < min_diff and diff < 3600:  # Max 1h Unterschied
                        min_diff = diff
                        closest_state = state
                
                if not closest_state:
                    continue
                
                # Erstelle Training-Record
                training_record = {
                    'state': {
                        'soc': closest_state.get('soc', 50.0),
                        'soh': 100.0,  # Annahme, falls nicht verfügbar
                        'temp_c': 25.0,  # Annahme
                        'p_bess': closest_state.get('p_bess', 0.0),
                        'p_pv': closest_state.get('p_pv', 0.0),
                        'p_load': closest_state.get('p_load', 0.0),
                        'p_grid': closest_state.get('p_grid', 0.0),
                        'current_strategy_score': opt.get('confidence', 0.0)
                    },
                    'forecast': {
                        'pv_6h_avg': closest_state.get('p_pv', 0.0),
                        'load_6h_avg': closest_state.get('p_load', 0.0),
                        'price_6h_avg': closest_state.get('price', 0.0)
                    },
                    'market': {
                        'current_price': closest_state.get('price', 0.0),
                        'price_trend': 0.0,  # Wird später berechnet
                        'price_volatility': 0.0
                    },
                    'best_strategy': opt.get('strategy_name', 'arbitrage'),
                    'actual_profit': opt.get('expected_profit', 0.0)
                }
                
                training_data.append(training_record)
            
            if len(training_data) >= 100:
                logger.info(f"Training AI Strategy Selector with {len(training_data)} records")
                self.ai_selector.train(training_data)
            else:
                logger.warning(f"Insufficient training data: {len(training_data)} records")
        except Exception as e:
            logger.error(f"Error training AI selector: {e}", exc_info=True)


