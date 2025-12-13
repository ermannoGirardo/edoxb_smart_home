from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from app.models import SensorConfig, SensorData


class ProtocolBase(ABC):
    """Classe base astratta per tutti i protocolli di comunicazione"""
    
    def __init__(self, config: SensorConfig):
        self.config = config
        self.name = config.name
        self.ip = config.ip
        self.port = config.port
        self.connected = False
        self.last_update: Optional[datetime] = None
    
    @abstractmethod
    async def connect(self) -> bool:
        """Stabilisce la connessione usando il protocollo"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Chiude la connessione"""
        pass
    
    @abstractmethod
    async def read_data(self) -> SensorData:
        """Legge i dati usando il protocollo"""
        pass
    
    @abstractmethod
    async def is_connected(self) -> bool:
        """Verifica se la connessione è attiva"""
        pass
    
    @abstractmethod
    async def execute_action(self, action_name: str, action_path: str) -> Dict[str, Any]:
        """Esegue un'azione usando il protocollo"""
        pass
    
    def update_last_update(self) -> None:
        """Aggiorna il timestamp dell'ultimo aggiornamento"""
        self.last_update = datetime.now()
    
    def get_protocol_name(self) -> str:
        """Restituisce il nome del protocollo"""
        return self.__class__.__name__


