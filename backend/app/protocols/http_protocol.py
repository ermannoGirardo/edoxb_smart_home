import aiohttp
from typing import Dict, Any
from datetime import datetime
from app.protocols.protocol_base import ProtocolBase
from app.models import SensorConfig, SensorData


class HTTPProtocol(ProtocolBase):
    """Protocollo HTTP per la comunicazione con i sensori"""
    
    def __init__(self, config: SensorConfig):
        super().__init__(config)
        # Percorso URL dal file di configurazione (default "/" se non specificato)
        self.endpoint = config.endpoint if config.endpoint is not None else "/"
        # Protocollo HTTP dal file di configurazione (default "http" se non specificato)
        protocol = config.http_protocol if config.http_protocol is not None else "http"
        if protocol not in ["http", "https"]:
            raise ValueError(f"Protocollo HTTP non valido per sensore {self.name}: {protocol}. Usare 'http' o 'https'")
        
        # Timeout dal file di configurazione (default 10 secondi se non specificato)
        timeout_seconds = config.timeout if config.timeout is not None else 10
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.session: aiohttp.ClientSession = None
        
        # Costruisce l'URL completo: protocol://ip:port/endpoint
        self.base_url = f"{protocol}://{config.ip}"
        if config.port:
            self.base_url += f":{config.port}"
        # Assicura che l'endpoint inizi con "/"
        if not self.endpoint.startswith("/"):
            self.endpoint = "/" + self.endpoint
        self.url = f"{self.base_url}{self.endpoint}"
        
        print(f"Protocollo HTTP configurato per sensore '{self.name}': URL={self.url}, timeout={timeout_seconds}s")
    
    async def connect(self) -> bool:
        """Connette al sensore HTTP con timeout breve per risposta rapida"""
        try:
            # Usa un timeout molto breve per la connessione iniziale (2 secondi)
            # Questo rende l'interfaccia molto più reattiva
            quick_timeout = aiohttp.ClientTimeout(total=2, connect=1)
            async with aiohttp.ClientSession(timeout=quick_timeout) as quick_session:
                async with quick_session.get(self.url) as response:
                    if response.status == 200:
                        self.connected = True
                        self.update_last_update()
                        # Crea la sessione permanente solo se la connessione è riuscita
                        if self.session is None or self.session.closed:
                            self.session = aiohttp.ClientSession(timeout=self.timeout)
                        return True
                    else:
                        self.connected = False
                        return False
        except Exception as e:
            print(f"Errore connessione protocollo HTTP per sensore {self.name}: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnette dal sensore HTTP"""
        if self.session and not self.session.closed:
            await self.session.close()
        self.connected = False
    
    async def read_data(self) -> SensorData:
        """Legge i dati dal sensore HTTP"""
        try:
            if not self.connected:
                await self.connect()
            
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            async with self.session.get(self.url) as response:
                if response.status == 200:
                    data = await response.json()
                    self.update_last_update()
                    self.connected = True
                    return SensorData(
                        sensor_name=self.name,
                        timestamp=datetime.now(),
                        data=data,
                        status="ok"
                    )
                else:
                    self.connected = False
                    return SensorData(
                        sensor_name=self.name,
                        timestamp=datetime.now(),
                        data={},
                        status="error",
                        error=f"HTTP {response.status}"
                    )
        except Exception as e:
            self.connected = False
            error_msg = str(e)
            return SensorData(
                sensor_name=self.name,
                timestamp=datetime.now(),
                data={},
                status="error",
                error=error_msg
            )
    
    async def is_connected(self) -> bool:
        """Verifica se il sensore è connesso con timeout molto breve per risposta rapida"""
        try:
            # Usa un timeout molto breve (1 secondo) per i controlli di connessione
            # Questo rende l'interfaccia praticamente immediata
            quick_timeout = aiohttp.ClientTimeout(total=1, connect=0.5)
            async with aiohttp.ClientSession(timeout=quick_timeout) as quick_session:
                async with quick_session.get(self.url) as response:
                    self.connected = (response.status == 200)
                    return self.connected
        except:
            self.connected = False
            return False
    
    async def execute_action(self, action_name: str, action_path: str) -> Dict[str, Any]:
        """Esegue un'azione configurata sul sensore"""
        # Assicura che l'URL dell'azione inizi con "/"
        if not action_path.startswith("/"):
            action_path = "/" + action_path
        
        # Costruisce l'URL completo per l'azione
        full_action_url = f"{self.base_url}{action_path}"
        print(f"Esecuzione azione '{action_name}' su sensore '{self.name}': GET {full_action_url}")
        
        try:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            async with self.session.get(full_action_url) as response:
                status_code = response.status
                self.connected = (status_code == 200)
                
                # Prova a leggere come JSON, altrimenti come testo
                try:
                    data = await response.json()
                except:
                    data = {"response": await response.text()}
                
                return {
                    "success": status_code == 200,
                    "status_code": status_code,
                    "data": data,
                    "error": None if status_code == 200 else f"HTTP {status_code}"
                }
        except Exception as e:
            self.connected = False
            error_msg = str(e)
            return {
                "success": False,
                "status_code": None,
                "data": None,
                "error": error_msg
            }

