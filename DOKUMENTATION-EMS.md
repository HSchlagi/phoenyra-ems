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
- ✅ **Settings-Dashboard:** System-Konfiguration mit MQTT-/Modbus-Assistent & Power-Control Setup
- ✅ **Monitoring-Dashboard:** Live-Telemetrie (SoC, SoH, Spannung, Temperatur, Leistungsgrenzen, Isolationswiderstand, Statuscode & Alarmbits) inkl. DSO-Power-Control-KPI (Normal/Safety/Abschalten mit Limit), Einspeisebegrenzung, Netzanschlussabsicherung & Powerflow-Diagramm mit Langzeitdaten (60 min, Tag, Woche, Monat, Jahr)
- ✅ **KPI-Tracking:** Gewinn, Zyklen, SoC, Strategien
- ✅ **Navigation:** Professionelles UI mit Tabs
- ✅ **Langzeitdaten:** Zeitbereichsauswahl für Monitoring-Charts und Powerflow (60 min, Tag, Woche, Monat, Jahr)

### **👥 Multiuser & Sicherheit** ⭐ NEU
- ✅ **Rollenbasierte Zugriffskontrolle:** Admin, Operator, Viewer
- ✅ **Benutzerverwaltung:** Vollständige CRUD-Operationen für Benutzer
- ✅ **Registrierung:** Selbstregistrierung für neue Benutzer
- ✅ **Passwort-Sicherheit:** Scrypt-basiertes Hashing
- ✅ **Session-Management:** Sichere Session-Verwaltung
- ✅ **Benachrichtigungen:** System-Alarme und Statusmeldungen (Modbus-Alarme, DSO-Abschaltanweisungen, Sicherheitsalarme, Leistungsbegrenzungen, Einspeisebegrenzungen, Netzanschlussauslastung, Optimierungsfehler)
- ✅ **Hilfe & Anleitungen:** Umfassende Dokumentation im System
- ✅ **Benutzerinfo:** Anzeige der eigenen Benutzerdaten im Dropdown-Menü

