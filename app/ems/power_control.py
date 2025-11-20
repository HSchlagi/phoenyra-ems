"""
Power Control Logic for Phoenyra EMS
------------------------------------

Stellt Infrastruktur für DSO-/Sicherheitsprioritäten und Setpoint-Limitierung bereit.
Aktuell werden Signale ausgewertet und Entscheidungen vorbereitet; das eigentliche
Schreiben von Modbus-Setpoints kann optional aktiviert werden.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SignalState:
    """Abbild der relevanten Eingangssignale für die Leistungssteuerung."""

    dso_trip: bool = False
    safety_alarm: bool = False
    dso_limit_pct: Optional[float] = None
    raw_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PowerControlDecision:
    """Ergebnis der Leistungssteuerung."""

    requested_power_kw: float
    effective_power_kw: float
    shutdown: bool
    dso_trip: bool
    safety_alarm: bool
    dso_limit_pct: Optional[float]
    limit_kw: Optional[float]
    reason: str
    commands: Dict[str, Any] = field(default_factory=dict)

    @property
    def active_power_limit_w(self) -> Optional[float]:
        if self.limit_kw is None:
            return None
        return self.limit_kw * 1000.0


class PowerControlManager:
    """
    Bewertet DSO-/Sicherheits-Signale und berechnet wirksame Leistungsgrenzen.

    Konfigurationsschema (`power_control`):
        enabled: bool
        max_power_kw: float (optional, sonst aus Constraints)
        auto_write: bool (optional, default False)
        signals:
            dso_trip:
                register: str
                mask: int (optional)
                equals: int (optional)
            safety_alarm: ...
            dso_limit_pct:
                register: str
                scale: float (optional, default 1.0)
                min_pct: float (optional)
                max_pct: float (optional)
        writes:
            remote_enable:
                register: str
                on: int (optional, default 1)
                off: int (optional, default 0)
            active_power_set_w:
                register: str
                scale: float (optional, default 1.0)
            active_power_limit_pct:
                register: str
                scale: float (optional, default 1.0)
    """

    def __init__(self, config: Dict[str, Any]):
        self.enabled: bool = bool(config.get("enabled", False))
        self.max_power_kw: Optional[float] = config.get("max_power_kw")
        self.auto_write: bool = bool(config.get("auto_write", False))
        self.signals_config: Dict[str, Any] = config.get("signals", {}) or {}
        self.write_config: Dict[str, Any] = config.get("writes", {}) or {}
        self._signal_state = SignalState()

    # ------------------------------------------------------------------ #
    # Signal-Verarbeitung
    # ------------------------------------------------------------------ #

    def ingest_status(self, status: Dict[str, Any]) -> SignalState:
        """
        Aktualisiert die internen Signalspeicher basierend auf Modbus-Statuswerten.
        """
        if not status:
            return self._signal_state

        self._signal_state.raw_values = {}

        # DSO Trip
        dso_trip_cfg = self.signals_config.get("dso_trip")
        if dso_trip_cfg:
            self._signal_state.dso_trip = self._extract_bool(status, dso_trip_cfg)
            register = dso_trip_cfg.get("register")
            if register in status:
                self._signal_state.raw_values[register] = status.get(register)

        # Safety Alarm
        safety_cfg = self.signals_config.get("safety_alarm")
        if safety_cfg:
            self._signal_state.safety_alarm = self._extract_bool(status, safety_cfg)
            register = safety_cfg.get("register")
            if register in status:
                self._signal_state.raw_values[register] = status.get(register)

        # DSO Limit in %
        limit_cfg = self.signals_config.get("dso_limit_pct")
        if limit_cfg:
            limit_value = self._extract_float(status, limit_cfg)
            self._signal_state.dso_limit_pct = limit_value
            register = limit_cfg.get("register")
            if register in status:
                self._signal_state.raw_values[register] = status.get(register)

        return self._signal_state

    # ------------------------------------------------------------------ #
    # Entscheidungslogik
    # ------------------------------------------------------------------ #

    def compute_decision(
        self,
        requested_power_kw: float,
        constraints: Dict[str, Any],
    ) -> PowerControlDecision:
        """
        Berechnet den wirksamen Sollwert unter Berücksichtigung der Signalsituation.
        """
        state = self._signal_state
        shutdown = False
        reason = "plan"

        if not self.enabled:
            return PowerControlDecision(
                requested_power_kw=requested_power_kw,
                effective_power_kw=requested_power_kw,
                shutdown=False,
                dso_trip=state.dso_trip,
                safety_alarm=state.safety_alarm,
                dso_limit_pct=state.dso_limit_pct,
                limit_kw=None,
                reason="power_control_disabled",
                commands={},
            )

        # maximale Anlageleistung ermitteln
        max_kw = self._determine_max_power_kw(constraints, requested_power_kw)

        effective_kw = requested_power_kw
        limit_kw: Optional[float] = None

        if state.dso_trip:
            shutdown = True
            reason = "dso_trip"
            effective_kw = 0.0
        elif state.safety_alarm:
            shutdown = True
            reason = "safety_alarm"
            effective_kw = 0.0
        else:
            limits: Dict[str, float] = {}

            if state.dso_limit_pct is not None and max_kw:
                try:
                    limit_kw = max_kw * (float(state.dso_limit_pct) / 100.0)
                    limit_kw = max(0.0, limit_kw)
                    limits["dso_limit_pct"] = limit_kw
                except (TypeError, ValueError):
                    logger.debug("Ungültiges DSO-Limit: %s", state.dso_limit_pct)
                    limit_kw = None

            if limits:
                # kleinstes Limit anwenden
                limit_name, limit_kw = sorted(limits.items(), key=lambda item: item[1])[0]
                effective_kw = self._apply_limit(requested_power_kw, limit_kw)
                reason = limit_name

        commands = self._prepare_commands(effective_kw, shutdown, state)

        return PowerControlDecision(
            requested_power_kw=requested_power_kw,
            effective_power_kw=effective_kw,
            shutdown=shutdown,
            dso_trip=state.dso_trip,
            safety_alarm=state.safety_alarm,
            dso_limit_pct=state.dso_limit_pct,
            limit_kw=limit_kw,
            reason=reason,
            commands=commands,
        )

    # ------------------------------------------------------------------ #
    # Anwenden von Kommandos
    # ------------------------------------------------------------------ #

    def apply_commands(self, modbus_client, decision: PowerControlDecision) -> None:
        """
        Sendet vorbereitete Modbus-Kommandos, falls `auto_write` aktiviert ist.
        """
        if not self.auto_write:
            return

        if not modbus_client or not getattr(modbus_client, "connected", False):
            logger.debug("PowerControl: Modbus-Client nicht verbunden, überspringe Write.")
            return

        for register_name, value in decision.commands.items():
            try:
                ok = modbus_client.write_register(register_name, value)
                if not ok:
                    logger.warning(
                        "PowerControl: Schreiben von %s=%s fehlgeschlagen", register_name, value
                    )
                else:
                    logger.debug(
                        "PowerControl: Write %s=%s (auto_write aktiv)", register_name, value
                    )
            except Exception as exc:
                logger.error(
                    "PowerControl: Fehler beim Schreiben von %s=%s: %s",
                    register_name,
                    value,
                    exc,
                )

    # ------------------------------------------------------------------ #
    # Hilfsfunktionen
    # ------------------------------------------------------------------ #

    def _extract_bool(self, status: Dict[str, Any], cfg: Dict[str, Any]) -> bool:
        register = cfg.get("register")
        if register not in status:
            return False

        value = status.get(register)
        try:
            int_val = int(value)
        except (TypeError, ValueError):
            logger.debug("PowerControl: Bool-Register %s unlesbar (%s)", register, value)
            return False

        mask = cfg.get("mask")
        if mask is not None:
            try:
                return bool(int_val & int(mask))
            except (TypeError, ValueError):
                logger.debug("PowerControl: Maske für %s ungültig: %s", register, mask)
                return False

        equals = cfg.get("equals")
        if equals is not None:
            try:
                return int_val == int(equals)
            except (TypeError, ValueError):
                logger.debug("PowerControl: Vergleichswert für %s ungültig: %s", register, equals)
                return False

        return bool(int_val)

    def _extract_float(self, status: Dict[str, Any], cfg: Dict[str, Any]) -> Optional[float]:
        register = cfg.get("register")
        if register not in status:
            return None

        value = status.get(register)
        try:
            float_val = float(value)
        except (TypeError, ValueError):
            logger.debug("PowerControl: Float-Register %s unlesbar (%s)", register, value)
            return None

        scale = cfg.get("scale", 1.0) or 1.0
        float_val *= float(scale)

        min_pct = cfg.get("min_pct")
        if min_pct is not None:
            float_val = max(float_val, float(min_pct))

        max_pct = cfg.get("max_pct")
        if max_pct is not None:
            float_val = min(float_val, float(max_pct))

        return float_val

    def _determine_max_power_kw(
        self, constraints: Dict[str, Any], requested_power_kw: float
    ) -> Optional[float]:
        """Ermittelt maximale Anlageleistung, berücksichtigt auch grid_connection.max_power_kw"""
        # Prüfe zuerst explizite max_power_kw aus power_control config
        if self.max_power_kw:
            return abs(float(self.max_power_kw))

        # Fallback: Aus Constraints
        discharge = abs(float(constraints.get("power_discharge_max_kw", 0.0)))
        charge = abs(float(constraints.get("power_charge_max_kw", 0.0)))
        max_kw = max(discharge, charge, abs(requested_power_kw))
        return max_kw if max_kw > 0 else None

    @staticmethod
    def _apply_limit(value_kw: float, limit_kw: float) -> float:
        limit_kw = abs(limit_kw)
        if value_kw >= 0:
            return min(value_kw, limit_kw)
        return -min(abs(value_kw), limit_kw)

    def _prepare_commands(
        self,
        effective_kw: float,
        shutdown: bool,
        state: SignalState,
    ) -> Dict[str, Any]:
        commands: Dict[str, Any] = {}

        remote_cfg = self.write_config.get("remote_enable")
        if remote_cfg and remote_cfg.get("register"):
            register = remote_cfg["register"]
            on_value = remote_cfg.get("on", 1)
            off_value = remote_cfg.get("off", 0)
            commands[register] = off_value if shutdown else on_value

        set_w_cfg = self.write_config.get("active_power_set_w")
        if set_w_cfg and set_w_cfg.get("register"):
            register = set_w_cfg["register"]
            scale = set_w_cfg.get("scale", 1.0) or 1.0
            commands[register] = int(round((effective_kw * 1000.0) / scale))

        limit_pct_cfg = self.write_config.get("active_power_limit_pct")
        if limit_pct_cfg and limit_pct_cfg.get("register"):
            register = limit_pct_cfg["register"]
            scale = limit_pct_cfg.get("scale", 1.0) or 1.0
            if state.dso_limit_pct is not None and not shutdown:
                commands[register] = int(round(float(state.dso_limit_pct) / scale))
            else:
                commands[register] = 0

        return commands


