# EMS Power Control – Phoenyra / CursorAI Modul

## Zweck

Dieses Modul definiert eine saubere, normnah gedachte Struktur, wie das Phoenyra EMS
Leistung und Abschaltung von PV‑Wechselrichtern und BESS steuern kann – **inklusive Vorrang
für Netzbetreiber und Sicherheitseinrichtungen**. Ziel ist eine klare Prioritätslogik, saubere
Modbus-Anbindung und Cursor-kompatibler Code-Aufbau.

---

## Systemübersicht

Beteiligte Komponenten:

- **Wechselrichter / BESS** mit Modbus-Schnittstelle
- **Phoenyra EMS** (dein Steuer- und Optimierungssystem)
- **Schutzeinrichtungen** (NA-Schutz, Kuppelschalter, Freischaltstelle)
- **Netzbetreiber-Signal** (direkt oder indirekt)
- Optionale externe Signale (z. B. Einspeiselimit vom Aggregator, Marktlogik, Not-Aus)

Wichtig: **Das EMS ergänzt, ersetzt aber nicht**:
- Hardware-Schutz (NA-Schutz, Leistungsschalter)
- Geforderte direkte Eingriffsmöglichkeiten des Netzbetreibers bei größeren Anlagen

---

## Prioritätenlogik (Empfohlen)

Von oben nach unten priorisiert:

1. **Netzbetreiber / NA-Schutz / Kuppelschalter (Hardware)**
   - Physikalische Trennung → alles aus, unabhängig vom EMS.
   - Hat immer höchste Priorität.

2. **Sicherheit & Not-Aus (Hardware + EMS)**
   - Lokaler NOT-AUS, Übertemperatur, Brandmeldung etc.
   - Kann direkt den WR/BESS sperren oder EMS zwingt P = 0.

3. **Netzbetreiber-/Aggregator-Override (Software/Signal)**
   - z. B. Digital-Eingang, Rundsteuersignal oder SCADA/Leitsystem.
   - „Max. Einspeiseleistung = X %“ oder „Abschalten“.
   - Wird im EMS als **DSO_OVERRIDE** oder **REMOTE_LIMIT** abgebildet.
   - Hat Vorrang vor betriebswirtschaftlichen Optimierungen.

4. **Phoenyra EMS Optimierung**
   - Setzt P/Q/Sollwerte basierend auf:
     - Fahrplan, Intraday, Flexvermarktung
     - SOC-Management
     - Eigenverbrauch, Peak Shaving

5. **Lokale Bedienung / HMI des Wechselrichters**
   - Kann (konfigurierbar) nur noch Begrenzungen verschärfen, nicht aushebeln.
   - Empfehlung: klar definierter „Remote Control Mode“ im WR.

Die Regel: **Höhere Priorität kann niedrigere überschreiben**, niemals umgekehrt.

---

## Modbus-Register-Design (Beispiel)

Diese Struktur dient als Template für Phoenyra-Module und Cursor-Automation.
Konkrete Adressen an WR/BESS-Datenblatt anpassen.

### Steuer-Register (Holding Register)

| Reg   | Name                     | Typ    | Beschreibung                                      |
|-------|--------------------------|--------|--------------------------------------------------|
| 40001 | CONTROL_MODE             | uint16 | 0=Local, 1=EMS, 2=DSO Override aktiv (read-only aus Sicht EMS) |
| 40002 | ACTIVE_POWER_LIMIT_PCT   | uint16 | 0–100 %, Wirkleistungsbegrenzung relativ         |
| 40003 | ACTIVE_POWER_LIMIT_W     | int32  | Absolutes Pac-Limit in W                         |
| 40005 | REMOTE_SHUTDOWN          | uint16 | 0=Ein, 1=Aus (sanft herunterfahren)              |
| 40006 | Q_MODE                   | uint16 | 0=fixed cosφ, 1=Q(U), 2=Q(P) etc.                |
| 40007 | COSPHI_SET               | int16  | cos φ * 1000 (z. B. 0.95 → 950)                  |

### Status- / Mess-Register (Input/Analog)

