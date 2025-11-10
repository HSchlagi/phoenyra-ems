# 📊 Phoenyra EMS Monitoring System - Dokumentation

## 📋 **Übersicht**

Phoenyra EMS (Energy Management System) ist ein intelligentes, strategiebasiertes Energiemanagementsystem für Batteriespeicher (BESS). Das System bietet ein umfassendes Monitoring- und Dashboard-System für Echtzeit-Visualisierung, Analytics und Performance-Tracking.

## 🎯 **System-Features**

### **🧠 Intelligenz & Optimierung**
- ✅ **4 Strategien:** Arbitrage, Peak Shaving, Self-Consumption, Load Balancing
- ✅ **Linear Programming:** Mathematisch optimale Lösungen mit CVXPY
- ✅ **Adaptive Strategiewahl:** Automatische Auswahl basierend auf Situation
- ✅ **Prophet ML:** Facebook Prophet für präzise Zeitreihen-Prognosen
- ✅ **Wetterbasiert:** OpenWeatherMap für PV-Prognosen

### **📊 Dashboard & Analytics**
- ✅ **Live-Dashboard:** Echtzeit-Visualisierung mit Chart.js
- ✅ **Analytics-Dashboard:** Historische Performance-Analyse
- ✅ **Forecasts-Dashboard:** Prognosen und Marktdaten
- ✅ **Settings-Dashboard:** System-Konfiguration mit MQTT-/Modbus-Assistent
- ✅ **Monitoring-Dashboard:** Live-Telemetrie für SoC, SoH, Spannung, Temperatur, Leistungsgrenzen, Isolationswiderstand, Statuscode & Alarmbits
- ✅ **KPI-Tracking:** Gewinn, Zyklen, SoC, Strategien
- ✅ **Navigation:** Professionelles UI mit Tabs

### **🔌 Integration & API**
- ✅ **REST API:** Vollständige API für alle Funktionen
- ✅ **aWATTar:** Day-Ahead Strompreise (AT/DE)
- ✅ **SQLite DB:** Historische Datenspeicherung
- ✅ **SSE:** Server-Sent Events für Live-Updates
- ✅ **MQTT:** IoT-Integration (optional)
- ✅ **Modbus:** Geräte-Integration via Profilbibliothek (z. B. Hithium ESS) inkl. Skalierung, Alarmbits, RTC-Synchronisation & UI-gestütztem Register-Editor

---

## 🏗️ **Architektur**

### **System-Übersicht**

```
┌─────────────────────────────────────────────────────────────────┐
│                     Phoenyra EMS Monitoring                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌────────────────────┐  ┌────────────────────┐               │
│  │   Web Dashboard    │  │   REST API Layer   │               │
│  │   (Flask + HTML)   │  │   (Flask Routes)   │               │
│  └────────────────────┘  └────────────────────┘               │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐ │
│  │              EMS Core Controller                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │ │
│  │  │   Strategy   │  │ Optimization │  │ Forecasting  │    │ │
│  │  │   Manager    │  │    Engine    │  │    Engine    │    │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘    │ │
│  └───────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Services Layer                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  aWATTar API │  │  Prophet ML  │  │  Weather API │         │
│  │  Price Data  │  │  Forecasting │  │  PV Forecast │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │  SQLite DB   │  │     MQTT     │  │    Modbus    │         │
│  │   History    │  │   Broker     │  │   Client     │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### **Container-Architektur (Docker)**

```
Phoenyra BESS EMS (Port 5050)
├── ems-web (Phoenyra BESS EMS Container)
│   ├── Flask Web Server (Gunicorn)
│   ├── Dashboard UI
│   ├── EMS Core Controller
│   └── REST API
└── mqtt-broker (Phoenyra EMS MQTT Container)
    └── Eclipse Mosquitto MQTT Broker (Port 1883)
