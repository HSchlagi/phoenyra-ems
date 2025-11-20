# Modbus Register Map Template – WSTECH PCS + HiTHIUM BESS
_For Phoenyra EMS / CursorAI Integration_

Dieses Template definiert eine herstellernahe, saubere Struktur für:
- Steuerung über **WSTECH PCS (Inverter)** als zentrale Modbus-Schnittstelle
- Optionale Auswertung von **HiTHIUM BESS**-Daten
- Verwendung im **Phoenyra EMS Power Control** Modul

> Hinweis: Alle Register-Adressen sind Platzhalter und müssen 1:1 aus den offiziellen
> WSTECH / HiTHIUM Modbus-Dokumenten ersetzt werden.

---

## 1. Verbindungsparameter

```yaml
wstech_pcs:
  host: 192.168.100.50        # Beispiel-IP PCS
  port: 502
  unit_id: 1
  timeout_ms: 1000
  retry: 3

hithium_bms_optional:
  host: 192.168.100.60        # Nur falls separates BMS-Gateway vorhanden
  port: 502
  unit_id: 1
  enabled: false              # default false, nur aktivieren wenn Doku vorhanden
```

---

## 2. WSTECH PCS – Control Registers (Phoenyra EMS schreibt)

Diese Register werden vom **Phoenyra EMS** beschrieben.
Sie verknüpfen direkt mit der Logik aus `EMS_Power_Control_Phoenyra_CursorAI.md`.

```yaml
wstech_pcs:
  control:
    REMOTE_ENABLE:
      register: 40001        # <WRITEN: PCS Remote/Local Enable>
      type: uint16
      comment: 1 = Remote/EMS Control aktiv, 0 = Lokal

    OPERATING_MODE:
      register: 40002        # <WRITE: Betriebsmodus / Run-Stop / Grid-Tied>
      type: uint16
      comment: z.B. 1 = Run, 2 = Stop, herstellerabhängig

    ACTIVE_POWER_SET_W:
      register: 40010        # <WRITE: P-Setpoint absolut in W>
      type: int32
      scale: 1
      comment: Von EMS berechneter P-Sollwert, Limitierung inkl. DSO & Safety Logik

    REACTIVE_POWER_SET_VAR:
      register: 40012        # <WRITE: Q-Setpoint in var>
      type: int32
      scale: 1
      comment: Optional, für cosφ / Q-Regelung

    ACTIVE_POWER_LIMIT_PCT:
      register: 40020        # <WRITE: P-Limit in % der Nennleistung>
      type: uint16
      scale: 0.1
      comment: Optional, wenn PCS Prozent-Limit unterstützt

    KEEP_ALIVE:
      register: 40030        # <WRITE: Heartbeat / Keep-Alive Counter>
      type: uint16
      comment: EMS erhöht z.B. alle 5 s; PCS überwacht Kommunikation
```

**Integration:**  
`compute_setpoints()` schreibt i. d. R. `ACTIVE_POWER_SET_W` (und optional `ACTIVE_POWER_LIMIT_PCT`) + `REMOTE_ENABLE` + `OPERATING_MODE`.

---

## 3. WSTECH PCS – Status/Register (Phoenyra EMS liest)

Diese Werte nutzt das EMS für Visualisierung, Logging, Schutzlogik & BESS-Steuerung.

```yaml
wstech_pcs:
  status:
    PAC_NOW_W:
      register: 30001        # <READ: aktuelle Wirkleistung>
      type: int32
      scale: 1

    QAC_NOW_VAR:
      register: 30003        # <READ: aktuelle Blindleistung>
      type: int32
      scale: 1

    U_AC_V:
      register: 30005        # <READ: Netzspannung>
      type: uint16
      scale: 1

    F_AC_HZ:
      register: 30006        # <READ: Netzfrequenz>
      type: uint16
      scale: 0.01

    STATUS_WORD:
      register: 30010        # <READ: Statusbits PCS>
      type: uint16
      comment: Bitmaske (OK, Fehler, Run, Stop, Fault etc.)

    ALARM_WORD:
      register: 30011        # <READ: Alarmbits>
      type: uint16

    EMS_COMM_STATE:
      register: 30020        # <READ: aus PCS-Sicht EMS OK?>
      type: uint16
      comment: 1 = EMS Keep-Alive gültig, 0 = Timeout

    SOC_FROM_BESS:
      register: 30030        # <READ: SOC des BESS sofern vom PCS bereitgestellt>
      type: uint16
      scale: 0.1
      comment: Nur verwenden, wenn laut WSTECH-Doku verfügbar
```

