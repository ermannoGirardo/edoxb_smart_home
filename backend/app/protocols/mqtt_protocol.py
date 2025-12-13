import os
import json
import asyncio
from typing import Dict, Any, Optional, Callable, Tuple
from datetime import datetime
from app.protocols.protocol_base import ProtocolBase
from app.models import SensorConfig, SensorData

try:
    from aiomqtt import Client as MQTTClient
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    MQTTClient = None


class MQTTProtocol(ProtocolBase):
    """Protocollo MQTT per comunicazione bidirezionale con sensori"""
    
    # Client MQTT condiviso (inizializzato dal sistema)
    _mqtt_client: Optional[MQTTClient] = None
    _mqtt_client_lock = asyncio.Lock()
    _mqtt_client_connected = False  # Flag per tracciare se il client è connesso
    _mongo_client = None  # Riferimento a MongoDB per salvare dati immediatamente
    _automation_service = None  # Riferimento ad AutomationService
    
    @classmethod
    def set_mqtt_client(cls, mqtt_client: MQTTClient) -> None:
        """Imposta il client MQTT condiviso per tutti i protocolli MQTT"""
        cls._mqtt_client = mqtt_client
    
    def __init__(self, config: SensorConfig):
        super().__init__(config)
        
        if not MQTT_AVAILABLE:
            raise ImportError("aiomqtt non installato. Installa con: pip install aiomqtt")
        
        # Topic MQTT: se specificati nella config (dal plugin), usali, altrimenti usa topic standardizzati
        # I topic possono essere definiti dal plugin del sensore nei metadata o nella configurazione
        # Sostituisci placeholder {device_id} e {name} se presenti
        topic_status_template = config.mqtt_topic_status or f"sensors/{config.name}/status"
        topic_command_template = config.mqtt_topic_command or f"sensors/{config.name}/command"
        
        # Sostituisci placeholder
        replacements = {
            "{name}": config.name,
            "{device_id}": config.device_id or ""
        }
        for placeholder, value in replacements.items():
            topic_status_template = topic_status_template.replace(placeholder, value)
            topic_command_template = topic_command_template.replace(placeholder, value)
        
        self.topic_status = topic_status_template
        # Usa direttamente il template dopo la sostituzione dei placeholder
        # La logica di default è già gestita alla linea 42
        self.topic_command = topic_command_template
        
        # Flag per indicare se il topic è un wildcard (contiene # o +)
        self.is_wildcard_topic = "#" in self.topic_status or "+" in self.topic_status
        
        print(f"Sensore {config.name}: Topic MQTT configurati - Status: {self.topic_status}, Command: {self.topic_command} (wildcard: {self.is_wildcard_topic})")
        
        # Broker MQTT (da variabili d'ambiente o default)
        self.broker_host = os.getenv("MQTT_BROKER_HOST", "mosquitto")
        self.broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        
        # Stato
        self._last_data: Optional[Dict[str, Any]] = None
        self._aggregated_data: Dict[str, Any] = {}  # Per aggregare dati da topic multipli (wildcard)
        self._message_callbacks: list[Callable] = []
        self._subscription_task: Optional[asyncio.Task] = None
    
    async def connect(self) -> bool:
        """Si connette al broker MQTT e si sottoscrive al topic di stato"""
        try:
            if not self._mqtt_client:
                raise RuntimeError("Client MQTT non inizializzato. Assicurati che MQTTProtocol.set_mqtt_client() sia stato chiamato.")
            
            # Apri connessione se non già aperta (lazy connection)
            # aiomqtt.Client usa un context manager, quindi dobbiamo entrare nel context
            async with self._mqtt_client_lock:
                if not self._mqtt_client_connected:
                    try:
                        # Entra nel context manager per aprire la connessione
                        await self._mqtt_client.__aenter__()
                        self._mqtt_client_connected = True
                        print(f"Client MQTT connesso a {self.broker_host}:{self.broker_port}")
                    except RuntimeError as e:
                        # Se il client è già nel context (RuntimeError: "Already entered")
                        if "already entered" in str(e).lower() or "already" in str(e).lower():
                            self._mqtt_client_connected = True
                            print(f"Client MQTT già connesso a {self.broker_host}:{self.broker_port}")
                        else:
                            raise
            
            # Sottoscrizione al topic di stato (riceve aggiornamenti dal sensore)
            await self._mqtt_client.subscribe(self.topic_status)
            print(f"Sensore {self.name}: Sottoscritto a topic MQTT: {self.topic_status}")
            
            # Avvia task per ricevere messaggi
            self._subscription_task = asyncio.create_task(self._message_loop())
            
            self.connected = True
            self.update_last_update()
            return True
            
        except Exception as e:
            print(f"Errore connessione MQTT per sensore {self.name}: {e}")
            import traceback
            traceback.print_exc()
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnette dal broker MQTT"""
        try:
            if self._subscription_task:
                self._subscription_task.cancel()
                try:
                    await self._subscription_task
                except asyncio.CancelledError:
                    pass
            
            if self._mqtt_client:
                # Unsubscribe dal topic
                try:
                    await self._mqtt_client.unsubscribe(self.topic_status)
                except:
                    pass
            
            self.connected = False
            print(f"Disconnesso MQTT per sensore {self.name}")
        except Exception as e:
            print(f"Errore disconnessione MQTT per sensore {self.name}: {e}")
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Verifica se un topic corrisponde a un pattern (supporta wildcard # e +)"""
        if not self.is_wildcard_topic:
            return topic == pattern
        
        # Converti pattern wildcard in regex
        # # = match tutto il resto
        # + = match un livello
        pattern_parts = pattern.split('/')
        topic_parts = topic.split('/')
        
        if len(topic_parts) < len(pattern_parts):
            return False
        
        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part == '#':
                # Match tutto il resto
                return True
            elif pattern_part == '+':
                # Match un livello qualsiasi
                continue
            elif pattern_part != topic_parts[i]:
                return False
        
        # Se il pattern non finisce con #, devono avere la stessa lunghezza
        if pattern_parts[-1] != '#' and len(topic_parts) != len(pattern_parts):
            return False
        
        return True
    
    def _extract_data_from_topic(self, topic: str) -> Tuple[str, Any]:
        """Estrae il tipo di dato dal topic (es: 'temperature' da 'shellies/shellyht-ABC123/sensor/temperature')"""
        parts = topic.split('/')
        if len(parts) >= 2:
            # Ultimo elemento è il tipo di dato
            data_type = parts[-1]
            return data_type, None
        return "value", None
    
    async def _message_loop(self) -> None:
        """Loop per ricevere messaggi MQTT"""
        try:
            async for message in self._mqtt_client.messages:
                try:
                    # Parse del messaggio
                    topic = str(message.topic)
                    
                    # Verifica se il topic corrisponde al pattern (supporta wildcard)
                    if not self._topic_matches(topic, self.topic_status):
                        continue
                    
                    # Prova a parsare come JSON, altrimenti come valore semplice
                    try:
                        payload = json.loads(message.payload.decode())
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Se non è JSON, prova come valore numerico o stringa
                        payload_str = message.payload.decode()
                        try:
                            # Prova come float
                            payload = float(payload_str)
                        except ValueError:
                            try:
                                # Prova come int
                                payload = int(payload_str)
                            except ValueError:
                                # Fallback a stringa
                                payload = payload_str
                    
                    # Se è un wildcard topic, aggrega i dati
                    if self.is_wildcard_topic:
                        # Estrai il tipo di dato dal topic (es: 'temperature' da '.../sensor/temperature')
                        data_type, _ = self._extract_data_from_topic(topic)
                        
                        # Aggrega nel dict
                        if not hasattr(self, '_aggregated_data'):
                            self._aggregated_data = {}
                        self._aggregated_data[data_type] = payload
                        
                        # Aggiorna _last_data con tutti i dati aggregati
                        self._last_data = self._aggregated_data.copy()
                        
                        print(f"Sensore {self.name}: Ricevuto messaggio MQTT su {topic} (tipo: {data_type}): {payload}")
                        print(f"  Dati aggregati: {self._aggregated_data}")
                    else:
                        # Topic normale, usa il payload direttamente
                        self._last_data = payload if isinstance(payload, dict) else {"value": payload}
                    
                    self.update_last_update()
                    
                    # Crea SensorData con timestamp preciso
                    sensor_data = SensorData(
                        sensor_name=self.name,
                        timestamp=datetime.now(),
                        data=self._last_data,
                        status="ok"
                    )
                    
                    # Salva immediatamente in MongoDB se disponibile
                    if self.__class__._mongo_client:
                        try:
                            await self.__class__._mongo_client.save_sensor_data(sensor_data)
                        except Exception as e:
                            print(f"Errore salvataggio MongoDB MQTT per {self.name}: {e}")
                    
                    # Notifica AutomationService se presente (stampa log immediatamente)
                    if self.__class__._automation_service:
                        try:
                            await self.__class__._automation_service.on_sensor_data(self.name, sensor_data)
                        except Exception as e:
                            print(f"Errore automazione MQTT per {self.name}: {e}")
                    
                    # Notifica callbacks registrati
                    for callback in self._message_callbacks:
                        try:
                            await callback(self.name, self._last_data)
                        except Exception as e:
                            print(f"Errore in callback MQTT per {self.name}: {e}")
                except json.JSONDecodeError as e:
                    print(f"Errore parsing JSON MQTT per {self.name}: {e}")
                except Exception as e:
                    print(f"Errore gestione messaggio MQTT per {self.name}: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Errore nel message loop MQTT per {self.name}: {e}")
            self.connected = False
    
    def register_message_callback(self, callback: Callable) -> None:
        """Registra un callback che viene chiamato quando arrivano messaggi"""
        self._message_callbacks.append(callback)
    
    async def read_data(self) -> SensorData:
        """Legge l'ultimo dato ricevuto via MQTT (aggregato se wildcard topic)"""
        if self._last_data is not None:
            return SensorData(
                sensor_name=self.name,
                timestamp=datetime.now(),
                data=self._last_data,
                status="ok"
            )
        else:
            return SensorData(
                sensor_name=self.name,
                timestamp=datetime.now(),
                data={},
                status="ok",
                error="Nessun dato disponibile"
            )
    
    async def is_connected(self) -> bool:
        """Verifica se la connessione MQTT è attiva"""
        return self.connected and self._mqtt_client is not None
    
    async def execute_action(self, action_name: str, action_path: str) -> Dict[str, Any]:
        """Pubblica un comando sul topic MQTT del sensore"""
        try:
            if not self.connected:
                await self.connect()
            
            # Il payload del comando può essere passato come action_path (JSON string)
            # oppure costruito da action_name
            try:
                payload = json.loads(action_path) if action_path else {}
            except json.JSONDecodeError:
                # Se non è JSON, costruisci payload semplice
                payload = {"action": action_name}
                if action_path:
                    payload["path"] = action_path
            
            # Pubblica sul topic di comando
            await self._mqtt_client.publish(
                self.topic_command,
                payload=json.dumps(payload).encode(),
                qos=1
            )
            
            print(f"Comando MQTT inviato a {self.name}: {action_name} su {self.topic_command}")
            
            return {
                "success": True,
                "status_code": 200,
                "data": {"topic": self.topic_command, "payload": payload},
                "error": None
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"Errore invio comando MQTT per {self.name}: {error_msg}")
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": error_msg
            }