```

---

## 📁 **Datei-Struktur**

```
phoenyra-EMS/
├── app/
│   ├── config/
│   │   ├── ems.yaml              # EMS Konfiguration
│   │   ├── modbus_profiles.py    # Modbus-Profilbibliothek
│   │   └── users.yaml            # Benutzer-Datenbank
│   ├── data/
│   │   └── ems_history.db        # SQLite Historien-Datenbank
│   ├── ems/
│   │   ├── controller.py         # EMS Core Controller
│   │   ├── optimizer.py          # Optimierungs-Engine
│   │   ├── strategy_manager.py   # Strategien-Manager
│   │   ├── optimizers/
│   │   │   └── lp_optimizer.py   # Linear Programming Optimizer
│   │   └── strategies/
│   │       ├── arbitrage_strategy.py
│   │       ├── peak_shaving_strategy.py
│   │       ├── self_consumption_strategy.py
│   │       └── load_balancing_strategy.py
│   ├── services/
│   │   ├── prices/
│   │   │   └── awattar.py        # aWATTar Preis-API
│   │   ├── forecast/
│   │   │   ├── simple.py         # Simple Forecasting
│   │   │   ├── prophet_forecaster.py  # Prophet ML Forecasting
│   │   │   └── weather_forecaster.py  # Weather-based Forecasting
│   │   ├── database/
│   │   │   └── history_db.py     # Historien-Datenbank
│   │   └── communication/
│   │       ├── mqtt_client.py    # MQTT Client
│   │       └── modbus_client.py  # Modbus Client
│   ├── web/
│   │   ├── app.py                # Flask Application
│   │   ├── routes.py             # Flask Routes
│   │   ├── static/
│   │   │   ├── css/
│   │   │   │   ├── dashboard.css
│   │   │   │   └── login.css
│   │   │   ├── js/
│   │   │   │   └── app.js        # Dashboard JavaScript
│   │   │   └── logo/
│   │   │       └── Phoenyra_Abstract.png
│   │   └── templates/
│   │       ├── base.html
│   │       ├── login.html
│   │       ├── dashboard.html
│   │       ├── analytics.html
│   │       ├── forecasts.html
│   │       └── settings.html
│   ├── auth/
│   │   └── security.py           # Authentifizierung
│   └── requirements.txt
├── deploy/
│   ├── docker-compose.yml        # Docker Compose Setup
│   ├── Dockerfile                # Docker Image Definition
│   ├── gunicorn.conf.py          # Gunicorn Configuration
│   └── mqtt/
│       └── config/
│           └── mosquitto.conf    # MQTT Broker Config
├── data/
│   └── ems.db                    # Haupt-Datenbank
├── README.md
├── EMS_MODUL_DOKUMENTATION.md
├── DOKUMENTATION-EMS.md          # Diese Datei
└── requirements.txt
```

---

## 🚀 **Installation & Deployment**

### **Option 1: Docker Deployment (Empfohlen)**

```bash
# Container bauen und starten
cd deploy
docker-compose up -d --build

# Logs anzeigen
docker-compose logs -f ems-web

# Container stoppen
docker-compose down
```

**Zugriff:** http://localhost:5050  
**Login:** admin / admin123

### **Option 2: Lokale Installation**

```bash
# In virtueller Umgebung installieren
cd app
pip install -r requirements.txt

