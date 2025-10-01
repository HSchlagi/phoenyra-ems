"""
Phoenyra EMS - Historical Database
SQLite-basierte Speicherung für Performance-Tracking
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging
import json

logger = logging.getLogger(__name__)


class HistoryDatabase:
    """
    Historische Datenbank für EMS Performance-Tracking
    
    Speichert:
    - Anlagenzustände (State History)
    - Optimierungsergebnisse (Optimization History)
    - Strategiewechsel (Strategy Changes)
    - Performance-Metriken (KPIs)
    """
    
    def __init__(self, db_path: str = "data/ems_history.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        logger.info(f"History database initialized: {self.db_path}")
    
    def _init_database(self):
        """Erstellt Datenbank-Schema"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # State History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS state_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    soc REAL,
                    p_bess REAL,
                    p_pv REAL,
                    p_load REAL,
                    p_grid REAL,
                    price REAL,
                    active_strategy TEXT,
                    setpoint_kw REAL,
                    mode TEXT
                )
            """)
            
            # Optimization History Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS optimization_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    strategy_name TEXT NOT NULL,
                    expected_profit REAL,
                    expected_revenue REAL,
                    expected_cost REAL,
                    confidence REAL,
                    optimization_status TEXT,
                    solver TEXT,
                    metadata TEXT
                )
            """)
            
            # Strategy Changes Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS strategy_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    old_strategy TEXT,
                    new_strategy TEXT,
                    reason TEXT,
                    scores TEXT
                )
            """)
            
            # Performance Metrics Table (aggregiert pro Tag)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL UNIQUE,
                    total_profit REAL,
                    total_revenue REAL,
                    total_cost REAL,
                    energy_charged REAL,
                    energy_discharged REAL,
                    cycles REAL,
                    avg_soc REAL,
                    min_soc REAL,
                    max_soc REAL,
                    strategy_usage TEXT,
                    optimization_count INTEGER
                )
            """)
            
            # Indices für Performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_state_timestamp 
                ON state_history(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_optimization_timestamp 
                ON optimization_history(timestamp)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_daily_date 
                ON daily_metrics(date)
            """)
            
            conn.commit()
    
    def log_state(self, state: Dict[str, Any]):
        """Speichert Anlagenzustand"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO state_history 
                (timestamp, soc, p_bess, p_pv, p_load, p_grid, price, 
                 active_strategy, setpoint_kw, mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state.get('timestamp', datetime.now(timezone.utc).isoformat()),
                state.get('soc'),
                state.get('p_bess'),
                state.get('p_pv'),
                state.get('p_load'),
                state.get('p_grid'),
                state.get('price'),
                state.get('active_strategy'),
                state.get('setpoint_kw'),
                state.get('mode')
            ))
            
            conn.commit()
    
    def log_optimization(self, optimization_result: Dict[str, Any]):
        """Speichert Optimierungsergebnis"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            metadata = optimization_result.get('metadata', {})
            
            cursor.execute("""
                INSERT INTO optimization_history 
                (timestamp, strategy_name, expected_profit, expected_revenue, 
                 expected_cost, confidence, optimization_status, solver, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                optimization_result.get('strategy_name'),
                optimization_result.get('expected_profit'),
                optimization_result.get('expected_revenue'),
                optimization_result.get('expected_cost'),
                optimization_result.get('confidence'),
                metadata.get('optimization_status'),
                metadata.get('solver'),
                json.dumps(metadata)
            ))
            
            conn.commit()
    
    def log_strategy_change(self, old_strategy: str, new_strategy: str, 
                           reason: str = "", scores: Optional[Dict[str, float]] = None):
        """Speichert Strategiewechsel"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO strategy_changes 
                (timestamp, old_strategy, new_strategy, reason, scores)
                VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                old_strategy,
                new_strategy,
                reason,
                json.dumps(scores) if scores else None
            ))
            
            conn.commit()
    
    def get_state_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Holt State History der letzten N Stunden"""
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM state_history 
                WHERE timestamp >= ? 
                ORDER BY timestamp ASC
            """, (cutoff.isoformat(),))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_optimization_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """Holt Optimization History der letzten N Tage"""
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM optimization_history 
                WHERE timestamp >= ? 
                ORDER BY timestamp DESC
            """, (cutoff.isoformat(),))
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                data = dict(row)
                if data.get('metadata'):
                    try:
                        data['metadata'] = json.loads(data['metadata'])
                    except:
                        pass
                results.append(data)
            
            return results
    
    def calculate_daily_metrics(self, date: Optional[datetime] = None):
        """Berechnet und speichert tägliche Metriken"""
        
        if date is None:
            date = datetime.now(timezone.utc).date()
        elif isinstance(date, datetime):
            date = date.date()
        
        start = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # State Metriken
            cursor.execute("""
                SELECT 
                    AVG(soc) as avg_soc,
                    MIN(soc) as min_soc,
                    MAX(soc) as max_soc,
                    SUM(CASE WHEN p_bess < 0 THEN ABS(p_bess) ELSE 0 END) as energy_charged,
                    SUM(CASE WHEN p_bess > 0 THEN p_bess ELSE 0 END) as energy_discharged
                FROM state_history
                WHERE timestamp >= ? AND timestamp < ?
            """, (start.isoformat(), end.isoformat()))
            
            state_metrics = dict(cursor.fetchone())
            
            # Optimization Metriken
            cursor.execute("""
                SELECT 
                    SUM(expected_profit) as total_profit,
                    SUM(expected_revenue) as total_revenue,
                    SUM(expected_cost) as total_cost,
                    COUNT(*) as optimization_count,
                    GROUP_CONCAT(strategy_name) as strategies
                FROM optimization_history
                WHERE timestamp >= ? AND timestamp < ?
            """, (start.isoformat(), end.isoformat()))
            
            opt_metrics = dict(cursor.fetchone())
            
            # Strategie-Nutzung
            strategy_usage = {}
            if opt_metrics.get('strategies'):
                strategies = opt_metrics['strategies'].split(',')
                for s in strategies:
                    strategy_usage[s] = strategy_usage.get(s, 0) + 1
            
            # Zyklen berechnen (vereinfacht)
            energy_discharged = state_metrics.get('energy_discharged', 0) or 0
            cycles = energy_discharged / 200.0  # Annahme: 200 kWh Kapazität
            
            # Speichere Daily Metrics
            cursor.execute("""
                INSERT OR REPLACE INTO daily_metrics
                (date, total_profit, total_revenue, total_cost, 
                 energy_charged, energy_discharged, cycles,
                 avg_soc, min_soc, max_soc, strategy_usage, optimization_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date.isoformat(),
                opt_metrics.get('total_profit', 0),
                opt_metrics.get('total_revenue', 0),
                opt_metrics.get('total_cost', 0),
                state_metrics.get('energy_charged', 0),
                energy_discharged,
                cycles,
                state_metrics.get('avg_soc'),
                state_metrics.get('min_soc'),
                state_metrics.get('max_soc'),
                json.dumps(strategy_usage),
                opt_metrics.get('optimization_count', 0)
            ))
            
            conn.commit()
            
            logger.info(f"Daily metrics calculated for {date}")
    
    def get_daily_metrics(self, days: int = 30) -> List[Dict[str, Any]]:
        """Holt tägliche Metriken"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM daily_metrics 
                ORDER BY date DESC 
                LIMIT ?
            """, (days,))
            
            rows = cursor.fetchall()
            results = []
            for row in rows:
                data = dict(row)
                if data.get('strategy_usage'):
                    try:
                        data['strategy_usage'] = json.loads(data['strategy_usage'])
                    except:
                        pass
                results.append(data)
            
            return results
    
    def get_performance_summary(self, days: int = 30) -> Dict[str, Any]:
        """Erstellt Performance-Zusammenfassung"""
        
        daily_metrics = self.get_daily_metrics(days)
        
        if not daily_metrics:
            return {}
        
        total_profit = sum(m.get('total_profit', 0) or 0 for m in daily_metrics)
        total_revenue = sum(m.get('total_revenue', 0) or 0 for m in daily_metrics)
        total_cost = sum(m.get('total_cost', 0) or 0 for m in daily_metrics)
        total_cycles = sum(m.get('cycles', 0) or 0 for m in daily_metrics)
        
        avg_soc = sum(m.get('avg_soc', 0) or 0 for m in daily_metrics) / len(daily_metrics)
        
        # Strategie-Verteilung
        all_strategies = {}
        for m in daily_metrics:
            usage = m.get('strategy_usage', {})
            if isinstance(usage, dict):
                for s, count in usage.items():
                    all_strategies[s] = all_strategies.get(s, 0) + count
        
        return {
            'period_days': len(daily_metrics),
            'total_profit': round(total_profit, 2),
            'total_revenue': round(total_revenue, 2),
            'total_cost': round(total_cost, 2),
            'avg_daily_profit': round(total_profit / len(daily_metrics), 2),
            'total_cycles': round(total_cycles, 2),
            'avg_soc': round(avg_soc, 1),
            'strategy_distribution': all_strategies,
            'first_date': daily_metrics[-1].get('date'),
            'last_date': daily_metrics[0].get('date')
        }


