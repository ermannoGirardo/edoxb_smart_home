import asyncio
from typing import Dict, List, Optional
from app.sensors.sensor_base import SensorBase
from app.sensors.factory import SensorFactory
from app.db.mongo_client import MongoClientWrapper
from app.models import SensorConfig, SensorStatus, SensorData, SensorActionResponse
from app.services.port_manager import PortManager


class SensorManagementService:
    """Servizio per gestire CRUD, connessioni e operazioni sui sensori"""
    
    def __init__(
        self,
        sensors: Dict[str, SensorBase],
        mongo_client: MongoClientWrapper
    ):
        self.sensors = sensors
        self.mongo_client = mongo_client
        # Inizializza il PortManager per la gestione delle porte WebSocket
        self.port_manager = PortManager()
        
        # Configura il PortManager per tutti i protocolli WebSocket
        from app.protocols.websocket_protocol import WebSocketProtocol
        WebSocketProtocol.set_port_manager(self.port_manager)
    
    async def connect_all_sensors(self) -> Dict[str, bool]:
        """Connette tutti i sensori abilitati, con validazione delle porte"""
        # Valida tutte le porte prima di connettere
        validation_results = self.port_manager.validate_all_ports(self.sensors)
        invalid_sensors = [name for name, valid in validation_results.items() if not valid]
        
        if invalid_sensors:
            print(f"ATTENZIONE: Porte non valide per sensori: {', '.join(invalid_sensors)}")
            print("Tentativo di auto-assegnazione porte...")
        
        results = {}
        for name, sensor in self.sensors.items():
            if sensor.enabled:
                try:
                    # Se la porta non è valida, il sensore proverà ad assegnarne una automaticamente
                    connected = await sensor.connect()
                    results[name] = connected
                    if connected:
                        # Verifica la porta assegnata e salva nel database se è stata auto-assegnata
                        from app.sensors.generic_sensor import GenericSensor
                        if isinstance(sensor, GenericSensor) and sensor.protocol:
                            protocol = sensor.protocol
                            if hasattr(protocol, 'port') and protocol.port:
                                print(f"Sensore {name} connesso su porta {protocol.port}")
                                # Se la porta è stata auto-assegnata, salva la configurazione aggiornata
                                if hasattr(protocol, '_requested_port') and protocol.config.port != protocol._requested_port:
                                    await self._save_sensor_config_if_needed(sensor)
                except Exception as e:
                    print(f"Errore connessione sensore {name}: {e}")
                    results[name] = False
        return results
    
    async def _save_sensor_config_if_needed(self, sensor: SensorBase) -> None:
        """Salva la configurazione del sensore nel database se necessario"""
        if self.mongo_client is not None:
            try:
                await self.mongo_client.save_sensor_config(sensor.config)
                print(f"Configurazione aggiornata per sensore {sensor.name} salvata nel database (porta: {sensor.config.port})")
            except Exception as e:
                print(f"Avviso: Impossibile salvare configurazione per sensore {sensor.name}: {e}")
    
    async def disconnect_all_sensors(self) -> None:
        """Disconnette tutti i sensori"""
        for sensor in self.sensors.values():
            try:
                await sensor.disconnect()
            except Exception as e:
                print(f"Errore disconnessione sensore {sensor.name}: {e}")
    
    async def check_sensor_connection(self, sensor: SensorBase) -> bool:
        """Verifica se un sensore è connesso"""
        try:
            # Usa il metodo is_connected del sensore che delega al protocollo
            return await sensor.is_connected()
        except Exception as e:
            # Se c'è un errore, il sensore non è connesso
            return False
    
    async def get_sensor_status(self, name: Optional[str] = None, check_connection: bool = False) -> List[SensorStatus]:
        """
        Ottiene lo stato di uno o tutti i sensori.
        
        Args:
            name: Nome del sensore (None per tutti)
            check_connection: Se True, verifica la connessione. Se False, restituisce solo lo stato cached (veloce)
        """
        if name:
            if name not in self.sensors:
                return []
            sensor = self.sensors[name]
            status_dict = sensor.get_status()
            
            if check_connection:
                # Verifica la connessione solo se richiesto
                is_connected = await self.check_sensor_connection(sensor)
                status_dict['connected'] = is_connected
            # Altrimenti usa lo stato cached (sensor.connected)
            
            return [SensorStatus(**status_dict)]
        else:
            sensors_list = list(self.sensors.values())
            status_list = []
            
            # Restituisce subito lo stato cached (veloce, non bloccante)
            for sensor in sensors_list:
                status_dict = sensor.get_status()
                status_list.append(SensorStatus(**status_dict))
            
            # Se richiesto, verifica le connessioni (blocca ma con timeout brevi)
            if check_connection:
                async def check_with_timeout(sensor: SensorBase) -> bool:
                    """Controlla la connessione con timeout di 1.5 secondi"""
                    try:
                        return await asyncio.wait_for(
                            self.check_sensor_connection(sensor),
                            timeout=1.5
                        )
                    except asyncio.TimeoutError:
                        return False
                    except Exception:
                        return False
                
                connection_checks = [check_with_timeout(sensor) for sensor in sensors_list]
                connection_results = await asyncio.gather(*connection_checks, return_exceptions=True)
                
                # Aggiorna lo stato cached dei sensori e ricrea la lista con i valori aggiornati
                updated_status_list = []
                for sensor, is_connected in zip(sensors_list, connection_results):
                    connected_value = is_connected if isinstance(is_connected, bool) else False
                    sensor.connected = connected_value
                    # Ricrea lo status con il valore aggiornato
                    status_dict = sensor.get_status()
                    status_dict['connected'] = connected_value
                    updated_status_list.append(SensorStatus(**status_dict))
                
                return updated_status_list
            
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
        return True
    
    def disable_sensor(self, name: str) -> bool:
        """Disabilita un sensore"""
        if name not in self.sensors:
            return False
        self.sensors[name].disable()
        return True
    
    async def add_sensor(self, sensor_config: SensorConfig) -> bool:
        """Aggiunge un nuovo sensore dinamicamente"""
        if sensor_config.name in self.sensors:
            return False  # Sensore già esistente
        
        try:
            # Salva nel database (senza porta se non specificata, verrà aggiunta dopo)
            if self.mongo_client is not None:
                await self.mongo_client.save_sensor_config(sensor_config)
            
            # Crea il sensore
            sensor = SensorFactory.create_sensor(sensor_config)
            self.sensors[sensor_config.name] = sensor
            
            # Connetti se abilitato
            if sensor_config.enabled:
                connected = await sensor.connect()
                if connected:
                    # Se la porta è stata auto-assegnata, salva la configurazione aggiornata
                    from app.sensors.generic_sensor import GenericSensor
                    if isinstance(sensor, GenericSensor) and sensor.protocol:
                        protocol = sensor.protocol
                        if hasattr(protocol, 'port') and protocol.port:
                            if hasattr(protocol, '_requested_port') and protocol.config.port != protocol._requested_port:
                                if self.mongo_client is not None:
                                    await self.mongo_client.save_sensor_config(sensor.config)
                                    print(f"Porta auto-assegnata {protocol.port} salvata nel database per sensore {sensor.name}")
            
            return True
        except Exception as e:
            print(f"Errore nell'aggiunta del sensore {sensor_config.name}: {e}")
            return False
    
    async def remove_sensor(self, name: str) -> bool:
        """Rimuove un sensore dinamicamente"""
        if name not in self.sensors:
            return False
        
        try:
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
        
        # Esegue l'azione usando il metodo del sensore base che delega al protocollo
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