### **🔌 Integration & API**
- ✅ **REST API:** Vollständige API für alle Funktionen
- ✅ **aWATTar:** Day-Ahead Strompreise (AT/DE)
- ✅ **SQLite DB:** Historische Datenspeicherung
- ✅ **SSE:** Server-Sent Events für Live-Updates
- ✅ **MQTT:** IoT-Integration (optional)
- ✅ **Modbus & Power-Control:** Geräte-Integration via Profilbibliothek (z. B. Hithium ESS, WSTECH PCS) inkl. Skalierung, Alarmbits, RTC-Synchronisation, UI-gestütztem Register-Editor sowie Power-Control-Logik (Trip, Prozentlimit, Auto-Write)

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
Phoenyra BESS EMS (Port 8080)
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
│   │   ├── power_control.py      # Power-Control / DSO-Logik
│   │   ├── feedin_limitation.py  # Einspeisebegrenzung
│   │   ├── optimizer.py          # Optimierungs-Engine
│   │   ├── strategy_manager.py   # Strategien-Manager
│   │   ├── optimizers/
│   │   │   └── lp_optimizer.py   # Linear Programming Optimizer
│   │   └── strategies/
│   │       ├── base_strategy.py
│   │       ├── arbitrage_strategy.py
│   │       ├── peak_shaving_strategy.py
│   │       ├── self_consumption_strategy.py
│   │       └── load_balancing_strategy.py
│   ├── services/
│   │   ├── communication/
│   │   │   ├── mqtt_client.py    # MQTT Client
│   │   │   └── modbus_client.py  # Modbus Client
│   │   ├── database/
│   │   │   ├── history_db.py     # Historien-Datenbank
│   │   │   └── user_db.py         # Benutzer-Datenbank
│   │   ├── forecast/
│   │   │   ├── simple.py          # Einfache Prognosen
│   │   │   ├── prophet_forecaster.py  # Prophet ML
│   │   │   └── weather_forecaster.py  # Wetterbasierte PV-Prognosen
│   │   └── prices/
│   │       ├── awattar.py         # aWATTar API
│   │       └── epex.py            # EPEX API
│   │   └── grid_tariff.py         # Dynamische Netzentgelte
│   └── web/
│       ├── app.py                 # Flask App
│       ├── routes.py              # Web & API Routes
│       ├── templates/             # HTML Templates
│       │   ├── base.html
│       │   ├── dashboard.html
│       │   ├── monitoring.html
│       │   ├── analytics.html
│       │   ├── forecasts.html
│       │   ├── settings.html
│       │   ├── users.html         # Benutzerverwaltung (Admin)
│       │   ├── help.html          # Hilfe & Anleitungen
│       │   ├── login.html         # Anmeldung
│       │   └── register.html      # Registrierung
│       └── static/
│           ├── css/
│           │   └── dashboard.css
│           └── js/
│               ├── app.js
│               └── monitoring.js
├── deploy/
│   ├── docker-compose.yml        # Docker Compose Setup
│   ├── Dockerfile                # Docker Image
│   └── mqtt/                     # MQTT Broker Config
└── data/                         # Persistente Daten
```

---

## 🎨 **Dashboard Features**

### **1. Main Dashboard (`/`)**

Echtzeit-Monitoring und KPI-Überwachung:

#### **KPI-Cards:**
- **State of Charge (SoC):** Aktueller Batterieladezustand in %
- **BESS Power:** Aktuelle Lade-/Entladeleistung in kW
- **Active Strategy:** Aktuell aktive Strategie (Arbitrage, Peak Shaving, etc.)
- **Expected Profit:** Erwarteter Gewinn für 24h

#### **Charts:**
- **24h Optimization Plan:** BESS, PV, Load Leistung über 24 Stunden
- **Price + SoC Forecast:** Strompreis und SoC-Prognose

#### **Live-Updates:**
- Server-Sent Events (SSE) für Echtzeit-Updates
- Automatische Chart-Aktualisierung alle 2 Sekunden

### **2. Monitoring Dashboard (`/monitoring`)** ⭐ ERWEITERT

Live-Telemetrie und Langzeit-Analyse:

Live-Telemetrie aus Modbus/MQTT oder Simulation inklusive BMS-Metadaten:

- **KPI-Kacheln:** SoC, SoH, Lade-/Entladeleistung, Batteriespannung, Temperatur, Isolationswiderstand
- **Grenzwerte:** Anzeige der vom BMS gelieferten max. Lade-/Entladeleistung & Ströme für eine sichere Fahrweise
- **Einspeisebegrenzung:** KPI für dynamische Begrenzung der Netzeinspeisung (aktueller Limit-Wert in %, Modus: Aus/Fest/Dynamisch)
- **Netzanschlussabsicherung:** KPIs für statische Leistungsgrenzen am Netzanschlusspunkt (max. Leistung in kW) und aktuelle Auslastung (in %)
- **DSO & Power-Control:** KPI für Netzbetreiberstatus (Normal/Safety/Abschalten) inkl. wirksamem Limit (%), Statusgründe und Vorwarnung bei deaktivierter Power-Control
- **Langzeitdaten:** Zeitbereichsauswahl für alle Charts (60 min, Tag, Woche, Monat, Jahr)
- **Charts:** SoC-Verlauf & Leistungskanäle (PV, Load, Grid, BESS) mit historischen Daten basierend auf gewähltem Zeitbereich
- **Powerflow-Diagramm:** Sankey-Diagramm zur Visualisierung der Energieflüsse (PV, Batterie, Netz, Last) mit Langzeitdaten-Unterstützung (60 min, Tag, Woche, Monat, Jahr)
- **Synchronisierte Zeitbereiche:** Zeitbereichsauswahl für Charts und Powerflow sind bidirektional synchronisiert
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
- **Modbus-Konfiguration:** Profil-Auswahl (z. B. Hithium ESS), Verbindungstyp (TCP/RTU), Host/Port/Slave-ID, Poll-Intervall, dynamischer Register-Editor inkl. Funktionscode, Skalierung & Alarmdefinitionen
- **Register-Mapping:** Werte werden direkt aus Profilen übernommen und können überschrieben werden (inkl. Anzeige der Skalierung/Offsets)
- **Einspeisebegrenzung:** Konfiguration der dynamischen Netzeinspeisungsbegrenzung (Aktivierung, Modus: Fest/Dynamisch, fester Limit-Wert, PV-Integration, zeitbasierte Regeln)
- **Netzanschlussabsicherung:** Konfiguration statischer Leistungsgrenzen am Netzanschlusspunkt (max. Leistung in kW, Monitoring-Aktivierung)
- **Dynamische Netzentgelte:** Konfiguration zeitvariabler Netzentgelte (NE3-NE7 Netzebenen, Hochlastfenster, Basis-Tarif)

### **6. Benutzerverwaltung (`/users`)** ⭐ NEU (Admin)

Vollständige Benutzerverwaltung für Administratoren:

- **Benutzerliste:** Übersicht aller registrierten Benutzer
- **Benutzer erstellen:** Neuen Benutzer mit Rollen (Admin, Operator, Viewer) anlegen
- **Benutzer bearbeiten:** Persönliche Daten, Rollen, Berechtigungen und Passwörter ändern
- **Benutzer löschen:** Benutzer entfernen
- **Rollenbasierte Zugriffskontrolle:** Admin, Operator, Viewer mit unterschiedlichen Berechtigungen

### **7. Hilfe & Anleitungen (`/help`)** ⭐ NEU

Umfassende Systemdokumentation:

- **Dashboard-Übersicht:** Erklärung aller Dashboard-Bereiche
- **Optimierungsstrategien:** Detaillierte Beschreibung der Strategien
- **Alarme & Sicherheit:** Informationen zu Alarmen und Sicherheitsfunktionen
- **Technische Details:** System-Architektur, Optimierung, Sicherheit
- **Support & Kontakt:** Kontaktinformationen

### **8. Benutzer-Menü** ⭐ NEU

Dropdown-Menü im Navigationsbereich:

- **Benutzerinfo:** Anzeige der eigenen Benutzerdaten (Name, E-Mail, Rolle, Berechtigungen)
- **Benachrichtigungen:** System-Alarme und Statusmeldungen (Modbus-Alarme, DSO-Abschaltanweisungen, Sicherheitsalarme, Leistungsbegrenzungen, etc.)
- **Hilfe & Anleitungen:** Link zur Hilfe-Seite
- **Admin-Dashboard:** Schnellzugriff für Administratoren
- **Benutzer-Verwaltung:** Link zur Benutzerverwaltung (nur Admin)
- **Abmelden:** Logout-Funktion

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
GET  /users                         # Benutzerverwaltung (Admin)
GET  /help                          # Hilfe & Anleitungen
GET  /login                         # Anmeldung
GET  /register                      # Registrierung
POST /login                         # Anmeldung durchführen
POST /register                      # Registrierung durchführen
GET  /logout                        # Abmelden
```

