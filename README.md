# ⚡ Phoenyra EMS - Intelligentes Energiemanagementsystem

## 📋 **Übersicht**

Phoenyra EMS ist ein intelligentes, strategiebasiertes Energiemanagementsystem für Batteriespeicher (BESS). Es optimiert automatisch den Batteriebetrieb basierend auf Strompreisen, Prognosen und verschiedenen Strategien.

## 🎯 **Hauptziele**

- **Strategische Steuerung** der BESS-Simulation
- **Grid-Integration** und Compliance
- **Multi-Asset-Management** (BESS, PV, Wind, etc.)
- **Intelligente Lastprognose** und Optimierung
- **VPP-Integration** (Virtuelles Kraftwerk)
- **Grid-Services** Koordination

## 🏗️ **Architektur**

```
EMS-Modul (Orchestrator)
├── Strategy Manager
├── Forecasting Engine
├── Optimization Engine
└── Interface Layer
    ├── BESS Interface
    ├── Grid Interface
    └── Market Interface
```

## 📁 **Ordnerstruktur**

```
EMS/
├── README.md                    # Diese Datei
├── EMS_MODUL_DOKUMENTATION.md   # Vollständige Dokumentation
├── docs/                        # Detaillierte Dokumentation
├── src/                         # Quellcode
├── config/                      # Konfigurationsdateien
├── tests/                       # Tests
├── examples/                    # Beispiel-Implementierungen
└── requirements.txt             # Python-Abhängigkeiten
```

## ✨ **Key Features**

### **🧠 Intelligenz & Optimierung**
- ✅ **4 Strategien:** Arbitrage, Peak Shaving, Self-Consumption, Load Balancing
- ✅ **Linear Programming:** Mathematisch optimale Lösungen mit CVXPY
- ✅ **Adaptive Strategiewahl:** Automatische Auswahl basierend auf Situation
- ✅ **Prophet ML:** Facebook Prophet für präzise Zeitreihen-Prognosen
- ✅ **Wetterbasiert:** OpenWeatherMap für PV-Prognosen

### **📊 Dashboard & Analytics**
- ✅ **Live-Dashboard:** Echtzeit-Visualisierung mit Chart.js
- ✅ **Analytics-Dashboard:** Historische Performance-Analyse
- ✅ **KPI-Tracking:** Gewinn, Zyklen, SoC, Strategien
- ✅ **Navigation:** Professionelles UI mit Tabs

### **🔌 Integration & API**
- ✅ **REST API:** Vollständige API für alle Funktionen
- ✅ **aWATTar:** Day-Ahead Strompreise (AT/DE)
- ✅ **SQLite DB:** Historische Datenspeicherung
- ✅ **SSE:** Server-Sent Events für Live-Updates

## 🚀 **Schnellstart**

### **Installation:**
```bash
cd phoenyra-EMS/app
pip install -r requirements.txt
```

### **Starten:**
```bash
python -m flask --app web.app run --debug
```

### **Dashboard öffnen:**
```
http://localhost:5000
Login: admin / admin123
```

📖 **Vollständige Installationsanleitung:** [app/INSTALLATION.md](app/INSTALLATION.md)

## 📚 **Dokumentation**

- **[Vollständige Dokumentation](EMS_MODUL_DOKUMENTATION.md)** - Umfassende EMS-Dokumentation
- **[Architektur](docs/EMS_ARCHITECTURE.md)** - Detaillierte Architektur-Beschreibung
- **[Strategien](docs/EMS_STRATEGIES.md)** - EMS-Strategien Dokumentation
- **[Integration](docs/EMS_INTEGRATION.md)** - BESS-Integration Guide
- **[API-Referenz](docs/EMS_API_REFERENCE.md)** - API-Dokumentation

## 🎯 **Implementierte Strategien**

### 1. **Arbitrage** 
- Kauft Strom bei niedrigen Preisen, verkauft bei hohen
- Nutzt Day-Ahead Preisunterschiede optimal aus
- **Optimierung:** Linear Programming (CVXPY)
- **Ergebnis:** Maximaler Gewinn durch Preisarbitrage

### 2. **Peak Shaving**
- Reduziert Lastspitzen automatisch
- Identifiziert und glättet Peaks im Lastprofil
- **Anwendung:** Industrie & Gewerbe
- **Ergebnis:** 20-30% Lastspitzen-Reduktion

### 3. **Self-Consumption**
- Maximiert PV-Eigenverbrauch
- Speichert Überschuss, nutzt bei Bedarf
- **Anwendung:** PV-Anlagen
- **Ergebnis:** >80% Eigenverbrauchsquote

### 4. **Load Balancing** ⭐ NEU
- Glättet Lastschwankungen und Volatilität
- Reduziert Netzbelastung durch Ausgleich
- **Methode:** Moving Average + BESS-Kompensation
- **Ergebnis:** Geglättetes Lastprofil, reduzierte Gradienten

## 🔗 **BESS-Simulation Integration**

Das EMS-Modul nutzt die bestehende BESS-Simulation als technische Basis:

- **Advanced Dispatch System** - Für technische Optimierung
- **Economic Analysis** - Für Wirtschaftlichkeitsberechnung
- **Market Data Integration** - Für Preisprognosen
- **Grid Services** - Für Netz-Services
- **Database Integration** - Für Datenzugriff

## 🧪 **Testing**

