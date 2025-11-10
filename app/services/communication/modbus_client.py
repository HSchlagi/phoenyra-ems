"""
Modbus Client Service for Phoenyra EMS
======================================

Provides Modbus TCP/RTU communication for industrial devices and BESS systems.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
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
    profile: Optional[str] = None
    poll_interval_s: float = 2.0
    status_codes: Dict[str, str] = field(default_factory=dict)
    
    # RTU specific
    serial_port: str = "/dev/ttyUSB0"
    baudrate: int = 115200
    parity: str = "N"  # N, E, O
    
    # Register mapping
    registers: Dict[str, Dict[str, Any]] = field(default_factory=dict)

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
        self._last_read_raw: Dict[str, Any] = {}
        
        # Initialize Modbus client if enabled
        if self.config.enabled:
            self._init_client()

    # ------------------------------------------------------------------
    # interne Hilfsfunktionen
    # ------------------------------------------------------------------

    def _clone_definition(self, register_name: str) -> Optional[Dict[str, Any]]:
        entry = self.config.registers.get(register_name)
        if entry is None:
            return None
        if isinstance(entry, dict):
            return dict(entry)
        if isinstance(entry, int):
            return {
                "address": entry,
                "function": 3,
                "count": 1,
                "data_type": "uint16",
                "scale": 1.0,
                "offset": 0.0,
                "unit": None,
                "description": register_name,
                "category": "telemetry",
                "zero_based": False,
                "signed": False,
            }
        logger.warning("Unsupported register mapping for %s: %s", register_name, entry)
        return None

    @staticmethod
    def _normalize_address(address: int, function_code: int, zero_based: bool) -> int:
        if zero_based:
            return address

        if function_code == 3 and address >= 40001:
            return address - 40001
        if function_code == 4 and address >= 30001:
            return address - 30001
        if function_code == 2 and address >= 10001:
            return address - 10001

        # Fallback auf 1-basige Adresse
        return max(address - 1, 0)

    def _read_raw(self, definition: Dict[str, Any]) -> Optional[List[int]]:
        if not self.connected:
            return None

        address = definition.get("address")
        if address is None:
            return None

        function_code = int(definition.get("function", 3))
        count = int(definition.get("count", 1))
        zero_based = bool(definition.get("zero_based", False))
        normalized_address = self._normalize_address(address, function_code, zero_based)

        try:
            with self._lock:
                if function_code == 4:
                    result = self.client.read_input_registers(
                        address=normalized_address,
                        count=count,
                        slave=self.config.slave_id
                    )
                    if result.isError():
                        logger.error("Modbus read_input error at %s: %s", address, result)
                        return None
                    return result.registers

                if function_code == 3:
                    result = self.client.read_holding_registers(
                        address=normalized_address,
                        count=count,
                        slave=self.config.slave_id
                    )
                    if result.isError():
                        logger.error("Modbus read_holding error at %s: %s", address, result)
                        return None
                    return result.registers

                if function_code == 2:
                    result = self.client.read_discrete_inputs(
                        address=normalized_address,
                        count=count,
                        slave=self.config.slave_id
                    )
                    if result.isError():
                        logger.error("Modbus read_discrete error at %s: %s", address, result)
                        return None
                    return result.bits[:count]

                logger.error("Unsupported Modbus function code %s", function_code)
                return None

        except Exception as exc:
            logger.error("Modbus read exception at %s: %s", address, exc)
            self._last_error = str(exc)
            return None

    @staticmethod
    def _combine_words(words: List[int], signed: bool) -> int:
        raw = 0
        for word in words:
            raw = (raw << 16) | (word & 0xFFFF)
        if signed and raw >= 1 << (16 * len(words) - 1):
            raw -= 1 << (16 * len(words))
        return raw

    def _decode_value(self, definition: Dict[str, Any], raw: List[int]) -> Optional[Union[int, float]]:
        if raw is None:
            return None

        data_type = definition.get("data_type", "uint16").lower()
        signed = bool(definition.get("signed", False)) or data_type.startswith("int")
        count = int(definition.get("count", 1))

        if not raw:
            return None

        if data_type in {"uint32", "int32", "float32"} or count > 1:
            value = self._combine_words(raw[:count], signed=signed)
        else:
            value = raw[0]
            if signed and value >= 0x8000:
                value -= 0x10000

        scale = float(definition.get("scale", 1.0))
        offset = float(definition.get("offset", 0.0))

        return value * scale + offset

    
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
        if not self.connected:
            return None
        
        definition = self._clone_definition(register_name)
        if not definition:
            return None

        raw = self._read_raw(definition)
        if raw is None:
            return None

        value = self._decode_value(definition, raw)
        self._last_read_raw[register_name] = {
            "raw": raw,
            "definition": definition,
        }
        return value
    
    def read_holding_register(self, address: int, count: int = 1, zero_based: bool = False) -> Optional[Union[int, float]]:
        """Read holding register(s)"""
        if not self.connected:
            return None
        
        definition = {
            "address": address,
            "function": 3,
            "count": count,
            "zero_based": zero_based,
            "scale": 1.0,
            "offset": 0.0,
            "data_type": "uint16" if count == 1 else "uint32",
            "signed": False,
        }
        raw = self._read_raw(definition)
        if raw is None:
            return None
        if count == 1:
            return raw[0]
        return raw
    
    def write_register(self, register_name: str, value: Union[int, float]) -> bool:
        """Write a single register by name"""
        if not self.connected:
            return False
        
        definition = self._clone_definition(register_name)
        if not definition:
            return False

        function_code = int(definition.get("function", 3))
        if function_code != 3:
            logger.error("Register %s ist nicht schreibbar (function=%s)", register_name, function_code)
            return False

        return self.write_holding_register(
            definition.get("address"),
            value,
            zero_based=bool(definition.get("zero_based", False)),
            definition=definition
        )
    
    def write_holding_register(
        self,
        address: int,
        value: Union[int, float],
        zero_based: bool = False,
        definition: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Write holding register"""
        if not self.connected:
            return False
        
        norm_address = self._normalize_address(address, 3, zero_based)

        if definition:
            scale = float(definition.get("scale", 1.0))
            offset = float(definition.get("offset", 0.0))
            if scale != 0:
                value_to_write = int(round((float(value) - offset) / scale))
            else:
                value_to_write = int(round(float(value)))
        else:
            value_to_write = int(round(float(value)))
        
        try:
            with self._lock:
                result = self.client.write_register(
                    address=norm_address,
                    value=value_to_write,
                    slave=self.config.slave_id
                )
                
                if result.isError():
                    self._last_error = f"Write error: {result}"
                    logger.error(f"Modbus write error at address {norm_address}: {result}")
                    return False
                
                logger.debug("Modbus write successful: address=%s, value=%s", norm_address, value_to_write)
                return True
                
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Modbus write exception at address {norm_address}: {e}")
            return False
    
    def read_bess_status(self) -> Dict[str, Any]:
        """Read complete BESS status from Modbus registers"""
        if not self.connected:
            return {}
        
        status: Dict[str, Any] = {}
        raw_snapshot: Dict[str, Any] = {}

        for reg_name in self.config.registers.keys():
            value = self.read_register(reg_name)
            if value is not None:
                status[reg_name] = value
                if reg_name in self._last_read_raw:
                    raw_snapshot[reg_name] = self._last_read_raw[reg_name]

        # Abgeleitete Kenngrößen
        voltage = status.get("voltage_v")
        current = status.get("current_a")
        if voltage is not None and current is not None:
            status.setdefault("power_kw", round((voltage * current) / 1000.0, 3))

        status_code = status.get("status_code")
        if status_code is not None:
            code_int = int(round(status_code))
            status_text = (
                self.config.status_codes.get(str(code_int))
                or self.config.status_codes.get(code_int)
            )
            if status_text:
                status["status_text"] = status_text

        status['timestamp'] = datetime.now().isoformat()
        status['connected'] = self.connected
        if raw_snapshot:
            status['raw_registers'] = raw_snapshot
        
        return status

    def read_alarm_flags(self, alarm_definitions: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """Liest diskrete Alarm-Flags gemäß Profildefinition"""
        if not self.connected or not alarm_definitions:
            return {}

        alarms: Dict[str, bool] = {}
        for name, definition in alarm_definitions.items():
            if not isinstance(definition, dict):
                continue

            entry = dict(definition)
            entry.setdefault("function", 2)
            entry.setdefault("count", 1)

            raw = self._read_raw(entry)
            if raw is None:
                continue

            bit_index = int(entry.get("bit", 0))
            value = False

            if isinstance(raw, list):
                if bit_index < len(raw):
                    value = bool(raw[bit_index])
                elif raw:
                    value = bool(raw[0])
            else:
                value = bool(raw)

            alarms[name] = value

        return alarms

    def sync_time(self, timestamp: Optional[datetime] = None) -> bool:
        """Synchronisiert die Echtzeituhr des BMS mittels RTC-Register"""
        if not self.connected:
            return False

        ts = timestamp or datetime.utcnow()
        year = max(min(ts.year - 2000, 100), 0)
        month = ts.month
        day = ts.day
        hour = ts.hour
        minute = ts.minute
        second = ts.second

        registers = [
            (524, year),
            (525, month),
            (526, day),
            (527, hour),
            (528, minute),
            (529, second)
        ]

        success = True
        for address, value in registers:
            if not self.write_holding_register(address, value, zero_based=False):
                success = False
        if success:
            logger.info("Modbus RTC synchronisiert (UTC %s)", ts.isoformat())
        else:
            logger.warning("Modbus RTC Synchronisation fehlgeschlagen")
        return success
    
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
            'max_charge_power_kw',
            'max_discharge_power_kw',
            'soc_min_percent',
            'soc_max_percent'
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
            register_names = list(self.config.registers.keys())
            if not register_names:
                logger.warning("Modbus connection test: keine Register konfiguriert")
                return False

            definition = self._clone_definition(register_names[0])
            if not definition:
                logger.warning("Modbus connection test: ungültige Registerdefinition")
                return False

            raw = self._read_raw(definition)
            return raw is not None
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
        self._last_read_raw = {}
        
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
    
    def get_register_mapping(self) -> Dict[str, Any]:
        """Get current register mapping"""
        mapping: Dict[str, Any] = {}
        for key, value in self.config.registers.items():
            if isinstance(value, dict):
                mapping[key] = dict(value)
            else:
                mapping[key] = value
        return mapping
    
    def add_register_mapping(self, name: str, address: int, **kwargs: Any):
        """Add a new register mapping"""
        definition = {
            "address": address,
            "function": kwargs.get("function", 3),
            "count": kwargs.get("count", 1),
            "data_type": kwargs.get("data_type", "uint16"),
            "scale": kwargs.get("scale", 1.0),
            "offset": kwargs.get("offset", 0.0),
            "unit": kwargs.get("unit"),
            "description": kwargs.get("description", name),
            "category": kwargs.get("category", "telemetry"),
            "zero_based": kwargs.get("zero_based", False),
            "signed": kwargs.get("signed", False),
        }
        self.config.registers[name] = definition
        logger.info("Added register mapping: %s -> %s", name, definition)
    
    def remove_register_mapping(self, name: str):
        """Remove a register mapping"""
        if name in self.config.registers:
            del self.config.registers[name]
            logger.info("Removed register mapping: %s", name)
