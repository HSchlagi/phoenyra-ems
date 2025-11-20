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
phoenyra-EMS/
├── README.md                          # Diese Datei
├── EMS_MODUL_DOKUMENTATION.md         # Vollständige EMS-Dokumentation
├── DOKUMENTATION-EMS.md               # Monitoring-System Dokumentation
├── PHASE2_FEATURES.md                 # Phase 2 Features
├── app/                               # Hauptanwendung
│   ├── config/                        # Konfigurationsdateien
│   ├── data/                          # Datenbanken
│   ├── ems/                           # EMS Core Module
│   ├── services/                      # Services (Prices, Forecasts, DB, Communication)
│   ├── web/                           # Web Interface
│   │   ├── templates/                 # HTML Templates
│   │   └── static/                    # CSS, JS, Assets
│   └── requirements.txt               # Python Dependencies
├── deploy/                            # Docker Deployment
│   ├── docker-compose.yml             # Docker Compose Setup
│   ├── Dockerfile                     # Docker Image
│   └── mqtt/                          # MQTT Broker Config
└── data/                              # Persistente Daten
```

## ✨ **Key Features**

### **👥 Multiuser & Sicherheit** ⭐ NEU
- ✅ **Rollenbasierte Zugriffskontrolle:** Admin, Operator, Viewer
- ✅ **Benutzerverwaltung:** Vollständige CRUD-Operationen für Benutzer
- ✅ **Registrierung:** Selbstregistrierung für neue Benutzer
- ✅ **Passwort-Sicherheit:** Scrypt-basiertes Hashing
- ✅ **Session-Management:** Sichere Session-Verwaltung
- ✅ **Benachrichtigungen:** System-Alarme und Statusmeldungen
- ✅ **Hilfe & Anleitungen:** Umfassende Dokumentation im System

### **🧠 Intelligenz & Optimierung**
- ✅ **4 Strategien:** Arbitrage, Peak Shaving, Self-Consumption, Load Balancing
- ✅ **Linear Programming:** Mathematisch optimale Lösungen mit CVXPY
- ✅ **Adaptive Strategiewahl:** Automatische Auswahl basierend auf Situation
- ✅ **KI-basierte Strategie-Auswahl:** ⭐ NEU - Machine Learning (Random Forest) für intelligente Strategieauswahl basierend auf Marktdaten, SoC, SoH, Temperatur und Prognosen
- ✅ **Prophet ML:** Facebook Prophet für präzise Zeitreihen-Prognosen
- ✅ **Wetterbasiert:** OpenWeatherMap für PV-Prognosen
- ✅ **Market Data Service:** Preis-Trends, Volatilität und Marktanalyse für KI-Entscheidungen

### **📊 Dashboard & Analytics**
- ✅ **Live-Dashboard:** Echtzeit-Visualisierung mit Chart.js
- ✅ **Analytics-Dashboard:** Historische Performance-Analyse
- ✅ **Monitoring Page:** Live-Telemetrie (SoC, SoH, Leistungsgrenzen, Isolationswiderstand, Statuscode & Alarme) inkl. Einspeisebegrenzung, Netzanschlussabsicherung, Powerflow-Diagramm & Rohdaten-Viewer
- ✅ **Settings UI:** MQTT- & Modbus-Konfiguration mit Profil-Auswahl, dynamischem Register-Mapping & Verbindungstest im Browser
- ✅ **KPI-Tracking:** Gewinn, Zyklen, SoC, Strategien
- ✅ **Navigation:** Professionelles UI mit Tabs

### **🔌 Integration & API**
- ✅ **REST API:** Vollständige API für alle Funktionen
- ✅ **aWATTar:** Day-Ahead Strompreise (AT/DE)
- ✅ **SQLite DB:** Historische Datenspeicherung
- ✅ **SSE:** Server-Sent Events für Live-Updates
- ✅ **MQTT:** IoT-Integration (optional)
- ✅ **Modbus & Power-Control:** Geräte-Integration via Profilbibliothek (z. B. Hithium ESS, WSTECH PCS) inkl. Skalierung, Alarmbits, Zeit-Sync, UI-gestütztem Register-Editor sowie vorbereiteter DSO-/Sicherheitslogik (Trip, Limit, Auto-Write)

### **🐳 Docker & Deployment**
- ✅ **Docker Compose:** Containerisierte Deployment
- ✅ **Gunicorn:** Production-Server
- ✅ **MQTT Broker:** Eclipse Mosquitto Integration
- ✅ **Volumes:** Persistente Daten und Konfiguration

## 🚀 **Schnellstart**

### **Installation:**
```bash
cd phoenyra-EMS/app
pip install -r requirements.txt
```

### **Starten:**
```bash
cd app
python -m flask --app web.app run --debug --port 5000
```

### **Dashboard öffnen:**
```
http://localhost:5000
Login: admin / admin123
```

## 🐳 **Docker Deployment**

### **Mit Docker starten:**
```bash
docker-compose -f deploy/docker-compose.yml up -d --build
```

### **Dashboard öffnen (Docker):**
```
http://localhost:8080
Login: E-Mail-Adresse / Passwort
(Standard: admin / admin123 - nach Migration in Datenbank)
```

### **Container-Verwaltung:**
```bash
# Logs anzeigen
docker-compose -f deploy/docker-compose.yml logs -f ems-web