```bash
# Alle Tests ausführen
python -m pytest tests/

# Spezifische Tests
python -m pytest tests/test_ems_engine.py
python -m pytest tests/test_strategies.py
```

## 📊 **Beispiele**

```python
# Basis EMS-Setup
from examples.basic_ems_setup import BasicEMSSetup

ems_setup = BasicEMSSetup()
ems_setup.run_demo()

# Strategie-Beispiele
from examples.strategy_examples import StrategyExamples

examples = StrategyExamples()
examples.run_peak_shaving_example()
```

## 🎨 **Dashboard Features**

### Live-Monitoring
- **KPI-Cards:** SoC, Power, Strategy, Expected Profit
- **Echtzeit-Updates:** Server-Sent Events (SSE)
- **Interaktive Charts:** Chart.js Visualisierungen

### Charts
1. **24h Optimization Plan:** BESS Power, PV, Load
2. **Price & SoC Forecast:** Strompreise und geplanter SoC-Verlauf

### System Status
- Grid Power, PV Generation, Load, Current Price
- Alle Werte live aktualisiert

## 📡 **API-Endpunkte**

### **Real-time & State**
```bash
GET  /api/state              # Aktueller Anlagenzustand
GET  /api/events             # SSE für Live-Updates
```

### **Optimization & Strategy**
```bash
GET  /api/plan               # Optimierungsplan (24h)
GET  /api/forecast           # Prognosen (Preise, PV, Last)
GET  /api/strategies         # Verfügbare Strategien
POST /api/strategy           # Strategie manuell setzen
POST /api/strategy/auto      # Auto-Modus aktivieren
```

### **Analytics & History** ⭐ NEU (Phase 2)
```bash
GET  /api/history/state           # State History (Parameter: hours)
GET  /api/history/optimization    # Optimization History (Parameter: days)
GET  /api/analytics/daily         # Tägliche Metriken (Parameter: days)
GET  /api/analytics/summary       # Performance-Zusammenfassung (Parameter: days)
```

## 🏗️ **Architektur**

```
┌─────────────────────────────────────────────────┐
│           Phoenyra EMS Architecture             │
├─────────────────────────────────────────────────┤
│  Web Dashboard (Flask + Chart.js)               │
├─────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐            │
│  │   Strategy   │  │ Optimization │            │
│  │   Manager    │  │    Engine    │            │
│  │              │  │   (CVXPY)    │            │
│  └──────────────┘  └──────────────┘            │
│                                                 │
│  ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│  │ Arbitrage  │  │    Peak    │  │   Self   │ │
│  │ Strategy   │  │  Shaving   │  │Consumptn │ │
│  └────────────┘  └────────────┘  └──────────┘ │
├─────────────────────────────────────────────────┤
│  Services: aWATTar API, Forecasting, Database  │
└─────────────────────────────────────────────────┘
```

## 🚀 **Implementierungsstatus**

### ✅ **Phase 1: Foundation** (Abgeschlossen)
- ✅ Strategie-Architektur (BaseStrategy, Strategy Manager)
- ✅ Linear Programming Optimierer (CVXPY)
- ✅ Arbitrage, Peak Shaving, Self-Consumption Strategien
- ✅ aWATTar Price Integration (AT/DE)
- ✅ EMS Controller mit intelligenter Steuerung
- ✅ Modernes Dashboard mit Charts
- ✅ REST API für alle Funktionen

### ✅ **Phase 2: Intelligence** (Abgeschlossen)
- ✅ **Prophet Forecasting:** ML-basierte Last- und Preisprognosen
- ✅ **Wetterbasierte PV-Prognosen:** OpenWeatherMap Integration + Clear-Sky Model
- ✅ **Historische Datenbank:** Performance-Tracking & Analytics
- ✅ **Load Balancing Strategie:** Glättung von Lastschwankungen
- ✅ **Analytics Dashboard:** Visualisierung historischer Daten
- ✅ **4 Strategien:** Arbitrage, Peak Shaving, Self-Consumption, Load Balancing

### 🔮 **Phase 3: Advanced** (Geplant)
- Multi-Asset Management
- VPP Integration
- Grid Services
- Blockchain Integration
- Advanced Analytics Dashboard

## 📈 **Erwartete Vorteile**

### **Technische Vorteile:**
- ✅ **Modulare Architektur** - Einfache Erweiterung
- ✅ **Skalierbarkeit** - Multi-Asset-Management
- ✅ **Flexibilität** - Verschiedene Strategien
- ✅ **Wartbarkeit** - Klare Trennung der Verantwortlichkeiten

### **Wirtschaftliche Vorteile:**
- ✅ **Erhöhte Erlöse** - Optimierte Strategien
- ✅ **Kosteneinsparungen** - Effizientere Nutzung
- ✅ **Grid-Services** - Zusätzliche Erlösquellen
- ✅ **Flexibilität** - Anpassung an Marktbedingungen

## 🔮 **Zukünftige Erweiterungen**

- Machine Learning für Prognosen
- VPP-Integration
- Blockchain-Integration
- IoT-Sensor-Integration
- KI-basierte Strategie-Auswahl

## 📞 **Support**

Bei Fragen oder Problemen:
1. Dokumentation durchlesen
2. Tests ausführen
3. Logs überprüfen
4. Issue erstellen

---

*Erstellt am: $(date)*
*Version: 1.0.0*
*Autor: Cursor AI Assistant*
