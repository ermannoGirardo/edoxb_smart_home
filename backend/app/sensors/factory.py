from typing import Dict, Type, Optional
from app.sensors.sensor_base import SensorBase
from app.sensors.http_sensor import HTTPSensor
from app.sensors.websocket_sensor import WebSocketSensor
from app.models import SensorConfig, SensorType


class SensorFactory:
    """Factory per creare istanze di sensori basandosi sulla configurazione"""
    
    # Registry dei tipi di sensori standard
    _sensor_registry: Dict[SensorType, Type[SensorBase]] = {
        SensorType.HTTP: HTTPSensor,
        SensorType.WEBSOCKET: WebSocketSensor,
    }
    
    # Registry per sensori custom (caricati dinamicamente)
    _custom_sensor_registry: Dict[str, Type[SensorBase]] = {}
    
    @classmethod
    def register_custom_sensor(cls, name: str, sensor_class: Type[SensorBase]) -> None:
        """Registra un sensore personalizzato"""
        cls._custom_sensor_registry[name] = sensor_class
    
    @classmethod
    def create_sensor(cls, config: SensorConfig) -> SensorBase:
        """Crea un'istanza di sensore basandosi sulla configurazione"""
        if not config.enabled:
            raise ValueError(f"Sensore {config.name} è disabilitato")
        
        # Gestione sensori custom
        if config.type == SensorType.CUSTOM:
            if not config.custom_class:
                raise ValueError(f"Sensore custom {config.name} richiede 'custom_class' nella configurazione")
            
            # Cerca nel registry custom
            if config.custom_class in cls._custom_sensor_registry:
                sensor_class = cls._custom_sensor_registry[config.custom_class]
                return sensor_class(config)
            else:
                # Prova a caricare dinamicamente
                try:
                    # Assumiamo formato: "module.path.ClassName"
                    parts = config.custom_class.split('.')
                    module_path = '.'.join(parts[:-1])
                    class_name = parts[-1]
                    
                    import importlib
                    module = importlib.import_module(module_path)
                    sensor_class = getattr(module, class_name)
                    
                    # Registra per uso futuro
                    cls._custom_sensor_registry[config.custom_class] = sensor_class
                    return sensor_class(config)
                except Exception as e:
                    raise ValueError(
                        f"Impossibile caricare sensore custom {config.custom_class} "
                        f"per {config.name}: {e}"
                    )
        
        # Sensori standard
        if config.type not in cls._sensor_registry:
            raise ValueError(f"Tipo sensore non supportato: {config.type}")
        
        sensor_class = cls._sensor_registry[config.type]
        return sensor_class(config)
    
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

