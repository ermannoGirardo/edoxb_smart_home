import asyncio
import websockets
import json
from typing import Dict, Any, Optional, Set, TYPE_CHECKING
from datetime import datetime
from app.protocols.protocol_base import ProtocolBase
from app.models import SensorConfig, SensorData

if TYPE_CHECKING:
    from app.services.port_manager import PortManager


class WebSocketProtocol(ProtocolBase):
    """Protocollo WebSocket per la comunicazione con i sensori"""
    
    # PortManager condiviso (inizializzato dal SensorManagementService)
    _port_manager: Optional['PortManager'] = None
    
    @classmethod
    def set_port_manager(cls, port_manager: 'PortManager') -> None:
        """Imposta il PortManager condiviso per tutti i protocolli WebSocket"""
        cls._port_manager = port_manager
    
    def __init__(self, config: SensorConfig):
        super().__init__(config)
        self.path = config.path or "/"
        self.timeout = config.timeout or 10
        self.host = "0.0.0.0"  # Ascolta su tutte le interfacce
        self._server: Optional[websockets.WebSocketServer] = None
        self._server_task: Optional[asyncio.Task] = None
        self._connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self._last_data: Optional[Dict[str, Any]] = None
        self._last_client_connection: Optional[datetime] = None
        
        # La porta verrà assegnata durante connect() se non specificata
        self._requested_port = config.port
        self.port: Optional[int] = None
    
    async def connect(self) -> bool:
        """Avvia il server WebSocket per questo sensore"""
        try:
            if self._server_task is None or self._server_task.done():
                # Assegna la porta se non già assegnata
                if self.port is None:
                    self.port = await self._assign_port()
                    # Aggiorna la configurazione con la porta assegnata
                    self.config.port = self.port
                
                # Avvia il server WebSocket
                self._server_task = asyncio.create_task(self._start_server())
                # Attendi un momento per permettere al server di avviarsi
                await asyncio.sleep(0.1)
                self.connected = True
                print(f"Server WebSocket avviato per sensore {self.name} su porta {self.port}")
                return True
            return self.connected
        except Exception as e:
            print(f"Errore avvio server WebSocket per sensore {self.name}: {e}")
            self.connected = False
            # Rilascia la porta in caso di errore
            await self._release_port()
            return False
    
    async def _assign_port(self) -> int:
        """Assegna una porta per questo sensore usando il PortManager"""
        if self._port_manager is None:
            # Fallback: usa la porta richiesta o una porta di default
            if self._requested_port is not None:
                return self._requested_port
            raise RuntimeError(
                f"PortManager non inizializzato per sensore {self.name}. "
                f"Impossibile assegnare porta automaticamente."
            )
        
        try:
            # Usa il PortManager per assegnare la porta
            assigned_port = self._port_manager.assign_port(
                sensor_name=self.name,
                requested_port=self._requested_port
            )
            return assigned_port
        except ValueError as e:
            raise RuntimeError(f"Impossibile assegnare porta per sensore {self.name}: {e}")
    
    async def _release_port(self) -> None:
        """Rilascia la porta assegnata a questo sensore"""
        if self._port_manager is not None and self.port is not None:
            self._port_manager.release_port(self.name)
            self.port = None
    
    async def disconnect(self) -> None:
        """Ferma il server WebSocket"""
        self.connected = False
        
        # Chiudi tutte le connessioni client
        if self._connected_clients:
            await asyncio.gather(
                *[client.close() for client in list(self._connected_clients)],
                return_exceptions=True
            )
            self._connected_clients.clear()
        
        # Ferma il server
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        
        # Cancella il task del server
        if self._server_task and not self._server_task.done():
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                pass
        
        self._server_task = None
        
        # Rilascia la porta
        await self._release_port()
        
        print(f"Server WebSocket fermato per sensore {self.name}")
    
    async def _start_server(self) -> None:
        """Avvia il server WebSocket e gestisce le connessioni"""
        if self.port is None:
            raise RuntimeError(f"Porta non assegnata per sensore {self.name}")
        
        try:
            async with websockets.serve(
                self._handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10
            ) as server:
                self._server = server
                await asyncio.Future()  # Mantiene il server in esecuzione
        except asyncio.CancelledError:
            pass
        except OSError as e:
            # Errore di porta già in uso o non disponibile
            print(f"Errore porta {self.port} per sensore {self.name}: {e}")
            self.connected = False
            # Rilascia la porta
            await self._release_port()
            raise
        except Exception as e:
            print(f"Errore nel server WebSocket per sensore {self.name}: {e}")
            self.connected = False
            # Rilascia la porta in caso di errore
            await self._release_port()
            raise
    
    async def _handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str) -> None:
        """Gestisce una connessione client"""
        # Verifica che il path corrisponda
        if path != self.path:
            await websocket.close(code=4004, reason="Path non corrispondente")
            return
        
        client_address = websocket.remote_address
        print(f"Client connesso al sensore {self.name} da {client_address}")
        self._connected_clients.add(websocket)
        self._last_client_connection = datetime.now()
        self.update_last_update()
        
        try:
            async for message in websocket:
                try:
                    # Parse del messaggio (assumiamo JSON)
                    data = json.loads(message)
                    self._last_data = data
                    self.update_last_update()
                    print(f"Dati ricevuti dal sensore {self.name}: {data}")
                    
                    # Notifica AutomationService se presente
                    sensor_data = SensorData(
                        sensor_name=self.name,
                        timestamp=datetime.now(),
                        data=data,
                        status="ok"
                    )
                    if hasattr(self, '_automation_service') and self._automation_service:
                        try:
                            await self._automation_service.on_sensor_data(self.name, sensor_data)
                        except Exception as e:
                            print(f"Errore automazione WebSocket per {self.name}: {e}")
                except json.JSONDecodeError as e:
                    print(f"Errore parsing JSON dal sensore {self.name}: {e}")
                except Exception as e:
                    print(f"Errore gestione messaggio dal sensore {self.name}: {e}")
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnesso dal sensore {self.name} ({client_address})")
        except Exception as e:
            print(f"Errore nella connessione client per sensore {self.name}: {e}")
        finally:
            self._connected_clients.discard(websocket)
            if not self._connected_clients:
                self.connected = False
    
    async def read_data(self) -> SensorData:
        """Legge i dati ricevuti dal sensore WebSocket"""
        try:
            if self._last_data is not None:
                data = self._last_data
                # Non resettiamo _last_data per mantenere l'ultimo valore disponibile
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
                    error="Nessun dato ricevuto dal sensore"
                )
        except Exception as e:
            error_msg = str(e)
            return SensorData(
                sensor_name=self.name,
                timestamp=datetime.now(),
                data={},
                status="error",
                error=error_msg
            )
    
    async def is_connected(self) -> bool:
        """Verifica se il server è in esecuzione e se ci sono client connessi"""
        return (
            self.connected 
            and self._server_task is not None 
            and not self._server_task.done()
            and len(self._connected_clients) > 0
        )
    
    async def execute_action(self, action_name: str, action_path: str) -> Dict[str, Any]:
        """Esegue un'azione configurata sul sensore WebSocket"""
        # Per WebSocket, le azioni potrebbero essere inviate come messaggi ai client connessi
        # Per ora, restituiamo un errore poiché WebSocket è principalmente per ricezione dati
        return {
            "success": False,
            "status_code": None,
            "data": None,
            "error": f"Azioni non supportate per protocollo WebSocket. Usare HTTP per azioni."
        }


