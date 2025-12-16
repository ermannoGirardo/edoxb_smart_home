from app.services.business_logic import BusinessLogic
from app.models import SensorData
from typing import Optional
import sys

class AutomationService:
    """Servizio di automazione centrale - logica hardcoded per cliente"""
    
    def __init__(self, business_logic: BusinessLogic):
        self.business_logic = business_logic
        self._mongo_client = None  # Verrà impostato da main.py
    
    async def on_sensor_data(self, sensor_name: str, data: SensorData):
        """Chiamato quando arrivano dati da qualsiasi sensore"""
        
        # Controlla se il sensore è il growbox (per nome o topic)
        # Il sensor_name può essere il nome del sensore (es: "grow box", "arduino_grow_box") 
        # oppure il topic MQTT completo (es: "growbox/grow box/sensor/temperature")
        is_growbox = (
            "growbox" in sensor_name.lower() or 
            "grow_box" in sensor_name.lower() or
            "grow box" in sensor_name.lower() or
            sensor_name.startswith("growbox/grow box/sensor/")
        )
        
        if is_growbox:
            # Normalizza il nome del sensore (potrebbe essere "grow box" o altro)
            normalized_name = sensor_name
            if "grow box" in sensor_name.lower():
                # Estrai il nome del sensore se è un topic MQTT
                if "/" in sensor_name:
                    # È un topic, usa il nome standard
                    normalized_name = "grow box"
                else:
                    normalized_name = sensor_name
            
            # Leggi la fase dal database
            phase = await self._get_growbox_phase(normalized_name)
            
            # Chiama la funzione del plugin se disponibile
            await self._call_plugin_automation(normalized_name, data.data, phase)
    
    async def _get_growbox_phase(self, sensor_name: str) -> Optional[str]:
        """Recupera la fase di crescita dal database"""
        if self._mongo_client is None or self._mongo_client.db is None:
            return None
        
        try:
            config = await self._mongo_client.db.sensor_configs.find_one({"name": sensor_name})
            if config:
                return config.get("growth_phase")
        except Exception as e:
            print(f"Errore lettura fase growbox per {sensor_name}: {e}")
        
        return None
    
    async def _call_plugin_automation(self, sensor_name: str, data: dict, phase: Optional[str]):
        """Chiama la funzione di automazione del plugin se disponibile"""
        try:
            # Prova a importare il modulo del plugin arduino_grow_box
            plugin_module_name = "sensor_arduino_grow_box"
            
            if plugin_module_name in sys.modules:
                plugin_module = sys.modules[plugin_module_name]
                
                # Cerca la funzione handle_growbox_automation
                if hasattr(plugin_module, "handle_growbox_automation"):
                    handler = getattr(plugin_module, "handle_growbox_automation")
                    if callable(handler):
                        await handler(sensor_name, data, phase)
                        return
            
            # Se il plugin non è disponibile, log di default
            print(f"GROWBOX {sensor_name}: Dati ricevuti (fase: {phase or 'non impostata'})")
            print(f"  Dati: {data}")
            
        except Exception as e:
            print(f"Errore chiamata automazione plugin growbox: {e}")

