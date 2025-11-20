# 🚀 Konkrete Vorschläge für zukünftige Erweiterungen

**Erstellt:** Basierend auf aktuellem Systemstand und Prüfliste  
**Datum:** 2025-11-20

---

## 📊 Priorisierungsmatrix

| Feature | Priorität | Aufwand | ROI | Empfohlene Phase |
|---------|-----------|---------|-----|------------------|
| **1. KI-basierte Strategie-Auswahl** | 🔴 **Hoch** | Mittel | ⭐⭐⭐⭐⭐ | Phase 3.1 |
| **2. Erweiterte ML-Prognosen** | 🟡 **Mittel** | Mittel | ⭐⭐⭐⭐ | Phase 3.2 |
| **3. IoT-Sensor-Integration** | 🟡 **Mittel** | Niedrig | ⭐⭐⭐⭐ | Phase 3.3 |
| **4. VPP-Integration** | 🟢 **Niedrig** | Hoch | ⭐⭐⭐ | Phase 4 |
| **5. Blockchain-Integration** | 🟢 **Niedrig** | Sehr Hoch | ⭐⭐ | Phase 5 |

---

## 🎯 **Phase 3.1: KI-basierte Strategie-Auswahl** ⭐ **TOP PRIORITÄT**

### **Aktueller Stand:**
- ✅ 4 Strategien implementiert (Arbitrage, Peak Shaving, Self-Consumption, Load Balancing)
- ✅ Einfache Strategie-Auswahl basierend auf Score-Vergleich
- ✅ Prophet ML bereits für Forecasting vorhanden

### **Was fehlt:**
- ❌ Intelligente, kontextbasierte Strategie-Auswahl
- ❌ Lernen aus historischen Entscheidungen
- ❌ Berücksichtigung von Marktbedingungen, Wetter, Lastprofilen

### **Konkrete Umsetzung:**

#### **3.1.1 Reinforcement Learning für Strategie-Auswahl**

**Technologie:** 
- `scikit-learn` für klassische ML-Modelle (Random Forest, Gradient Boosting)
- Optional: `stable-baselines3` für Reinforcement Learning (später)

**Implementierung:**
```python
# app/ems/strategies/ai_strategy_selector.py

from sklearn.ensemble import RandomForestClassifier
import numpy as np
from typing import Dict, Any, List

class AIStrategySelector:
    """
    KI-basierte Strategie-Auswahl basierend auf:
    - Historischen Performance-Daten
    - Marktbedingungen (Preise, Volatilität)
    - Wetterprognosen
    - Lastprofilen
    - Systemzustand (SoC, BESS-Status)
    """
    
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.is_trained = False
        self.feature_history = []
        self.decision_history = []
    
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
        features = [
            state.get('soc', 50.0) / 100.0,  # Normalisiert
            state.get('soh', 100.0) / 100.0,
            state.get('temp_c', 25.0) / 50.0,
            market_data.get('price_trend', 0.0),  # -1 bis +1
            market_data.get('price_volatility', 0.0),
            forecast.get('pv_6h_avg', 0.0) / 100.0,
            forecast.get('load_6h_avg', 0.0) / 100.0,
            datetime.now().hour / 24.0,
            datetime.now().weekday() / 7.0,
            state.get('current_strategy_score', 0.0)
        ]
        return np.array(features).reshape(1, -1)
    
    def select_strategy(self,
                       state: Dict[str, Any],
                       forecast: Dict[str, Any],
                       market_data: Dict[str, Any],
                       strategy_scores: Dict[str, float]) -> str:
        """
        Wählt beste Strategie basierend auf ML-Modell
        """
        if not self.is_trained:
            # Fallback: Beste Score-Strategie
            return max(strategy_scores, key=strategy_scores.get)
        
        features = self.extract_features(state, forecast, market_data)
        predicted_strategy_idx = self.model.predict(features)[0]
        
        strategy_names = list(strategy_scores.keys())
        return strategy_names[predicted_strategy_idx]
    
    def train(self, historical_data: List[Dict[str, Any]]):
        """
        Trainiert Modell mit historischen Daten:
        - Features: Systemzustand, Marktdaten, Prognosen
        - Labels: Beste Strategie (basierend auf tatsächlichem Gewinn)
        """
        X = []
        y = []
        
        for record in historical_data:
            features = self.extract_features(
                record['state'],
                record['forecast'],
                record['market']
            )
            X.append(features[0])
            y.append(record['best_strategy_index'])
        
        if len(X) > 100:  # Mindestens 100 Datenpunkte
            self.model.fit(X, y)
            self.is_trained = True
            logger.info(f"AI Strategy Selector trained on {len(X)} samples")
```