| Reg   | Name            | Typ    | Beschreibung                 |
|-------|-----------------|--------|-----------------------------|
| 30001 | PAC_NOW_W       | int32  | Aktuelle Wirkleistung WR    |
| 30003 | QAC_NOW_VAR     | int32  | Aktuelle Blindleistung      |
| 30005 | GRID_STATUS     | uint16 | 0=OK, 1=Fehler, 2=Trennung  |
| 30006 | EMS_COMM_OK     | uint16 | 0=Timeout, 1=OK             |

### Digitale Eingänge (physisch, am WR/BESS oder I/O-Modul)

- **DI1_NETZBETREIBER_ABSCHALTUNG**  
  High = Einspeisung aus / WR/BESS in sicheren Zustand.

- **DI2_NETZBETREIBER_LIMIT**  
  High = Limit gemäß definierter Stufe (z. B. 50 % Einspeisung).

Diese Signale wertet der WR direkt aus **und/oder** werden vom EMS gelesen, um die Priorität zu setzen.

---

## Steuerlogik (Pseudocode)

Beispielhafte Entscheidungslogik im EMS (z. B. als Python-Modul für Cursor):

```python
def compute_setpoints(state):
    """
    state enthält u.a.:
    - dso_trip (bool)
    - dso_limit_pct (0-100 oder None)
    - safety_alarm (bool)
    - market_setpoint_w (int)
    - peak_shaving_limit_w (int oder None)
    - soc (0-100)
    """

    # 1) Netzbetreiber / Sicherheit
    if state.get("dso_trip") or state.get("safety_alarm"):
        return {
            "REMOTE_SHUTDOWN": 1,
            "ACTIVE_POWER_LIMIT_W": 0,
        }

    limits_w = []

    # 2) DSO-Limit (in Prozent vom technisch max.)
    if state.get("dso_limit_pct") is not None and state.get("p_max_w") is not None:
        limits_w.append(state["p_max_w"] * state["dso_limit_pct"] / 100.0)

    # 3) Peak Shaving Limit (absolute Grenze)
    if state.get("peak_shaving_limit_w") is not None:
        limits_w.append(state["peak_shaving_limit_w"])

    # 4) Markt-/Optimierungs-Setpoint
    if state.get("market_setpoint_w") is not None:
        limits_w.append(state["market_setpoint_w"])

    if not limits_w:
        # Kein spezielles Limit → 0 oder definierter Default
        return {
            "REMOTE_SHUTDOWN": 0,
            "ACTIVE_POWER_LIMIT_W": 0
        }

    # Strengstes (kleinstes) Limit wählen
    chosen = int(min(limits_w))

    return {
        "REMOTE_SHUTDOWN": 0,
        "ACTIVE_POWER_LIMIT_W": max(chosen, 0)
    }
```

Empfehlungen:
- Schreib-/Lesezyklen: z. B. alle 1–5 s.
- Timeout-Mechanismus: Wenn EMS eine bestimmte Zeit nicht schreibt → WR geht automatisch in sicheren Default (z. B. 0 % oder lokales Limit).
- Alle Befehle protokollieren (Audit-Trail).

---

## Integration mit CursorAI

Beispielhafte Struktur für dein Repo / Phoenyra-Projekt:

```text
phoenyra-ems/
  modules/
    EMS_Power_Control_Phoenyra_CursorAI.md  # Diese Spezifikation
    ems_power_control.py                    # Von Cursor generierter Code basierend auf dieser MD
  config/
    modbus_register_map.yaml                # Gerätespezifische Adressen
```

Vorgehensweise:
1. Diese `.md` in Cursor einbinden.
2. Cursor den Python-Code `ems_power_control.py` generieren lassen.
3. Im EMS:
   - Zustände einsammeln (Modbus, MQTT, Digitaleingänge).
   - `compute_setpoints()` aufrufen.
   - Setpoints in die echten WR/BESS-Register schreiben.

---

## Fail-Safe & Hinweise

- Hardware-Abschaltung und NA-Schutz bleiben führend.
- Netzbetreiber-Vorgaben (Abschaltung, Limit) dürfen durch das EMS nicht aufgehoben werden.
- Logging & Nachvollziehbarkeit sind Pflichtbestandteile eines professionellen EMS.
- Diese Spezifikation ist herstellerneutral und kann je Gerät gemappt werden.

---

**Autor:** Phoenyra Engineering  
**Status:** Draft – einsatzbereit für CursorAI & Phoenyra EMS  
**Version:** 1.0.0  
**Datum:** 2025-11-11
