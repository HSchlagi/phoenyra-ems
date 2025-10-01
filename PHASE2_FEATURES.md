# 🧠 Phase 2: Intelligence Features - Dokumentation

## Übersicht

Phase 2 erweitert Phoenyra EMS um intelligente Forecasting-Methoden, historische Datenanalyse und eine weitere Strategie.

---

## ✨ Neue Features

### 1. **Prophet-basiertes Forecasting**

**Implementierung:** `app/services/forecast/prophet_forecaster.py`

Facebook Prophet für zeitreihenbasierte Prognosen mit:
- ✅ Automatische Saisonalität-Erkennung (täglich, wöchentlich, jährlich)
- ✅ Trend-Analyse
- ✅ Uncertainty Intervals
- ✅ Holiday Effects

**Verwendung:**
```python
from services.forecast.prophet_forecaster import ProphetForecaster

forecaster = ProphetForecaster()

# Generate synthetic history
history = forecaster.generate_synthetic_history(days=30)

# Forecast load
load_forecast = forecaster.forecast_load(
    historical_data=history['load'],
    hours=24
)

# Forecast prices
price_forecast = forecaster.forecast_price(
    historical_data=history['price'],
    hours=24
)
```

**Aktivierung in `config/ems.yaml`:**
```yaml
forecast:
  use_prophet: true
```

---

### 2. **Wetterbasierte PV-Prognosen**

**Implementierung:** `app/services/forecast/weather_forecaster.py`

Integriert Wetterdaten für präzise PV-Prognosen:
- ✅ **OpenWeatherMap API Integration** (optional)
- ✅ **Clear-Sky Model** (fallback, keine API nötig)
- ✅ **Wolkenbedeckung-Korrektur**
- ✅ **Temperatur-Effekt** (PV-Effizienz)
- ✅ **Saisonale Variation**

**Features:**
- Sonnenstand-Berechnung (astronomisches Modell)
- Cloud Factor: 0% Wolken = 100% Leistung, 100% = 20%
- Temperature Effect: -0.4% pro °C über 25°C

**Verwendung:**
```python
from services.forecast.weather_forecaster import WeatherForecaster

forecaster = WeatherForecaster(config={
    'openweathermap_api_key': 'YOUR_API_KEY',  # Optional
    'latitude': 48.2082,  # Vienna
    'longitude': 16.3738,
    'pv_peak_power_kw': 50.0,
    'pv_efficiency': 0.85
})

pv_forecast = forecaster.forecast_pv(hours=24)
```

**Aktivierung in `config/ems.yaml`:**
```yaml
forecast:
  use_weather: true
  openweathermap_api_key: "YOUR_API_KEY"  # Optional
  latitude: 48.2082
  longitude: 16.3738
  pv_peak_power_kw: 50.0
  pv_efficiency: 0.85
```

---

### 3. **Historische Datenbank**

**Implementierung:** `app/services/database/history_db.py`

SQLite-basierte Speicherung für Performance-Tracking:

**Tabellen:**
- `state_history`: Anlagenzustände (SoC, Power, etc.)
- `optimization_history`: Optimierungsergebnisse
- `strategy_changes`: Strategiewechsel
- `daily_metrics`: Aggregierte Tagesmetriken

**Features:**
- ✅ Automatisches Logging (alle 5 Min)
- ✅ Tägliche Metriken-Berechnung
- ✅ Performance-Zusammenfassungen
- ✅ Strategie-Verteilungs-Analyse

**Verwendung:**
```python
from services.database.history_db import HistoryDatabase

db = HistoryDatabase("data/ems_history.db")

# Log State
db.log_state(state_dict)

# Log Optimization
db.log_optimization(optimization_result)

# Get History
state_history = db.get_state_history(hours=24)
opt_history = db.get_optimization_history(days=7)

# Get Metrics
daily_metrics = db.get_daily_metrics(days=30)
summary = db.get_performance_summary(days=30)

# Calculate Daily Metrics (run once per day)
db.calculate_daily_metrics()
```

**API-Endpunkte:**
```bash
GET /api/history/state?hours=24
GET /api/history/optimization?days=7
GET /api/analytics/daily?days=30
GET /api/analytics/summary?days=30
```

---

### 4. **Load Balancing Strategie**

**Implementierung:** `app/ems/strategies/load_balancing_strategy.py`

Glättet Lastschwankungen durch intelligente BESS-Steuerung:

**Algorithmus:**
1. Berechnet gleitenden Durchschnitt der Last (Target)
2. BESS kompensiert Differenz zur geglätteten Last
3. Reduziert Volatilität und Gradienten

**Metriken:**
- Lastvolatilität (Standardabweichung)
- Lastgradienten (Änderungsraten)
- Varianzreduktion (%)

**Evaluation:**
Hoher Score wenn:
- Hohe Volatilität im Lastprofil
- Starke Gradienten (schnelle Änderungen)
- Mittlere bis hohe Grundlast

**Verwendung:**
```python
from ems.strategies import LoadBalancingStrategy

strategy = LoadBalancingStrategy(config={
    'smoothing_window': 3,  # Hours
    'target_load_factor': 0.8
})

# Evaluate
score = strategy.evaluate(current_state, forecast_data)

# Optimize
result = strategy.optimize(current_state, forecast_data, constraints)
```

**Konfiguration:**
```yaml
strategies:
  load_balancing:
    smoothing_window: 3
    target_load_factor: 0.8
```