---

## 🔧 **Konfiguration**

### **EMS-Konfiguration (`app/config/ems.yaml`)**

Die Hauptkonfigurationsdatei enthält alle wichtigen Parameter:

```yaml
# BESS-Parameter
bess:
  capacity_kwh: 50.0
  max_power_kw: 30.0
  efficiency: 0.95

# Strategie-Konfiguration
strategy:
  mode: auto  # auto | manual
  current: null

# Prognose-Konfiguration
forecast:
  use_prophet: false
  use_weather: false

# MQTT-Konfiguration
mqtt:
  enabled: true
  broker: localhost
  port: 1883
  topics:
    telemetry: phoenyra/bess/telemetry

# Modbus-Konfiguration
modbus:
  enabled: true
  profile: hithium_ess_5016
  connection_type: tcp
  host: 192.168.1.100
  port: 502
  slave_id: 1
  poll_interval_seconds: 2

# Power-Control & DSO-Logik
power_control:
  enabled: false
  dso_trip_register: null
  safety_alarm_register: null
  auto_write: false

# Einspeisebegrenzung
feedin_limitation:
  enabled: false
  mode: off  # off | fixed | dynamic
  fixed_limit_pct: 70.0
  pv_integration_enabled: false
  dynamic_rules: []

# Netzanschlussabsicherung
grid_connection:
  max_power_kw: 30.0
  monitoring_enabled: true
```

---

## 🔌 **Modbus-Integration**

### **Profilbibliothek**

- Basis-Datei: `app/config/modbus_profiles.py`
- Enthält vordefinierte Profile (z. B. `hithium_ess_5016`) mit:
  - Register-Definitionen (Adresse, Funktionscode, Datentyp, Skalierung, Offset, Einheit, Kategorie)
  - Alarmdefinitionen (Discrete Inputs mit Bit-Mapping)
  - Statuscode-Mapping (Code → Beschreibung)
  - Standard-Verbindungsparameter (Port, Slave-ID, Poll-Intervall)
