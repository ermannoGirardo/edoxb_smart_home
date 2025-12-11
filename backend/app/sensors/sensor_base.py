from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from app.models import SensorConfig, SensorData


class SensorBase(ABC):
    """Classe base astratta per tutti i sensori"""
    
    def __init__(self, config: SensorConfig):
        self.config = config
        self.name = config.name
        self.type = config.type
        self.ip = config.ip
        self.port = config.port
        self.connected = False
        self.last_update: Optional[datetime] = None
        self._enabled = config.enabled
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connette al sensore"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnette dal sensore"""
        pass
    
    @abstractmethod
    async def read_data(self) -> SensorData:
        """Legge i dati dal sensore"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Verifica se il sensore è connesso"""
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """Restituisce lo stato del sensore"""
        return {
            "name": self.name,
            "type": self.type.value,
            "ip": self.ip,
            "port": self.port,
            "connected": self.connected,
            "last_update": self.last_update,
            "enabled": self._enabled
        }
    
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