# Server starten
python -m flask --app web.app run --debug --port 5000
```

**Zugriff:** http://localhost:5000  
**Login:** admin / admin123

---

## 📊 **Dashboard-Features**

### **1. Haupt-Dashboard (`/`)**

Echtzeit-Monitoring und KPI-Überwachung:

#### **KPI-Cards:**
- **State of Charge (SoC):** Aktueller Batteriezustand (0-100%)
- **BESS Power:** Aktuelle Lade-/Entladeleistung (kW)
- **Active Strategy:** Aktuell verwendete Strategie
- **Expected Profit:** Erwarteter Gewinn (24h Forecast)

#### **Charts:**
- **24h Optimization Plan:** BESS Power, PV, Load Trends
- **Price & SoC Forecast:** Strompreise und geplanter SoC-Verlauf

#### **System Status:**
- Grid Power, PV Generation, Load, Current Price

#### **Live-Updates:**
- Server-Sent Events (SSE) für Echtzeit-Updates
- Automatische Chart-Aktualisierung alle 2 Sekunden

### **2. Monitoring Dashboard (`/monitoring`)**

Live-Telemetrie aus Modbus/MQTT oder Simulation inklusive BMS-Metadaten:

- **KPI-Kacheln:** SoC, SoH, Lade-/Entladeleistung, Batteriespannung, Temperatur, Isolationswiderstand
- **Grenzwerte:** Anzeige der vom BMS gelieferten max. Lade-/Entladeleistung & Ströme für eine sichere Fahrweise
- **Charts:** SoC-Verlauf & Leistungskanäle (PV, Load, Grid, BESS) der letzten 60 Minuten
- **Status & Rohdaten:** Systemstatus-Text + Code, aktive Alarmmeldungen, Datenquelle sowie JSON-View der aktuellen Telemetrie (entprellt)
- **Telemetrie-Puffer:** autom. Entprellung & Zusammenführung unterschiedlicher Quellen (MQTT/Modbus/Simulation)

### **3. Analytics Dashboard (`/analytics`)**

Performance-Analysen und historische Daten:

#### **Performance Summary:**
- Gesamt-Gewinn (30 Tage)
- Ø Täglicher Gewinn
- Vollzyklen (Batterie)
- Ø SoC (durchschnittlich)

#### **Charts:**
- **Täglicher Gewinn:** Bar Chart der täglichen Gewinne
- **Strategie-Verteilung:** Pie Chart der Strategienutzung

#### **Optimization History:**
- Letzte 15 Optimierungen
- Zeit, Strategie, Gewinn, Status, Solver

### **4. Forecasts Dashboard (`/forecasts`)**

Prognosen und Marktdaten:

- Strompreis-Prognosen
- PV-Erzeugungsprognosen
- Lastprognosen
- Prophet ML-Vorhersagen
- Wetterbasierte PV-Prognosen

### **5. Settings Dashboard (`/settings`)**

System-Konfiguration mit interaktivem Assistenten:

- EMS-Parameter & Strategiemodus (Auto/Manuell)
- Prognose-Optionen & BESS-Constraints
- **MQTT-Konfiguration:** Broker, Credentials, Topics, Verbindungstest
- **Modbus-Konfiguration:** Profil-Auswahl (z. B. Hithium ESS), Verbindungstyp (TCP/RTU), Host/Port/Slave-ID, Poll-Intervall, dynamischer Register-Editor inkl. Funktionscode, Skalierung & Alarmdefinitionen
- **Register-Mapping:** Werte werden direkt aus Profilen übernommen und können überschrieben werden (inkl. Anzeige der Skalierung/Offsets)

---

## 🔌 **API-Endpunkte**

### **Real-time & State**

```bash
GET  /api/state              # Aktueller Anlagenzustand
GET  /api/events             # SSE für Live-Updates
GET  /api/monitoring/telemetry   # Telemetrie-Historie (Parameter: minutes, limit)
```

### **Optimization & Strategy**

```bash
GET  /api/plan               # Optimierungsplan (24h)
GET  /api/forecast           # Prognosen (Preise, PV, Last)
GET  /api/strategies         # Verfügbare Strategien
POST /api/strategy           # Strategie manuell setzen
POST /api/strategy/auto      # Auto-Modus aktivieren
```

### **Analytics & History**

```bash
GET  /api/history/state           # State History (Parameter: hours)
GET  /api/history/optimization    # Optimization History (Parameter: days)
GET  /api/analytics/daily         # Tägliche Metriken (Parameter: days)
GET  /api/analytics/summary       # Performance-Zusammenfassung (Parameter: days)
```

### **Configuration**

```bash
GET  /api/mqtt/config        # MQTT Konfiguration
POST /api/mqtt/config        # MQTT Konfiguration aktualisieren
POST /api/mqtt/test          # MQTT Verbindung testen
GET  /api/modbus/config      # Modbus Konfiguration
POST /api/modbus/config      # Modbus Konfiguration aktualisieren
POST /api/modbus/test        # Modbus Verbindung testen
GET  /api/modbus/profiles    # Verfügbare Modbus-Profile (optional: ?profile=<key> für Details)
```

---

## 🎯 **Strategien**

### **1. Arbitrage**
Kauft Strom bei niedrigen Preisen, verkauft bei hohen. Nutzt Day-Ahead Preisunterschiede optimal aus.

**Optimierung:** Linear Programming (CVXPY)  
**Ergebnis:** Maximaler Gewinn durch Preisarbitrage

### **2. Peak Shaving**
Reduziert Lastspitzen automatisch. Identifiziert und glättet Peaks im Lastprofil.

**Anwendung:** Industrie & Gewerbe  
**Ergebnis:** 20-30% Lastspitzen-Reduktion

### **3. Self-Consumption**
Maximiert PV-Eigenverbrauch. Speichert Überschuss, nutzt bei Bedarf.

**Anwendung:** PV-Anlagen  
**Ergebnis:** >80% Eigenverbrauchsquote

### **4. Load Balancing**
Glättet Lastschwankungen und Volatilität. Reduziert Netzbelastung durch Ausgleich.

**Methode:** Moving Average + BESS-Kompensation  
**Ergebnis:** Geglättetes Lastprofil, reduzierte Gradienten

---

## 🔧 **Konfiguration**

### **EMS-Konfiguration (`config/ems.yaml`)**

```yaml
bess:
  efficiency_charge: 0.95
  efficiency_discharge: 0.95
  energy_capacity_kwh: 200.0
  power_charge_max_kw: 100.0
  power_discharge_max_kw: 100.0
  soc_max_percent: 90.0
  soc_min_percent: 10.0

