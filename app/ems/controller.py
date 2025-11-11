"""
Phoenyra EMS - Core Controller
Intelligenter EMS-Controller mit Strategien und Optimierung
"""

import time
import threading
import queue
import logging
import uuid
from collections import deque
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple

from .strategy_manager import StrategyManager
from .power_control import PowerControlManager, PowerControlDecision
from services.prices.awattar import get_day_ahead
from services.forecast.simple import pv_forecast, load_forecast
from services.forecast.prophet_forecaster import ProphetForecaster
from services.forecast.weather_forecaster import WeatherForecaster
from services.database.history_db import HistoryDatabase
from services.communication import MQTTClient, MQTTConfig, ModbusClient, ModbusConfig
from config.modbus_profiles import get_profile

logger = logging.getLogger(__name__)


@dataclass
class PlantState:
    """Aktueller Anlagenzustand"""
    
    # Echtzeitwerte
    soc: float = 55.0  # %
    p_pv: float = 0.0  # kW
    p_load: float = 5.0  # kW
    p_grid: float = 0.0  # kW
    p_bess: float = 0.0  # kW
    price: float = 100.0  # EUR/MWh
    temp_c: float = 25.0  # °C
    voltage_v: float = 400.0  # V
    soh: float = 100.0  # %
    
    # Status
    alarm: bool = False
    mode: str = 'auto'  # 'auto', 'manual', 'idle'
    status_bits: Optional[str] = None
    status_code: Optional[int] = None
    status_text: Optional[str] = None
    active_alarms: List[str] = field(default_factory=list)
    telemetry_source: str = 'simulation'
    max_charge_power_kw: float = 0.0
    max_discharge_power_kw: float = 0.0
    max_charge_current_a: float = 0.0
    max_discharge_current_a: float = 0.0
    insulation_kohm: float = 0.0
    
    # Sollwerte
    setpoint_kw: float = 0.0  # Aktueller Sollwert
    active_power_limit_w: Optional[float] = None
    power_limit_reason: Optional[str] = None
    remote_shutdown_requested: bool = False
    
    # EMS-Informationen
    active_strategy: str = 'arbitrage'
    optimization_status: str = 'pending'
    next_optimization: Optional[str] = None
    
    # Site
    site_id: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    # Power-Control / DSO
    dso_trip: bool = False
    safety_alarm: bool = False
    dso_limit_pct: Optional[float] = None