**Integration:**
```python
# app/ems/strategy_manager.py - Erweiterung

class StrategyManager:
    def __init__(self, config):
        # ... bestehender Code ...
        self.ai_selector = None
        if config.get('ai_strategy_selection', {}).get('enabled', False):
            from .strategies.ai_strategy_selector import AIStrategySelector
            self.ai_selector = AIStrategySelector()
            # Trainiere mit historischen Daten
            self._train_ai_selector()
    
    def select_strategy(self, state, forecast):
        if self.ai_selector and self.ai_selector.is_trained:
            return self.ai_selector.select_strategy(
                state, forecast, self._get_market_data(), 
                self._calculate_strategy_scores(state, forecast)
            )
        else:
            # Fallback: Bestehende Logik
            return self._select_best_score_strategy(state, forecast)
```

**Konfiguration:**
```yaml
# app/config/ems.yaml
strategy:
  selection_mode: auto
  ai_selection:
    enabled: true
    training_data_days: 30  # Mindestens 30 Tage Historie
    retrain_interval_days: 7  # Wöchentliches Re-Training
    min_samples: 100
```

**Aufwand:** ~3-5 Tage  
**Vorteile:**
- Automatische Optimierung basierend auf Erfahrung
- Bessere Gewinne durch kontextbasierte Entscheidungen
- Selbstlernendes System

---

## 🧠 **Phase 3.2: Erweiterte ML-Prognosen**

### **Aktueller Stand:**
- ✅ Prophet ML für Last- und Preisprognosen
- ✅ Wetterbasierte PV-Prognosen (OpenWeatherMap + Clear-Sky)
- ✅ Einfache Prognosen als Fallback

### **Was erweitert werden kann:**

#### **3.2.1 LSTM/Transformer für Zeitreihen-Prognosen**

**Technologie:** `tensorflow` oder `pytorch` (optional, nur wenn Prophet nicht ausreicht)

**Umsetzung:**
```python
# app/services/forecast/lstm_forecaster.py

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

class LSTMForecaster:
    """
    LSTM-basierte Prognosen für komplexe Zeitreihen
    - Multi-Variable Input (Preis, Last, PV, SoC)
    - Sequenz-basierte Vorhersage
    - Bessere Genauigkeit bei nicht-linearen Mustern
    """
    
    def __init__(self, sequence_length=24, forecast_horizon=24):
        self.sequence_length = sequence_length  # 24h Input
        self.forecast_horizon = forecast_horizon  # 24h Output
        self.model = None
    
    def build_model(self, input_features=4):
        """
        LSTM-Modell für Multi-Variable Zeitreihen
        """
        model = Sequential([
            LSTM(50, return_sequences=True, input_shape=(self.sequence_length, input_features)),
            Dropout(0.2),
            LSTM(50, return_sequences=True),
            Dropout(0.2),
            LSTM(50),
            Dropout(0.2),
            Dense(self.forecast_horizon)
        ])
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model
    
    def forecast(self, historical_sequence: np.ndarray) -> np.ndarray:
        """
        Prognose basierend auf historischer Sequenz
        """
        if self.model is None:
            self.model = self.build_model(historical_sequence.shape[-1])
        
        prediction = self.model.predict(historical_sequence.reshape(1, *historical_sequence.shape))
        return prediction[0]
```

**Aufwand:** ~5-7 Tage (inkl. Training, Evaluation)  
**Vorteile:**
- Bessere Genauigkeit bei komplexen Mustern
- Multi-Variable Prognosen
- Lernen von langfristigen Abhängigkeiten

#### **3.2.2 Ensemble-Methoden (Prophet + LSTM + Weather)**

**Umsetzung:**
```python
# app/services/forecast/ensemble_forecaster.py

class EnsembleForecaster:
    """
    Kombiniert mehrere Prognose-Methoden für bessere Genauigkeit
    """
    
    def __init__(self):
        self.prophet = ProphetForecaster()
        self.weather = WeatherForecaster()
        self.lstm = LSTMForecaster()  # Optional
    
    def forecast_pv(self, hours=24):
        """
        Ensemble PV-Prognose:
        - 40% Prophet (historische Muster)
        - 40% Weather (Wetterdaten)
        - 20% LSTM (wenn verfügbar)
        """
        prophet_fc = self.prophet.forecast_pv(hours)
        weather_fc = self.weather.forecast_pv(hours)
        
        # Gewichtete Kombination
        ensemble = []
        for i in range(hours):
            p_val = prophet_fc[i][1] if i < len(prophet_fc) else 0
            w_val = weather_fc[i][1] if i < len(weather_fc) else 0
            ensemble.append((prophet_fc[i][0], 0.4 * p_val + 0.6 * w_val))
        
        return ensemble
```

