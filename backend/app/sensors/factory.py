from typing import Dict, Type, Optional
from app.sensors.sensor_base import SensorBase
from app.sensors.generic_sensor import GenericSensor
from app.models import SensorConfig, SensorType
from app.protocols.protocol_registry import ProtocolRegistry


class SensorFactory:
    """Factory per creare istanze di sensori basandosi sulla configurazione"""
    
    @classmethod
    def create_sensor(cls, config: SensorConfig) -> SensorBase:
        """Crea un'istanza di sensore basandosi sulla configurazione"""
        if not config.enabled:
            raise ValueError(f"Sensore {config.name} è disabilitato")
        
        # Usa il sistema di protocolli modulare
        protocol_name = config.get_communication_protocol()
        
        # Crea il protocollo appropriato
        try:
            protocol = ProtocolRegistry.get_protocol(protocol_name, config)
        except ValueError as e:
            raise ValueError(
                f"Impossibile creare protocollo '{protocol_name}' per sensore {config.name}: {e}"
            )
        
        # Crea un sensore generico con il protocollo
        return GenericSensor(config, protocol)
    
    @classmethod
    def create_sensors_from_configs(cls, configs: list[SensorConfig]) -> Dict[str, SensorBase]:
        """Crea multiple istanze di sensori da una lista di configurazioni"""
        sensors = {}
        for config in configs:
            try:
                sensor = cls.create_sensor(config)
                sensors[config.name] = sensor
            except Exception as e:
                print(f"Errore nella creazione del sensore {config.name}: {e}")
                continue
        return sensors