ems:
  mode: auto
  optimization_interval_minutes: 15
  timestep_s: 2

strategies:
  selection_mode: auto
  manual_strategy: arbitrage
  switch_threshold: 0.15

prices:
  demo_mode: true
  provider: awattar
  region: AT

mqtt:
  enabled: true
  broker_host: localhost
  broker_port: 1883

modbus:
  enabled: false
  profile: hithium_ess_5016
  connection_type: tcp
  host: localhost
  port: 502
  slave_id: 1
  timeout: 3.0
  retries: 3
  poll_interval_s: 2.0
  status_codes:
    "0": Initialisierung
    "1": Laden
    "2": Entladen
    "3": Bereit
    "5": Ladesperre
    "6": Entladesperre
    "7": Lade- & Entladesperre
    "8": Fehler
  registers:
    soc_percent:
      address: 4
      function: 4
      scale: 1.0
      unit: "%"
      description: System State of Charge
    voltage_v:
      address: 2
      function: 4
      scale: 0.1
      unit: V
      description: System-Gesamtspannung
    max_charge_power_kw:
      address: 33
      function: 4
      scale: 0.1
      unit: kW
      description: Zulässige maximale Ladeleistung
    status_code:
      address: 43
      function: 4
      description: BMS Systemstatus
```

> 💡 **Hinweis:** Profile liefern vollständige Registerdefinitionen inkl. Funktionscode, Skalierung, Offsets & Alarmbits. Über das Settings-Dashboard können Werte überschrieben, Profile gewechselt oder eigene Register ergänzt werden. Alle Änderungen landen direkt in `config/ems.yaml`.

### **Modbus-Profilbibliothek**

- Basis-Datei: `app/config/modbus_profiles.py`
- Enthält vordefinierte Profile (z. B. `hithium_ess_5016`) mit:
  - Register-Definitionen (Adresse, Funktionscode, Datentyp, Skalierung, Offset, Einheit, Kategorie)
  - Alarmdefinitionen (Discrete Inputs mit Bit-Mapping)
  - Statuscode-Mapping (Code → Beschreibung)
  - Standard-Verbindungsparameter (Port, Slave-ID, Poll-Intervall)
- Erweiterung: Weitere Hersteller können durch Ergänzung eines neuen Eintrags im Dictionary `MODBUS_PROFILES` hinzugefügt werden.
- UI-Integration: Profile stehen im Settings-Dashboard zur Auswahl; beim Wechsel wird das Register-Mapping automatisch aktualisiert.

### **RTC-Synchronisation**

- Beim ersten erfolgreichen Modbus-Verbindungsaufbau synchronisiert das EMS die Echtzeituhr des BMS automatisch mit UTC (Register 524–529).
- Wird die Verbindung unterbrochen, erfolgt die Synchronisation erneut nach dem nächsten erfolgreichen Connect.

---

## 🐳 **Docker Container**

### **Verfügbare Container**

| Container | Port | Beschreibung |
|-----------|------|--------------|
| `phoenyra-bess-ems` | 5050 | EMS Web Interface & API |
| `phoenyra-ems-mqtt` | 1883 | MQTT Broker |

### **Docker Befehle**

```bash
# Container starten
docker-compose -f deploy/docker-compose.yml up -d

# Logs anzeigen
docker-compose -f deploy/docker-compose.yml logs -f

