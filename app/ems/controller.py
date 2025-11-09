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
from services.prices.awattar import get_day_ahead
from services.forecast.simple import pv_forecast, load_forecast
from services.forecast.prophet_forecaster import ProphetForecaster
from services.forecast.weather_forecaster import WeatherForecaster
from services.database.history_db import HistoryDatabase
from services.communication.mqtt_client import MQTTClient, MQTTConfig

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
    
    # Status
    alarm: bool = False
    mode: str = 'auto'  # 'auto', 'manual', 'idle'
    status_bits: Optional[str] = None
    telemetry_source: str = 'simulation'
    
    # Sollwerte
    setpoint_kw: float = 0.0  # Aktueller Sollwert
    
    # EMS-Informationen
    active_strategy: str = 'arbitrage'
    optimization_status: str = 'pending'
    next_optimization: Optional[str] = None
    
    # Site
    site_id: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


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
        
        # MQTT Integration
        self.mqtt_client: Optional[MQTTClient] = None
        self._mqtt_telemetry_topic: Optional[str] = None
        self._live_telemetry = False
        self._last_telemetry: Optional[datetime] = None
        self._init_mqtt(cfg.get('mqtt', {}))
        
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
                'p_bess_kw': self.state.p_bess,
                'p_grid_kw': self.state.p_grid,
                'p_load_kw': self.state.p_load,
                'p_pv_kw': self.state.p_pv,
                'setpoint_kw': self.state.setpoint_kw,
                'voltage_v': self.state.voltage_v,
                'temperature_c': self.state.temp_c,
                'mode': self.state.mode,
                'status_bits': self.state.status_bits,
                'telemetry_source': source
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
        
        with self._state_lock:
            # Hole Sollwert aus aktuellem Fahrplan
            if self.current_plan and self.current_plan.schedule:
                setpoint = self._get_setpoint_from_plan(now)
                self.state.setpoint_kw = setpoint
            else:
                self.state.setpoint_kw = 0.0
            
            # Prüfe ob Telemetrie noch aktuell ist (max 120s)
            if self._live_telemetry and self._last_telemetry:
                age = (now - self._last_telemetry).total_seconds()
                if age > 120:
                    self._live_telemetry = False
                    self.state.telemetry_source = 'simulation'
                    logger.warning("MQTT telemetry stale (>120s); reverting to simulated values")
            
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