@dataclass
class OptimizationPlan:
    """Optimierter Fahrplan"""
    
    schedule: List[Tuple[datetime, float]] = field(default_factory=list)
    strategy_name: str = ""
    expected_profit: float = 0.0
    confidence: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class EmsCore:
    """
    Intelligenter EMS Core Controller
    
    Funktionen:
    - Strategiebasierte Optimierung
    - Echtzeitsteuerung
    - Prognoseerstellung
    - Fahrplanverfolgung
    """
    
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.state = PlantState()
        
        # Threading & synchronization
        self._stop = threading.Event()
        self._thr = None
        self._listeners = []
        self._state_lock = threading.Lock()
        
        # Strategien und Optimierung
        self.strategy_manager = StrategyManager(cfg.get('strategies', {}))
        self.current_plan: Optional[OptimizationPlan] = None
        
        # Advanced Forecasting (Phase 2)
        self.use_prophet = cfg.get('forecast', {}).get('use_prophet', False)
        self.use_weather = cfg.get('forecast', {}).get('use_weather', False)
        
        if self.use_prophet:
            self.prophet_forecaster = ProphetForecaster(cfg.get('forecast', {}))
            logger.info("Prophet forecaster enabled")
        else:
            self.prophet_forecaster = None
        
        if self.use_weather:
            self.weather_forecaster = WeatherForecaster(cfg.get('forecast', {}))
            logger.info("Weather-based PV forecasting enabled")
        else:
            self.weather_forecaster = None
        
        # Historical Database (Phase 2)
        db_path = cfg.get('database', {}).get('history_path', 'data/ems_history.db')
        self.history_db = HistoryDatabase(db_path)
        logger.info("Historical database initialized")
        
        # Power-Control Manager (DSO / Safety Prioritäten)
        self.power_control_manager = PowerControlManager(cfg.get('power_control', {}))
        
        # Optimierungs-Intervall
        self.optimization_interval_minutes = cfg.get('ems', {}).get('optimization_interval_minutes', 15)
        self.last_optimization = None
        
        # Constraints (aus Config oder Defaults)
        self.constraints = {
            'power_charge_max_kw': cfg.get('bess', {}).get('power_charge_max_kw', 100.0),
            'power_discharge_max_kw': cfg.get('bess', {}).get('power_discharge_max_kw', 100.0),
            'energy_capacity_kwh': cfg.get('bess', {}).get('energy_capacity_kwh', 200.0),
            'soc_min_percent': cfg.get('bess', {}).get('soc_min_percent', 10.0),
            'soc_max_percent': cfg.get('bess', {}).get('soc_max_percent', 90.0),
            'efficiency_charge': cfg.get('bess', {}).get('efficiency_charge', 0.95),
            'efficiency_discharge': cfg.get('bess', {}).get('efficiency_discharge', 0.95),
            'timestep_hours': 1.0
        }
        
        # Demo Mode
        self.demo_mode = cfg.get('prices', {}).get('demo_mode', True)
        
        # Telemetrie-Puffer
        self.telemetry_buffer = deque(maxlen=1800)  # ~1 Stunde bei 2s Intervall
        self._telemetry_lock = threading.Lock()
        self._last_sim_telemetry: Optional[datetime] = None
        
        # MQTT & Modbus Integration
        self.mqtt_client: Optional[MQTTClient] = None
        self._mqtt_telemetry_topic: Optional[str] = None
        self._live_telemetry = False
        self._last_telemetry: Optional[datetime] = None
        self.modbus_client: Optional[ModbusClient] = None
        self._modbus_thread: Optional[threading.Thread] = None
        self._modbus_alarm_definitions: Dict[str, Dict[str, Any]] = {}
        self._modbus_time_synced = False
        self._init_mqtt(cfg.get('mqtt', {}))
        self._init_modbus(cfg.get('modbus', {}))
        
        logger.info("EMS Core initialized with intelligent optimization")
    
    def _init_mqtt(self, mqtt_cfg: Dict[str, Any]):
        """Initialisiert MQTT-Client falls aktiviert"""
        if not mqtt_cfg.get('enabled'):
            logger.info("MQTT integration disabled in configuration")
            return
        
        try:
            base_client_id = mqtt_cfg.get('client_id', 'phoenyra_ems') or 'phoenyra_ems'
            unique_client_id = f"{base_client_id}-{uuid.uuid4().hex[:6]}"
            mqtt_config = MQTTConfig(
                enabled=True,
                broker_host=mqtt_cfg.get('broker_host', 'localhost'),
                broker_port=mqtt_cfg.get('broker_port', 1883),
                username=mqtt_cfg.get('username'),
                password=mqtt_cfg.get('password'),
                client_id=unique_client_id,
                keepalive=mqtt_cfg.get('keepalive', 60),
                qos=mqtt_cfg.get('qos', 1),
                topics=mqtt_cfg.get('topics', {})
            )
            self.mqtt_client = MQTTClient(mqtt_config)
            
            telemetry_topic = mqtt_config.topics.get('subscribe', {}).get('telemetry')
            if telemetry_topic:
                self._mqtt_telemetry_topic = telemetry_topic
                self.mqtt_client.subscribe_to_topic(telemetry_topic, self._handle_mqtt_telemetry)
                logger.info(f"MQTT telemetry topic configured: {telemetry_topic} (client-id: {unique_client_id})")
            else:
                logger.warning("MQTT enabled but no telemetry topic configured; live data will not be ingested")
        except Exception as e:
            logger.error(f"Failed to initialize MQTT client: {e}")
            self.mqtt_client = None

    def _init_modbus(self, modbus_cfg: Dict[str, Any]):
        """Initialisiert Modbus-Client und Polling-Thread"""
        if not modbus_cfg or not modbus_cfg.get('enabled'):
            logger.info("Modbus integration disabled in configuration")
            return

        profile_key = modbus_cfg.get('profile')
        profile = get_profile(profile_key) if profile_key else None

        # Register-Mapping zusammenführen (Profil + Konfiguration)
        registers: Dict[str, Dict[str, Any]] = {}
        if profile:
            profile_registers = profile.get('registers', {})
            for name, definition in profile_registers.items():
                registers[name] = dict(definition)

        user_registers = modbus_cfg.get('registers', {})
        for name, definition in user_registers.items():
            base = registers.get(name, {})
            merged = dict(base)
            if isinstance(definition, dict):
                merged.update(definition)
            else:
                merged['address'] = definition
            registers[name] = merged

        status_codes = {}
        if profile:
            status_codes.update({str(k): v for k, v in profile.get('status_codes', {}).items()})
        config_status_codes = modbus_cfg.get('status_codes', {})
        status_codes.update({str(k): v for k, v in config_status_codes.items()})

        self._modbus_alarm_definitions = {}
        if profile:
            self._modbus_alarm_definitions.update(profile.get('alarms', {}))
        if 'alarms' in modbus_cfg:
            self._modbus_alarm_definitions.update(modbus_cfg.get('alarms', {}))

        try:
            modbus_config = ModbusConfig(
                enabled=True,
                connection_type=modbus_cfg.get('connection_type', 'tcp'),
                host=modbus_cfg.get('host', 'localhost'),
                port=modbus_cfg.get('port', 502),
                slave_id=modbus_cfg.get('slave_id', 1),
                timeout=modbus_cfg.get('timeout', 3.0),
                retries=modbus_cfg.get('retries', 3),
                profile=profile_key,
                poll_interval_s=modbus_cfg.get('poll_interval_s', 2.0),
                status_codes=status_codes,
                registers=registers,
                serial_port=modbus_cfg.get('serial_port', '/dev/ttyUSB0'),
                baudrate=modbus_cfg.get('baudrate', 115200),
                parity=modbus_cfg.get('parity', 'N'),
            )

            self.modbus_client = ModbusClient(modbus_config)

            if not self.modbus_client.config.enabled:
                logger.warning("Modbus client could not be initialized; check configuration")
                self.modbus_client = None
                return

            self._modbus_thread = threading.Thread(
                target=self._modbus_poll_loop,
                name="ems-modbus",
                daemon=True,
            )
            self._modbus_thread.start()
            logger.info("Modbus polling thread started (profile=%s)", profile_key or 'custom')
        except Exception as exc:
            logger.error("Failed to initialize Modbus integration: %s", exc, exc_info=True)
            self.modbus_client = None
            self._modbus_alarm_definitions = {}

    def _modbus_poll_loop(self):
        """Pollt periodisch Modbus-Telemetrie"""
        if not self.modbus_client:
            return

        interval = max(float(self.modbus_client.config.poll_interval_s or 2.0), 0.5)

        while not self._stop.is_set():
            try:
                if not self.modbus_client.connected:
                    if not self.modbus_client.connect():
                        self._modbus_time_synced = False
                        time.sleep(min(interval, 5.0))
                        continue
                if not self._modbus_time_synced:
                    if self.modbus_client.sync_time(datetime.now(timezone.utc)):
                        self._modbus_time_synced = True

                status = self.modbus_client.read_bess_status()
                alarms = {}
                if self._modbus_alarm_definitions:
                    alarms = self.modbus_client.read_alarm_flags(self._modbus_alarm_definitions)

                if status:
                    self._handle_modbus_status(status, alarms)
            except Exception as exc:
                logger.error("Modbus polling error: %s", exc, exc_info=True)
                if self.modbus_client:
                    self.modbus_client.disconnect()
                self._modbus_time_synced = False
                time.sleep(min(interval, 5.0))
            else:
                time.sleep(interval)

    def _handle_modbus_status(self, status: Dict[str, Any], alarms: Optional[Dict[str, bool]] = None):
        """Überführt Modbus-Telemetrie in den internen Anlagenzustand"""
        if not status:
            return

        active_alarm_labels: List[str] = []
        if alarms:
            active_alarm_labels = [name for name, active in alarms.items() if active]

        with self._state_lock:
            self._live_telemetry = True
            self._last_telemetry = datetime.now(timezone.utc)
            self.state.telemetry_source = 'modbus'

            mapping = {
                'soc_percent': ('soc', float),
                'power_kw': ('p_bess', float),
                'voltage_v': ('voltage_v', float),
                'temperature_c': ('temp_c', float),
                'soh_percent': ('soh', float),
                'max_charge_power_kw': ('max_charge_power_kw', float),
                'max_discharge_power_kw': ('max_discharge_power_kw', float),
                'max_charge_current_a': ('max_charge_current_a', float),
                'max_discharge_current_a': ('max_discharge_current_a', float),
                'insulation_resistance_kohm': ('insulation_kohm', float),
            }

            for key, (attr, cast) in mapping.items():
                if key in status and status[key] is not None:
                    try:
                        setattr(self.state, attr, cast(status[key]))
                    except (TypeError, ValueError):
                        logger.debug("Unable to cast Modbus value %s=%s", key, status[key])

            if 'status_code' in status and status['status_code'] is not None:
                try:
                    self.state.status_code = int(round(status['status_code']))
                except (TypeError, ValueError):
                    self.state.status_code = None

            if 'status_text' in status and status['status_text']:
                self.state.status_text = str(status['status_text'])
                self.state.mode = self.state.status_text
            elif self.state.status_code is not None:
                self.state.status_text = f"Status {self.state.status_code}"
                self.state.mode = self.state.status_text

            if active_alarm_labels:
                self.state.active_alarms = active_alarm_labels
                self.state.status_bits = ', '.join(active_alarm_labels)
                self.state.alarm = True
            else:
                self.state.active_alarms = []
                self.state.status_bits = None
                self.state.alarm = False

            self.state.timestamp = datetime.now(timezone.utc).isoformat()
            
            signals = self.power_control_manager.ingest_status(status)
            self.state.dso_trip = signals.dso_trip
            self.state.safety_alarm = signals.safety_alarm
            self.state.dso_limit_pct = signals.dso_limit_pct

        payload = dict(status)
        if alarms is not None:
            payload['alarms'] = alarms

        self._record_telemetry('modbus', payload)
    def _handle_mqtt_telemetry(self, topic: str, payload: Dict[str, Any]):
        """Verarbeitet eingehende Hoymiles-Telemetrie"""
        def as_float(value) -> Optional[float]:
            if value is None:
                return None
            if isinstance(value, (int, float)):
                return float(value)
            try:
                return float(str(value))
            except (TypeError, ValueError):
                return None
        
        try:
            with self._state_lock:
                self._live_telemetry = True
                self._last_telemetry = datetime.now(timezone.utc)
                self.state.telemetry_source = 'mqtt'
                
                soc = as_float(payload.get('soc') or payload.get('sys_soc'))
                if soc is not None:
                    self.state.soc = soc
                
                bat_power = as_float(payload.get('bat_p') or payload.get('sys_bat_p'))
                if bat_power is not None:
                    self.state.p_bess = bat_power / 1000.0  # W -> kW
                
                pv_power = as_float(payload.get('sys_pv_p'))
                if pv_power is not None:
                    self.state.p_pv = pv_power / 1000.0
                
                load_power = as_float(payload.get('sys_load_p'))
                if load_power is not None:
                    self.state.p_load = load_power / 1000.0
                
                grid_power = as_float(payload.get('sys_grid_p') or payload.get('grid_on_p'))
                if grid_power is not None:
                    self.state.p_grid = grid_power / 1000.0
                
                status = payload.get('bat_sts')
                if isinstance(status, str) and status:
                    self.state.mode = status
                    self.state.status_bits = payload.get('status_bits') or payload.get('fault_code')
                
                voltage = as_float(payload.get('voltage') or payload.get('bat_v') or payload.get('sys_dc_v'))
                if voltage is not None:
                    self.state.voltage_v = voltage
                
                temperature = as_float(payload.get('temperature') or payload.get('bat_temp') or payload.get('cell_temp'))
                if temperature is not None:
                    self.state.temp_c = temperature
                
                self.state.timestamp = datetime.now(timezone.utc).isoformat()

            self._record_telemetry('mqtt', payload)
        except Exception as e:
            logger.error(f"Failed to process MQTT telemetry message on {topic}: {e}", exc_info=True)
    
    def _record_telemetry(self, source: str, payload: Optional[Dict[str, Any]] = None):
        """Speichert Telemetrie-Schnappschuss im Ringpuffer"""
        with self._state_lock:
            snapshot = {
                'timestamp': self.state.timestamp,
                'soc': self.state.soc,
                'soh': self.state.soh,
                'p_bess_kw': self.state.p_bess,
                'p_grid_kw': self.state.p_grid,
                'p_load_kw': self.state.p_load,
                'p_pv_kw': self.state.p_pv,
                'setpoint_kw': self.state.setpoint_kw,
                'voltage_v': self.state.voltage_v,
                'temperature_c': self.state.temp_c,
                'mode': self.state.mode,
                'status_code': self.state.status_code,
                'status_text': self.state.status_text,
                'status_bits': self.state.status_bits,
                'max_charge_power_kw': self.state.max_charge_power_kw,
                'max_discharge_power_kw': self.state.max_discharge_power_kw,
                'max_charge_current_a': self.state.max_charge_current_a,
                'max_discharge_current_a': self.state.max_discharge_current_a,
                'insulation_kohm': self.state.insulation_kohm,
                'alarms': list(self.state.active_alarms),
                'telemetry_source': source,
                'dso_trip': self.state.dso_trip,
                'safety_alarm': self.state.safety_alarm,
                'dso_limit_pct': self.state.dso_limit_pct,
                'active_power_limit_w': self.state.active_power_limit_w,
                'power_limit_reason': self.state.power_limit_reason,
                'remote_shutdown_requested': self.state.remote_shutdown_requested,
            }
        
        if payload:
            snapshot['raw'] = payload
        
        with self._telemetry_lock:
            self.telemetry_buffer.append(snapshot)
    
    def get_recent_telemetry(self, minutes: int = 60, limit: int = 900) -> List[Dict[str, Any]]:
        """Gibt Telemetrie der letzten Minuten zurück"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        cutoff_iso = cutoff.isoformat()
        
        with self._telemetry_lock:
            data = [entry for entry in self.telemetry_buffer if entry['timestamp'] >= cutoff_iso]
        
        if limit and len(data) > limit:
            data = data[-limit:]
        
        return data

    def get_power_flow(self, minutes: int = 5) -> Dict[str, Any]:
        """Aggregiert Energieflüsse (kWh) für Powerflow-Diagramm"""
        telemetry = self.get_recent_telemetry(minutes=minutes, limit=0)
        if len(telemetry) < 2:
            return {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'interval_minutes': minutes,
                'links': [],
                'summary': {
                    'pv_generated_kwh': 0.0,
                    'load_consumed_kwh': 0.0,
                    'bess_charge_kwh': 0.0,
                    'bess_discharge_kwh': 0.0,
                    'grid_import_kwh': 0.0,
                    'grid_export_kwh': 0.0
                }
            }

        def _as_float(sample: Dict[str, Any], key: str) -> float:
            value = sample.get(key)
            if value is None:
                return 0.0
            try:
                return float(value)
            except (TypeError, ValueError):
                return 0.0

        flows = {
            ('PV', 'Last'): 0.0,
            ('PV', 'Batterie'): 0.0,
            ('PV', 'Netz'): 0.0,
            ('Batterie', 'Last'): 0.0,
            ('Batterie', 'Netz'): 0.0,
            ('Netz', 'Last'): 0.0,
            ('Netz', 'Batterie'): 0.0,
        }
        summary = {
            'pv_generated_kwh': 0.0,
            'load_consumed_kwh': 0.0,
            'bess_charge_kwh': 0.0,
            'bess_discharge_kwh': 0.0,
            'grid_import_kwh': 0.0,
            'grid_export_kwh': 0.0
        }

        try:
            prev = telemetry[0]
            prev_ts = datetime.fromisoformat(prev['timestamp'])
        except (KeyError, ValueError, TypeError):
            prev = None
            prev_ts = None

        for point in telemetry[1:]:
            if not prev_ts:
                try:
                    prev = point
                    prev_ts = datetime.fromisoformat(point['timestamp'])
                except (KeyError, ValueError, TypeError):
                    prev = None
                    prev_ts = None
                continue

            try:
                current_ts = datetime.fromisoformat(point['timestamp'])
            except (KeyError, ValueError, TypeError):
                prev = point
                prev_ts = None
                continue

            delta_hours = (current_ts - prev_ts).total_seconds() / 3600.0
            if delta_hours <= 0:
                prev = point
                prev_ts = current_ts
                continue

            load_kw = max((_as_float(prev, 'p_load_kw') + _as_float(point, 'p_load_kw')) / 2.0, 0.0)
            pv_kw = max((_as_float(prev, 'p_pv_kw') + _as_float(point, 'p_pv_kw')) / 2.0, 0.0)
            bess_kw = (_as_float(prev, 'p_bess_kw') + _as_float(point, 'p_bess_kw')) / 2.0
            grid_kw = (_as_float(prev, 'p_grid_kw') + _as_float(point, 'p_grid_kw')) / 2.0

            bess_discharge_kw = max(bess_kw, 0.0)
            bess_charge_kw = max(-bess_kw, 0.0)
            grid_import_kw = max(grid_kw, 0.0)
            grid_export_kw = max(-grid_kw, 0.0)

            summary['pv_generated_kwh'] += pv_kw * delta_hours
            summary['load_consumed_kwh'] += load_kw * delta_hours
            summary['bess_discharge_kwh'] += bess_discharge_kw * delta_hours
            summary['bess_charge_kwh'] += bess_charge_kw * delta_hours
            summary['grid_import_kwh'] += grid_import_kw * delta_hours
            summary['grid_export_kwh'] += grid_export_kw * delta_hours

            pv_to_load_kw = min(pv_kw, load_kw)
            remaining_load_kw = max(load_kw - pv_to_load_kw, 0.0)

            bess_to_load_kw = min(bess_discharge_kw, remaining_load_kw)
            remaining_load_kw -= bess_to_load_kw

            grid_to_load_kw = min(grid_import_kw, remaining_load_kw)
            remaining_load_kw -= grid_to_load_kw

            pv_surplus_kw = max(pv_kw - pv_to_load_kw, 0.0)
            bess_charge_remaining_kw = bess_charge_kw

            pv_to_bess_kw = min(pv_surplus_kw, bess_charge_remaining_kw)
            pv_surplus_kw -= pv_to_bess_kw
            bess_charge_remaining_kw -= pv_to_bess_kw

            grid_to_bess_kw = min(max(grid_import_kw - grid_to_load_kw, 0.0), bess_charge_remaining_kw)
            bess_charge_remaining_kw -= grid_to_bess_kw

            pv_to_grid_kw = max(pv_surplus_kw, 0.0)
            bess_to_grid_kw = max(bess_discharge_kw - bess_to_load_kw, 0.0)

            flows[('PV', 'Last')] += pv_to_load_kw * delta_hours
            flows[('PV', 'Batterie')] += pv_to_bess_kw * delta_hours
            flows[('PV', 'Netz')] += pv_to_grid_kw * delta_hours
            flows[('Batterie', 'Last')] += bess_to_load_kw * delta_hours
            flows[('Batterie', 'Netz')] += bess_to_grid_kw * delta_hours
            flows[('Netz', 'Last')] += grid_to_load_kw * delta_hours
            flows[('Netz', 'Batterie')] += grid_to_bess_kw * delta_hours

            prev = point
            prev_ts = current_ts

        links = [
            {'source': src, 'target': tgt, 'energy_kwh': round(val, 3)}
            for (src, tgt), val in flows.items()
            if val > 0.0005
        ]

        return {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'interval_minutes': minutes,
            'links': links,
            'summary': {key: round(value, 3) for key, value in summary.items()}
        }

    def decide(self):
        """
        Haupt-Entscheidungslogik
        
        1. Prüfe ob neue Optimierung nötig
        2. Hole aktuellen Sollwert aus Fahrplan
        3. Aktualisiere State
        """
        
        now = datetime.now(timezone.utc)
        
        # Prüfe ob Optimierung nötig
        if self._needs_optimization(now):
            self._run_optimization()
        
        record_simulation = False
        control_decision: Optional[PowerControlDecision] = None
        
        with self._state_lock:
            # Hole Sollwert aus aktuellem Fahrplan
            if self.current_plan and self.current_plan.schedule:
                requested_setpoint_kw = self._get_setpoint_from_plan(now)
            else:
                requested_setpoint_kw = 0.0
            
            # Prüfe ob Telemetrie noch aktuell ist (max 120s)
            if self._live_telemetry and self._last_telemetry:
                age = (now - self._last_telemetry).total_seconds()
                if age > 120:
                    self._live_telemetry = False
                    self.state.telemetry_source = 'simulation'
                    logger.warning("Live telemetry stale (>120s); reverting to simulated values")
            
            # Power-Control Entscheidung anwenden
            control_decision = self.power_control_manager.compute_decision(
                requested_power_kw=requested_setpoint_kw,
                constraints=self.constraints,
            )
            self.state.setpoint_kw = control_decision.effective_power_kw
            self.state.remote_shutdown_requested = control_decision.shutdown
            self.state.active_power_limit_w = control_decision.active_power_limit_w
            self.state.power_limit_reason = control_decision.reason
            if control_decision.dso_limit_pct is not None:
                self.state.dso_limit_pct = control_decision.dso_limit_pct
            
            # Simuliere BESS-Reaktion nur wenn keine Live-Daten vorliegen
            if not self._live_telemetry:
                self.state.telemetry_source = 'simulation'
                self.state.p_bess = self.state.setpoint_kw
                self.state.p_grid = self.state.p_load - self.state.p_pv - self.state.p_bess
                
                if not self._last_sim_telemetry or (now - self._last_sim_telemetry).total_seconds() >= 10:
                    record_simulation = True
                    self._last_sim_telemetry = now
            
            # Update Timestamp
            self.state.timestamp = now.isoformat()
            
            # Log State to History (alle 5 Minuten)
            should_log = not hasattr(self, '_last_history_log') or (now - self._last_history_log).total_seconds() >= 300
            if should_log:
                try:
                    self.history_db.log_state(self.to_dict())
                    self._last_history_log = now
                except Exception as e:
                    logger.error(f"Failed to log state to history: {e}")
            
            soc = self.state.soc
            setpoint_kw = self.state.setpoint_kw
            strategy = self.state.active_strategy
        
        logger.debug(f"State: SoC={soc:.1f}%, "
                    f"Setpoint={setpoint_kw:.1f}kW, "
                    f"Strategy={strategy}")
        
        if control_decision:
            self.power_control_manager.apply_commands(self.modbus_client, control_decision)
        
        if record_simulation:
            self._record_telemetry('simulation')
    
    def _needs_optimization(self, now: datetime) -> bool:
        """Prüft ob neue Optimierung nötig ist"""
        
        if self.last_optimization is None:
            return True
        
        time_since_last = (now - self.last_optimization).total_seconds() / 60
        
        return time_since_last >= self.optimization_interval_minutes
    
    def _run_optimization(self):
        """
        Führt vollständige Optimierung durch
        
        1. Hole Prognosedaten (Preise, Last, PV)
        2. Wähle optimale Strategie
        3. Optimiere Fahrplan
        4. Speichere Plan
        """
        
        logger.info("Running optimization cycle...")
        
        try:
            # 1. Hole Prognosedaten
            forecast_data = self._get_forecast_data()
            
            # 2. Aktueller Zustand
            current_state = {
                'soc': self.state.soc,
                'p_bess': self.state.p_bess,
                'p_pv': self.state.p_pv,
                'p_load': self.state.p_load,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # 3. Wähle Strategie
            strategy_name = self.strategy_manager.select_strategy(current_state, forecast_data)
            self.state.active_strategy = strategy_name
            
            # 4. Optimiere mit gewählter Strategie
            result = self.strategy_manager.optimize_with_strategy(
                strategy_name,
                current_state,
                forecast_data,
                self.constraints
            )
            
            # 5. Speichere Fahrplan
            self.current_plan = OptimizationPlan(
                schedule=result.schedule,
                strategy_name=result.strategy_name,
                expected_profit=result.expected_profit,
                confidence=result.confidence_score,
                metadata=result.metadata
            )
            
            self.last_optimization = datetime.now(timezone.utc)
            self.state.optimization_status = 'success'
            
            # Log Optimization to History
            try:
                self.history_db.log_optimization(result.to_dict())
            except Exception as e:
                logger.error(f"Failed to log optimization to history: {e}")
            
            logger.info(f"Optimization completed: strategy={strategy_name}, "
                       f"profit={result.expected_profit:.2f} EUR, "
                       f"confidence={result.confidence_score:.2f}")
            
        except Exception as e:
            logger.error(f"Optimization failed: {e}", exc_info=True)
            self.state.optimization_status = 'failed'
    
    def _get_forecast_data(self) -> Dict[str, Any]:
        """
        Hole alle Prognosedaten
        
        Phase 2: Verwendet Prophet und Weather-Based Forecasting wenn verfügbar
        """
        
        site_id = self.state.site_id
        
        # Preise (immer von aWATTar oder Demo)
        prices = get_day_ahead(
            region=self.cfg.get('prices', {}).get('region', 'AT'),
            demo_mode=self.demo_mode
        )
        
        # PV-Prognose (Weather-based wenn verfügbar)
        if self.weather_forecaster:
            try:
                pv = self.weather_forecaster.forecast_pv(hours=24)
                logger.debug("Using weather-based PV forecast")
            except Exception as e:
                logger.warning(f"Weather-based PV forecast failed: {e}, using fallback")
                pv = pv_forecast(site_id=site_id, hours=24, 
                               demo_mode=self.cfg.get('forecast', {}).get('demo_mode', True))
        else:
            pv = pv_forecast(
                site_id=site_id,
                hours=24,
                demo_mode=self.cfg.get('forecast', {}).get('demo_mode', True)
            )
        
        # Last-Prognose (Prophet wenn verfügbar)
        if self.prophet_forecaster:
            try:
                # Generiere oder hole historische Daten
                history = self.prophet_forecaster.generate_synthetic_history(days=30)
                load = self.prophet_forecaster.forecast_load(
                    historical_data=history['load'],
                    hours=24
                )
                logger.debug("Using Prophet load forecast")
            except Exception as e:
                logger.warning(f"Prophet load forecast failed: {e}, using fallback")
                load = load_forecast(site_id=site_id, hours=24,
                                   demo_mode=self.cfg.get('forecast', {}).get('demo_mode', True))
        else:
            load = load_forecast(
                site_id=site_id,
                hours=24,
                demo_mode=self.cfg.get('forecast', {}).get('demo_mode', True)
            )
        
        return {
            'prices': prices,
            'pv': pv,
            'load': load
        }
    
    def _get_setpoint_from_plan(self, now: datetime) -> float:
        """
        Extrahiert Sollwert aus Fahrplan für aktuelle Zeit
        
        Verwendet den nächstgelegenen Zeitpunkt im Fahrplan
        """
        
        if not self.current_plan or not self.current_plan.schedule:
            return 0.0
        
        # Finde nächstgelegenen Eintrag
        closest_entry = None
        min_diff = None
        
        for ts, power in self.current_plan.schedule:
            diff = abs((ts - now).total_seconds())
            
            if min_diff is None or diff < min_diff:
                min_diff = diff
                closest_entry = (ts, power)
        
        if closest_entry:
            return closest_entry[1]
        
        return 0.0
    
    def _loop(self):
        """Haupt-Loop"""
        dt = self.cfg.get('ems', {}).get('timestep_s', 2)
        
        logger.info(f"EMS loop started (timestep={dt}s)")
        
        while not self._stop.is_set():
            self.decide()
            self._broadcast()
            time.sleep(dt)
    
    def _broadcast(self):
        """Broadcast State zu SSE-Listenern"""
        for q in list(self._listeners):
            try:
                q.put_nowait(self.to_dict())
            except queue.Full:
                pass
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
    
    def sse_register(self):
        """Registriert SSE-Listener"""
        q = queue.Queue(maxsize=10)
        self._listeners.append(q)
        return q
    
    def sse_unregister(self, q):
        """Deregistriert SSE-Listener"""
        try:
            self._listeners.remove(q)
        except ValueError:
            pass
    
    def start(self):
        """Startet EMS Loop"""
        if self._thr and self._thr.is_alive():
            return
        
        self._stop.clear()
        self._thr = threading.Thread(target=self._loop, daemon=True)
        self._thr.start()
        
        if self.mqtt_client:
            if self.mqtt_client.connect():
                logger.info("MQTT client connection initiated")
            else:
                logger.error("Failed to initiate MQTT connection")
        
        logger.info("EMS Core started")
    
    def stop(self):
        """Stoppt EMS Loop"""
        self._stop.set()
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        if self.modbus_client:
            self.modbus_client.disconnect()
        if self._modbus_thread and self._modbus_thread.is_alive():
            self._modbus_thread.join(timeout=5)
            self._modbus_thread = None
        logger.info("EMS Core stopped")
    
    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert State zu Dictionary"""
        state_dict = asdict(self.state)
        
        # Füge Plan-Informationen hinzu
        if self.current_plan:
            state_dict['current_plan'] = {
                'strategy': self.current_plan.strategy_name,
                'expected_profit': round(self.current_plan.expected_profit, 2),
                'confidence': round(self.current_plan.confidence, 2),
                'schedule_length': len(self.current_plan.schedule)
            }
        
        return state_dict
    
    def get_current_plan(self) -> Optional[Dict[str, Any]]:
        """Gibt aktuellen Fahrplan zurück"""
        if not self.current_plan:
            return None
        
        return {
            'schedule': [(ts.isoformat(), power) for ts, power in self.current_plan.schedule],
            'strategy_name': self.current_plan.strategy_name,
            'expected_profit': self.current_plan.expected_profit,
            'confidence': self.current_plan.confidence,
            'created_at': self.current_plan.created_at.isoformat(),
            'metadata': self.current_plan.metadata
        }
    
    def set_manual_strategy(self, strategy_name: str) -> bool:
        """Setzt manuelle Strategie"""
        success = self.strategy_manager.set_manual_strategy(strategy_name)
        if success:
            # Trigger sofortige Neuoptimierung
            self.last_optimization = None
        return success
