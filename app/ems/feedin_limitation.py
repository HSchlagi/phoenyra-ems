"""
Feed-in Limitation (Einspeisebegrenzung) für Phoenyra EMS
---------------------------------------------------------

Stellt dynamische Einspeisebegrenzung bereit (0% / 50% / 70% / 100%).
Kann zeitbasiert oder fest konfiguriert werden.
"""

import logging
from datetime import datetime, time
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)


class FeedinLimitationManager:
    """
    Verwaltet Einspeisebegrenzung basierend auf Konfiguration.
    
    Konfigurationsschema (`feedin_limitation`):
        enabled: bool
        mode: 'off' | 'fixed' | 'dynamic'
        fixed_limit_pct: float (bei mode: fixed)
        dynamic_rules:
            - time: "HH:MM-HH:MM"  # Zeitfenster
              limit_pct: float
        pv_forecast_integration: bool (optional, default false)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.enabled: bool = bool(config.get("enabled", False))
        self.mode: str = config.get("mode", "off")  # 'off', 'fixed', 'dynamic'
        self.fixed_limit_pct: float = float(config.get("fixed_limit_pct", 70.0))
        self.dynamic_rules: List[Dict[str, Any]] = config.get("dynamic_rules", [])
        self.pv_forecast_integration: bool = bool(config.get("pv_forecast_integration", False))
        
        # Parse Zeitfenster
        self._parsed_rules: List[Tuple[time, time, float]] = []
        for rule in self.dynamic_rules:
            try:
                time_str = rule.get("time", "")
                limit_pct = float(rule.get("limit_pct", 100.0))
                
                if "-" in time_str:
                    start_str, end_str = time_str.split("-", 1)
                    start_time = self._parse_time(start_str.strip())
                    end_time = self._parse_time(end_str.strip())
                    self._parsed_rules.append((start_time, end_time, limit_pct))
                else:
                    logger.warning(f"Ungültiges Zeitfenster-Format: {time_str}")
            except Exception as e:
                logger.warning(f"Fehler beim Parsen der Regel {rule}: {e}")
    
    def _parse_time(self, time_str: str) -> time:
        """Parst Zeitstring 'HH:MM' zu time-Objekt"""
        try:
            parts = time_str.split(":")
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            return time(hour, minute)
        except (ValueError, IndexError) as e:
            logger.error(f"Ungültiges Zeitformat: {time_str}: {e}")
            return time(0, 0)
    
    def get_current_limit_pct(self, current_time: Optional[datetime] = None) -> float:
        """
        Gibt die aktuelle Einspeisebegrenzung in Prozent zurück.
        
        Returns:
            float: Limit in Prozent (0.0 - 100.0)
        """
        if not self.enabled or self.mode == "off":
            return 100.0  # Keine Begrenzung
        
        if self.mode == "fixed":
            return max(0.0, min(100.0, self.fixed_limit_pct))
        
        if self.mode == "dynamic":
            if not self._parsed_rules:
                logger.warning("Dynamic mode aktiviert, aber keine Regeln definiert. Fallback zu 100%")
                return 100.0
            
            now = current_time or datetime.now()
            current_time_obj = now.time()
            
            # Prüfe alle Regeln (erste passende wird verwendet)
            for start_time, end_time, limit_pct in self._parsed_rules:
                if self._time_in_range(current_time_obj, start_time, end_time):
                    return max(0.0, min(100.0, limit_pct))
            
            # Keine Regel passt -> 100% (keine Begrenzung)
            return 100.0
        
        return 100.0
    
    def _time_in_range(self, check_time: time, start_time: time, end_time: time) -> bool:
        """Prüft ob check_time im Bereich [start_time, end_time) liegt"""
        if start_time <= end_time:
            # Normales Zeitfenster (z.B. 06:00-18:00)
            return start_time <= check_time < end_time
        else:
            # Über Mitternacht (z.B. 22:00-06:00)
            return check_time >= start_time or check_time < end_time
    
    def apply_limit_to_schedule(
        self,
        schedule: List[Tuple[datetime, float]],
        pv_forecast: Optional[List[Tuple[datetime, float]]] = None
    ) -> List[Tuple[datetime, float]]:
        """
        Wendet Einspeisebegrenzung auf einen Fahrplan an.
        
        Args:
            schedule: Liste von (timestamp, power_kw) Tupeln
            pv_forecast: Optional PV-Prognose für präzisere Begrenzung
        
        Returns:
            Angepasster Fahrplan
        """
        if not self.enabled or self.mode == "off":
            return schedule
        
        result = []
        
        # Erstelle PV-Lookup für schnellen Zugriff
        pv_lookup: Dict[datetime, float] = {}
        if pv_forecast and self.pv_forecast_integration:
            for ts, pv_kw in pv_forecast:
                # Runde auf Minute für Lookup
                ts_rounded = ts.replace(second=0, microsecond=0)
                pv_lookup[ts_rounded] = pv_kw
        
        for ts, power_kw in schedule:
            limit_pct = self.get_current_limit_pct(ts)
            
            # Wenn Einspeisung (negativ = Entladen = Einspeisung ins Netz)
            if power_kw < 0:
                # Berechne maximale Einspeiseleistung
                if self.pv_forecast_integration and ts in pv_lookup:
                    pv_kw = pv_lookup[ts]
                    # Begrenze auf limit_pct der PV-Leistung
                    max_feedin_kw = pv_kw * (limit_pct / 100.0)
                    # power_kw ist negativ (Entladen), also muss es >= -max_feedin_kw sein
                    power_kw = max(power_kw, -max_feedin_kw)
                else:
                    # Fallback: Begrenze auf limit_pct der aktuellen Entladeleistung
                    power_kw = power_kw * (limit_pct / 100.0)
            
            result.append((ts, power_kw))
        
        return result
    
    def get_limit_info(self, current_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Gibt Informationen über die aktuelle Begrenzung zurück.
        
        Returns:
            Dict mit 'limit_pct', 'mode', 'active_rule' etc.
        """
        limit_pct = self.get_current_limit_pct(current_time)
        
        info = {
            "enabled": self.enabled,
            "mode": self.mode,
            "current_limit_pct": limit_pct,
            "active_rule": None
        }
        
        if self.mode == "dynamic" and current_time:
            now = current_time.time()
            for start_time, end_time, rule_limit in self._parsed_rules:
                if self._time_in_range(now, start_time, end_time):
                    info["active_rule"] = {
                        "time_range": f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}",
                        "limit_pct": rule_limit
                    }
                    break
        
        return info

