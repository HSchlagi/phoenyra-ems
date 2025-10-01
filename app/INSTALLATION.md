# Phoenyra EMS - Installation & Quick Start

## 📋 Voraussetzungen

- Python 3.10 oder höher
- pip (Python Package Manager)

## 🚀 Installation

### 1. Repository klonen / Ordner öffnen

```bash
cd phoenyra-EMS/app
```

### 2. Python-Dependencies installieren

```bash
pip install -r requirements.txt
```

**Wichtig:** Wenn CVXPY Probleme macht, installiere es separat:

```bash
# Windows
pip install cvxpy

# Linux/Mac
pip install cvxpy
```

Falls CVXPY nicht verfügbar ist, verwendet das System automatisch einen Fallback-Algorithmus.

### 3. Konfiguration anpassen (optional)

Passe `config/ems.yaml` an deine Bedürfnisse an:

```yaml
bess:
  energy_capacity_kwh: 200.0  # Batteriekapazität
  power_charge_max_kw: 100.0   # Max Ladeleistung
  power_discharge_max_kw: 100.0 # Max Entladeleistung

prices:
  demo_mode: true  # false für echte aWATTar API
  region: AT       # AT oder DE
```

## ▶️ Starten

### Entwicklungsmodus

```bash
cd app
python -m flask --app web.app run --debug --port 5000
```

### Produktionsmodus (mit Gunicorn)

```bash
cd app
gunicorn -c ../deploy/gunicorn.conf.py web.app:app
```

### Mit Docker

```bash
cd deploy
docker-compose up -d
```

## 🌐 Zugriff

- **Web-Interface:** http://localhost:5000
- **Login:** 
  - Username: `admin`
  - Password: `admin123`

## 📊 Features

### Automatische Optimierung

Das EMS führt automatisch alle 15 Minuten eine Optimierung durch:

1. **Holt Prognosedaten:**
   - Day-Ahead Strompreise (aWATTar)
   - PV-Erzeugungsprognose
   - Lastprognose

2. **Wählt optimale Strategie:**
   - **Arbitrage:** Bei hoher Preisvolatilität
   - **Peak Shaving:** Bei Lastspitzen
   - **Self-Consumption:** Bei PV-Erzeugung

3. **Berechnet optimalen Fahrplan:**
   - Linear Programming Optimierung (CVXPY)
   - 24h-Horizont
   - Berücksichtigt alle Constraints

4. **Führt Fahrplan aus:**
   - Echtzeit-Steuerung
   - Live-Updates im Dashboard

## 🎯 Strategien

### 1. Arbitrage (Standard)
- Kauft Strom bei niedrigen Preisen
- Verkauft Strom bei hohen Preisen
- Maximiert Gewinn

### 2. Peak Shaving
- Reduziert Lastspitzen
- Spart Netzentgelte
- Optimiert für Industrieanwendungen

### 3. Self-Consumption
- Maximiert PV-Eigenverbrauch
- Minimiert Netzbezug
- Ideal für PV-Anlagen

## 🔧 API-Endpunkte

### Aktueller Status
```bash
curl http://localhost:5000/api/state
```

### Optimierungsplan
```bash
curl http://localhost:5000/api/plan
```

### Prognosen
```bash
curl http://localhost:5000/api/forecast
```

### Verfügbare Strategien
```bash
curl http://localhost:5000/api/strategies
```

### Strategie manuell setzen
```bash
curl -X POST http://localhost:5000/api/strategy \
  -H "Content-Type: application/json" \
  -d '{"strategy": "arbitrage"}'
```

## 📈 Dashboard

Das Dashboard zeigt:

- **KPI-Cards:** SoC, Power, Strategy, Profit
- **Power Chart:** 24h Optimierungsplan (BESS, PV, Load)
- **Price & SoC Chart:** Strompreise und geplanter SoC-Verlauf
- **System Status:** Echtzeit-Werte

Alle Daten werden live über Server-Sent Events (SSE) aktualisiert.

## 🐛 Troubleshooting

### CVXPY Installation fehlgeschlagen
```bash
# Installiere Build-Tools
pip install --upgrade pip setuptools wheel
pip install cvxpy
```

Falls das nicht funktioniert: Das System verwendet automatisch einen Heuristik-Fallback.

### Port bereits belegt
```bash
# Ändere Port in app.py oder beim Start:
python -m flask --app web.app run --port 5001
```

### Keine Preise verfügbar
- Prüfe Internetverbindung
- Setze `demo_mode: true` in `config/ems.yaml`

## 🔄 Updates & Weiterentwicklung

### Phase 2 (geplant):
- Machine Learning Forecasting (Prophet, LSTM)
- Echte Wetter-API Integration
- Historische Datenanalyse
- Performance-Metriken

### Phase 3 (geplant):
- Multi-Asset Management
- VPP Integration
- Grid Services
- Advanced Analytics

## 📞 Support

Bei Fragen oder Problemen:
1. Logs prüfen: `tail -f app/logs/ems.log`
2. Debug-Modus aktivieren: `flask run --debug`
3. Issue erstellen

---

**Version:** 1.0.0  
**Last Updated:** 2025-10-01



