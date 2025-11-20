# Prüfliste EMS-Integration – Doppelt Intelligentes Energiemanagement

Diese Datei dient zur systematischen Überprüfung, ob unser **EMS-System (Phoenyra EMS / BESS Studio)** alle wesentlichen Funktionen abdeckt oder integrierbar macht.

---

## 🎯 1. Eigenverbrauchsoptimierung
- Prüfen, ob PV-Überschuss automatisch erkannt wird  
- Speicherladung nach Eigenverbrauchslogik  
- Priorisierung Last → Speicher → Netz  

---

## 🔒 2. Netzanschlussabsicherung
- Dynamische Leistungsbegrenzung am Netzanschlusspunkt  
- Regelung gemäß maximal zulässiger kW (z. B. Netz OÖ 30 kW-Grenze)  
- Reaktive und aktive Leistungssteuerung möglich?  

---

## 📉 3. Peak Shaving
- Lastspitzen werden erkannt  
- Speicher entlädt automatisch zur Reduktion des Bezugs  
- Parametrierbare Schwellwerte  

---

## ⚡ 4. Intelligente Steuerung (Offenes EMS)
- Offene API (Modbus, MQTT, REST, Webhooks)  
- Steuerung beliebiger Verbraucher/Erzeuger  
- Dynamische Regeln (IF/THEN, zeitbasiert, preisbasiert)  
- Unterstützung von Multi-Asset-Steuerung (PV, BESS, EV, WP, etc.)  

---

## 🔌 5. Ersatzstromfunktion
- Inselbetrieb möglich?  
- Automatische Netztrennung kompatibel?  
- Startsequenzen des BESS dokumentiert?  

---

## ↕ 6. Einspeisebegrenzung
- 0 % / 50 % / 70 % dynamische Grenzen  
- Kombination mit PV-Prognosen realisierbar  
- Regelalgorithmen verfügbar?  

---

## 💶 7. Dynamische Stromtarife
- aWATTar / EPEX Spot Unterstützung  
- API-Anbindung für Day-Ahead + Intraday  
- Automatisiertes Laden/Entladen abhängig vom Preis  

---

## 🤝 8. Laden / Einspeisen in Energiegemeinschaften
- Erkennung des Überschusses für EG  
- EG-Schnittstellen (z. B. Systron, PIA, Zähler-API)  
- Abrechnungsschnittstellen?  

---

## 🧾 9. Dynamische Netzentgelte
- Tarife nach Netzstufe (NE5 / NE7 / etc.)  
- Zeitvariable Netzentgelte (z. B. Hochlastzeitfenster)  
- Steuerlogik integriert?  

---

## 🔄 10. Flexibilitätsvermarktung
- aFRR / mFRR / FCR kompatible Steuerung  
- Aggregator-Anbindung (z. B. Entelios, Next Kraftwerke)  
- Fernansteuerung + digitale Schnittstellen  

---

## ✔ Ergebnis / Umsetzungsmatrix
| Punkt | Vorhanden | Geplant | Integration notwendig | Notizen |
|-------|-----------|---------|------------------------|---------|
| Eigenverbrauchsoptimierung | ✅ | - | - | ✅ **Implementiert** - Self-Consumption Strategy vorhanden |
| Netzanschlussabsicherung | ⚠️ | ✅ | ✅ | ⚠️ **Teilweise** - DSO Power Control vorhanden, statische Grenze & Q-Steuerung fehlen |
| Peak Shaving | ✅ | - | - | ✅ **Implementiert** - Peak Shaving Strategy vorhanden |
| Intelligente Steuerung | ✅ | - | - | ✅ **Implementiert** - REST API, MQTT, Modbus vorhanden |
| Ersatzstrom | ❌ | ✅ | ✅ | ❌ **Fehlt** - Inselbetrieb nicht implementiert (siehe INTEGRATIONSVORSCHLAG.md) |
| Einspeisebegrenzung | ❌ | ✅ | ✅ | ❌ **Fehlt** - Dynamische 0%/50%/70% Begrenzung fehlt (siehe INTEGRATIONSVORSCHLAG.md) |
| Dynamische Stromtarife | ✅ | - | - | ✅ **Implementiert** - aWATTar & EPEX Integration vorhanden |
| Energiegemeinschaften | ❌ | ✅ | ✅ | ❌ **Fehlt** - EG-Schnittstellen fehlen (siehe INTEGRATIONSVORSCHLAG.md) |
| Dynamische Netzentgelte | ❌ | ✅ | ✅ | ❌ **Fehlt** - NE5/NE7 Tarife fehlen (siehe INTEGRATIONSVORSCHLAG.md) |
| Flexibilitätsvermarktung | ❌ | ✅ | ✅ | ❌ **Fehlt** - aFRR/mFRR/FCR fehlen (siehe INTEGRATIONSVORSCHLAG.md) |

**📋 Detaillierter Integrationsvorschlag:** Siehe `INTEGRATIONSVORSCHLAG.md`

---

## 💡 Hinweis für Cursor AI
Diese Datei kann in Cursor als Grundlage für:
- Feature-Gap-Analyse  
- API- und Funktionsentwicklung  
- EMS-Modulaufbau  
- Automatisierte Tests / Unit-Tests  
- Architekturplanung  

verwendet werden.

