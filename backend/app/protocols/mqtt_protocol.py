import os
import json
import asyncio
from typing import Dict, Any, Optional, Callable, Tuple
from datetime import datetime
from app.protocols.protocol_base import ProtocolBase
from app.models import SensorConfig, SensorData

try:
    from aiomqtt import Client as MQTTClient
    from aiomqtt.exceptions import MqttReentrantError
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    MQTTClient = None
    MqttReentrantError = None


class MQTTProtocol(ProtocolBase):
    """Protocollo MQTT per comunicazione bidirezionale con sensori"""
    
    # Client MQTT condiviso (inizializzato dal sistema)
    _mqtt_client: Optional[MQTTClient] = None
    _mqtt_client_lock = asyncio.Lock()
    _mqtt_client_connected = False  # Flag per tracciare se il client è connesso
    _connected_sensors_count = 0  # Contatore sensori MQTT connessi
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
        self.topic_command = topic_command_template if topic_command_template != "sensors/{name}/command" else f"sensors/{config.name}/command"
        
        # Flag per indicare se il topic è un wildcard (contiene # o +)
        self.is_wildcard_topic = "#" in self.topic_status or "+" in self.topic_status
        
        print(f"Sensore {config.name}: Topic MQTT configurati - Status: {self.topic_status}, Command: {self.topic_command} (wildcard: {self.is_wildcard_topic})")
        
        # Broker MQTT (da variabili d'ambiente o default)
        self.broker_host = os.getenv("MQTT_BROKER_HOST", "mosquitto")
        self.broker_port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        
        # Stato in RAM per il sensore
        self._ram_state: Dict[str, Any] = {}  # Stato completo in RAM con tutti i valori
        self._ram_state_timestamp: Optional[datetime] = None  # Timestamp dell'ultimo aggiornamento dello stato
        
        # Stato legacy (mantenuto per compatibilità)
        self._last_data: Optional[Dict[str, Any]] = None
        self._aggregated_data: Dict[str, Any] = {}  # Per aggregare dati da topic multipli (wildcard)
        self._message_callbacks: list[Callable] = []
        self._subscription_task: Optional[asyncio.Task] = None
        self._periodic_save_task: Optional[asyncio.Task] = None  # Task periodico per salvare nel DB ogni 10 secondi
        self._save_lock = asyncio.Lock()  # Lock per evitare race condition nel salvataggio
        self._data_lock = asyncio.Lock()  # Lock per garantire consistenza dello stato in RAM
        self._last_message_time: Optional[datetime] = None  # Timestamp dell'ultimo messaggio ricevuto
    
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
                    except (RuntimeError, MqttReentrantError) as e:
                        # Se il client è già nel context (MqttReentrantError o RuntimeError: "Already entered")
                        if MqttReentrantError and isinstance(e, MqttReentrantError):
                            # Client già nel context manager (connesso da un altro sensore)
                            self._mqtt_client_connected = True
                            print(f"Client MQTT già connesso (reentrant) a {self.broker_host}:{self.broker_port}")
                        elif "already entered" in str(e).lower() or "already" in str(e).lower():
                            self._mqtt_client_connected = True
                            print(f"Client MQTT già connesso a {self.broker_host}:{self.broker_port}")
                        else:
                            raise
            
            # Sottoscrizione al topic di stato (riceve aggiornamenti dal sensore)
            await self._mqtt_client.subscribe(self.topic_status)
            print(f"Sensore {self.name}: Sottoscritto a topic MQTT: {self.topic_status}")
            
            # Avvia task per ricevere messaggi
            self._subscription_task = asyncio.create_task(self._message_loop())
            
            # Avvia task periodico per salvare nel DB ogni 10 secondi
            self._periodic_save_task = asyncio.create_task(self._periodic_save_loop())
            
            # Incrementa contatore sensori connessi
            async with self._mqtt_client_lock:
                self._connected_sensors_count += 1
                print(f"📊 Sensori MQTT connessi: {self._connected_sensors_count}")
            
            self.connected = True
            self.update_last_update()
            return True
            
        except Exception as e:
            print(f"Errore connessione MQTT per sensore {self.name}: {e}")
            import traceback
            traceback.print_exc()
            self.connected = False
            return False
    
    async def clear_retained_messages(self) -> None:
        """Pulisce i messaggi retained pubblicando payload vuoti"""
        if not self._mqtt_client or not self.connected:
            return
        
        try:
            # Se il topic è un wildcard, dobbiamo pulire tutti i sottotopic
            if self.is_wildcard_topic:
                # Per wildcard, pubblica un messaggio vuoto sul topic base e sui sottotopic comuni
                base_topic = self.topic_status.replace('/#', '').replace('/+', '')
                
                # Pulisci il topic base
                await self._mqtt_client.publish(
                    base_topic,
                    payload=b'',
                    qos=1,
                    retain=True
                )
                
                # Pulisci anche i topic comuni per growbox (se applicabile)
                if 'growbox' in base_topic.lower() or 'grow box' in base_topic.lower():
                    # Pulisci i topic dei sensori comuni
                    sensor_topics = [
                        f"{base_topic}/temperature_1",
                        f"{base_topic}/temperature_2",
                        f"{base_topic}/temperature_3",
                        f"{base_topic}/temperature_4",
                        f"{base_topic}/humidity_1",
                        f"{base_topic}/humidity_2",
                        f"{base_topic}/humidity_3",
                        f"{base_topic}/humidity_4",
                        f"{base_topic}/water_level"
                    ]
                    for topic in sensor_topics:
                        try:
                            await self._mqtt_client.publish(
                                topic,
                                payload=b'',
                                qos=1,
                                retain=True
                            )
                        except Exception as e:
                            print(f"⚠ Errore pulizia topic {topic}: {e}")
                
                print(f"🧹 Puliti messaggi retained per sensore {self.name} su {base_topic} e sottotopic")
            else:
                # Per topic normale, pulisci direttamente
                await self._mqtt_client.publish(
                    self.topic_status,
                    payload=b'',
                    qos=1,
                    retain=True
                )
                print(f"🧹 Puliti messaggi retained per sensore {self.name} su {self.topic_status}")
        except Exception as e:
            print(f"⚠ Errore pulizia messaggi retained per {self.name}: {e}")
    
    async def disconnect(self) -> None:
        """Disconnette dal broker MQTT"""
        try:
            # Pulisci messaggi retained prima di disconnettere
            await self.clear_retained_messages()
            
            if self._subscription_task:
                self._subscription_task.cancel()
                try:
                    await self._subscription_task
                except asyncio.CancelledError:
                    pass
            
            if self._periodic_save_task:
                self._periodic_save_task.cancel()
                try:
                    await self._periodic_save_task
                except asyncio.CancelledError:
                    pass
            
            if self._mqtt_client:
                # Unsubscribe dal topic
                try:
                    await self._mqtt_client.unsubscribe(self.topic_status)
                except:
                    pass
            
            # Decrementa contatore sensori connessi
            async with self._mqtt_client_lock:
                if self._connected_sensors_count > 0:
                    self._connected_sensors_count -= 1
                print(f"📊 Sensori MQTT connessi: {self._connected_sensors_count}")
                
                # Se non ci sono più sensori connessi, chiudi la connessione MQTT condivisa
                if self._connected_sensors_count == 0 and self._mqtt_client_connected:
                    try:
                        await self._mqtt_client.__aexit__(None, None, None)
                        self._mqtt_client_connected = False
                        print(f"🔌 Connessione MQTT condivisa chiusa (nessun sensore connesso)")
                    except Exception as e:
                        print(f"⚠ Errore chiusura connessione MQTT condivisa: {e}")
            
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
                    
                    # Verifica se il messaggio è retained e se il sensore è offline
                    is_retained = getattr(message, 'retain', False)
                    if is_retained:
                        # Calcola il tempo trascorso dall'ultimo aggiornamento
                        time_since_last_update = (datetime.now() - self.last_update).total_seconds() if self.last_update else float('inf')
                        
                        # Se lo stato in RAM è vuoto, accetta sempre i messaggi retained (prima connessione)
                        # Altrimenti, se non abbiamo ricevuto messaggi recenti (più di 60 secondi), ignora i retained
                        if not self._ram_state and not self._ram_state_timestamp:
                            # Stato vuoto: accetta i retained per inizializzare lo stato
                            print(f"ℹ Sensore {self.name}: Accettato messaggio retained su {topic} (inizializzazione stato)")
                        elif time_since_last_update > 60:
                            # Sensore offline: ignora i retained per evitare dati vecchi
                            print(f"⚠ Sensore {self.name}: Ignorato messaggio retained su {topic} (sensore offline da {time_since_last_update:.1f}s)")
                            continue
                        else:
                            # Messaggio retained ma sensore ancora attivo (probabilmente primo messaggio dopo connessione)
                            print(f"ℹ Sensore {self.name}: Ricevuto messaggio retained su {topic} (sensore attivo)")
                    
                    # Verifica se il topic corrisponde al pattern (supporta wildcard)
                    if not self._topic_matches(topic, self.topic_status):
                        # Non loggare messaggi non corrispondenti (comportamento normale con client MQTT condiviso)
                        continue
                    
                    # Prova a parsare come JSON, altrimenti come valore semplice
                    try:
                        payload = json.loads(message.payload.decode())
                        # Log dettagliato solo per altri sensori (non per energia che riceve messaggi molto frequenti e voluminosi)
                        if self.name != "energia" and (isinstance(payload, dict) and ("method" in payload or "em1" in str(payload))):
                            print(f"📨 Sensore {self.name}: Messaggio MQTT ricevuto su {topic}")
                            print(f"   Payload (primi 500 char): {json.dumps(payload, indent=2)[:500]}")
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
                    
                    # Aggiorna lo stato in RAM
                    current_time = datetime.now()
                    
                    if self.is_wildcard_topic:
                        # Estrai il tipo di dato dal topic (es: 'temperature_1' da '.../sensor/temperature_1')
                        data_type, _ = self._extract_data_from_topic(topic)
                        
                        # Aggiorna lo stato in RAM con lock per garantire consistenza
                        async with self._data_lock:
                            # Aggiorna lo stato in RAM
                            self._ram_state[data_type] = payload
                            self._ram_state_timestamp = current_time
                            
                            # Mantieni anche _aggregated_data e _last_data per compatibilità
                            if not hasattr(self, '_aggregated_data'):
                                self._aggregated_data = {}
                            self._aggregated_data[data_type] = payload
                            self._last_data = self._aggregated_data.copy()
                            self._last_message_time = current_time
                        
                        print(f"Sensore {self.name}: Ricevuto messaggio MQTT su {topic} (tipo: {data_type}): {payload}")
                        print(f"  Stato RAM aggiornato: {self._ram_state}")
                    else:
                        # Topic normale, aggiorna lo stato in RAM
                        async with self._data_lock:
                            if isinstance(payload, dict):
                                # Se è un dict, unisci con lo stato esistente
                                self._ram_state.update(payload)
                            else:
                                # Se è un valore semplice, usa "value" come chiave
                                self._ram_state["value"] = payload
                            
                            self._ram_state_timestamp = current_time
                            self._last_data = self._ram_state.copy()
                            self._last_message_time = current_time
                    
                    self.update_last_update()
                    
                    # Notifica AutomationService con lo stato in RAM aggiornato (non bloccante)
                    if self.__class__._automation_service:
                        # Crea task asincrono senza await per non bloccare il loop dei messaggi
                        async def notify_automation():
                            try:
                                # Crea SensorData con lo stato in RAM corrente
                                async with self._data_lock:
                                    ram_state_copy = self._ram_state.copy()
                                    ram_timestamp = self._ram_state_timestamp
                                
                                if ram_state_copy and ram_timestamp:
                                    sensor_data = SensorData(
                                        sensor_name=self.name,
                                        timestamp=ram_timestamp,
                                        data=ram_state_copy,
                                        status="ok"
                                    )
                                    await self.__class__._automation_service.on_sensor_data(self.name, sensor_data)
                            except Exception as e:
                                print(f"Errore automazione MQTT per {self.name}: {e}")
                        
                        # Esegui in background senza bloccare il loop dei messaggi
                        asyncio.create_task(notify_automation())
                    
                    # Notifica callbacks registrati
                    for callback in self._message_callbacks:
                        try:
                            async with self._data_lock:
                                state_copy = self._ram_state.copy()
                            await callback(self.name, state_copy)
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
    
    async def _periodic_save_loop(self) -> None:
        """Task periodico che salva lo stato in RAM nel DB ogni 10 secondi"""
        try:
            while True:
                await asyncio.sleep(10)  # Aspetta 10 secondi
                
                async with self._data_lock:
                    # Verifica se ci sono dati da salvare
                    if not self._ram_state or self._ram_state_timestamp is None:
                        continue
                    
                    # Crea SensorData con lo stato corrente
                    sensor_data = SensorData(
                        sensor_name=self.name,
                        timestamp=self._ram_state_timestamp,
                        data=self._ram_state.copy(),
                        status="ok"
                    )
                
                # Salva nel DB (fuori dal lock per non bloccare)
                if self.__class__._mongo_client:
                    async with self._save_lock:
                        try:
                            await self.__class__._mongo_client.save_sensor_data(sensor_data)
                            print(f"💾 Sensore {self.name}: Stato salvato nel DB (periodico)")
                        except Exception as e:
                            print(f"Errore salvataggio periodico MongoDB per {self.name}: {e}")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Errore nel loop di salvataggio periodico per {self.name}: {e}")
    
    async def read_data(self) -> SensorData:
        """Legge i dati dallo stato in RAM. Se il timestamp è più vecchio di 2 minuti, restituisce no data e segna come disconnesso"""
        async with self._data_lock:
            current_time = datetime.now()
            
            # Verifica se ci sono dati nello stato in RAM
            if not self._ram_state or self._ram_state_timestamp is None:
                # Nessun dato disponibile
                self.connected = False
                return SensorData(
                    sensor_name=self.name,
                    timestamp=current_time,
                    data={},
                    status="error",
                    error="Nessun dato disponibile"
                )
            
            # Calcola il tempo trascorso dall'ultimo aggiornamento
            time_since_update = (current_time - self._ram_state_timestamp).total_seconds()
            
            # Se il timestamp è più vecchio di 2 minuti (120 secondi), restituisci no data
            if time_since_update > 120:
                self.connected = False
                return SensorData(
                    sensor_name=self.name,
                    timestamp=self._ram_state_timestamp,
                    data={},
                    status="error",
                    error=f"Dati non aggiornati (ultimo aggiornamento: {time_since_update:.1f}s fa)"
                )
            
            # Dati validi, restituisci lo stato in RAM
            self.connected = True
            # Crea una copia profonda per evitare modifiche concorrenti
            data_copy = self._ram_state.copy()
            return SensorData(
                sensor_name=self.name,
                timestamp=self._ram_state_timestamp,
                data=data_copy,
                status="ok"
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

