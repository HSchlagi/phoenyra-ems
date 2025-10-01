# 🏭 EMS-Modul Dokumentation - Energiemanagementsystem für BESS-Simulation

## 📋 **Übersicht**

Das EMS-Modul (Energy Management System) ist ein eigenständiges, strategisches Energiemanagementsystem, das als Orchestrator für die bestehende BESS-Simulation fungiert. Es koordiniert verschiedene Energiestrategien, Grid-Services und optimiert den Gesamtenergiefluss.

---

## 🎯 **Ziele und Vision**

### **Hauptziele:**
- **Strategische Steuerung** der BESS-Simulation
- **Grid-Integration** und Compliance
- **Multi-Asset-Management** (BESS, PV, Wind, etc.)
- **Intelligente Lastprognose** und Optimierung
- **VPP-Integration** (Virtuelles Kraftwerk)
- **Grid-Services** Koordination

### **Vision:**
Ein modulares, skalierbares EMS, das die bestehende BESS-Simulation als technische Basis nutzt und um strategische Energiemanagement-Features erweitert.

---

## 🏗️ **Architektur-Übersicht**

```
┌─────────────────────────────────────────────────────────────┐
│                    EMS-Modul (Orchestrator)                 │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Strategy  │  │ Forecasting │  │ Optimization│         │
│  │   Manager   │  │   Engine    │  │   Engine    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│                    Interface Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │    BESS     │  │    Grid     │  │   Market    │         │
│  │  Interface  │  │  Interface  │  │  Interface  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│              BESS-Simulation (Bestehend)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Advanced  │  │  Economic   │  │   Market    │         │
│  │   Dispatch  │  │  Analysis   │  │   Data      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

---

## 📁 **Ordnerstruktur**

```
EMS/
├── README.md                           # Hauptdokumentation
├── docs/                              # Dokumentation
│   ├── EMS_ARCHITECTURE.md            # Detaillierte Architektur
│   ├── EMS_STRATEGIES.md              # Strategien-Dokumentation
│   ├── EMS_INTEGRATION.md             # BESS-Integration Guide
│   └── EMS_API_REFERENCE.md           # API-Referenz
├── src/                               # Quellcode
│   ├── core/                          # Kern-EMS-Funktionen
│   │   ├── __init__.py
│   │   ├── ems_engine.py              # Haupt-EMS-Engine
│   │   ├── strategy_manager.py        # Strategie-Manager
│   │   ├── optimization_engine.py     # EMS-Optimierung
│   │   └── coordination_engine.py     # Koordinations-Engine
│   ├── forecasting/                   # Prognose-Module
│   │   ├── __init__.py
│   │   ├── load_forecasting.py        # Lastprognose
│   │   ├── generation_forecasting.py  # Erzeugungsprognose
│   │   ├── price_forecasting.py       # Preisprognose
│   │   └── weather_forecasting.py     # Wetterprognose
│   ├── strategies/                    # EMS-Strategien
│   │   ├── __init__.py
│   │   ├── peak_shaving.py            # Peak Shaving
│   │   ├── load_balancing.py          # Lastausgleich
│   │   ├── frequency_regulation.py    # Frequenzregelung
│   │   ├── emergency_backup.py        # Notstrom
│   │   ├── demand_response.py         # Demand Response
│   │   └── grid_services.py           # Grid-Services
│   ├── interfaces/                    # Interface-Module
│   │   ├── __init__.py
│   │   ├── bess_interface.py          # BESS-Simulation Interface
│   │   ├── grid_interface.py          # Netzanschluss Interface
│   │   ├── market_interface.py        # Markt-APIs Interface
│   │   └── device_interface.py        # Geräte-Interface
│   ├── optimization/                  # Optimierungs-Algorithmen
│   │   ├── __init__.py
│   │   ├── genetic_algorithm.py       # Genetischer Algorithmus
│   │   ├── particle_swarm.py          # Particle Swarm
│   │   ├── linear_programming.py      # Lineare Programmierung
│   │   └── machine_learning.py        # ML-Optimierung
│   └── utils/                         # Hilfsfunktionen
│       ├── __init__.py
│       ├── data_processing.py         # Datenverarbeitung
│       ├── validation.py              # Validierung
│       ├── logging.py                 # Logging
│       └── config_manager.py          # Konfigurations-Manager
├── config/                            # Konfigurationsdateien
│   ├── ems_config.yaml                # Hauptkonfiguration
│   ├── grid_codes.yaml                # Netzanschlussbedingungen
│   ├── strategies_config.yaml         # Strategien-Konfiguration
│   └── forecasting_config.yaml        # Prognose-Konfiguration
├── tests/                             # Tests
│   ├── __init__.py
│   ├── test_ems_engine.py             # EMS-Engine Tests
│   ├── test_strategies.py             # Strategien Tests
│   ├── test_forecasting.py            # Prognose Tests
│   └── test_integration.py            # Integration Tests
├── examples/                          # Beispiel-Implementierungen
│   ├── basic_ems_setup.py             # Basis EMS-Setup
│   ├── strategy_examples.py           # Strategie-Beispiele
│   └── integration_examples.py        # Integration-Beispiele
└── requirements.txt                   # Python-Abhängigkeiten
```

---

## 🔧 **Kern-Komponenten**

### **1. EMS-Engine (`ems_engine.py`)**
```python
class EMSEngine:
    """
    Haupt-EMS-Engine - Orchestriert alle EMS-Funktionen
    """
    def __init__(self, config_path: str):
        self.strategy_manager = StrategyManager()
        self.forecasting_engine = ForecastingEngine()
        self.optimization_engine = OptimizationEngine()
        self.bess_interface = BESSInterface()
        self.grid_interface = GridInterface()
    
    def run_optimization_cycle(self, current_time: datetime) -> Dict:
        """Führt einen Optimierungszyklus durch"""
        pass
    
    def select_optimal_strategy(self, conditions: Dict) -> str:
        """Wählt optimale Strategie basierend auf Bedingungen"""
        pass
    
    def coordinate_energy_flow(self, strategy: str) -> Dict:
        """Koordiniert Energiefluss basierend auf Strategie"""
        pass
