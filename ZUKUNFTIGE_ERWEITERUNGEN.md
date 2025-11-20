# 🚀 Konkrete Vorschläge für zukünftige Erweiterungen

**Erstellt:** Basierend auf aktuellem Systemstand und Prüfliste  
**Datum:** 2025-11-20

---

## 📊 Priorisierungsmatrix

| Feature | Priorität | Aufwand | ROI | Empfohlene Phase |
|---------|-----------|---------|-----|------------------|
| **0. Multi-Site/Multi-BESS** | 🔴 **SEHR HOCH** | Hoch | ⭐⭐⭐⭐⭐ | Phase 2.5 |
| **1. KI-basierte Strategie-Auswahl** | 🔴 **Hoch** | Mittel | ⭐⭐⭐⭐⭐ | Phase 3.1 |
| **2. Erweiterte ML-Prognosen** | 🟡 **Mittel** | Mittel | ⭐⭐⭐⭐ | Phase 3.2 |
| **3. IoT-Sensor-Integration** | 🟡 **Mittel** | Niedrig | ⭐⭐⭐⭐ | Phase 3.3 |
| **4. VPP-Integration** | 🟢 **Niedrig** | Hoch | ⭐⭐⭐ | Phase 4 |
| **5. Blockchain-Integration** | 🟢 **Niedrig** | Sehr Hoch | ⭐⭐ | Phase 5 |

---

## 🏢 **Phase 2.5: Multi-Site/Multi-BESS-Integration** ⭐ **KRITISCH - ZUERST UMSETZEN**

### **Aktueller Stand:**
- ✅ `site_id` bereits im `PlantState` vorhanden
- ✅ `user_sites` Tabelle in User-Datenbank für Site-basierte Zugriffskontrolle
- ✅ Forecast-Funktionen akzeptieren bereits `site_id` als Parameter
- ❌ **NUR EINE `EmsCore`-Instanz** pro Anwendung
- ❌ **NUR EINE BESS-Konfiguration** in `ems.yaml`
- ❌ Keine Multi-Site-Verwaltung im Frontend

### **Was fehlt:**
- ❌ Multi-Site-Manager für mehrere Standorte
- ❌ Separate `EmsCore`-Instanzen pro Standort
- ❌ Site-spezifische Konfigurationen
- ❌ Multi-Site-Dashboard im Frontend
- ❌ Aggregierte Ansicht über alle Standorte

### **Konkrete Umsetzung:**

#### **2.5.1 Multi-Site-Manager**

