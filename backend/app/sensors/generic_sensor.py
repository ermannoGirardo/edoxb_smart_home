from app.sensors.sensor_base import SensorBase
from app.models import SensorConfig
from app.protocols.protocol_base import ProtocolBase


class GenericSensor(SensorBase):
    """Sensore generico che usa un protocollo di comunicazione"""
    
    def __init__(self, config: SensorConfig, protocol: ProtocolBase):
        super().__init__(config, protocol)
        # Aggiorna la porta dal protocollo se disponibile (es. WebSocket auto-assigna porta)
        if hasattr(protocol, 'port') and protocol.port:
            self.port = protocol.port
            self.config.port = protocol.port