```

### **2. Strategy Manager (`strategy_manager.py`)**
```python
class StrategyManager:
    """
    Verwaltet und koordiniert verschiedene EMS-Strategien
    """
    def __init__(self):
        self.strategies = {
            'peak_shaving': PeakShavingStrategy(),
            'load_balancing': LoadBalancingStrategy(),
            'frequency_regulation': FrequencyRegulationStrategy(),
            'emergency_backup': EmergencyBackupStrategy(),
            'demand_response': DemandResponseStrategy()
        }
    
    def evaluate_strategies(self, conditions: Dict) -> Dict[str, float]:
        """Bewertet alle Strategien basierend auf aktuellen Bedingungen"""
        pass
    
    def get_optimal_strategy(self, conditions: Dict) -> str:
        """Gibt optimale Strategie zurück"""
        pass
```

### **3. Forecasting Engine (`forecasting_engine.py`)**
```python
class ForecastingEngine:
    """
    Prognose-Engine für Last, Erzeugung und Preise
    """
    def __init__(self):
        self.load_forecaster = LoadForecaster()
        self.generation_forecaster = GenerationForecaster()
        self.price_forecaster = PriceForecaster()
        self.weather_forecaster = WeatherForecaster()
    
    def generate_forecasts(self, horizon_hours: int = 24) -> Dict:
        """Generiert alle Prognosen für den Zeithorizont"""
        pass
    
    def update_forecasts(self, new_data: Dict) -> None:
        """Aktualisiert Prognosen mit neuen Daten"""
        pass
