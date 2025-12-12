import asyncio
import aiohttp
from typing import Dict, List, Optional
from datetime import datetime
from app.sensors.sensor_base import SensorBase
from app.sensors.factory import SensorFactory
from app.db.mongo_client import MongoClientWrapper
from app.services.mqtt_client import MQTTClient
from app.models import SensorData, SensorStatus, SensorConfig, SensorActionResponse


class BusinessLogic:
    """Logica centralizzata per la gestione dei sensori"""
    
    def __init__(
        self,
        sensors: Dict[str, SensorBase],
        mongo_client: MongoClientWrapper,
        mqtt_client: Optional[MQTTClient] = None
    ):
        self.sensors = sensors
        self.mongo_client = mongo_client
        self.mqtt_client = mqtt_client
        self._polling_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
    
    async def start_polling(self) -> None:
        """Avvia il polling di tutti i sensori abilitati"""
        self._running = True
        for name, sensor in self.sensors.items():
            if sensor.enabled:
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
        poll_interval = sensor.config.poll_interval or 5
        
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
    
    async def connect_all_sensors(self) -> Dict[str, bool]:
        """Connette tutti i sensori abilitati"""
        results = {}
        for name, sensor in self.sensors.items():
            if sensor.enabled:
                try:
                    connected = await sensor.connect()
                    results[name] = connected
                except Exception as e:
                    print(f"Errore connessione sensore {name}: {e}")
                    results[name] = False
        return results
    
    async def disconnect_all_sensors(self) -> None:
        """Disconnette tutti i sensori"""
        for sensor in self.sensors.values():
            try:
                await sensor.disconnect()
            except Exception as e:
                print(f"Errore disconnessione sensore {sensor.name}: {e}")
    
    async def check_sensor_connection(self, sensor: SensorBase) -> bool:
        """Verifica se un sensore è connesso facendo una richiesta GET a ip/status"""
        try:
            # Costruisce l'URL per il check di status
            protocol = getattr(sensor.config, 'protocol', 'http') or 'http'
            if protocol not in ['http', 'https']:
                protocol = 'http'
            
            base_url = f"{protocol}://{sensor.ip}"
            if sensor.port:
                base_url += f":{sensor.port}"
            
            status_url = f"{base_url}/status"
            
            # Timeout breve per il check di connessione (2 secondi)
            timeout = aiohttp.ClientTimeout(total=2)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(status_url) as response:
                    # Se otteniamo una risposta (qualsiasi status code), il sensore è raggiungibile
                    return response.status < 500
        except Exception as e:
            # Se c'è un errore (timeout, connessione rifiutata, ecc.), il sensore non è connesso
            return False
    
    async def get_sensor_status(self, name: Optional[str] = None) -> List[SensorStatus]:
        """Ottiene lo stato di uno o tutti i sensori, verificando la connessione per ognuno"""
        if name:
            if name not in self.sensors:
                return []
            sensor = self.sensors[name]
            # Verifica la connessione
            is_connected = await self.check_sensor_connection(sensor)
            status_dict = sensor.get_status()
            status_dict['connected'] = is_connected
            return [SensorStatus(**status_dict)]
        else:
            # Per tutti i sensori, verifica la connessione in parallelo
            sensors_list = list(self.sensors.values())
            connection_checks = [self.check_sensor_connection(sensor) for sensor in sensors_list]
            connection_results = await asyncio.gather(*connection_checks, return_exceptions=True)
            
            status_list = []
            for sensor, is_connected in zip(sensors_list, connection_results):
                status_dict = sensor.get_status()
                # Se il check ha generato un'eccezione, considera il sensore come non connesso
                status_dict['connected'] = is_connected if isinstance(is_connected, bool) else False
                status_list.append(SensorStatus(**status_dict))
            
            return status_list
    
    async def read_sensor_data(self, name: str) -> Optional[SensorData]:
        """Legge i dati da un sensore specifico"""
        if name not in self.sensors:
            return None
        
        sensor = self.sensors[name]
        if not sensor.enabled:
            return None
        
        try:
            return await sensor.read_data()
        except Exception as e:
            print(f"Errore lettura sensore {name}: {e}")
            return None
    
    def get_sensors_list(self) -> List[str]:
        """Restituisce la lista di tutti i sensori"""
        return list(self.sensors.keys())
    
    def enable_sensor(self, name: str) -> bool:
        """Abilita un sensore"""
        if name not in self.sensors:
            return False
        self.sensors[name].enable()
        if self._running and name not in self._polling_tasks:
            task = asyncio.create_task(self._poll_sensor(name, self.sensors[name]))
            self._polling_tasks[name] = task
        return True
    
    def disable_sensor(self, name: str) -> bool:
        """Disabilita un sensore"""
        if name not in self.sensors:
            return False
        self.sensors[name].disable()
        if name in self._polling_tasks:
            self._polling_tasks[name].cancel()
            del self._polling_tasks[name]
        return True
    
    async def add_sensor(self, sensor_config: SensorConfig) -> bool:
        """Aggiunge un nuovo sensore dinamicamente"""
        if sensor_config.name in self.sensors:
            return False  # Sensore già esistente
        
        try:
            # Salva nel database
            if self.mongo_client is not None:
                await self.mongo_client.save_sensor_config(sensor_config)
            
            # Crea il sensore
            sensor = SensorFactory.create_sensor(sensor_config)
            self.sensors[sensor_config.name] = sensor
            
            # Connetti se abilitato
            if sensor_config.enabled:
                await sensor.connect()
                
                # Avvia polling se il sistema è in esecuzione
                if self._running:
                    task = asyncio.create_task(self._poll_sensor(sensor_config.name, sensor))
                    self._polling_tasks[sensor_config.name] = task
            
            return True
        except Exception as e:
            print(f"Errore nell'aggiunta del sensore {sensor_config.name}: {e}")
            return False
    
    async def remove_sensor(self, name: str) -> bool:
        """Rimuove un sensore dinamicamente"""
        if name not in self.sensors:
            return False
        
        try:
            # Ferma polling se attivo
            if name in self._polling_tasks:
                self._polling_tasks[name].cancel()
                await asyncio.gather(self._polling_tasks[name], return_exceptions=True)
                del self._polling_tasks[name]
            
            # Disconnette
            sensor = self.sensors[name]
            await sensor.disconnect()
            
            # Rimuove dal dizionario
            del self.sensors[name]
            
            # Rimuove dal database
            if self.mongo_client is not None:
                await self.mongo_client.delete_sensor_config(name)
            
            return True
        except Exception as e:
            print(f"Errore nella rimozione del sensore {name}: {e}")
            return False
    
    async def update_sensor(self, name: str, updates: Dict) -> bool:
        """Aggiorna un sensore esistente"""
        if name not in self.sensors:
            return False
        
        try:
            # Recupera la configurazione attuale
            current_config = self.sensors[name].config
            
            # Crea un dizionario con i valori aggiornati
            config_dict = current_config.model_dump()
            config_dict.update(updates)
            
            # Ricrea la configurazione
            new_config = SensorConfig(**config_dict)
            
            # Rimuove il sensore vecchio
            await self.remove_sensor(name)
            
            # Aggiunge il sensore aggiornato
            return await self.add_sensor(new_config)
        except Exception as e:
            print(f"Errore nell'aggiornamento del sensore {name}: {e}")
            return False
    
    async def execute_sensor_action(self, sensor_name: str, action_name: str) -> SensorActionResponse:
        """Esegue un'azione su un sensore"""
        if sensor_name not in self.sensors:
            raise ValueError(f"Sensore '{sensor_name}' non trovato")
        
        sensor = self.sensors[sensor_name]
        
        # Verifica che il sensore supporti azioni (per ora solo HTTP)
        from app.sensors.http_sensor import HTTPSensor
        if not isinstance(sensor, HTTPSensor):
            raise ValueError(f"Il sensore '{sensor_name}' non supporta azioni (solo sensori HTTP supportano azioni)")
        
        # Esegue l'azione
        try:
            result = await sensor.execute_action(action_name)
            return SensorActionResponse(
                sensor_name=sensor_name,
                action_name=action_name,
                success=result["success"],
                status_code=result.get("status_code"),
                data=result.get("data"),
                error=result.get("error")
            )
        except ValueError as e:
            # Azione non trovata
            return SensorActionResponse(
                sensor_name=sensor_name,
                action_name=action_name,
                success=False,
                status_code=None,
                data=None,
                error=str(e)
            )
        except Exception as e:
            # Altri errori
            return SensorActionResponse(
                sensor_name=sensor_name,
                action_name=action_name,
                success=False,
                status_code=None,
                data=None,
                error=f"Errore nell'esecuzione dell'azione: {str(e)}"
            )