- Erweiterung: Weitere Hersteller können durch Ergänzung eines neuen Eintrags im Dictionary `MODBUS_PROFILES` hinzugefügt werden.
- UI-Integration: Profile stehen im Settings-Dashboard zur Auswahl; beim Wechsel wird das Register-Mapping automatisch aktualisiert.

### **Power-Control & DSO-Logik**

- Konfiguration über `power_control` in `app/config/ems.yaml` (standardmäßig deaktiviert). Enthält Mapping für `dso_trip`, `safety_alarm`, `dso_limit_pct`, maximale Leistung und Auto-Write-Optionen.
- Implementierung in `app/ems/power_control.py`: wertet Signale aus, erstellt `PowerControlDecision` (wirksamer Sollwert, Limit-Grund) und bereitet Modbus-Schreibkommandos vor.
- `app/ems/controller.py` integriert die Entscheidungen in den Fahrplan-Setpoint und schreibt resultierende Felder in `PlantState` (`remote_shutdown_requested`, `active_power_limit_w`, `power_limit_reason`).
- Monitoring zeigt den aktuellen Status (Normal/Safety/Abschalten) samt Limit (%) und Grund; ermöglicht schnelle Diagnose bei Netzbetreiber-Eingriffen.
- Optionales `auto_write`: schreibt `remote_enable`, `active_power_set_w` und `active_power_limit_pct` auf das ausgewählte Modbus-Profil (z. B. WSTECH PCS).

### **Einspeisebegrenzung (Feed-in Limitation)**

- Konfiguration über `feedin_limitation` in `app/config/ems.yaml`. Ermöglicht dynamische Begrenzung der Netzeinspeisung basierend auf festen Prozentsätzen (0%, 50%, 70%) oder zeitbasierten Regeln.
- Implementierung in `app/ems/feedin_limitation.py`: `FeedinLimitationManager` verwaltet die Logik zur Berechnung des aktuellen Limits und passt den Optimierungsplan entsprechend an.

### **Dynamische Netzentgelte** ⭐ NEU

Zeitvariable Netzentgelte für verschiedene Netzebenen (NE3-NE7):

- **Tarifstrukturen:** Vordefinierte Tarife für verschiedene Netzebenen (NE3: Höchstspannung, NE4: Hochspannung, NE5: Mittelspannung, NE6: Niederspannung, NE7: Niederspannung)
- **Hochlastfenster:** Konfigurierbare Zeitfenster mit Multiplikatoren für erhöhte Tarife
- **Integration:** Automatische Berücksichtigung in der Optimierungsberechnung
- **Implementierung:** `app/services/grid_tariff.py` - `GridTariffService` verwaltet Tarifkonfigurationen und berechnet Kosten

### **Multiuser-System** ⭐ NEU

Lokale SQLite-basierte Benutzerverwaltung:

- **Datenbank:** `app/services/database/user_db.py` - `UserDatabase` und `UserManagementService`
- **Tabellen:** `users` (Benutzerdaten) und `user_sites` (Standort-Zuordnungen)
- **Rollen:** Admin (Vollzugriff), Operator (Lesen & Schreiben), Viewer (Nur Lesen)
- **Passwort-Sicherheit:** Scrypt-basiertes Hashing mit `werkzeug.security`
- **Migration:** Automatische Migration von `users.yaml` zu SQLite-Datenbank
- **API:** Vollständige CRUD-Operationen für Benutzerverwaltung

### **Langzeitdaten & Historische Analyse** ⭐ NEU

Zeitbereichsauswahl für Monitoring und Powerflow:

- **Zeitbereiche:** 60 min, Tag (24h), Woche (7 Tage), Monat (30 Tage), Jahr (365 Tage)
- **Datenquellen:** 
  - Kurze Zeiträume (≤ 60 min): Telemetrie-API (`/api/monitoring/telemetry`)
  - Längere Zeiträume (> 60 min): History-Datenbank (`/api/history/state`)
- **Synchronisation:** Bidirektionale Synchronisation zwischen Chart- und Powerflow-Zeitbereich
- **Powerflow:** Unterstützung für Langzeitdaten mit aggregierten Energieflüssen über längere Perioden
- **Modi:**
  - `off`: Einspeisebegrenzung deaktiviert
  - `fixed`: Fester Prozentsatz (z.B. 70% der PV-Leistung)
  - `dynamic`: Zeitbasierte Regeln mit verschiedenen Limits zu unterschiedlichen Tageszeiten