**Aufwand:** ~2-3 Tage  
**Vorteile:**
- Robustere Prognosen durch Kombination
- Reduziertes Risiko von Fehlprognosen
- Beste Eigenschaften jeder Methode

---

## 📡 **Phase 3.3: IoT-Sensor-Integration** ⭐ **PRAKTISCH & NUTZBRINGEND**

### **Aktueller Stand:**
- ✅ MQTT-Integration vorhanden
- ✅ Modbus-Integration vorhanden
- ✅ Telemetrie-Puffer für verschiedene Quellen

### **Was erweitert werden kann:**

#### **3.3.1 Multi-Sensor-Aggregation**

**Umsetzung:**
```python
# app/services/communication/sensor_aggregator.py

class SensorAggregator:
    """
    Aggregiert Daten von mehreren IoT-Sensoren:
    - Temperatursensoren (mehrere Messpunkte)
    - Feuchtigkeitssensoren
    - Umgebungslicht-Sensoren
    - Zusätzliche Leistungsmesser
    """
    
    def __init__(self):
        self.sensors = {}  # {sensor_id: SensorConfig}
        self.data_buffer = {}  # {sensor_id: deque}
    
    def register_sensor(self, sensor_id: str, config: Dict[str, Any]):
        """
        Registriert neuen Sensor:
        - MQTT-Topic oder Modbus-Register
        - Sensor-Typ (temperature, humidity, power, etc.)
        - Aggregations-Methode (avg, max, min, weighted)
        """
        self.sensors[sensor_id] = config
        self.data_buffer[sensor_id] = deque(maxlen=100)
    
    def aggregate_temperature(self) -> float:
        """
        Aggregiert Temperaturen von mehreren Sensoren
        - Gewichteter Durchschnitt basierend auf Position
        - Ignoriert Ausreißer
        """
        temps = []
        weights = []
        
        for sensor_id, config in self.sensors.items():
            if config['type'] == 'temperature':
                recent_values = list(self.data_buffer[sensor_id])
                if recent_values:
                    avg_temp = np.mean(recent_values)
                    weight = config.get('weight', 1.0)
                    temps.append(avg_temp)
                    weights.append(weight)
        
        if temps:
            return np.average(temps, weights=weights)
        return None
```

**Konfiguration:**
```yaml
# app/config/ems.yaml
sensors:
  enabled: true
  aggregation:
    temperature_method: weighted_avg  # avg, max, min, weighted_avg
    power_method: sum  # sum, max, avg
  sensors:
    - id: temp_battery_room
      type: temperature
      source: mqtt
      topic: sensors/temperature/battery_room
      weight: 1.5  # Höhere Gewichtung
    - id: temp_pcs_room
      type: temperature
      source: mqtt
      topic: sensors/temperature/pcs_room
      weight: 1.0
    - id: humidity_outdoor
      type: humidity
      source: modbus
      register: humidity_outdoor
```

**Aufwand:** ~2-3 Tage  
**Vorteile:**
- Mehrere Messpunkte für bessere Genauigkeit
- Redundanz bei Sensorausfällen
- Erweiterte Umgebungsüberwachung

#### **3.3.2 Edge-Device-Integration (Raspberry Pi, ESP32, etc.)**

**Umsetzung:**
- MQTT-Bridge für Edge-Devices
- Standardisierte Topic-Struktur: `phoenyra/sensors/<device_id>/<sensor_type>`
- Auto-Discovery von neuen Sensoren

**Aufwand:** ~3-4 Tage  
**Vorteile:**
- Einfache Integration von günstigen IoT-Sensoren
- Skalierbare Sensor-Infrastruktur
- Offene Architektur

---

## 🔗 **Phase 4: VPP-Integration (Virtuelles Kraftwerk)**

### **Aktueller Stand:**
- ✅ REST API vorhanden
- ✅ Modbus/MQTT für externe Steuerung
- ✅ Power-Control-Logik vorhanden

### **Konkrete Umsetzung:**

#### **4.1 Aggregator-Schnittstelle**

