import asyncio
import websockets
from typing import Dict, Any, Optional
from datetime import datetime
from app.sensors.sensor_base import SensorBase
from app.models import SensorConfig, SensorData


class WebSocketSensor(SensorBase):
    """Adapter per sensori WebSocket"""
    
    def __init__(self, config: SensorConfig):
        super().__init__(config)
        self.path = config.path or "/"
        self.timeout = config.timeout or 10
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.uri = f"ws://{config.ip}"
        if config.port:
            self.uri += f":{config.port}"
        self.uri += self.path
        self._receive_task: Optional[asyncio.Task] = None
        self._last_data: Optional[Dict[str, Any]] = None
    
    async def connect(self) -> bool:
        """Connette al sensore WebSocket"""
        try:
            if self.websocket is None or self.websocket.closed:
                self.websocket = await websockets.connect(
                    self.uri,
                    ping_interval=20,
                    ping_timeout=10
                )
                self.connected = True
                
                # Avvia task per ricevere messaggi
                if self._receive_task is None or self._receive_task.done():
                    self._receive_task = asyncio.create_task(self._receive_loop())
                
                return True
        except Exception as e:
            print(f"Errore connessione sensore WebSocket {self.name}: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnette dal sensore WebSocket"""
        if self._receive_task and not self._receive_task.done():
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        
        if self.websocket and not self.websocket.closed:
            await self.websocket.close()
        
        self.websocket = None
        self.connected = False
    
    async def _receive_loop(self) -> None:
        """Loop per ricevere messaggi dal WebSocket"""
        try:
            while self.connected and self.websocket and not self.websocket.closed:
                try:
                    message = await asyncio.wait_for(
                        self.websocket.recv(),
                        timeout=self.timeout
                    )
                    # Parse del messaggio (assumiamo JSON)
                    import json
                    self._last_data = json.loads(message)
                    self.update_last_update()
                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    self.connected = False
                    break
                except Exception as e:
                    print(f"Errore ricezione messaggio WebSocket {self.name}: {e}")
                    continue
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Errore nel loop di ricezione WebSocket {self.name}: {e}")
            self.connected = False
    
    async def read_data(self) -> SensorData:
        """Legge i dati dal sensore WebSocket"""
        try:
            if not self.connected:
                await self.connect()
            
            if self._last_data is not None:
                data = self._last_data
                self._last_data = None  # Reset dopo lettura
                return SensorData(
                    sensor_name=self.name,
                    timestamp=datetime.now(),
                    data=data,
                    status="ok"
                )
            else:
                # Nessun dato disponibile
                return SensorData(
                    sensor_name=self.name,
                    timestamp=datetime.now(),
                    data={},
                    status="ok",
                    error="Nessun dato disponibile"
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
        return self.connected and self.websocket is not None and not self.websocket.closed

