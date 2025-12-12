import aiohttp
from typing import Dict, Any
from datetime import datetime
from app.sensors.sensor_base import SensorBase
from app.models import SensorConfig, SensorData


class HTTPSensor(SensorBase):
    """Adapter per sensori HTTP"""
    
    def __init__(self, config: SensorConfig):
        super().__init__(config)
        # Percorso URL dal file di configurazione (default "/" se non specificato)
        self.endpoint = config.endpoint if config.endpoint is not None else "/"
        # Protocollo dal file di configurazione (default "http" se non specificato)
        protocol = config.protocol if config.protocol is not None else "http"
        if protocol not in ["http", "https"]:
            raise ValueError(f"Protocollo non valido per sensore {self.name}: {protocol}. Usare 'http' o 'https'")
        
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
        
        # Memorizza le azioni disponibili
        self.actions = config.actions if config.actions else {}
        
        print(f"Sensore HTTP '{self.name}' configurato: URL={self.url}, timeout={timeout_seconds}s, azioni={list(self.actions.keys())}")
    
    async def connect(self) -> bool:
        """Connette al sensore HTTP"""
        try:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession(timeout=self.timeout)
            
            # Test di connessione
            async with self.session.get(self.url) as response:
                if response.status == 200:
                    self.connected = True
                    return True
                else:
                    self.connected = False
                    return False
        except Exception as e:
            print(f"Errore connessione sensore HTTP {self.name}: {e}")
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
        """Verifica se il sensore è connesso"""
        try:
            if self.session is None or self.session.closed:
                return False
            
            async with self.session.get(self.url) as response:
                self.connected = (response.status == 200)
                return self.connected
        except:
            self.connected = False
            return False
    
    async def execute_action(self, action_name: str) -> Dict[str, Any]:
        """Esegue un'azione configurata sul sensore"""
        if action_name not in self.actions:
            raise ValueError(f"Azione '{action_name}' non trovata. Azioni disponibili: {list(self.actions.keys())}")
        
        action_url = self.actions[action_name]
        # Assicura che l'URL dell'azione inizi con "/"
        if not action_url.startswith("/"):
            action_url = "/" + action_url
        
        # Costruisce l'URL completo per l'azione
        full_action_url = f"{self.base_url}{action_url}"
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

