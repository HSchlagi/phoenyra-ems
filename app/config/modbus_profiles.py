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
    },
    "wstech_pcs": {
        "label": "WSTECH PCS (Inverter)",
        "manufacturer": "WSTECH",
        "documentation": "WSTECH PCS Modbus Register Map – Phoenyra Mapping",
        "default_connection": {
            "connection_type": "tcp",
            "port": 502,
            "slave_id": 1,
            "timeout": 1.5,
            "poll_interval_s": 2.0,
        },
        "registers": {
            # Control (write) registers
            "remote_enable": RegisterDefinition(
                address=40001,
                function=3,
                data_type="uint16",
                unit=None,
                description="Fernfreigabe EMS (1=Remote aktiv, 0=Lokal)",
                category="control",
            ).to_dict(),
            "operating_mode": RegisterDefinition(
                address=40002,
                function=3,
                data_type="uint16",
                unit=None,
                description="Betriebsmodus / Run-Stop",
                category="control",
            ).to_dict(),
            "active_power_set_w": RegisterDefinition(
                address=40010,
                function=3,
                count=2,
                data_type="int32",
                signed=True,
                unit="W",
                description="Wirkleistung Sollwert absolut",
                category="control",
            ).to_dict(),
            "reactive_power_set_var": RegisterDefinition(
                address=40012,
                function=3,
                count=2,
                data_type="int32",
                signed=True,
                unit="var",
                description="Blindleistung Sollwert absolut",
                category="control",
            ).to_dict(),
            "active_power_limit_pct": RegisterDefinition(
                address=40020,
                function=3,
                data_type="uint16",
                scale=0.1,
                unit="%",
                description="Wirkleistungslimit in % der Nennleistung",
                category="control",
            ).to_dict(),
            "keep_alive": RegisterDefinition(
                address=40030,
                function=3,
                data_type="uint16",
                unit=None,
                description="Heartbeat / Keep-Alive Counter",
                category="control",
            ).to_dict(),
            # Status (read) registers
            "pac_now_w": RegisterDefinition(
                address=30001,
                function=4,
                count=2,
                data_type="int32",
                signed=True,
                unit="W",
                description="Aktuelle Wirkleistung des PCS",
                category="telemetry",
            ).to_dict(),
            "qac_now_var": RegisterDefinition(
                address=30003,
                function=4,
                count=2,
                data_type="int32",
                signed=True,
                unit="var",
                description="Aktuelle Blindleistung des PCS",
                category="telemetry",
            ).to_dict(),
            "u_ac_v": RegisterDefinition(
                address=30005,
                function=4,
                data_type="uint16",
                unit="V",
                description="Netzspannung",
                category="telemetry",
            ).to_dict(),
            "f_ac_hz": RegisterDefinition(
                address=30006,
                function=4,
                data_type="uint16",
                scale=0.01,
                unit="Hz",
                description="Netzfrequenz",
                category="telemetry",
            ).to_dict(),
            "status_word": RegisterDefinition(
                address=30010,
                function=4,
                data_type="uint16",
                unit=None,
                description="Statuswort (Bitmaske) des PCS",
                category="status",
            ).to_dict(),
            "alarm_word": RegisterDefinition(
                address=30011,
                function=4,
                data_type="uint16",
                unit=None,
                description="Alarmwort (Bitmaske) des PCS",
                category="alarm",
            ).to_dict(),
            "ems_comm_state": RegisterDefinition(
                address=30020,
                function=4,
                data_type="uint16",
                unit=None,
                description="Kommunikationsstatus EMS ↔ PCS",
                category="diagnostics",
            ).to_dict(),
            "soc_from_bess": RegisterDefinition(
                address=30030,
                function=4,
                data_type="uint16",
                scale=0.1,
                unit="%",
                description="SOC vom BESS (falls vom PCS bereitgestellt)",
                category="telemetry",
            ).to_dict(),
        },
    },
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


