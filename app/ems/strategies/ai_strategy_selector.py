"""
Phoenyra EMS - AI Strategy Selector
KI-basierte Strategie-Auswahl basierend auf ML-Modell
"""

import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
import pickle
from pathlib import Path

try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logging.warning("scikit-learn not available. AI Strategy Selection will be disabled.")

logger = logging.getLogger(__name__)


class AIStrategySelector:
    """
    KI-basierte Strategie-Auswahl basierend auf:
    - Historischen Performance-Daten
    - Marktbedingungen (Preise, Volatilität)
    - Wetterprognosen
    - Lastprofilen
    - Systemzustand (SoC, BESS-Status)
    """
    
    def __init__(self, model_path: Optional[str] = None):
        if not SKLEARN_AVAILABLE:
            self.model = None
            self.is_trained = False
            logger.warning("scikit-learn not available. AI Strategy Selection disabled.")
            return
        
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_history: List[np.ndarray] = []
        self.decision_history: List[Dict[str, Any]] = []
        self.strategy_names: List[str] = []
        self.model_path = Path(model_path) if model_path else None
        
        # Lade gespeichertes Modell falls vorhanden
        if self.model_path and self.model_path.exists():
            self._load_model()
    
    def extract_features(self, 
                        state: Dict[str, Any],
                        forecast: Dict[str, Any],
                        market_data: Dict[str, Any]) -> np.ndarray:
        """
        Extrahiert Features für ML-Modell:
        - SoC, SoH, Temperatur
        - Preis-Trend (steigend/fallend)
        - Preis-Volatilität
        - PV-Prognose (nächste 6h)
        - Last-Prognose (nächste 6h)
        - Tageszeit, Wochentag
        - Aktuelle Strategie-Performance
        """
        now = datetime.now(timezone.utc)
        
        # Systemzustand (normalisiert)
        soc = state.get('soc', 50.0) / 100.0
        soh = state.get('soh', 100.0) / 100.0
        temp_c = state.get('temp_c', 25.0) / 50.0  # Normalisiert auf 0-1 (0-50°C)
        
        # Marktdaten
        price_trend = market_data.get('price_trend', 0.0)  # -1 bis +1
        price_volatility = market_data.get('price_volatility', 0.0)  # 0-1
        current_price = market_data.get('current_price', 0.0) / 100.0  # Normalisiert
        
        # Prognosen (nächste 6h Durchschnitt)
        pv_6h_avg = forecast.get('pv_6h_avg', 0.0) / 100.0  # Normalisiert
        load_6h_avg = forecast.get('load_6h_avg', 0.0) / 100.0  # Normalisiert
        price_6h_avg = forecast.get('price_6h_avg', 0.0) / 100.0  # Normalisiert
        
        # Zeit-Features
        hour = now.hour / 24.0  # 0-1
        weekday = now.weekday() / 7.0  # 0-1
        is_weekend = 1.0 if now.weekday() >= 5 else 0.0
        
        # Aktuelle Strategie-Performance
        current_strategy_score = state.get('current_strategy_score', 0.0)
        
        # Power-Features
        p_bess = state.get('p_bess', 0.0) / 100.0  # Normalisiert (Annahme: max 100kW)
        p_pv = state.get('p_pv', 0.0) / 100.0
        p_load = state.get('p_load', 0.0) / 100.0
        p_grid = state.get('p_grid', 0.0) / 100.0
        
        features = np.array([
            soc,
            soh,
            temp_c,
            price_trend,
            price_volatility,
            current_price,
            pv_6h_avg,
            load_6h_avg,
            price_6h_avg,
            hour,
            weekday,
            is_weekend,
            current_strategy_score,
            p_bess,
            p_pv,
            p_load,
            p_grid
        ])
        
        return features.reshape(1, -1)
    
    def select_strategy(self,
                       state: Dict[str, Any],
                       forecast: Dict[str, Any],
                       market_data: Dict[str, Any],
                       strategy_scores: Dict[str, float]) -> str:
        """
        Wählt beste Strategie basierend auf ML-Modell
        
        Args:
            state: Aktueller Systemzustand
            forecast: Prognosedaten
            market_data: Marktdaten (Preise, Trends)
            strategy_scores: Scores aller verfügbaren Strategien
            
        Returns:
            Name der ausgewählten Strategie
        """
        if not self.is_trained or not self.model:
            # Fallback: Beste Score-Strategie
            if strategy_scores:
                best_strategy = max(strategy_scores, key=strategy_scores.get)
                logger.debug(f"AI not trained, using best score strategy: {best_strategy}")
                return best_strategy
            return 'arbitrage'  # Default
        
        if not strategy_scores:
            logger.warning("No strategy scores provided, using arbitrage")
            return 'arbitrage'
        
        # Extrahiere Features
        features = self.extract_features(state, forecast, market_data)
        
        # Skaliere Features
        try:
            features_scaled = self.scaler.transform(features)
        except:
            # Falls Scaler noch nicht trainiert, verwende unskalierte Features
            features_scaled = features
        
        # Vorhersage
        try:
            predicted_strategy_idx = self.model.predict(features_scaled)[0]
            strategy_names = list(strategy_scores.keys())
            
            if predicted_strategy_idx < len(strategy_names):
                predicted_strategy = strategy_names[predicted_strategy_idx]
                
                # Log Decision
                self.decision_history.append({
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'predicted_strategy': predicted_strategy,
                    'strategy_scores': strategy_scores,
                    'features': features[0].tolist()
                })
                
                logger.debug(f"AI selected strategy: {predicted_strategy} (idx: {predicted_strategy_idx})")
                return predicted_strategy
            else:
                logger.warning(f"Predicted index {predicted_strategy_idx} out of range, using best score")
                return max(strategy_scores, key=strategy_scores.get)
        except Exception as e:
            logger.error(f"Error in AI strategy prediction: {e}", exc_info=True)
            # Fallback zu best score
            return max(strategy_scores, key=strategy_scores.get)
    
    def train(self, historical_data: List[Dict[str, Any]]):
        """
        Trainiert Modell mit historischen Daten:
        - Features: Systemzustand, Marktdaten, Prognosen
        - Labels: Beste Strategie (basierend auf tatsächlichem Gewinn)
        
        Args:
            historical_data: Liste von Dicts mit:
                - 'state': Systemzustand
                - 'forecast': Prognosedaten
                - 'market': Marktdaten
                - 'best_strategy': Name der besten Strategie
                - 'actual_profit': Tatsächlicher Gewinn (optional)
        """
        if not SKLEARN_AVAILABLE:
            logger.error("Cannot train: scikit-learn not available")
            return
        
        if not historical_data:
            logger.warning("No historical data provided for training")
            return
        
        X = []
        y = []
        strategy_names_set = set()
        
        for record in historical_data:
            try:
                features = self.extract_features(
                    record.get('state', {}),
                    record.get('forecast', {}),
                    record.get('market', {})
                )
                X.append(features[0])
                
                best_strategy = record.get('best_strategy')
                if best_strategy:
                    strategy_names_set.add(best_strategy)
                    y.append(best_strategy)
                else:
                    # Skip records without best strategy
                    continue
            except Exception as e:
                logger.error(f"Error processing training record: {e}")
                continue
        
        if len(X) < 100:  # Mindestens 100 Datenpunkte
            logger.warning(f"Insufficient training data: {len(X)} samples (need at least 100)")
            return
        
        # Erstelle Strategie-Index-Mapping
        self.strategy_names = sorted(list(strategy_names_set))
        strategy_to_idx = {s: i for i, s in enumerate(self.strategy_names)}
        
        # Konvertiere Labels zu Indices
        y_indices = [strategy_to_idx.get(label, 0) for label in y]
        
        # Skaliere Features
        X_scaled = self.scaler.fit_transform(X)
        
        # Prüfe ob stratify möglich ist (mindestens 2 Samples pro Klasse)
        from collections import Counter
        class_counts = Counter(y_indices)
        min_class_count = min(class_counts.values()) if class_counts else 0
        use_stratify = min_class_count >= 2
        
        # Train-Test Split
        if use_stratify:
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y_indices, test_size=0.2, random_state=42, stratify=y_indices
            )
        else:
            logger.warning(f"Not enough samples per class for stratified split (min: {min_class_count}), using random split")
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y_indices, test_size=0.2, random_state=42
            )
        
        # Trainiere Modell
        try:
            self.model.fit(X_train, y_train)
            
            # Evaluierung
            train_score = self.model.score(X_train, y_train)
            test_score = self.model.score(X_test, y_test)
            
            self.is_trained = True
            
            logger.info(f"AI Strategy Selector trained on {len(X)} samples")
            logger.info(f"Train accuracy: {train_score:.3f}, Test accuracy: {test_score:.3f}")
            logger.info(f"Strategy classes: {self.strategy_names}")
            
            # Speichere Modell
            if self.model_path:
                self._save_model()
        except Exception as e:
            logger.error(f"Error training AI model: {e}", exc_info=True)
            self.is_trained = False
    
    def _save_model(self):
        """Speichert trainiertes Modell"""
        if not self.model_path:
            return
        
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'strategy_names': self.strategy_names,
                'trained_at': datetime.now(timezone.utc).isoformat()
            }
            
            with open(self.model_path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"AI model saved to {self.model_path}")
        except Exception as e:
            logger.error(f"Error saving AI model: {e}", exc_info=True)
    
    def _load_model(self):
        """Lädt gespeichertes Modell"""
        if not self.model_path or not self.model_path.exists():
            return
        
        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data.get('model')
            self.scaler = model_data.get('scaler')
            self.strategy_names = model_data.get('strategy_names', [])
            self.is_trained = True
            
            logger.info(f"AI model loaded from {self.model_path}")
        except Exception as e:
            logger.error(f"Error loading AI model: {e}", exc_info=True)
            self.is_trained = False
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Gibt Feature-Importance zurück (für Debugging/Analyse)"""
        if not self.is_trained or not self.model:
            return {}
        
        feature_names = [
            'soc', 'soh', 'temp_c', 'price_trend', 'price_volatility',
            'current_price', 'pv_6h_avg', 'load_6h_avg', 'price_6h_avg',
            'hour', 'weekday', 'is_weekend', 'current_strategy_score',
            'p_bess', 'p_pv', 'p_load', 'p_grid'
        ]
        
        importances = self.model.feature_importances_
        return dict(zip(feature_names, importances))

