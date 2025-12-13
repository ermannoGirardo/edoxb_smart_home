from typing import Dict, List, Optional
from app.sensors.sensor_base import SensorBase
from app.db.mongo_client import MongoClientWrapper
from app.services.mqtt_client import MQTTClient
from app.services.sensor_polling_service import SensorPollingService
from app.services.sensor_management_service import SensorManagementService
from app.models import SensorData, SensorStatus, SensorConfig, SensorActionResponse


class BusinessLogic:
    """
    Orchestratore principale per la gestione dei sensori.
    Delega le operazioni ai servizi modulari specializzati.
    """
    
    def __init__(
        self,
        sensors: Dict[str, SensorBase],
        mongo_client: MongoClientWrapper,
        mqtt_client: Optional[MQTTClient] = None
    ):
        self.sensors = sensors
        self.mongo_client = mongo_client
        self.mqtt_client = mqtt_client
        
        # Inizializza i servizi modulari
        self._polling_service = SensorPollingService(
            sensors=sensors,
            mongo_client=mongo_client,
            mqtt_client=mqtt_client
        )
        self._management_service = SensorManagementService(
            sensors=sensors,
            mongo_client=mongo_client
        )
    
    # ========== Polling Management ==========
    
    async def start_polling(self) -> None:
        """Avvia il polling di tutti i sensori abilitati"""
        await self._polling_service.start_polling()
    
    async def stop_polling(self) -> None:
        """Ferma il polling di tutti i sensori"""
        await self._polling_service.stop_polling()
    
    # ========== Sensor Connection Management ==========
    
    async def connect_all_sensors(self) -> Dict[str, bool]:
        """Connette tutti i sensori abilitati"""
        return await self._management_service.connect_all_sensors()
    
    async def disconnect_all_sensors(self) -> None:
        """Disconnette tutti i sensori"""
        await self._management_service.disconnect_all_sensors()
    
    # ========== Sensor Status & Data ==========
    
    async def get_sensor_status(self, name: Optional[str] = None, check_connection: bool = False) -> List[SensorStatus]:
        """Ottiene lo stato di uno o tutti i sensori"""
        return await self._management_service.get_sensor_status(name, check_connection=check_connection)
    
    async def read_sensor_data(self, name: str) -> Optional[SensorData]:
        """Legge i dati da un sensore specifico"""
        return await self._management_service.read_sensor_data(name)
    
    def get_sensors_list(self) -> List[str]:
        """Restituisce la lista di tutti i sensori"""
        return self._management_service.get_sensors_list()
    
    # ========== Sensor CRUD Operations ==========
    
    def enable_sensor(self, name: str) -> bool:
        """Abilita un sensore"""
        success = self._management_service.enable_sensor(name)
        if success and self._polling_service.running:
            sensor = self.sensors[name]
            self._polling_service.start_sensor_polling(name, sensor)
        return success
    
    def disable_sensor(self, name: str) -> bool:
        """Disabilita un sensore"""
        success = self._management_service.disable_sensor(name)
        if success:
            self._polling_service.stop_sensor_polling(name)
        return success
    
    async def add_sensor(self, sensor_config: SensorConfig) -> bool:
        """Aggiunge un nuovo sensore dinamicamente"""
        success = await self._management_service.add_sensor(sensor_config)
        if success and sensor_config.enabled and self._polling_service.running:
            sensor = self.sensors[sensor_config.name]
            self._polling_service.start_sensor_polling(sensor_config.name, sensor)
        return success
    
    async def remove_sensor(self, name: str) -> bool:
        """Rimuove un sensore dinamicamente"""
        self._polling_service.stop_sensor_polling(name)
        return await self._management_service.remove_sensor(name)
    
    async def update_sensor(self, name: str, updates: Dict) -> bool:
        """Aggiorna un sensore esistente"""
        # Ferma il polling del sensore vecchio
        self._polling_service.stop_sensor_polling(name)
        
        # Aggiorna il sensore
        success = await self._management_service.update_sensor(name, updates)
        
        # Riavvia il polling se necessario
        if success and name in self.sensors:
            sensor = self.sensors[name]
            if sensor.enabled and self._polling_service.running:
                self._polling_service.start_sensor_polling(name, sensor)
        
        return success
    
    # ========== Sensor Actions ==========
    
    async def execute_sensor_action(self, sensor_name: str, action_name: str) -> SensorActionResponse:
        """Esegue un'azione su un sensore"""
        return await self._management_service.execute_sensor_action(sensor_name, action_name)