# Container stoppen
docker-compose -f deploy/docker-compose.yml down

# Neu starten
docker-compose -f deploy/docker-compose.yml restart
```

📖 **Vollständige Installationsanleitung:** [app/INSTALLATION.md](app/INSTALLATION.md)  
🐳 **Docker-Setup Details:** [deploy/README.md](deploy/README.md)

## 📚 **Dokumentation**

- **[DOKUMENTATION-EMS.md](DOKUMENTATION-EMS.md)** - **Monitoring-System Dokumentation**
- **[EMS_MODUL_DOKUMENTATION.md](EMS_MODUL_DOKUMENTATION.md)** - Vollständige EMS-Dokumentation
- **[app/INSTALLATION.md](app/INSTALLATION.md)** - Installationsanleitung
- **[deploy/README.md](deploy/README.md)** - Docker-Setup Details

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

### Main Dashboard (`/`)
- **KPI-Cards:** SoC, Power, Active Strategy, Expected Profit
- **Charts:** 24 h Optimization Plan (BESS/PV/Load) & Price + SoC Forecast
- **System Status:** Grid Power, PV Generation, Load, Current Price
- **Live-Updates:** Server-Sent Events (SSE) im 2‑Sekunden-Takt

### Monitoring (`/monitoring`) ⭐ NEU
- **Live-Telemetrie:** SoC, SoH, Lade-/Entladeleistung, Netz-/Last-/PV-Leistung
- **Grenzwerte:** Anzeige der zulässigen Lade-/Entladeleistung & Ströme laut BMS, Isolationswiderstand
- **DSO & Power-Control:** KPI für Netzbetreiberstatus (Normal/Safety/Abschalten) inkl. wirksamem Limit (%), Statusgründe und Vorwarnung bei deaktivierter Power-Control
- **Einspeisebegrenzung:** Dynamische Begrenzung der Netzeinspeisung (0%/50%/70%) mit Fest- oder Dynamikmodus
- **Netzanschlussabsicherung:** Statische Leistungsgrenzen am Netzanschlusspunkt (z.B. 30 kW) mit Auslastungsanzeige
- **Statusübersicht:** Systemstatus inkl. Statuscode, aktive Alarmmeldungen & Datenquelle (MQTT/Modbus/Simulation)
- **Charts:** SoC-Verlauf & Leistungskanäle der letzten 60 min
- **Rohdaten:** JSON-View der letzten Telemetrie-Payloads, automatisch entprellt

### Analytics (`/analytics`)
- **Performance Summary:** Gewinn, Vollzyklen, Ø SoC der letzten 30 Tage
- **Charts:** Daily Profit & Strategie-Verteilung
- **Optimization History:** Tabelle mit den letzten Runs inkl. Solver-Status

### Forecasts (`/forecasts`)
- **aWATTar Preise**, **PV-/Lastprognosen**, Prophet-basierte Forecasts
- **Interaktive Charts** mit Y-Achsenbegrenzung und Tooltips

### Settings (`/settings`)
- **Strategiemodus:** Auto/Manuell inkl. Sofortumschaltung
- **MQTT-Konfiguration:** Broker, Credentials, Topics mit Testfunktion
- **Modbus-Konfiguration:** Profil-Auswahl (z. B. Hithium, WSTECH), Verbindungstyp, Host/Port/Slave-ID, Poll-Intervall sowie dynamischer Register-Editor inkl. Funktionscode, Skalierung & Alarmdefinitionen
- **Power-Control:** Aktivierung der DSO-/Sicherheitslogik (Trip, Prozentlimit) und optionales Auto-Write der Modbus-Kommandos (`remote_enable`, `active_power_set_w`, `active_power_limit_pct`)
- **Einspeisebegrenzung:** Konfiguration der dynamischen Netzeinspeisungsbegrenzung (Aktivierung, Modus: Fest/Dynamisch, fester Limit-Wert, PV-Integration, zeitbasierte Regeln)
- **Netzanschlussabsicherung:** Konfiguration statischer Leistungsgrenzen am Netzanschlusspunkt (max. Leistung in kW, Monitoring-Aktivierung)

## 📡 **API-Endpunkte**

### **Real-time & State**
```bash
GET  /api/state              # Aktueller Anlagenzustand
GET  /api/events             # SSE für Live-Updates
GET  /api/monitoring/telemetry   # Telemetrie-Historie (Parameter: minutes, limit)
GET  /api/modbus/profiles        # Verfügbare Modbus-Profile (optional: ?profile=key)
```

### **Optimization & Strategy**
```bash
GET  /api/plan               # Optimierungsplan (24h)
GET  /api/forecast           # Prognosen (Preise, PV, Last)
GET  /api/strategies         # Verfügbare Strategien
POST /api/strategy           # Strategie manuell setzen
POST /api/strategy/auto      # Auto-Modus aktivieren
GET  /api/ai/status          # KI-Strategie-Auswahl Status (Parameter: site_id)
POST /api/ai/config          # KI-Strategie-Auswahl aktivieren/deaktivieren (Parameter: site_id)
POST /api/ai/train           # KI-Modell manuell trainieren (Parameter: site_id)
GET  /api/ai/features        # Feature-Importance des KI-Modells (Parameter: site_id)
```

### **Analytics & History** ⭐ NEU (Phase 2)
```bash
GET  /api/history/state           # State History (Parameter: hours)
GET  /api/history/optimization    # Optimization History (Parameter: days)
GET  /api/analytics/daily         # Tägliche Metriken (Parameter: days)
GET  /api/analytics/summary       # Performance-Zusammenfassung (Parameter: days)
```

### **Configuration**
```bash
GET/POST /api/feedin_limitation/config    # Einspeisebegrenzung konfigurieren
GET/POST /api/grid_connection/config      # Netzanschlussabsicherung konfigurieren
GET/POST /api/config/grid_tariffs        # Dynamische Netzentgelte konfigurieren
```

### **User Management & Authentication** ⭐ NEU
```bash
GET  /api/users                    # Liste aller Benutzer (Admin)
POST /api/users                    # Neuen Benutzer erstellen (Admin)
PUT  /api/users/<id>               # Benutzer aktualisieren (Admin)
DELETE /api/users/<id>             # Benutzer löschen (Admin)
POST /api/users/<id>/password      # Passwort ändern (Admin)
GET  /api/notifications            # Benachrichtigungen & Alarme
```

### **Web Pages**
```bash
GET  /                              # Dashboard
GET  /monitoring                    # Monitoring & Telemetrie
GET  /analytics                     # Analytics & Performance
GET  /forecasts                     # Prognosen & Marktdaten
GET  /settings                      # System-Einstellungen
GET  /sites                         # Multi-Site Übersicht (nur bei Multi-Site aktiviert)
GET  /users                         # Benutzerverwaltung (Admin)
GET  /help                          # Hilfe & Anleitungen
GET  /login                         # Anmeldung
GET  /register                      # Registrierung
```

### **Multi-Site Management** ⭐ NEU
```bash
GET  /api/sites                     # Liste aller Standorte
POST /api/sites                     # Neuen Standort erstellen
GET  /api/sites/<id>                # Standort-Details
PUT  /api/sites/<id>                # Standort aktualisieren
DELETE /api/sites/<id>              # Standort löschen
POST /api/sites/<id>/duplicate      # Standort duplizieren
GET  /api/sites/<id>/state          # Standort-spezifischer Zustand
GET  /api/sites/aggregated          # Aggregierte Daten aller Standorte
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
- ✅ **Dynamische Netzentgelte:** Zeitvariable Netzentgelte (NE3-NE7, Hochlastfenster) mit Integration in Optimierung