**Umsetzung:**
```python
# app/services/vpp/aggregator_client.py

class AggregatorClient:
    """
    Client für VPP-Aggregatoren (z.B. Entelios, Next Kraftwerke)
    - Registrierung als Flexibilitätsanbieter
    - Empfang von Fahrplan-Anweisungen
    - Rückmeldung von Ist-Werten
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.aggregator_url = config.get('api_url')
        self.api_key = config.get('api_key')
        self.site_id = config.get('site_id')
        self.enabled = config.get('enabled', False)
    
    def register_flexibility(self, 
                           max_power_kw: float,
                           min_power_kw: float,
                           response_time_s: int) -> bool:
        """
        Registriert BESS als Flexibilitätsanbieter
        """
        payload = {
            'site_id': self.site_id,
            'max_power_kw': max_power_kw,
            'min_power_kw': min_power_kw,
            'response_time_s': response_time_s,
            'technology': 'bess'
        }
        # API-Call zum Aggregator
        return True
    
    def receive_schedule(self) -> Optional[List[Dict[str, Any]]]:
        """
        Empfängt Fahrplan vom Aggregator
        """
        # REST API oder MQTT
        return None
    
    def send_telemetry(self, state: Dict[str, Any]):
        """
        Sendet Ist-Werte an Aggregator
        """
        payload = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'power_kw': state.get('p_bess', 0.0),
            'soc': state.get('soc', 0.0),
            'available_capacity_kwh': state.get('available_capacity', 0.0)
        }
        # API-Call
```

**Konfiguration:**
```yaml
# app/config/ems.yaml
vpp:
  enabled: false
  aggregator: entelios  # entelios, next_kraftwerke, custom
  api_url: https://api.entelios.de/v1
  api_key: YOUR_API_KEY
  site_id: phoenyra_001
  flexibility:
    max_power_kw: 100.0
    min_power_kw: -100.0
    response_time_s: 5
```

**Aufwand:** ~7-10 Tage (abhängig von Aggregator-API)  
**Vorteile:**
- Zusätzliche Erlösquellen (aFRR, mFRR)
- Grid-Services
- Marktintegration

---

## ⛓️ **Phase 5: Blockchain-Integration** (Experimentell)

### **Konkrete Anwendungsfälle:**

#### **5.1 Energiehandel auf Blockchain**

**Umsetzung:**
- Smart Contracts für P2P-Energiehandel
- Tokenisierung von Energieeinheiten
- Transparente Abrechnung

**Technologie:** Ethereum, Polygon, oder spezialisierte Energy-Blockchains

**Aufwand:** ~15-20 Tage (sehr komplex)  
**ROI:** Niedrig (experimentell, regulatorische Unsicherheit)

**Empfehlung:** Nur wenn konkreter Use-Case vorhanden

---

## 📋 **Empfohlene Implementierungsreihenfolge**

### **Sofort umsetzbar (Phase 3.1):**
1. ✅ **KI-basierte Strategie-Auswahl** (3-5 Tage)
   - Größter ROI
   - Nutzt vorhandene Daten
   - Sofort messbare Verbesserung

### **Kurzfristig (Phase 3.2-3.3):**
2. ✅ **Erweiterte ML-Prognosen** (5-7 Tage)
   - Bessere Prognosegenauigkeit
   - Ensemble-Methoden
3. ✅ **IoT-Sensor-Integration** (2-3 Tage)
   - Praktischer Nutzen
   - Einfache Umsetzung

### **Mittelfristig (Phase 4):**
4. ⚠️ **VPP-Integration** (7-10 Tage)
   - Abhängig von Aggregator-APIs
   - Regulatorische Anforderungen prüfen

### **Langfristig (Phase 5):**
5. ❓ **Blockchain-Integration** (15-20 Tage)
   - Nur bei konkretem Bedarf
   - Experimentell

---

## 🎯 **Konkreter Startvorschlag: Phase 3.1**

**Warum Phase 3.1 zuerst:**
- ✅ Nutzt vorhandene Infrastruktur (Prophet, Historien-DB)
- ✅ Sofort messbarer Mehrwert (bessere Strategie-Auswahl = mehr Gewinn)
- ✅ Modulare Erweiterung (keine Breaking Changes)
- ✅ Geringer Aufwand, hoher ROI

**Erste Schritte:**
1. Implementiere `AIStrategySelector` mit Random Forest
2. Trainiere mit vorhandenen historischen Daten
3. A/B-Testing: KI vs. Score-basierte Auswahl
4. Monitoring der Performance-Verbesserung

**Erfolgsmetriken:**
- Gewinnsteigerung durch bessere Strategie-Auswahl
- Reduzierte Strategiewechsel (stabilere Fahrweise)
- Höhere Prognosegenauigkeit

---

**© 2025 Phoenyra.com by Ing. Heinz Schlagintweit**