**Architektur:**
```python
# app/ems/multi_site_manager.py

from typing import Dict, List, Optional
from .controller import EmsCore
import logging

logger = logging.getLogger(__name__)


class MultiSiteManager:
    """
    Verwaltet mehrere Standorte (Sites) mit jeweils eigenem EmsCore
    
    Jeder Standort hat:
    - Eigene BESS-Konfiguration
    - Eigene Modbus/MQTT-Verbindungen
    - Eigene Strategien und Optimierung
    - Eigene Historien-Datenbank
    """
    
    def __init__(self, sites_config: Dict[str, Any]):
        """
        Initialisiert Multi-Site-Manager
        
        Args:
            sites_config: Dictionary mit Site-Konfigurationen
                {
                    'sites': {
                        1: { 'name': 'Standort Wien', 'bess': {...}, 'modbus': {...}, ... },
                        2: { 'name': 'Standort Linz', 'bess': {...}, 'modbus': {...}, ... }
                    },
                    'default_site_id': 1
                }
        """
        self.sites: Dict[int, EmsCore] = {}
        self.site_configs: Dict[int, Dict[str, Any]] = {}
        self.default_site_id = sites_config.get('default_site_id', 1)
        
        # Initialisiere alle Sites
        for site_id, site_cfg in sites_config.get('sites', {}).items():
            self._initialize_site(int(site_id), site_cfg)
        
        logger.info(f"MultiSiteManager initialized with {len(self.sites)} sites")
    
    def _initialize_site(self, site_id: int, site_config: Dict[str, Any]):
        """
        Initialisiert einen einzelnen Standort
        """
        try:
            # Erstelle vollständige Config für diesen Standort
            full_config = {
                'bess': site_config.get('bess', {}),
                'modbus': site_config.get('modbus', {}),
                'mqtt': site_config.get('mqtt', {}),
                'forecast': site_config.get('forecast', {}),
                'grid_connection': site_config.get('grid_connection', {}),
                'feedin_limitation': site_config.get('feedin_limitation', {}),
                'grid_tariffs': site_config.get('grid_tariffs', {}),
                'ems': site_config.get('ems', {}),
                'database': {
                    'history_path': f"data/ems_history_site_{site_id}.db"
                }
            }
            
            # Erstelle EmsCore-Instanz für diesen Standort
            ems_core = EmsCore(full_config)
            ems_core.state.site_id = site_id
            ems_core.start()
            
            self.sites[site_id] = ems_core
            self.site_configs[site_id] = site_config
            
            logger.info(f"Site {site_id} ({site_config.get('name', 'Unnamed')}) initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize site {site_id}: {e}")
    
    def get_site(self, site_id: Optional[int] = None) -> Optional[EmsCore]:
        """
        Gibt EmsCore für einen Standort zurück
        
        Args:
            site_id: Site-ID (None = Default-Site)
        
        Returns:
            EmsCore-Instanz oder None
        """
        site_id = site_id or self.default_site_id
        return self.sites.get(site_id)
    
    def get_all_sites(self) -> Dict[int, EmsCore]:
        """Gibt alle Site-Instanzen zurück"""
        return self.sites
    
    def get_site_state(self, site_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Gibt aktuellen Zustand eines Standorts zurück"""
        ems = self.get_site(site_id)
        if ems:
            return asdict(ems.state)
        return None
    
    def get_all_sites_state(self) -> Dict[int, Dict[str, Any]]:
        """Gibt Zustand aller Standorte zurück"""
        return {
            site_id: asdict(ems.state)
            for site_id, ems in self.sites.items()
        }
    
    def get_aggregated_state(self) -> Dict[str, Any]:
        """
        Aggregiert Zustand aller Standorte
        
        Returns:
            {
                'total_p_bess': sum aller BESS-Leistungen,
                'total_p_pv': sum aller PV-Leistungen,
                'total_p_load': sum aller Lasten,
                'total_energy_capacity': sum aller Kapazitäten,
                'avg_soc': durchschnittlicher SoC,
                'sites': {site_id: state}
            }
        """
        all_states = self.get_all_sites_state()
        
        aggregated = {
            'total_p_bess': 0.0,
            'total_p_pv': 0.0,
            'total_p_load': 0.0,
            'total_p_grid': 0.0,
            'total_energy_capacity': 0.0,
            'total_soc_weighted': 0.0,
            'total_capacity': 0.0,
            'sites': all_states,
            'site_count': len(all_states)
        }
        
        for site_id, state in all_states.items():
            aggregated['total_p_bess'] += state.get('p_bess', 0.0)
            aggregated['total_p_pv'] += state.get('p_pv', 0.0)
            aggregated['total_p_load'] += state.get('p_load', 0.0)
            aggregated['total_p_grid'] += state.get('p_grid', 0.0)
            
            capacity = self.site_configs[site_id].get('bess', {}).get('energy_capacity_kwh', 0.0)
            aggregated['total_energy_capacity'] += capacity
            aggregated['total_soc_weighted'] += state.get('soc', 0.0) * capacity
            aggregated['total_capacity'] += capacity
        
        # Gewichteter Durchschnitts-SoC
        if aggregated['total_capacity'] > 0:
            aggregated['avg_soc'] = aggregated['total_soc_weighted'] / aggregated['total_capacity']
        else:
            aggregated['avg_soc'] = 0.0
        
        return aggregated
```

#### **2.5.2 Erweiterte Konfiguration**

**Struktur:**
```yaml
# app/config/ems.yaml

# Multi-Site-Konfiguration
sites:
  default_site_id: 1
  sites:
    1:
      name: "Standort Wien"
      location:
        city: "Wien"
        latitude: 48.2082
        longitude: 16.3738
      bess:
        energy_capacity_kwh: 200.0
        power_charge_max_kw: 100.0
        power_discharge_max_kw: 100.0
        efficiency_charge: 0.95
        efficiency_discharge: 0.95
      modbus:
        enabled: true
        connection_type: tcp
        host: "192.168.1.100"
        port: 502
        profile: hithium_ess_5016
      mqtt:
        enabled: true
        broker: "mqtt.wien.local"
        topics:
          telemetry: "phoenyra/site1/telemetry"
          commands: "phoenyra/site1/commands"
      forecast:
        pv_peak_power_kw: 50.0
        latitude: 48.2082
        longitude: 16.3738
      grid_connection:
        max_power_kw: 30.0
      feedin_limitation:
        enabled: true
        mode: fixed
        fixed_limit_pct: 70.0
    
    2:
      name: "Standort Linz"
      location:
        city: "Linz"
        latitude: 48.3069
        longitude: 14.2858
      bess:
        energy_capacity_kwh: 300.0
        power_charge_max_kw: 150.0
        power_discharge_max_kw: 150.0
        efficiency_charge: 0.95
        efficiency_discharge: 0.95
      modbus:
        enabled: true
        connection_type: tcp
        host: "192.168.1.200"
        port: 502
        profile: wstech_pcs
      mqtt:
        enabled: true
        broker: "mqtt.linz.local"
        topics:
          telemetry: "phoenyra/site2/telemetry"
          commands: "phoenyra/site2/commands"
      forecast:
        pv_peak_power_kw: 75.0
        latitude: 48.3069
        longitude: 14.2858
      grid_connection:
        max_power_kw: 50.0
      feedin_limitation:
        enabled: true
        mode: dynamic
        dynamic_rules:
          - time: "06:00-18:00"
            limit_pct: 70.0
          - time: "18:00-22:00"
            limit_pct: 50.0
```

#### **2.5.3 Integration in Flask-App**