---

## 4. Optional: HiTHIUM BESS – Direkter Zugriff (nur falls freigegeben)

Nur verwenden, wenn:
- Offizielle HiTHIUM Modbus-Dokumentation vorhanden
- Zugriff explizit vom Lieferanten freigegeben
- Keine Schutzfunktionen umgangen werden

```yaml
hithium_bms_optional:
  status:
    RACK_SOC_AVG:
      register: 31001        # <READ: SOC Durchschnitt aller Racks>
      type: uint16
      scale: 0.1

    RACK_CURRENT_A:
      register: 31002        # <READ: Gesamtstrom>
      type: int16
      scale: 0.1

    RACK_VOLTAGE_V:
      register: 31003        # <READ: Gesamtspannung>
      type: uint16
      scale: 0.1

    BMS_ALARM_WORD:
      register: 31010        # <READ: BMS Alarme>
      type: uint16

  control:
    # Nur falls in Doku vorgesehen und abgestimmt:
    BMS_CHARGE_ENABLE:
      register: 41001        # <WRITE: Laden erlauben/verhindern>
      type: uint16
      enabled: false

    BMS_DISCHARGE_ENABLE:
      register: 41002        # <WRITE: Entladen erlauben/verhindern>
      type: uint16
      enabled: false
```

**Best Practice:**  
- Primäre Leistungsregelung nur über **PCS (WSTECH)**.
- Direkte BMS-Kommandos restriktiv, dokumentiert, evtl. nur lesend.

---

## 5. Phoenyra EMS – Binding zur Logik

Beispielhafte Zuordnung für `compute_setpoints()`:

```yaml
phoenyra_power_control_binding:
  input:
    dso_trip:               wstech_pcs.status.ALARM_WORD        # aus Bits abgeleitet
    safety_alarm:           wstech_pcs.status.ALARM_WORD
    soc:                    wstech_pcs.status.SOC_FROM_BESS
    p_max_w:                5000000                             # Beispiel: 5 MW

  output:
    REMOTE_SHUTDOWN:        wstech_pcs.control.REMOTE_SHUTDOWN
    ACTIVE_POWER_SET_W:     wstech_pcs.control.ACTIVE_POWER_SET_W
    ACTIVE_POWER_LIMIT_PCT: wstech_pcs.control.ACTIVE_POWER_LIMIT_PCT
```

Im Code (Pseudo):

```python
setpoints = compute_setpoints(state)

modbus_write("wstech_pcs", "control.ACTIVE_POWER_SET_W", setpoints["ACTIVE_POWER_LIMIT_W"])
modbus_write("wstech_pcs", "control.REMOTE_SHUTDOWN", setpoints["REMOTE_SHUTDOWN"])
```

---

## 6. ToDo für dein Projekt

1. Offizielle **WSTECH PCS Modbus Register Map** öffnen.
2. Alle `<register: ...>` Platzhalter in dieser Datei 1:1 ersetzen.
3. Falls vorhanden: HiTHIUM BMS Map prüfen → nur Statuswerte übernehmen.
4. Diese `.md` in CursorAI laden → daraus:
   - `modbus_register_map_wstech_hithium.yaml`
   - Python-Modul für Modbus-Client & Binding generieren lassen.
5. Im Phoenyra EMS Deploy testen:
   - Simulation-Mode (trocken)
   - Live mit PCS, Logging aller Setpoints & Antworten.

---

**Status:** Template bereit zur Anpassung  
**Autor:** Phoenyra Engineering  
**Version:** 1.0.0  
**Datum:** 2025-11-11
