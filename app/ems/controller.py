"""
Phoenyra EMS - Core Controller
Intelligenter EMS-Controller mit Strategien und Optimierung
"""

import time
import threading
import queue
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple

from .strategy_manager import StrategyManager
from services.prices.awattar import get_day_ahead
from services.forecast.simple import pv_forecast, load_forecast
from services.forecast.prophet_forecaster import ProphetForecaster
from services.forecast.weather_forecaster import WeatherForecaster
from services.database.history_db import HistoryDatabase

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
    
    # Status
    alarm: bool = False
    mode: str = 'auto'  # 'auto', 'manual', 'idle'
    
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
        
        # Threading
        self._stop = threading.Event()
        self._thr = None
        self._listeners = []
        
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
        
        logger.info("EMS Core initialized with intelligent optimization")
    
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
        
        # Hole Sollwert aus aktuellem Fahrplan
        if self.current_plan and self.current_plan.schedule:
            setpoint = self._get_setpoint_from_plan(now)
            self.state.setpoint_kw = setpoint
        else:
            self.state.setpoint_kw = 0.0
        
        # Simuliere BESS-Reaktion (vereinfacht)
        self.state.p_bess = self.state.setpoint_kw
        self.state.p_grid = self.state.p_load - self.state.p_pv - self.state.p_bess
        
        # Update Timestamp
        self.state.timestamp = now.isoformat()
        
        # Log State to History (alle 5 Minuten)
        if not hasattr(self, '_last_history_log') or (now - self._last_history_log).total_seconds() >= 300:
            try:
                self.history_db.log_state(self.to_dict())
                self._last_history_log = now
            except Exception as e:
                logger.error(f"Failed to log state to history: {e}")
        
        logger.debug(f"State: SoC={self.state.soc:.1f}%, "
                    f"Setpoint={self.state.setpoint_kw:.1f}kW, "
                    f"Strategy={self.state.active_strategy}")
    
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
        
        logger.info("EMS Core started")
    
    def stop(self):
        """Stoppt EMS Loop"""
        self._stop.set()
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