**Änderungen in `app/web/app.py`:**
```python
# app/web/app.py

from ems.multi_site_manager import MultiSiteManager

def create_app():
    # ... bestehender Code ...
    
    cfg = yaml.safe_load(open(Path(__file__).resolve().parents[1]/'config'/'ems.yaml'))
    
    # Multi-Site-Manager initialisieren
    if 'sites' in cfg and 'sites' in cfg['sites']:
        # Multi-Site-Modus
        app.ems = MultiSiteManager(cfg['sites'])
        app.multi_site = True
    else:
        # Single-Site-Modus (Rückwärtskompatibilität)
        app.ems = EmsCore(cfg)
        app.ems.start()
        app.multi_site = False
    
    # ... restlicher Code ...
```

#### **2.5.4 API-Erweiterungen**

**Neue Endpunkte in `app/web/routes.py`:**
```python
# GET /api/sites - Liste aller Standorte
@bp.route('/api/sites', methods=['GET'])
@login_required
def list_sites():
    if not current_app.multi_site:
        return jsonify({'sites': [{'id': 1, 'name': 'Default Site'}]})
    
    sites = []
    for site_id, site_cfg in current_app.ems.site_configs.items():
        sites.append({
            'id': site_id,
            'name': site_cfg.get('name', f'Site {site_id}'),
            'location': site_cfg.get('location', {}),
            'state': current_app.ems.get_site_state(site_id)
        })
    return jsonify({'sites': sites})

# GET /api/sites/<int:site_id>/state - Zustand eines Standorts
@bp.route('/api/sites/<int:site_id>/state', methods=['GET'])
@login_required
def get_site_state(site_id):
    # Prüfe Site-Zugriff (user_sites Tabelle)
    if not has_site_access(current_user, site_id):
        abort(403)
    
    state = current_app.ems.get_site_state(site_id)
    if state:
        return jsonify(state)
    abort(404)

# GET /api/sites/aggregated - Aggregierter Zustand aller Standorte
@bp.route('/api/sites/aggregated', methods=['GET'])
@login_required
@role_required('admin')  # Nur Admins sehen alle Standorte
def get_aggregated_state():
    if not current_app.multi_site:
        return jsonify(asdict(current_app.ems.state))
    
    aggregated = current_app.ems.get_aggregated_state()
    return jsonify(aggregated)
```

#### **2.5.5 Frontend-Erweiterungen**

**Neue Dashboard-Seite: `/sites`**
- Übersicht aller Standorte
- Aggregierte KPIs (Gesamtleistung, Durchschnitts-SoC, etc.)
- Site-spezifische Detailansicht
- Site-Auswahl im Monitoring

**Änderungen in `base.html`:**
- Site-Auswahl-Dropdown in der Navigation (für Multi-Site-User)
- Aktueller Standort wird in der Session gespeichert

**Aufwand:** ~7-10 Tage  
**Vorteile:**
- ✅ Zentrale Verwaltung mehrerer Standorte
- ✅ Site-spezifische Konfigurationen
- ✅ Aggregierte Übersicht
- ✅ Skalierbare Architektur
- ✅ Nutzt bereits vorhandene `site_id`-Infrastruktur

**Kritisch:** Diese Funktion sollte **VOR** den anderen Features implementiert werden, da:
- Alle anderen Features (KI-Strategie, ML-Prognosen, etc.) dann pro Standort funktionieren
- VPP-Integration profitiert von Multi-Site (Aggregation)
- IoT-Sensor-Integration wird pro Standort benötigt

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

### **KRITISCH - Zuerst umsetzen (Phase 2.5):**
0. 🔴 **Multi-Site/Multi-BESS-Integration** (7-10 Tage)
   - **MUSS zuerst kommen**, da alle anderen Features davon profitieren
   - Ermöglicht Skalierung auf mehrere Standorte
   - Nutzt bereits vorhandene `site_id`-Infrastruktur
   - Basis für VPP-Aggregation

### **Sofort danach (Phase 3.1):**
1. ✅ **KI-basierte Strategie-Auswahl** (3-5 Tage)
   - Größter ROI
   - Nutzt vorhandene Daten
   - Sofort messbare Verbesserung
   - **Pro Standort implementierbar**

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

## 🎯 **Konkreter Startvorschlag: Phase 2.5 (Multi-Site)**

**Warum Phase 2.5 ZUERST:**
- ✅ **Kritische Grundlage** für alle weiteren Features
- ✅ Nutzt bereits vorhandene `site_id`-Infrastruktur
- ✅ Ermöglicht Skalierung auf mehrere Standorte
- ✅ Alle anderen Features (KI, ML, IoT, VPP) profitieren davon
- ✅ VPP-Integration benötigt Multi-Site für Aggregation

**Danach Phase 3.1 (KI-Strategie):**
- ✅ Nutzt vorhandene Infrastruktur (Prophet, Historien-DB)
- ✅ Sofort messbarer Mehrwert (bessere Strategie-Auswahl = mehr Gewinn)
- ✅ Modulare Erweiterung (keine Breaking Changes)
- ✅ Geringer Aufwand, hoher ROI
- ✅ **Pro Standort implementierbar** (dank Phase 2.5)

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

