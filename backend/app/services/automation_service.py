from app.services.business_logic import BusinessLogic
from app.models import SensorData

class AutomationService:
    """Servizio di automazione centrale - logica hardcoded per cliente"""
    
    def __init__(self, business_logic: BusinessLogic):
        self.business_logic = business_logic
    
    async def on_sensor_data(self, sensor_name: str, data: SensorData):
        """Chiamato quando arrivano dati da qualsiasi sensore"""
        # Log del messaggio ricevuto sulla console
        print(f"AutomationService: Ricevuto messaggio da sensore '{sensor_name}': {data.data} (status: {data.status}, timestamp: {data.timestamp})")
        
        # Esempio minimo: sensore temperatura MQTT → accendi Shelly HTTP
        if sensor_name == "werfdwfv" and data.data:
            temp = data.data.get("temperature")
            
            # Converti temperatura a float se necessario
            try:
                if temp is not None:
                    temp_float = float(temp)
                    
                    if temp_float > 25:
                        print(f"AutomationService: Temperatura {temp_float}°C > 25°C, accendo la luce sala...")
                        # Accendi Shelly usando il metodo diretto invece della richiesta HTTP
                        try:
                            result = await self.business_logic.execute_sensor_action("luce sala", "turn-on")
                            if result.success:
                                print(f"AutomationService: ✓ Luce sala accesa con successo")
                            else:
                                print(f"AutomationService: ✗ Errore nell'accensione della luce sala: {result.error}")
                        except ValueError as e:
                            # L'errore contiene le azioni disponibili
                            print(f"AutomationService: ✗ Errore: {e}")
                            # Prova a ottenere le azioni disponibili dal sensore
                            if "luce sala" in self.business_logic.sensors:
                                sensor = self.business_logic.sensors["luce sala"]
                                if sensor.config.actions:
                                    print(f"AutomationService: Azioni disponibili per 'luce sala': {list(sensor.config.actions.keys())}")
                        except Exception as e:
                            print(f"AutomationService: ✗ Errore nell'esecuzione dell'azione: {e}")
                    else:
                        print(f"AutomationService: Temperatura {temp_float}°C <= 25°C, nessuna azione")
            except (ValueError, TypeError) as e:
                print(f"AutomationService: Errore conversione temperatura '{temp}': {e}")