```

---

## 🎯 **EMS-Strategien**

### **1. Peak Shaving Strategy**
- **Ziel**: Reduzierung von Lastspitzen
- **Anwendung**: Industrie, Gewerbe
- **BESS-Nutzung**: Entladung während Spitzenzeiten
- **Erlöspotenzial**: Netzgebühren-Einsparung

### **2. Load Balancing Strategy**
- **Ziel**: Ausgleich von Lastschwankungen
- **Anwendung**: Kontinuierliche Optimierung
- **BESS-Nutzung**: Bidirektionaler Betrieb
- **Erlöspotenzial**: Arbitrage, Grid-Services

### **3. Frequency Regulation Strategy**
- **Ziel**: Frequenzregelung für das Netz
- **Anwendung**: Primärregelung, Sekundärregelung
- **BESS-Nutzung**: Schnelle Reaktion auf Frequenzabweichungen
- **Erlöspotenzial**: Regelenergie-Vergütung

### **4. Emergency Backup Strategy**
- **Ziel**: Notstromversorgung
- **Anwendung**: Netzausfälle, kritische Lasten
- **BESS-Nutzung**: Entladung bei Netzausfall
- **Erlöspotenzial**: Verfügbarkeitsprämien

### **5. Demand Response Strategy**
- **Ziel**: Lastverschiebung basierend auf Marktsignalen
- **Anwendung**: Flexibilitätsmärkte
- **BESS-Nutzung**: Koordinierte Lade-/Entladestrategien
- **Erlöspotenzial**: Flexibilitäts-Vergütung

---

## 🔗 **BESS-Simulation Integration**

### **Interface-Design:**
```python
class BESSInterface:
    """
    Interface zur bestehenden BESS-Simulation
    """
    def __init__(self, bess_simulation_path: str):
        self.bess_sim = BESSSimulation(bess_simulation_path)
        self.advanced_dispatch = AdvancedDispatchSystem()
        self.economic_analysis = EconomicAnalysis()
    
    def run_optimization(self, strategy: str, parameters: Dict) -> Dict:
        """Führt BESS-Optimierung für spezifische Strategie durch"""
        pass
    
    def get_current_status(self) -> Dict:
        """Gibt aktuellen BESS-Status zurück"""
        pass
    
    def update_parameters(self, parameters: Dict) -> bool:
        """Aktualisiert BESS-Parameter"""
        pass
```

### **Integration-Punkte:**
1. **Advanced Dispatch System** - Für technische Optimierung
2. **Economic Analysis** - Für Wirtschaftlichkeitsberechnung
3. **Market Data Integration** - Für Preisprognosen
4. **Grid Services** - Für Netz-Services
5. **Database Integration** - Für Datenzugriff

---

## 📊 **Datenfluss und Kommunikation**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Market    │───▶│     EMS     │───▶│    BESS     │
│    Data     │    │   Engine    │    │ Simulation  │
└─────────────┘    └─────────────┘    └─────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Forecasts  │    │  Strategy   │    │  Dispatch   │
│             │    │  Selection  │    │  Commands   │
└─────────────┘    └─────────────┘    └─────────────┘
```

---

## ⚙️ **Konfiguration**

### **Hauptkonfiguration (`ems_config.yaml`):**
```yaml
ems:
  name: "BESS-EMS-System"
  version: "1.0.0"
  timezone: "Europe/Vienna"
  
  # Optimierungszyklus
  optimization:
    cycle_interval_minutes: 15
    forecast_horizon_hours: 24
    strategy_evaluation_interval_minutes: 5
    
  # Strategien
  strategies:
    enabled: ["peak_shaving", "load_balancing", "frequency_regulation"]
    default: "load_balancing"
    switching_threshold: 0.1
    
  # BESS-Integration
  bess_integration:
    simulation_path: "../"
    api_endpoint: "http://localhost:5000/api"
    update_interval_seconds: 30
    
  # Grid-Integration
  grid_integration:
    grid_code: "AT"
    compliance_check_interval_minutes: 1
    emergency_response_time_seconds: 1
    
  # Logging
  logging:
    level: "INFO"
    file: "logs/ems.log"
    max_size_mb: 10
    backup_count: 5
```

---

