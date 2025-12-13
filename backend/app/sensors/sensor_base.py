from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from app.models import SensorConfig, SensorData
from app.protocols.protocol_base import ProtocolBase


class SensorBase(ABC):
    """Classe base astratta per tutti i sensori"""
    
    def __init__(self, config: SensorConfig, protocol: Optional[ProtocolBase] = None):
        self.config = config
        self.name = config.name
        self.type = config.type
        self.ip = config.ip
        self.port = config.port
        self.connected = False
        self.last_update: Optional[datetime] = None
        self._enabled = config.enabled
        self._protocol = protocol
    
    @property
    def protocol(self) -> Optional[ProtocolBase]:
        """Restituisce il protocollo associato al sensore"""
        return self._protocol
    
    @protocol.setter
    def protocol(self, protocol: ProtocolBase) -> None:
        """Imposta il protocollo associato al sensore"""
        self._protocol = protocol
    
    async def connect(self) -> bool:
        """Connette al sensore usando il protocollo"""
        if self._protocol:
            self.connected = await self._protocol.connect()
            if self.connected:
                self.update_last_update()
            return self.connected
        return False
    
    async def disconnect(self) -> None:
        """Disconnette dal sensore usando il protocollo"""
        if self._protocol:
            await self._protocol.disconnect()
        self.connected = False
    
    async def read_data(self) -> SensorData:
        """Legge i dati dal sensore usando il protocollo"""
        if self._protocol:
            data = await self._protocol.read_data()
            self.connected = self._protocol.connected
            if self.connected:
                self.update_last_update()
            return data
        return SensorData(
            sensor_name=self.name,
            timestamp=datetime.now(),
            data={},
            status="error",
            error="Nessun protocollo configurato"
        )
    
    async def is_connected(self) -> bool:
        """Verifica se il sensore è connesso"""
        if self._protocol:
            self.connected = await self._protocol.is_connected()
        return self.connected
    
    def get_status(self) -> Dict[str, Any]:
        """Restituisce lo stato del sensore"""
        # Ottieni la porta dal protocollo se disponibile (per WebSocket auto-assegnate)
        port = self.port
        if self._protocol and hasattr(self._protocol, 'port') and self._protocol.port:
            port = self._protocol.port
        
        status = {
            "name": self.name,
            "type": self.type.value,
            "ip": self.ip,
            "port": port,
            "connected": self.connected,
            "last_update": self.last_update,
            "enabled": self._enabled,
            "actions": self.config.actions or {},
            "template_id": self.config.template_id
        }
        # Aggiungi informazioni sul protocollo se disponibile
        if self._protocol:
            protocol_name = self._protocol.get_protocol_name()
            # Rimuovi "Protocol" dal nome per renderlo più leggibile
            status["protocol"] = protocol_name.replace("Protocol", "").lower()
        else:
            # Retrocompatibilità: deduci dal tipo
            if self.type.value == "http":
                status["protocol"] = "http"
            elif self.type.value == "websocket":
                status["protocol"] = "websocket"
        return status
    
    async def execute_action(self, action_name: str) -> Dict[str, Any]:
        """Esegue un'azione sul sensore usando il protocollo"""
        if not self.config.actions or action_name not in self.config.actions:
            raise ValueError(f"Azione '{action_name}' non trovata. Azioni disponibili: {list(self.config.actions.keys()) if self.config.actions else []}")
        
        if not self._protocol:
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": "Nessun protocollo configurato"
            }
        
        action_path = self.config.actions[action_name]
        return await self._protocol.execute_action(action_name, action_path)
    
    def enable(self) -> None:
        """Abilita il sensore"""
        self._enabled = True
    
    def disable(self) -> None:
        """Disabilita il sensore"""
        self._enabled = False
    
    @property
    def enabled(self) -> bool:
        """Verifica se il sensore è abilitato"""
        return self._enabled
    
    def update_last_update(self) -> None:
        """Aggiorna il timestamp dell'ultimo aggiornamento"""
        self.last_update = datetime.now()