- **PV-Integration:** Optional kann die PV-Prognose in die Limit-Berechnung einbezogen werden.
- **Monitoring:** KPI zeigt aktuellen Limit-Wert (%) und aktiven Modus auf der Monitoring-Seite.
- **API:** `GET/POST /api/feedin_limitation/config` für Konfiguration über die Settings-UI.

### **Netzanschlussabsicherung (Grid Connection Security)**

- Konfiguration über `grid_connection` in `app/config/ems.yaml`. Definiert statische Leistungsgrenzen am Netzanschlusspunkt für Einspeisung und Bezug.
- **Maximale Leistung:** Konfigurierbare Obergrenze (z.B. 30 kW) für die Gesamtleistung am Netzanschlusspunkt.
- **Monitoring:** KPI zeigt maximale Leistungsgrenze (kW) und aktuelle Auslastung (%) mit Farbcodierung (grün < 50%, gelb 50-80%, rot > 80%).
- **Integration:** Die Grenzen werden direkt in `app/ems/controller.py` als zusätzliche Constraints in der Optimierungslogik berücksichtigt.
- **API:** `GET/POST /api/grid_connection/config` für Konfiguration über die Settings-UI.

### **RTC-Synchronisation**

- Beim ersten erfolgreichen Modbus-Verbindungsaufbau synchronisiert das EMS die Echtzeituhr des BMS automatisch mit UTC (Register 524–529).
- Wird die Verbindung unterbrochen, erfolgt die Synchronisation erneut nach dem nächsten erfolgreichen Connect.

---

## 🐳 **Docker Container**

### **Verfügbare Container**

| Container | Port | Beschreibung |
|-----------|------|--------------|
| `phoenyra-bess-ems` | 8080 | Flask Web Server mit EMS Core |
| `phoenyra-ems-mqtt` | 1883 | MQTT Broker (Eclipse Mosquitto) |

### **Container starten:**

```bash
cd deploy
docker-compose up -d --build
```

### **Container stoppen:**

```bash
cd deploy
docker-compose down
```

### **Logs anzeigen:**

```bash
docker-compose -f deploy/docker-compose.yml logs -f ems-web
```

### **Volumes**

- `../data:/app/data` - Persistente Datenbanken
- `../app/config:/app/config:rw` - Konfigurationsdateien (read-write)
- `../app/web/templates:/app/web/templates:ro` - HTML Templates (read-only)
- `../app/web/static:/app/web/static:ro` - CSS/JS Dateien (read-only)
- `./logs:/app/logs` - Log-Dateien

---

## 📈 **Monitoring & Logging**

### **Live-Monitoring**

- **Dashboard:** Echtzeit-Visualisierung aller KPIs
- **Charts:** Live-Updates alle 2 Sekunden
- **Telemetrie:** Automatische Entprellung und Zusammenführung
- **Status:** Systemstatus mit Alarmmeldungen
- **KPI-Tracking:** Gewinn, Zyklen, SoC, Strategien

### **Logging**

- **Flask-Logs:** Standard Python-Logging
- **EMS-Logs:** Controller-Logs mit Timestamps
- **Modbus-Logs:** Verbindungs- und Register-Logs
- **MQTT-Logs:** Broker-Verbindungs-Logs

---

## 🚀 **Schnellstart**

### **1. Installation**

```bash
cd app
pip install -r requirements.txt
```

### **2. Konfiguration**

Bearbeiten Sie `app/config/ems.yaml` nach Ihren Bedürfnissen.

### **3. Starten**

```bash
python -m flask --app web.app run --debug --port 5000
```

### **4. Dashboard öffnen**

```
http://localhost:5000
Login: admin / admin123
```

---

## 📚 **Weitere Dokumentation**

- **README.md:** Hauptdokumentation
- **EMS_MODUL_DOKUMENTATION.md:** Vollständige EMS-Dokumentation
- **DOKUMENTATION-EMS.md:** Diese Datei (Monitoring-System)
- **app/INSTALLATION.md:** Installationsanleitung
- **deploy/README.md:** Docker-Setup Details

---

**© 2025 Phoenyra.com by Ing. Heinz Schlagintweit. Alle Rechte vorbehalten.**

_Phoenyra EMS - Intelligentes Energiemanagementsystem v2.0_
