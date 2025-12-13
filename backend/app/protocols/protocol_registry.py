from typing import Dict, Type, Optional
from app.protocols.protocol_base import ProtocolBase
from app.models import SensorConfig


class ProtocolRegistry:
    """Registry per registrare e recuperare protocolli di comunicazione"""
    
    # Registry dei protocolli standard
    _protocol_registry: Dict[str, Type[ProtocolBase]] = {}
    
    @classmethod
    def register_protocol(cls, protocol_name: str, protocol_class: Type[ProtocolBase]) -> None:
        """Registra un nuovo protocollo"""
        if not issubclass(protocol_class, ProtocolBase):
            raise ValueError(f"La classe {protocol_class.__name__} deve essere una sottoclasse di ProtocolBase")
        cls._protocol_registry[protocol_name.lower()] = protocol_class
        print(f"Protocollo '{protocol_name}' registrato")
    
    @classmethod
    def get_protocol(cls, protocol_name: str, config: SensorConfig) -> ProtocolBase:
        """Crea e restituisce un'istanza del protocollo richiesto"""
        protocol_name_lower = protocol_name.lower()
        
        if protocol_name_lower not in cls._protocol_registry:
            raise ValueError(
                f"Protocollo '{protocol_name}' non trovato. "
                f"Protocolli disponibili: {list(cls._protocol_registry.keys())}"
            )
        
        protocol_class = cls._protocol_registry[protocol_name_lower]
        return protocol_class(config)
    
    @classmethod
    def list_protocols(cls) -> list[str]:
        """Restituisce la lista di tutti i protocolli registrati"""
        return list(cls._protocol_registry.keys())
    
    @classmethod
    def is_protocol_registered(cls, protocol_name: str) -> bool:
        """Verifica se un protocollo è registrato"""
        return protocol_name.lower() in cls._protocol_registry


