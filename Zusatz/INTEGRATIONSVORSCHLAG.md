# 🚀 Integrationsvorschlag für Phoenyra EMS

**Erstellt:** Basierend auf `ems_pruefliste.md` und aktuellem Systemstand  
**Datum:** 2025

---

## 📊 Status-Übersicht der Prüfliste

| Feature | Status | Priorität | Komplexität | Empfehlung |
|---------|--------|-----------|-------------|------------|
| **1. Eigenverbrauchsoptimierung** | ✅ **Implementiert** | - | - | ✅ Fertig |
| **2. Netzanschlussabsicherung** | ⚠️ **Teilweise** | 🔴 **Hoch** | Mittel | 🔧 **Erweitern** |
| **3. Peak Shaving** | ✅ **Implementiert** | - | - | ✅ Fertig |
| **4. Intelligente Steuerung** | ✅ **Implementiert** | - | - | ✅ Fertig |
| **5. Ersatzstromfunktion** | ❌ **Fehlt** | 🟡 Mittel | Hoch | 📋 **Phase 2** |
| **6. Einspeisebegrenzung** | ❌ **Fehlt** | 🔴 **Hoch** | Niedrig | 🎯 **Phase 1** |
| **7. Dynamische Stromtarife** | ✅ **Implementiert** | - | - | ✅ Fertig |
| **8. Energiegemeinschaften** | ❌ **Fehlt** | 🟡 Mittel | Hoch | 📋 **Phase 3** |
| **9. Dynamische Netzentgelte** | ❌ **Fehlt** | 🟡 Mittel | Mittel | 📋 **Phase 2** |
| **10. Flexibilitätsvermarktung** | ❌ **Fehlt** | 🟢 Niedrig | Sehr Hoch | 📋 **Phase 4** |

---

## 🎯 **Phase 1: Kritische Features (Sofort umsetzbar)**

### **1.1 Einspeisebegrenzung (Feed-in Limitation)** ⭐ **TOP PRIORITÄT**

**Warum wichtig:**
- Gesetzliche Anforderungen (z.B. 70%-Regel in Deutschland)
- Netzstabilität und Compliance
- Häufig nachgefragte Funktion

**Was fehlt:**
- Dynamische Einspeisebegrenzung (0% / 50% / 70% / 100%)
- Integration in Optimierungslogik
- UI-Konfiguration in Settings

**Umsetzung:**
```yaml
# Erweiterung in ems.yaml
feedin_limitation:
  enabled: true
  mode: dynamic  # 'off', 'fixed', 'dynamic'
  fixed_limit_pct: 70.0  # Bei mode: fixed
  dynamic_rules:
    - time: "06:00-18:00"
      limit_pct: 70.0
    - time: "18:00-22:00"
      limit_pct: 50.0
    - time: "22:00-06:00"
      limit_pct: 0.0
  pv_forecast_integration: true
```

**Technische Details:**
- Neue Strategie-Komponente: `FeedinLimitationStrategy`
- Integration in `EmsCore.optimize()` als Constraint
- Modbus-Write für `active_power_limit_pct` (falls PCS unterstützt)
- UI: Neuer Abschnitt in Settings mit Zeitregeln

**Aufwand:** ~2-3 Tage

---

### **1.2 Netzanschlussabsicherung (Erweiterung)** 🔧

**Was bereits da ist:**
- ✅ DSO Power Control (Trip, Limit)
- ✅ Modbus-Integration für externe Signale

**Was noch fehlt:**
- ⚠️ Statische Leistungsbegrenzung am Netzanschlusspunkt (z.B. 30 kW)
- ⚠️ Reaktive Leistungssteuerung (Q-Steuerung)
- ⚠️ Monitoring der Netzanschlussleistung

**Umsetzung:**
```yaml
# Erweiterung in ems.yaml
grid_connection:
  max_power_kw: 30.0  # Netzanschlussgrenze
  monitoring:
    enabled: true
    measurement_point: "grid_meter"  # MQTT-Topic oder Modbus-Register
  reactive_power:
    enabled: false
    cos_phi_target: 0.95
    q_control_mode: "fixed"  # 'fixed', 'dynamic'
```

**Technische Details:**
- Erweiterung `PowerControlManager` um statische Netzanschlussgrenze
- Neue Constraint in Optimierung: `p_grid <= max_power_kw`
- Optional: Q-Steuerung über Modbus (falls PCS unterstützt)
- UI: KPI für "Netzanschlussauslastung" auf Monitoring-Seite

**Aufwand:** ~1-2 Tage

---

## 📋 **Phase 2: Wichtige Features (Nächste Iteration)**

### **2.1 Dynamische Netzentgelte** 💰

**Warum wichtig:**
- Wirtschaftlichkeitsoptimierung
- Reduzierung der Netzgebühren
- Unterschiedliche Tarife nach Netzstufe (NE5/NE7)

**Umsetzung:**
```yaml
# Neue Konfiguration
grid_tariffs:
  enabled: true
  tariff_structure: "NE7"  # 'NE5', 'NE7', 'custom'
  time_variable: true
  high_load_windows:
    - start: "17:00"
      end: "20:00"
      multiplier: 1.5
  base_tariff_eur_per_kw: 0.15
```

**Technische Details:**
- Neue Service-Komponente: `GridTariffService`
- Integration in Optimierungslogik (Kostenfunktion)
- UI: Tarif-Konfiguration in Settings, Visualisierung in Analytics

**Aufwand:** ~3-4 Tage