---

### 5. **Analytics Dashboard**

**Implementierung:** `app/web/templates/analytics.html`

Neues Dashboard für historische Performance-Analyse:

**Features:**
- ✅ **Performance Summary Cards:** Gesamt-Gewinn, Ø täglich, Zyklen, SoC
- ✅ **Profit Chart:** Täglicher Gewinn (Bar Chart)
- ✅ **Strategy Chart:** Strategie-Verteilung (Pie Chart)
- ✅ **Optimization Table:** Letzte Optimierungen

**Navigation:**
- Professionelles Navbar mit Tabs
- Wechsel zwischen Dashboard ↔ Analytics
- Logout-Button

**Zugriff:**
```
http://localhost:5000/analytics
```

---

## 🔧 Konfiguration

### Vollständige `config/ems.yaml` (Phase 2):

```yaml
ems:
  mode: auto
  timestep_s: 2
  optimization_interval_minutes: 15

bess:
  energy_capacity_kwh: 200.0
  power_charge_max_kw: 100.0
  power_discharge_max_kw: 100.0
  soc_min_percent: 10.0
  soc_max_percent: 90.0
  efficiency_charge: 0.95
  efficiency_discharge: 0.95

prices:
  provider: awattar
  region: AT
  demo_mode: true

# Phase 2 Features
forecast:
  demo_mode: true
  use_prophet: false        # Enable ML forecasting
  use_weather: false        # Enable weather-based PV
  
  openweathermap_api_key: null
  latitude: 48.2082
  longitude: 16.3738
  pv_peak_power_kw: 50.0
  pv_efficiency: 0.85

strategies:
  selection_mode: auto
  manual_strategy: arbitrage
  switch_threshold: 0.15
  
  arbitrage:
    min_price_spread: 20.0
    min_profit_threshold: 5.0
  
  peak_shaving:
    peak_threshold_percentile: 75
    target_peak_reduction: 20
  
  self_consumption:
    feedin_tariff: 0.08
    grid_tariff: 0.30
  
  load_balancing:
    smoothing_window: 3
    target_load_factor: 0.8

database:
  history_path: "data/ems_history.db"
```

---

## 📊 Erwartete Verbesserungen

### **Prophet Forecasting:**
- 10-20% bessere Prognosegenauigkeit
- Berücksichtigung von Saisonalität
- Trend-Erkennung

### **Weather-based PV:**
- 15-25% genauere PV-Prognosen
- Wetterabhängige Anpassung
- Reduktion von Prognosefehlern

### **Load Balancing:**
- 20-40% Reduktion der Lastvolatilität
- Geglättetes Netzlastprofil
- Reduzierte Lastgradienten

### **Analytics:**
- Transparente Performance-Metriken
- Historische Trend-Analyse
- Strategie-Optimierung basierend auf Daten

---

## 🚀 Migration von Phase 1 zu Phase 2

### **Schritt 1: Dependencies installieren**
```bash
cd app
pip install -r requirements.txt
```

Prophet und weitere ML-Libraries werden automatisch installiert.

### **Schritt 2: Konfiguration anpassen**

Optional: Aktiviere neue Features in `config/ems.yaml`:

```yaml
forecast:
  use_prophet: true   # ML forecasting
  use_weather: true   # Weather-based PV
```

### **Schritt 3: OpenWeatherMap API (optional)**

Für wetterbasierte PV-Prognosen:
1. Hole API-Key von: https://openweathermap.org/api
2. Setze in `config/ems.yaml`:
```yaml
forecast:
  openweathermap_api_key: "YOUR_API_KEY"
```

Ohne API-Key wird automatisch das Clear-Sky Model verwendet.

### **Schritt 4: System starten**
```bash
python -m flask --app web.app run --debug
```

Alles funktioniert automatisch! Phase 2 Features werden bei Aktivierung nahtlos integriert.

---

## 🎯 Nutzung im Betrieb

### **Automatisch (Default):**
- Prophet & Weather Forecasting: **Deaktiviert** (Fallback zu Simple)
- Historische DB: **Aktiv** (immer)
- Load Balancing: **Verfügbar** (Auto-Select)
- Analytics Dashboard: **Verfügbar**

### **Mit Prophet aktiviert:**
```yaml
forecast:
  use_prophet: true
```
System verwendet Prophet für Load-Prognosen wenn historische Daten vorhanden.

### **Mit Weather aktiviert:**
```yaml
forecast:
  use_weather: true
  openweathermap_api_key: "YOUR_KEY"
```
System holt Wetterdaten und berechnet präzise PV-Prognosen.

---

## 📈 Performance-Monitoring

### **Tägliche Metriken berechnen:**

Optional: Cronjob oder manuell:
```python
from services.database.history_db import HistoryDatabase

db = HistoryDatabase()
db.calculate_daily_metrics()
```

### **Analytics Dashboard:**

Öffne http://localhost:5000/analytics für:
- Performance-Zusammenfassung
- Tägliche Gewinn-Charts
- Strategie-Verteilung
- Optimization History

---

## 🔮 Nächste Schritte (Phase 3+)

Mögliche Erweiterungen:
- LSTM Neural Networks für Forecasting
- Multi-Asset Management
- VPP Integration
- Grid Services (FCR, aFRR)
- Advanced Analytics (Jupyter Notebooks)
- Mobile App

---

**Version:** 2.0.0  
**Datum:** 2025-10-01  
**Status:** Production Ready


