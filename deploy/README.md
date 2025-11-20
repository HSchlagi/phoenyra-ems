# Phoenyra BESS EMS - Docker Deployment

## 🐳 Docker Setup

Dieses Verzeichnis enthält die Docker-Konfiguration für Phoenyra BESS EMS.

## 📋 Voraussetzungen

- Docker Desktop installiert und laufend
- Docker Compose installiert
- Mindestens 4GB RAM verfügbar

## 🚀 Schnellstart

### 1. Container bauen und starten

```bash
cd deploy
docker-compose up -d --build
```

### 2. Zugriff auf das Web-Interface

- **Web-Interface:** http://localhost:8080
- **Login:** 
  - Username: `admin`
  - Password: `admin123`

### 3. MQTT Broker

- **MQTT Broker:** `localhost:1883`
- **MQTT WebSocket:** `localhost:9001`

## 📊 Container-Übersicht

| Container | Port | Beschreibung |
|-----------|------|--------------|
| `phoenyra-bess-ems` | 8080 | EMS Web Interface |
| `phoenyra-ems-mqtt` | 1883 | MQTT Broker |

## 🔧 Wartung

### Logs anzeigen

```bash
# Alle Logs
docker-compose logs -f

# Nur EMS Logs
docker-compose logs -f ems-web

# Nur MQTT Logs
docker-compose logs -f mqtt-broker
```

### Container neu starten

```bash
# Alle Container
docker-compose restart

# Nur EMS Container
docker-compose restart ems-web
```

### Container stoppen

```bash
docker-compose down
```

### Container mit Daten löschen

```bash
docker-compose down -v
```

### Images neu bauen

```bash
docker-compose build --no-cache
docker-compose up -d
```

## 📁 Verzeichnisstruktur

```
deploy/
├── docker-compose.yml      # Docker Compose Konfiguration
├── Dockerfile              # Docker Image Definition
├── gunicorn.conf.py        # Gunicorn Konfiguration
├── requirements.txt        # Python Dependencies
├── mqtt/
│   ├── config/
│   │   └── mosquitto.conf  # MQTT Broker Konfiguration
│   ├── data/               # MQTT Daten (persistent)
│   └── log/                # MQTT Logs
└── logs/                   # Anwendungslogs
```

## 🔐 Volumes

Das System verwendet folgende Volumes:

- `../data` → `app/data`: Datenbank und historische Daten
- `../app/config` → `app/config:ro`: Konfiguration (Read-Only)
- `./logs` → `app/logs`: Anwendungslogs
- `./mqtt/data` → `mosquitto/data`: MQTT Persistenz
- `./mqtt/log` → `mosquitto/log`: MQTT Logs

## 🌐 Netzwerk

Das System verwendet ein privates Docker-Netzwerk:
- **Netzwerk Name:** `phoenyra-ems-network`
- **Typ:** Bridge

Container können sich über ihren Service-Namen erreichen:
- `ems-web` → `http://ems-web:8000`
- `mqtt-broker` → `mqtt://mqtt-broker:1883`

## 🔍 Troubleshooting

### Port bereits belegt

Falls Port 8080 oder 1883 bereits belegt ist, ändere die Ports in `docker-compose.yml`:

```yaml
ports:
  - '8081:8000'  # Statt 8080:8000
```

### Container startet nicht

1. Logs prüfen: `docker-compose logs ems-web`
2. Image neu bauen: `docker-compose build --no-cache ems-web`
3. Abhängigkeiten prüfen: `docker-compose config`

### MQTT Verbindung fehlgeschlagen

1. MQTT Broker Status: `docker-compose logs mqtt-broker`
2. MQTT Config prüfen: `cat mqtt/config/mosquitto.conf`
3. Netzwerk prüfen: `docker network inspect phoenyra-ems-network`

### Datenbank-Probleme

Die Datenbank liegt im Volume `../data`. Prüfen Sie die Berechtigungen:

```bash
ls -la ../data/
```

## 📝 Weitere Informationen

- **Dokumentation:** `../README.md`
- **Installation:** `../app/INSTALLATION.md`
- **EMS Dokumentation:** `../EMS_MODUL_DOKUMENTATION.md`

