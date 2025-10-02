"""
Modbus Client Service for Phoenyra EMS
======================================

Provides Modbus TCP/RTU communication for industrial devices and BESS systems.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class ModbusConnectionType(Enum):
    TCP = "tcp"
    RTU = "rtu"

@dataclass
class ModbusConfig:
    """Modbus Configuration"""
    enabled: bool = False
    connection_type: str = "tcp"  # tcp, rtu
    host: str = "localhost"
    port: int = 502
    slave_id: int = 1
    timeout: float = 3.0
    retries: int = 3
    
    # RTU specific
    serial_port: str = "/dev/ttyUSB0"
    baudrate: int = 115200
    parity: str = "N"  # N, E, O
    
    # Register mapping
    registers: Dict[str, int] = None
    
    def __post_init__(self):
        if self.registers is None:
            self.registers = {
                # BESS Status Registers
                'soc_percent': 40001,
                'power_kw': 40002,
                'voltage_v': 40003,
                'current_a': 40004,
                'temperature_c': 40005,
                
                # Control Registers
                'setpoint_power_kw': 40010,
                'enable_charge': 40011,
                'enable_discharge': 40012,
                'emergency_stop': 40013,
                
                # Configuration Registers
                'max_charge_power': 40020,
                'max_discharge_power': 40021,
                'soc_min_percent': 40022,
                'soc_max_percent': 40023
            }

class ModbusClient:
    """
    Modbus Client for EMS Communication
    
    Features:
    - TCP/IP and RTU communication
    - Read/write holding registers
    - Automatic reconnection
    - Register mapping for BESS parameters
    - Error handling and logging
    """
    
    def __init__(self, config: ModbusConfig):
        self.config = config
        self.client = None
        self.connected = False
        self._lock = threading.Lock()
        self._last_error = None
        
        # Initialize Modbus client if enabled
        if self.config.enabled:
            self._init_client()
    
    def _init_client(self):
        """Initialize Modbus client"""
        try:
            from pymodbus.client import ModbusTcpClient, ModbusSerialClient
            
            if self.config.connection_type == ModbusConnectionType.TCP.value:
                self.client = ModbusTcpClient(
                    host=self.config.host,
                    port=self.config.port,
                    timeout=self.config.timeout
                )
                logger.info(f"Modbus TCP client initialized: {self.config.host}:{self.config.port}")
                
            elif self.config.connection_type == ModbusConnectionType.RTU.value:
                self.client = ModbusSerialClient(
                    port=self.config.serial_port,
                    baudrate=self.config.baudrate,
                    parity=self.config.parity,
                    timeout=self.config.timeout
                )
                logger.info(f"Modbus RTU client initialized: {self.config.serial_port}")
            
            else:
                raise ValueError(f"Unsupported connection type: {self.config.connection_type}")
                
        except ImportError:
            logger.error("pymodbus not installed. Modbus functionality disabled.")
            self.config.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Modbus client: {e}")
            self.config.enabled = False
    
    def connect(self) -> bool:
        """Connect to Modbus device"""
        if not self.config.enabled or not self.client:
            return False
        
        try:
            with self._lock:
                if self.client.connect():
                    self.connected = True
                    self._last_error = None
                    logger.info("Modbus connected successfully")
                    return True
                else:
                    self.connected = False
                    self._last_error = "Connection failed"
                    logger.error("Modbus connection failed")
                    return False
                    
        except Exception as e:
            self.connected = False
            self._last_error = str(e)
            logger.error(f"Modbus connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Modbus device"""
        if self.client and self.connected:
            try:
                with self._lock:
                    self.client.close()
                    self.connected = False
                    logger.info("Modbus disconnected")
            except Exception as e:
                logger.error(f"Error disconnecting Modbus: {e}")
    
    def read_register(self, register_name: str) -> Optional[Union[int, float]]:
        """Read a single register by name"""
        if not self.connected or register_name not in self.config.registers:
            return None
        
        register_address = self.config.registers[register_name]
        return self.read_holding_register(register_address)
    
    def read_holding_register(self, address: int, count: int = 1) -> Optional[Union[int, float]]:
        """Read holding register(s)"""
        if not self.connected:
            return None
        
        try:
            with self._lock:
                result = self.client.read_holding_registers(
                    address=address,
                    count=count,
                    slave=self.config.slave_id
                )
                
                if result.isError():
                    self._last_error = f"Read error: {result}"
                    logger.error(f"Modbus read error at address {address}: {result}")
                    return None
                
                if count == 1:
                    return result.registers[0]
                else:
                    return result.registers
                    
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Modbus read exception at address {address}: {e}")
            return None
    
    def write_register(self, register_name: str, value: Union[int, float]) -> bool:
        """Write a single register by name"""
        if not self.connected or register_name not in self.config.registers:
            return False
        
        register_address = self.config.registers[register_name]
        return self.write_holding_register(register_address, value)
    
    def write_holding_register(self, address: int, value: Union[int, float]) -> bool:
        """Write holding register"""
        if not self.connected:
            return False
        
        try:
            with self._lock:
                result = self.client.write_register(
                    address=address,
                    value=int(value),
                    slave=self.config.slave_id
                )
                
                if result.isError():
                    self._last_error = f"Write error: {result}"
                    logger.error(f"Modbus write error at address {address}: {result}")
                    return False
                
                logger.debug(f"Modbus write successful: address={address}, value={value}")
                return True
                
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Modbus write exception at address {address}: {e}")
            return False
    
    def read_bess_status(self) -> Dict[str, Any]:
        """Read complete BESS status from Modbus registers"""
        if not self.connected:
            return {}
        
        status = {}
        
        # Read status registers
        status_registers = [
            'soc_percent', 'power_kw', 'voltage_v', 
            'current_a', 'temperature_c'
        ]
        
        for reg_name in status_registers:
            value = self.read_register(reg_name)
            if value is not None:
                status[reg_name] = value
        
        # Add timestamp
        status['timestamp'] = datetime.now().isoformat()
        status['connected'] = self.connected
        
        return status
    
    def write_bess_setpoint(self, power_kw: float) -> bool:
        """Write BESS power setpoint"""
        return self.write_register('setpoint_power_kw', power_kw)
    
    def enable_charge(self, enable: bool = True) -> bool:
        """Enable/disable BESS charging"""
        return self.write_register('enable_charge', 1 if enable else 0)
    
    def enable_discharge(self, enable: bool = True) -> bool:
        """Enable/disable BESS discharging"""
        return self.write_register('enable_discharge', 1 if enable else 0)
    
    def emergency_stop(self) -> bool:
        """Trigger emergency stop"""
        return self.write_register('emergency_stop', 1)
    
    def update_bess_config(self, config_data: Dict[str, Any]) -> bool:
        """Update BESS configuration registers"""
        if not self.connected:
            return False
        
        success = True
        
        # Update configuration registers
        config_registers = [
            'max_charge_power', 'max_discharge_power',
            'soc_min_percent', 'soc_max_percent'
        ]
        
        for reg_name in config_registers:
            if reg_name in config_data:
                if not self.write_register(reg_name, config_data[reg_name]):
                    success = False
        
        return success
    
    def test_connection(self) -> bool:
        """Test Modbus connection by reading a register"""
        if not self.connected:
            return False
        
        try:
            # Try to read the first register
            result = self.read_holding_register(40001, 1)
            return result is not None
        except Exception as e:
            logger.error(f"Modbus connection test failed: {e}")
            return False
    
    def update_config(self, new_config: ModbusConfig):
        """Update Modbus configuration"""
        was_connected = self.connected
        
        # Disconnect if connected
        if was_connected:
            self.disconnect()
        
        # Update config
        self.config = new_config
        
        # Reinitialize if enabled
        if self.config.enabled:
            self._init_client()
            if was_connected:
                self.connect()
    
    def get_status(self) -> Dict[str, Any]:
        """Get Modbus client status"""
        return {
            'enabled': self.config.enabled,
            'connected': self.connected,
            'connection_type': self.config.connection_type,
            'host': self.config.host if self.config.connection_type == 'tcp' else self.config.serial_port,
            'port': self.config.port if self.config.connection_type == 'tcp' else self.config.baudrate,
            'slave_id': self.config.slave_id,
            'last_error': self._last_error,
            'available_registers': list(self.config.registers.keys())
        }
    
    def get_register_mapping(self) -> Dict[str, int]:
        """Get current register mapping"""
        return self.config.registers.copy()
    
    def add_register_mapping(self, name: str, address: int):
        """Add a new register mapping"""
        self.config.registers[name] = address
        logger.info(f"Added register mapping: {name} -> {address}")
    
    def remove_register_mapping(self, name: str):
        """Remove a register mapping"""
        if name in self.config.registers:
            del self.config.registers[name]
            logger.info(f"Removed register mapping: {name}")
