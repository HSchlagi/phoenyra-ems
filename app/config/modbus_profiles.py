"""
Vordefinierte Modbus-Profile für verschiedene BESS-Hersteller.

Aktuell enthalten:
    - Hithium ESS 5.016/4.180 kWh Container (SBMU ↔ EMS)
        Basierend auf „BMS Communication Protocol with EMS via Modbus V1.6“
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass(frozen=True)
class RegisterDefinition:
    """Beschreibung eines Modbus-Registers inkl. Skalierung."""

    address: int
    function: int = 3  # 3 = Holding Register, 4 = Input Register, 2 = Discrete Input
    count: int = 1
    data_type: str = "uint16"
    scale: float = 1.0
    offset: float = 0.0
    unit: Optional[str] = None
    description: str = ""
    category: str = "telemetry"
    zero_based: bool = False
    signed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "function": self.function,
            "count": self.count,
            "data_type": self.data_type,
            "scale": self.scale,
            "offset": self.offset,
            "unit": self.unit,
            "description": self.description,
            "category": self.category,
            "zero_based": self.zero_based,
            "signed": self.signed,
        }


@dataclass(frozen=True)
class AlarmDefinition:
    """Beschreibung eines diskreten Alarmbits."""

    address: int
    bit: int
    description: str
    category: str = "alarm"
    zero_based: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "bit": self.bit,
            "description": self.description,
            "category": self.category,
            "zero_based": self.zero_based,
        }


MODBUS_PROFILES: Dict[str, Dict[str, Any]] = {
    "hithium_ess_5016": {
        "label": "Hithium ESS 5.016/4.180 kWh",
        "manufacturer": "Hithium",
        "documentation": "BMS Communication Protocol with EMS via Modbus V1.6",
        "default_connection": {
            "connection_type": "tcp",
            "port": 502,
            "slave_id": 1,
            "timeout": 3.0,
            "poll_interval_s": 2.0,
        },
        "status_codes": {
            0: "Initialisierung",
            1: "Laden",
            2: "Entladen",
            3: "Bereit",
            5: "Ladesperre",
            6: "Entladesperre",
            7: "Lade- & Entladesperre",
            8: "Fehler",
        },
        "registers": {
            "soc_percent": RegisterDefinition(
                address=4,
                function=4,
                scale=1.0,
                unit="%",
                description="System State of Charge",
            ).to_dict(),
            "soh_percent": RegisterDefinition(
                address=5,
                function=4,
                scale=1.0,
                unit="%",
                description="System State of Health",
            ).to_dict(),
            "voltage_v": RegisterDefinition(
                address=2,
                function=4,
                scale=0.1,
                unit="V",
                description="System-Gesamtspannung",
            ).to_dict(),
            "current_a": RegisterDefinition(
                address=3,
                function=4,
                scale=0.1,
                offset=-3200.0,
                unit="A",
                description="Systemstrom (positive Werte = Laden)",
            ).to_dict(),
            "temperature_c": RegisterDefinition(
                address=42,
                function=4,
                scale=1.0,
                offset=-40.0,
                unit="°C",
                description="Durchschnittliche Systemtemperatur",
            ).to_dict(),
            "max_discharge_power_kw": RegisterDefinition(
                address=32,
                function=4,
                scale=0.1,
                unit="kW",
                description="Zulässige maximale Entladeleistung",
                category="limit",
            ).to_dict(),
            "max_charge_power_kw": RegisterDefinition(
                address=33,
                function=4,
                scale=0.1,
                unit="kW",
                description="Zulässige maximale Ladeleistung",
                category="limit",
            ).to_dict(),
            "max_discharge_current_a": RegisterDefinition(
                address=34,
                function=4,
                scale=0.1,
                unit="A",
                description="Zulässiger maximaler Entladestrom",
                category="limit",
            ).to_dict(),
            "max_charge_current_a": RegisterDefinition(
                address=35,
                function=4,
                scale=0.1,
                unit="A",
                description="Zulässiger maximaler Ladestrom",
                category="limit",
            ).to_dict(),
            "insulation_resistance_kohm": RegisterDefinition(
                address=45,
                function=4,
                scale=1.0,
                unit="kΩ",
                description="System-Isolationswiderstand",
                category="diagnostics",
            ).to_dict(),
            "status_code": RegisterDefinition(
                address=43,
                function=4,
                scale=1.0,
                unit=None,
                description="Systemstatus laut BMS",
                category="status",
            ).to_dict(),
            "pcs_comm_fault": RegisterDefinition(
                address=46,
                function=4,
                scale=1.0,
                unit=None,
                description="Kommunikationsfehler PCS ↔ BMS (0=OK, 1=Fehler)",
                category="diagnostics",
            ).to_dict(),
            "ems_comm_fault": RegisterDefinition(
                address=47,
                function=4,
                scale=1.0,
                unit=None,
                description="Kommunikationsfehler EMS ↔ BMS (0=OK, 1=Fehler)",
                category="diagnostics",
            ).to_dict(),
        },
        "alarms": {
            "charge_prohibited": AlarmDefinition(
                address=55,
                bit=0,
                description="Ladesperre aktiv",
            ).to_dict(),
            "discharge_prohibited": AlarmDefinition(
                address=56,
                bit=0,
                description="Entladesperre aktiv",
            ).to_dict(),
            "system_fault": AlarmDefinition(
                address=57,
                bit=0,
                description="BMS-Systemfehler",
            ).to_dict(),
            "contactor_abnormal_open": AlarmDefinition(
                address=53,
                bit=0,
                description="Schützzustand: unerwartet geöffnet",
            ).to_dict(),
            "contactor_abnormal_closed": AlarmDefinition(
                address=54,
                bit=0,
                description="Schützzustand: unerwartet geschlossen",
            ).to_dict(),
        },
    }
}


def get_profile(profile_key: str) -> Optional[Dict[str, Any]]:
    """Liefert eine tiefe Kopie des Profil-Dictionaries."""
    profile = MODBUS_PROFILES.get(profile_key)
    return deepcopy(profile) if profile else None


def list_profiles() -> Dict[str, Dict[str, Any]]:
    """Liefert eine flache Liste aller verfügbaren Profile (ohne Registerdetails)."""
    return {
        key: {
            "label": value.get("label", key),
            "manufacturer": value.get("manufacturer"),
            "documentation": value.get("documentation"),
        }
        for key, value in MODBUS_PROFILES.items()
    }