# Container neu bauen
docker-compose -f deploy/docker-compose.yml up -d --build

# Container stoppen
docker-compose -f deploy/docker-compose.yml down

# Alle Container anzeigen
docker ps --filter "name=phoenyra"
```

### **Volumes**

- `../data` → `/app/data`: Datenbank und historische Daten
- `../app/config` → `/app/config:ro`: Konfiguration (Read-Only)
- `./logs` → `/app/logs`: Anwendungslogs
- `./mqtt/data` → `/mosquitto/data`: MQTT Persistenz
- `./mqtt/log` → `/mosquitto/log`: MQTT Logs

---

## 📈 **Monitoring & Logging**

### **Live-Monitoring**

Das Dashboard bietet:
- **Echtzeit-Updates:** Server-Sent Events (SSE)
- **Interaktive Charts:** Chart.js Visualisierungen
- **KPI-Tracking:** Gewinn, Zyklen, SoC, Strategien
- **Status-Badges:** Live-Systemstatus

### **Historische Daten**

SQLite-Datenbank speichert:
- State History (SoC, Power, Temperature, etc.)
- Optimization History (Strategie, Gewinn, Status)
- Daily Metrics (tägliche Metriken)
- Performance Summary (Performance-Zusammenfassung)

### **Logging**

Logs werden geschrieben in:
- Console (stdout)
- Log-Files (optional)
- Docker Logs (`docker logs phoenyra-bess-ems`)

---

## 🔐 **Sicherheit**

### **Authentifizierung**

- **Login:** Session-basiert
- **Benutzer:** Konfigurierbar in `config/users.yaml`
- **Rollensystem:** admin, viewer

### **CSP (Content Security Policy)**

Das System verwendet Content Security Policy für:
- Script-Sicherheit
- XSS-Schutz
- Ressourcen-Kontrolle

---

## 🧪 **Testing**

```bash
# Alle Tests ausführen
python -m pytest tests/

# Spezifische Tests
python -m pytest tests/test_ems_controller.py
python -m pytest tests/test_strategies.py
python -m pytest tests/test_api.py
```

---

## 📊 **Performance**

### **Optimierungs-Performance**

- **Optimierungszeit:** < 1 Sekunde (Linear Programming)
- **Forecast-Zeit:** < 5 Sekunden (Prophet ML)
- **Update-Frequenz:** 2 Sekunden (Live-Dashboard)
- **DB-Queries:** < 100ms (SQLite)

### **Skalierbarkeit**

- **Multi-Site-Support:** Konfigurierbar
- **Historical Data:** SQLite-Datenbank
- **Forecasting:** Prophet ML + Weather API

---

## 🔮 **Zukünftige Erweiterungen**

### **Phase 3: Advanced (Geplant)**
- Multi-Asset Management
- VPP Integration
- Grid Services
- Blockchain Integration
- Advanced Analytics Dashboard
- Mobile App

---

## 📞 **Support & Dokumentation**

### **Verfügbare Dokumentation**

- **README.md:** Hauptdokumentation
- **EMS_MODUL_DOKUMENTATION.md:** Vollständige EMS-Dokumentation
- **DOKUMENTATION-EMS.md:** Diese Datei (Monitoring-System)
- **app/INSTALLATION.md:** Installationsanleitung
- **deploy/README.md:** Docker-Setup Details

### **API-Dokumentation**

- **OpenAPI Spec:** `/api/openapi.yaml`
- **REST API:** Alle Endpunkte dokumentiert

---

## 📝 **Changelog**

### **Version 2.0 (Aktuell)**
- ✅ Docker-Integration
- ✅ MQTT Broker Integration
- ✅ Datum/Zeit im Header
- ✅ Footer mit Copyright
- ✅ Analytics Dashboard
- ✅ Historische Datenbank
- ✅ Prophet ML Forecasting
- ✅ Weather-based PV Forecasting
- ✅ 4 Strategien implementiert

### **Version 1.0**
- Grundlegendes EMS-System
- Arbitrage, Peak Shaving, Self-Consumption Strategien
- Basis-Dashboard
- aWATTar Integration

---

**© 2025 Phoenyra.com by Ing. Heinz Schlagintweit. Alle Rechte vorbehalten.**

*Phoenyra EMS - Intelligentes Energiemanagementsystem*