---

### **2.2 Ersatzstromfunktion (Inselbetrieb)** 🔌

**Warum wichtig:**
- Notstromversorgung bei Netzausfall
- Kritische Infrastruktur
- Komplex, aber hochwertiges Feature

**Umsetzung:**
```yaml
# Neue Konfiguration
island_mode:
  enabled: true
  grid_loss_detection:
    method: "modbus"  # 'modbus', 'mqtt', 'io_module'
    register: "grid_status"
    timeout_s: 5.0
  startup_sequence:
    delay_s: 2.0
    min_soc_pct: 20.0
    load_shedding: true
  critical_loads:
    - name: "Kühlschrank"
      priority: 1
      max_power_kw: 0.5
```

**Technische Details:**
- Neue Komponente: `IslandModeManager`
- Grid-Loss-Detection über Modbus/MQTT
- Automatische Umschaltung auf Inselbetrieb
- Lastabwurf-Logik für kritische Verbraucher
- UI: Status-Anzeige, manuelle Aktivierung/Deaktivierung

**Aufwand:** ~5-7 Tage (inkl. Tests)

---

## 📋 **Phase 3: Erweiterte Features (Mittelfristig)**

### **3.1 Energiegemeinschaften (Energy Communities)** 🤝

**Warum wichtig:**
- Zunehmende Relevanz in Österreich/Deutschland
- Zusätzliche Einnahmequelle
- Komplexe Schnittstellen

**Umsetzung:**
```yaml
# Neue Konfiguration
energy_community:
  enabled: false
  provider: "systron"  # 'systron', 'pia', 'custom'
  api_endpoint: "https://api.example.com"
  api_key: null
  site_id: null
  sharing_rules:
    min_soc_pct: 30.0
    max_export_kw: 10.0
    priority: "self_consumption"  # 'self_consumption', 'community', 'balanced'
```

**Technische Details:**
- Neue Service-Komponente: `EnergyCommunityService`
- API-Integration für verschiedene Provider
- Überschuss-Erkennung und -Weiterleitung
- UI: Community-Dashboard, Überschuss-Visualisierung

**Aufwand:** ~7-10 Tage (abhängig von Provider-API)

---

## 📋 **Phase 4: Zukünftige Features (Langfristig)**

### **4.1 Flexibilitätsvermarktung (aFRR/mFRR/FCR)** 🔄

**Warum wichtig:**
- Hochwertiges Feature für kommerzielle Anlagen
- Zusätzliche Einnahmequelle
- Komplexe Aggregator-Integration

**Umsetzung:**
```yaml
# Neue Konfiguration
flexibility_marketing:
  enabled: false
  aggregator: "entelios"  # 'entelios', 'next_kraftwerke', 'custom'
  services:
    - name: "aFRR"
      enabled: false
      min_capacity_kw: 100.0
    - name: "mFRR"
      enabled: false
      min_capacity_kw: 50.0
    - name: "FCR"
      enabled: false
      min_capacity_kw: 200.0
  api_endpoint: null
  api_key: null
```

**Technische Details:**
- Neue Komponente: `FlexibilityMarketService`
- Aggregator-API-Integration
- Real-time Setpoint-Receiving
- UI: Service-Status, Einnahmen-Tracking

**Aufwand:** ~10-15 Tage (sehr komplex)

---

## 🎯 **Empfohlene Reihenfolge der Umsetzung**

### **Sprint 1 (2-3 Wochen):**
1. ✅ **Einspeisebegrenzung** (Phase 1.1)
2. ✅ **Netzanschlussabsicherung Erweiterung** (Phase 1.2)

### **Sprint 2 (3-4 Wochen):**
3. ✅ **Dynamische Netzentgelte** (Phase 2.1)
4. ✅ **Ersatzstromfunktion** (Phase 2.2) - Optional, falls benötigt

### **Sprint 3 (4-6 Wochen):**
5. ✅ **Energiegemeinschaften** (Phase 3.1) - Falls Marktbedarf

### **Sprint 4 (6-8 Wochen):**
6. ✅ **Flexibilitätsvermarktung** (Phase 4.1) - Nur bei kommerziellem Bedarf

---

## 💡 **Technische Empfehlungen**

### **Architektur-Erweiterungen:**
1. **Neue Strategie-Basis:** `FeedinLimitationStrategy` als Constraint-Strategy
2. **Service-Layer:** `GridTariffService`, `EnergyCommunityService`
3. **Manager-Komponenten:** `IslandModeManager`, `FlexibilityMarketService`
4. **UI-Erweiterungen:** Settings-Abschnitte, neue KPIs, Visualisierungen

### **Konfiguration:**
- Alle neuen Features über `ems.yaml` konfigurierbar
- Feature-Flags für schrittweise Aktivierung
- Backward-Kompatibilität gewährleisten

### **Testing:**
- Unit-Tests für neue Strategien/Services
- Integration-Tests für Modbus/MQTT-Interaktionen
- UI-Tests für neue Settings-Bereiche

---

## 📝 **Nächste Schritte**

1. **Priorisierung mit Stakeholdern** - Welche Features sind wirklich wichtig?
2. **Phase 1 starten** - Einspeisebegrenzung + Netzanschlussabsicherung
3. **Dokumentation aktualisieren** - Nach jeder Phase
4. **Testing & Validierung** - Vor Produktivsetzung

---

**Fragen oder Anpassungen gewünscht?** Gerne können wir die Prioritäten gemeinsam anpassen!

