import asyncio
from typing import Dict
from app.sensors.sensor_base import SensorBase
from app.db.mongo_client import MongoClientWrapper
from app.services.mqtt_client import MQTTClient
from app.models import SensorData


class SensorPollingService:
    """Servizio per gestire il polling dei sensori e la persistenza dei dati"""
    
    def __init__(
        self,
        sensors: Dict[str, SensorBase],
        mongo_client: MongoClientWrapper,
        mqtt_client: MQTTClient = None
    ):
        self.sensors = sensors
        self.mongo_client = mongo_client
        self.mqtt_client = mqtt_client
        self._polling_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
    
    async def start_polling(self) -> None:
        """Avvia il polling di tutti i sensori abilitati (salta quelli con poll_interval=None o 0, e sensori MQTT)"""
        self._running = True
        for name, sensor in self.sensors.items():
            if sensor.enabled:
                # Salta sensori MQTT (ricevono dati in tempo reale, non serve polling)
                if sensor.protocol and hasattr(sensor.protocol, 'get_protocol_name'):
                    protocol_name = sensor.protocol.get_protocol_name()
                    if protocol_name == "MQTTProtocol":
                        continue
                
                # Salta sensori senza polling (pulsanti, ecc.)
                poll_interval = sensor.config.poll_interval
                if poll_interval is not None and poll_interval > 0:
                    task = asyncio.create_task(self._poll_sensor(name, sensor))
                    self._polling_tasks[name] = task
        print(f"Avviato polling per {len(self._polling_tasks)} sensori")
    
    async def stop_polling(self) -> None:
        """Ferma il polling di tutti i sensori"""
        self._running = False
        for task in self._polling_tasks.values():
            task.cancel()
        await asyncio.gather(*self._polling_tasks.values(), return_exceptions=True)
        self._polling_tasks.clear()
        print("Polling fermato")
    
    async def _poll_sensor(self, name: str, sensor: SensorBase) -> None:
        """Loop di polling per un singolo sensore"""
        poll_interval = sensor.config.poll_interval
        
        # Se poll_interval è None o 0, non fare polling (es. pulsanti)
        if poll_interval is None or poll_interval == 0:
            return
        
        # Default 5 secondi se non specificato
        poll_interval = poll_interval or 5
        
        while self._running and sensor.enabled:
            try:
                # Leggi i dati dal sensore
                sensor_data = await sensor.read_data()
                
                # Salva in MongoDB
                try:
                    if self.mongo_client is not None:
                        await self.mongo_client.save_sensor_data(sensor_data)
                except Exception as e:
                    print(f"Errore salvataggio MongoDB per {name}: {e}")
                
                # Notifica AutomationService se presente
                if hasattr(self, '_automation_service') and self._automation_service:
                    try:
                        await self._automation_service.on_sensor_data(name, sensor_data)
                    except Exception as e:
                        print(f"Errore automazione per {name}: {e}")
                
                # Pubblica su MQTT se disponibile
                if self.mqtt_client and sensor_data.status == "ok":
                    try:
                        await self.mqtt_client.publish_sensor_data(sensor_data)
                    except Exception as e:
                        print(f"Errore pubblicazione MQTT per {name}: {e}")
                
                # Attendi prima della prossima lettura
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Errore nel polling del sensore {name}: {e}")
                await asyncio.sleep(poll_interval)
    
    def start_sensor_polling(self, name: str, sensor: SensorBase) -> None:
        """Avvia il polling per un singolo sensore"""
        if self._running and name not in self._polling_tasks:
            task = asyncio.create_task(self._poll_sensor(name, sensor))
            self._polling_tasks[name] = task
    
    def stop_sensor_polling(self, name: str) -> None:
        """Ferma il polling per un singolo sensore"""
        if name in self._polling_tasks:
            self._polling_tasks[name].cancel()
            del self._polling_tasks[name]
    
    @property
    def running(self) -> bool:
        """Verifica se il polling è in esecuzione"""
        return self._running