## 🧪 **Testing-Strategie**

### **Test-Kategorien:**
1. **Unit Tests** - Einzelne Komponenten
2. **Integration Tests** - BESS-Simulation Integration
3. **Strategy Tests** - Strategie-spezifische Tests
4. **Performance Tests** - Optimierungs-Performance
5. **End-to-End Tests** - Vollständige EMS-Zyklen

### **Test-Beispiele:**
```python
def test_ems_engine_initialization():
    """Test EMS-Engine Initialisierung"""
    pass

def test_strategy_selection():
    """Test Strategie-Auswahl"""
    pass

def test_bess_integration():
    """Test BESS-Simulation Integration"""
    pass

def test_forecasting_accuracy():
    """Test Prognose-Genauigkeit"""
    pass
```

---

## 🚀 **Implementierungsplan**

### **Phase 1: Grundlagen (Woche 1-2)**
- [ ] EMS-Engine Grundstruktur
- [ ] BESS-Interface Entwicklung
- [ ] Basis-Konfiguration
- [ ] Unit Tests Setup

### **Phase 2: Strategien (Woche 3-4)**
- [ ] Peak Shaving Strategy
- [ ] Load Balancing Strategy
- [ ] Strategy Manager
- [ ] Integration Tests

### **Phase 3: Prognosen (Woche 5-6)**
- [ ] Load Forecasting
- [ ] Generation Forecasting
- [ ] Price Forecasting
- [ ] Forecasting Engine

### **Phase 4: Optimierung (Woche 7-8)**
- [ ] Optimization Engine
- [ ] Genetic Algorithm
- [ ] Linear Programming
- [ ] Performance Tests

### **Phase 5: Grid-Integration (Woche 9-10)**
- [ ] Grid Interface
- [ ] Frequency Regulation
- [ ] Emergency Backup
- [ ] Grid Code Compliance

### **Phase 6: Advanced Features (Woche 11-12)**
- [ ] Machine Learning
- [ ] VPP Integration
- [ ] Multi-Asset Management
- [ ] End-to-End Tests

---

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

### **Operative Vorteile:**
- ✅ **Automatisierung** - Reduzierte manuelle Eingriffe
- ✅ **Prognose-Genauigkeit** - Bessere Planung
- ✅ **Compliance** - Grid-Code-Konformität
- ✅ **Monitoring** - Umfassende Überwachung

---

## 🔮 **Zukünftige Erweiterungen**

### **Kurzfristig (3-6 Monate):**
- Machine Learning für Prognosen
- Erweiterte Optimierungsalgorithmen
- Mobile App für Monitoring

### **Mittelfristig (6-12 Monate):**
- VPP-Integration
- Blockchain-Integration
- IoT-Sensor-Integration

### **Langfristig (1-2 Jahre):**
- KI-basierte Strategie-Auswahl
- Multi-Markt-Arbitrage
- Internationale Grid-Integration

---

## 📞 **Support und Wartung**

### **Dokumentation:**
- API-Referenz
- Benutzerhandbuch
- Entwickler-Guide
- Troubleshooting-Guide

### **Monitoring:**
- System-Health-Checks
- Performance-Monitoring
- Error-Tracking
- Log-Analyse

### **Updates:**
- Regelmäßige Updates
- Bug-Fixes
- Feature-Erweiterungen
- Sicherheits-Updates

---

## 🎯 **Fazit**

Das EMS-Modul wird als strategischer Orchestrator für die bestehende BESS-Simulation fungieren und das System um professionelle Energiemanagement-Features erweitern. Die modulare Architektur ermöglicht eine schrittweise Implementierung und einfache Erweiterung.

**Nächste Schritte:**
1. EMS-Ordnerstruktur erstellen
2. Grundlegende EMS-Engine entwickeln
3. BESS-Interface implementieren
4. Erste Strategien entwickeln
5. Integration mit BESS-Simulation testen

---

*Erstellt am: $(date)*
*Version: 1.0.0*
*Autor: Cursor AI Assistant*