### ✅ **Phase 2.5: Multi-Site/Multi-BESS** (Abgeschlossen) ⭐ NEU
- ✅ **MultiSiteManager:** Zentrale Verwaltung mehrerer Standorte
- ✅ **Standort-spezifische Konfigurationen:** MQTT, Modbus, BESS-Parameter, Strategien, Einspeisebegrenzung, Netzanschluss, Netzentgelte
- ✅ **Standort-Verwaltung:** CRUD-Operationen für Standorte
- ✅ **Standort-Duplikation:** Kopieren bestehender Standort-Konfigurationen
- ✅ **Aggregierte Daten:** Konsolidierte Ansicht aller Standorte
- ✅ **UI-Integration:** Standort-Auswahl in Settings, dedizierte Standorte-Seite

### ✅ **Phase 3.1: KI-basierte Strategie-Auswahl** (Abgeschlossen) ⭐ NEU
- ✅ **AIStrategySelector:** Random Forest Classifier für intelligente Strategieauswahl
- ✅ **Market Data Service:** Preis-Trends, Volatilität und Marktanalyse
- ✅ **Feature-Extraktion:** SoC, SoH, Temperatur, Marktdaten, Prognosen, Zeitfeatures
- ✅ **Modell-Training:** Automatisches Training mit historischen Optimierungsdaten
- ✅ **Feature-Importance:** Visualisierung der wichtigsten Entscheidungsfaktoren
- ✅ **UI-Integration:** Konfiguration und Monitoring in Settings

### 🔮 **Phase 3: Advanced** (Geplant)
- Erweiterte ML-Prognosen
- VPP Integration
- Grid Services
- Blockchain Integration
- IoT-Sensor-Integration

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

- Erweiterte ML-Prognosen (mehr Datenquellen, bessere Genauigkeit)
- VPP-Integration (Virtuelles Kraftwerk Anbindung)
- Blockchain-Integration (Transparenz und Nachverfolgbarkeit)
- IoT-Sensor-Integration (Zusätzliche Sensoren für erweiterte Überwachung)

📖 **Detaillierte Vorschläge:** Siehe [ZUKUNFTIGE_ERWEITERUNGEN.md](ZUKUNFTIGE_ERWEITERUNGEN.md)

## 📞 **Support**

Bei Fragen oder Problemen:
1. Dokumentation durchlesen
2. Tests ausführen
3. Logs überprüfen
4. Issue erstellen

---

**© 2025 Phoenyra.com by Ing. Heinz Schlagintweit. Alle Rechte vorbehalten.**

*Phoenyra EMS - Intelligentes Energiemanagementsystem v2.0*
