"""
MQTT Client Service for Phoenyra EMS
====================================

Provides MQTT communication for IoT devices and external systems.
"""

import json
import logging
import threading
import time
from typing import Dict, Any, Callable, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class MQTTConfig:
    """MQTT Configuration"""
    enabled: bool = False
    broker_host: str = "localhost"
    broker_port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: str = "phoenyra_ems"
    keepalive: int = 60
    qos: int = 1
    
    # Topics
    topics: Dict[str, str] = None
    
    def __post_init__(self):
        if self.topics is None:
            self.topics = {
                'publish': {
                    'status': 'ems/status',
                    'optimization': 'ems/optimization',
                    'alerts': 'ems/alerts'
                },
                'subscribe': {
                    'commands': 'ems/commands',
                    'setpoints': 'ems/setpoints'
                }
            }

class MQTTClient:
    """
    MQTT Client for EMS Communication
    
    Features:
    - Publish EMS status and optimization data
    - Subscribe to external commands and setpoints
    - Automatic reconnection
    - Message queuing when disconnected
    """
    
    def __init__(self, config: MQTTConfig):
        self.config = config
        self.client = None
        self.connected = False
        self.message_queue = []
        self.subscribers = {}
        self._lock = threading.Lock()
        
        # Initialize MQTT client if enabled
        if self.config.enabled:
            self._init_client()
    
    def _init_client(self):
        """Initialize MQTT client"""
        try:
            import paho.mqtt.client as mqtt
            
            self.client = mqtt.Client(self.config.client_id)
            
            # Set authentication if provided
            if self.config.username:
                self.client.username_pw_set(self.config.username, self.config.password)
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish
            
            logger.info(f"MQTT client initialized: {self.config.client_id}")
            
        except ImportError:
            logger.error("paho-mqtt not installed. MQTT functionality disabled.")
            self.config.enabled = False
    
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected successfully")
            
            # Subscribe to topics
            for topic in self.config.topics['subscribe'].values():
                client.subscribe(topic, qos=self.config.qos)
                logger.info(f"Subscribed to topic: {topic}")
            
            # Process queued messages
            self._process_message_queue()
            
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnection callback"""
        self.connected = False
        if rc != 0:
            logger.warning(f"MQTT disconnected unexpectedly (code: {rc})")
        else:
            logger.info("MQTT disconnected")
    
    def _on_message(self, client, userdata, msg):
        """MQTT message received callback"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode('utf-8'))
            
            logger.debug(f"MQTT message received on {topic}: {payload}")
            
            # Notify subscribers
            if topic in self.subscribers:
                for callback in self.subscribers[topic]:
                    try:
                        callback(topic, payload)
                    except Exception as e:
                        logger.error(f"Error in MQTT message callback: {e}")
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        logger.debug(f"MQTT message published (mid: {mid})")
    
    def connect(self):
        """Connect to MQTT broker"""
        if not self.config.enabled or not self.client:
            return False
        
        try:
            self.client.connect(
                self.config.broker_host,
                self.config.broker_port,
                self.config.keepalive
            )
            self.client.loop_start()
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.client and self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            logger.info("MQTT disconnected")
    
    def publish_status(self, status_data: Dict[str, Any]):
        """Publish EMS status data"""
        topic = self.config.topics['publish']['status']
        self._publish_message(topic, status_data)
    
    def publish_optimization(self, optimization_data: Dict[str, Any]):
        """Publish optimization results"""
        topic = self.config.topics['publish']['optimization']
        self._publish_message(topic, optimization_data)
    
    def publish_alert(self, alert_data: Dict[str, Any]):
        """Publish system alerts"""
        topic = self.config.topics['publish']['alerts']
        self._publish_message(topic, alert_data)
    
    def _publish_message(self, topic: str, data: Dict[str, Any]):
        """Publish message to MQTT topic"""
        if not self.config.enabled:
            return
        
        # Add timestamp
        data['timestamp'] = datetime.now().isoformat()
        
        try:
            payload = json.dumps(data)
            
            if self.connected and self.client:
                result = self.client.publish(topic, payload, qos=self.config.qos)
                if result.rc != 0:
                    logger.error(f"Failed to publish to {topic}: {result.rc}")
            else:
                # Queue message for later
                with self._lock:
                    self.message_queue.append((topic, payload))
                logger.debug(f"Message queued for {topic} (not connected)")
                
        except Exception as e:
            logger.error(f"Error publishing MQTT message: {e}")
    
    def _process_message_queue(self):
        """Process queued messages"""
        with self._lock:
            while self.message_queue and self.connected:
                topic, payload = self.message_queue.pop(0)
                try:
                    self.client.publish(topic, payload, qos=self.config.qos)
                except Exception as e:
                    logger.error(f"Error publishing queued message: {e}")
    
    def subscribe_to_topic(self, topic: str, callback: Callable[[str, Dict], None]):
        """Subscribe to a topic with callback"""
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        
        self.subscribers[topic].append(callback)
        
        # Subscribe to topic if connected
        if self.connected and self.client:
            self.client.subscribe(topic, qos=self.config.qos)
            logger.info(f"Subscribed to topic: {topic}")
    
    def unsubscribe_from_topic(self, topic: str, callback: Callable[[str, Dict], None]):
        """Unsubscribe from a topic"""
        if topic in self.subscribers:
            try:
                self.subscribers[topic].remove(callback)
                if not self.subscribers[topic]:
                    del self.subscribers[topic]
                    if self.connected and self.client:
                        self.client.unsubscribe(topic)
                        logger.info(f"Unsubscribed from topic: {topic}")
            except ValueError:
                pass
    
    def update_config(self, new_config: MQTTConfig):
        """Update MQTT configuration"""
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
        """Get MQTT client status"""
        return {
            'enabled': self.config.enabled,
            'connected': self.connected,
            'broker_host': self.config.broker_host,
            'broker_port': self.config.broker_port,
            'client_id': self.config.client_id,
            'queued_messages': len(self.message_queue),
            'subscribed_topics': list(self.subscribers.keys())
        }
