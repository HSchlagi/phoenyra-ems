"""
Phoenyra EMS - Multi-Site Manager
Verwaltet mehrere Standorte (Sites) mit jeweils eigenem EmsCore
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from .controller import EmsCore, PlantState
import numpy as np

logger = logging.getLogger(__name__)


class MultiSiteManager:
    """
    Verwaltet mehrere Standorte (Sites) mit jeweils eigenem EmsCore
    
    Jeder Standort hat:
    - Eigene BESS-Konfiguration
    - Eigene Modbus/MQTT-Verbindungen
    - Eigene Strategien und Optimierung
    - Eigene Historien-Datenbank
    """
    
    def __init__(self, sites_config: Dict[str, Any]):
        """
        Initialisiert Multi-Site-Manager
        
        Args:
            sites_config: Dictionary mit Site-Konfigurationen
                {
                    'sites': {
                        1: { 'name': 'Standort Wien', 'bess': {...}, 'modbus': {...}, ... },
                        2: { 'name': 'Standort Linz', 'bess': {...}, 'modbus': {...}, ... }
                    },
                    'default_site_id': 1
                }
        """
        self.sites: Dict[int, EmsCore] = {}
        self.site_configs: Dict[int, Dict[str, Any]] = {}
        self.default_site_id = sites_config.get('default_site_id', 1)
        
        # Initialisiere alle Sites
        sites_dict = sites_config.get('sites', {})
        if not sites_dict:
            raise ValueError("Keine Sites in Konfiguration gefunden. Bitte 'sites.sites' in ems.yaml konfigurieren.")
        
        for site_id, site_cfg in sites_dict.items():
            self._initialize_site(int(site_id), site_cfg)
        
        logger.info(f"MultiSiteManager initialized with {len(self.sites)} sites")
    
    def _initialize_site(self, site_id: int, site_config: Dict[str, Any]):
        """
        Initialisiert einen einzelnen Standort
        """
        try:
            # Erstelle vollständige Config für diesen Standort
            # Merge mit globalen Defaults falls vorhanden
            full_config = {
                'bess': site_config.get('bess', {}),
                'modbus': site_config.get('modbus', {}),
                'mqtt': site_config.get('mqtt', {}),
                'forecast': site_config.get('forecast', {}),
                'grid_connection': site_config.get('grid_connection', {}),
                'feedin_limitation': site_config.get('feedin_limitation', {}),
                'grid_tariffs': site_config.get('grid_tariffs', {}),
                'ems': site_config.get('ems', {}),
                'strategies': site_config.get('strategies', {}),
                'power_control': site_config.get('power_control', {}),
                'prices': site_config.get('prices', {}),
                'database': {
                    'history_path': site_config.get('database', {}).get(
                        'history_path', 
                        f"data/ems_history_site_{site_id}.db"
                    )
                }
            }
            
            # Erstelle EmsCore-Instanz für diesen Standort
            ems_core = EmsCore(full_config)
            ems_core.state.site_id = site_id
            ems_core.start()
            
            self.sites[site_id] = ems_core
            self.site_configs[site_id] = site_config
            
            site_name = site_config.get('name', f'Site {site_id}')
            logger.info(f"✅ Site {site_id} ({site_name}) initialized and started")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize site {site_id}: {e}", exc_info=True)
            raise
    
    def get_site(self, site_id: Optional[int] = None) -> Optional[EmsCore]:
        """
        Gibt EmsCore für einen Standort zurück
        
        Args:
            site_id: Site-ID (None = Default-Site)
        
        Returns:
            EmsCore-Instanz oder None
        """
        site_id = site_id or self.default_site_id
        return self.sites.get(site_id)
    
    def get_all_sites(self) -> Dict[int, EmsCore]:
        """Gibt alle Site-Instanzen zurück"""
        return self.sites
    
    def get_site_state(self, site_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Gibt aktuellen Zustand eines Standorts zurück"""
        ems = self.get_site(site_id)
        if ems:
            return asdict(ems.state)
        return None
    
    def get_all_sites_state(self) -> Dict[int, Dict[str, Any]]:
        """Gibt Zustand aller Standorte zurück"""
        return {
            site_id: asdict(ems.state)
            for site_id, ems in self.sites.items()
        }
    
    def get_aggregated_state(self) -> Dict[str, Any]:
        """
        Aggregiert Zustand aller Standorte
        
        Returns:
            {
                'total_p_bess': sum aller BESS-Leistungen,
                'total_p_pv': sum aller PV-Leistungen,
                'total_p_load': sum aller Lasten,
                'total_energy_capacity': sum aller Kapazitäten,
                'avg_soc': durchschnittlicher SoC (gewichtet),
                'sites': {site_id: state},
                'site_count': Anzahl Standorte
            }
        """
        all_states = self.get_all_sites_state()
        
        aggregated = {
            'total_p_bess': 0.0,
            'total_p_pv': 0.0,
            'total_p_load': 0.0,
            'total_p_grid': 0.0,
            'total_energy_capacity': 0.0,
            'total_soc_weighted': 0.0,
            'total_capacity': 0.0,
            'sites': all_states,
            'site_count': len(all_states),
            'avg_price': 0.0,
            'total_price_weighted': 0.0
        }
        
        for site_id, state in all_states.items():
            # Leistungen summieren
            aggregated['total_p_bess'] += state.get('p_bess', 0.0)
            aggregated['total_p_pv'] += state.get('p_pv', 0.0)
            aggregated['total_p_load'] += state.get('p_load', 0.0)
            aggregated['total_p_grid'] += state.get('p_grid', 0.0)
            
            # Kapazität und gewichteter SoC
            capacity = self.site_configs[site_id].get('bess', {}).get('energy_capacity_kwh', 0.0)
            aggregated['total_energy_capacity'] += capacity
            soc = state.get('soc', 0.0)
            aggregated['total_soc_weighted'] += soc * capacity
            aggregated['total_capacity'] += capacity
            
            # Gewichteter Preis (nach Last)
            price = state.get('price', 0.0)
            load = abs(state.get('p_load', 0.0))
            aggregated['total_price_weighted'] += price * load
        
        # Gewichteter Durchschnitts-SoC
        if aggregated['total_capacity'] > 0:
            aggregated['avg_soc'] = aggregated['total_soc_weighted'] / aggregated['total_capacity']
        else:
            aggregated['avg_soc'] = 0.0
        
        # Gewichteter Durchschnittspreis
        total_load = abs(aggregated['total_p_load'])
        if total_load > 0:
            aggregated['avg_price'] = aggregated['total_price_weighted'] / total_load
        else:
            aggregated['avg_price'] = 0.0
        
        return aggregated
    
    def get_site_info(self, site_id: int) -> Optional[Dict[str, Any]]:
        """
        Gibt Informationen über einen Standort zurück
        
        Returns:
            {
                'id': site_id,
                'name': site_name,
                'location': {...},
                'config': {...},
                'state': {...}
            }
        """
        if site_id not in self.site_configs:
            return None
        
        config = self.site_configs[site_id]
        state = self.get_site_state(site_id)
        
        return {
            'id': site_id,
            'name': config.get('name', f'Site {site_id}'),
            'location': config.get('location', {}),
            'config': {
                'bess': config.get('bess', {}),
                'modbus': {
                    'enabled': config.get('modbus', {}).get('enabled', False),
                    'host': config.get('modbus', {}).get('host', 'N/A')
                },
                'mqtt': {
                    'enabled': config.get('mqtt', {}).get('enabled', False),
                    'broker': config.get('mqtt', {}).get('broker', 'N/A')
                }
            },
            'state': state
        }
    
    def list_sites(self) -> List[Dict[str, Any]]:
        """
        Gibt Liste aller Standorte mit Basis-Informationen zurück
        """
        sites_list = []
        for site_id in self.sites.keys():
            site_info = self.get_site_info(site_id)
            if site_info:
                sites_list.append(site_info)
        return sites_list
    
    def stop_all(self):
        """
        Stoppt alle Site-Instanzen
        """
        logger.info("Stopping all sites...")
        for site_id, ems in self.sites.items():
            try:
                ems.stop()
                logger.info(f"Site {site_id} stopped")
            except Exception as e:
                logger.error(f"Error stopping site {site_id}: {e}")
    
    def __getattr__(self, name):
        """
        Delegiert Attribute-Zugriffe an Default-Site für Rückwärtskompatibilität
        
        Ermöglicht: multi_site_manager.state statt multi_site_manager.get_site().state
        """
        default_site = self.get_site()
        if default_site:
            return getattr(default_site, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

