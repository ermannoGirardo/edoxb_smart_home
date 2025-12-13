import socket
import os
from typing import Set, Optional, Tuple
from app.sensors.sensor_base import SensorBase


class PortManager:
    """Gestisce l'assegnazione automatica delle porte per i sensori WebSocket"""
    
    # Range di porte predefinito (configurabile via variabile d'ambiente)
    _default_port_range: Tuple[int, int] = (9000, 9999)
    
    def __init__(self):
        """Inizializza il PortManager con il range di porte configurabile"""
        # Leggi il range dalle variabili d'ambiente
        port_min = int(os.getenv("WEBSOCKET_PORT_MIN", str(self._default_port_range[0])))
        port_max = int(os.getenv("WEBSOCKET_PORT_MAX", str(self._default_port_range[1])))
        
        # Valida il range
        if port_min < 1024 or port_max > 65535:
            raise ValueError(f"Range porte non valido: {port_min}-{port_max}. Deve essere tra 1024 e 65535")
        if port_min >= port_max:
            raise ValueError(f"Range porte non valido: {port_min} deve essere minore di {port_max}")
        
        self.port_min = port_min
        self.port_max = port_max
        self._used_ports: Set[int] = set()
        self._sensor_ports: dict[str, int] = {}  # Mappa nome sensore -> porta
    
    def get_port_range(self) -> Tuple[int, int]:
        """Restituisce il range di porte configurato"""
        return (self.port_min, self.port_max)
    
    def is_port_available(self, port: int) -> bool:
        """Verifica se una porta è disponibile (non in uso e non occupata dal sistema)"""
        # Verifica se è già assegnata internamente
        if port in self._used_ports:
            return False
        
        # Verifica se la porta è effettivamente libera nel sistema
        return self._check_port_free(port)
    
    def _check_port_free(self, port: int) -> bool:
        """Verifica se una porta è libera nel sistema operativo"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('0.0.0.0', port))
                return True
        except OSError:
            return False
    
    def assign_port(self, sensor_name: str, requested_port: Optional[int] = None) -> int:
        """
        Assegna una porta per un sensore.
        
        Args:
            sensor_name: Nome del sensore
            requested_port: Porta richiesta (opzionale). Se None, assegna automaticamente
        
        Returns:
            Porta assegnata
        
        Raises:
            ValueError: Se la porta richiesta non è disponibile o se non ci sono porte libere
        """
        # Se il sensore ha già una porta assegnata, rilasciala prima
        if sensor_name in self._sensor_ports:
            self.release_port(sensor_name)
        
        # Se è stata richiesta una porta specifica
        if requested_port is not None:
            if not self.is_port_available(requested_port):
                raise ValueError(
                    f"Porta {requested_port} non disponibile per sensore {sensor_name}. "
                    f"Porta già in uso o occupata dal sistema."
                )
            self._used_ports.add(requested_port)
            self._sensor_ports[sensor_name] = requested_port
            return requested_port
        
        # Auto-assegnazione: trova la prima porta libera nel range
        for port in range(self.port_min, self.port_max + 1):
            if self.is_port_available(port):
                self._used_ports.add(port)
                self._sensor_ports[sensor_name] = port
                return port
        
        # Nessuna porta disponibile
        raise ValueError(
            f"Nessuna porta disponibile nel range {self.port_min}-{self.port_max} "
            f"per sensore {sensor_name}"
        )
    
    def release_port(self, sensor_name: str) -> None:
        """Rilascia la porta assegnata a un sensore"""
        if sensor_name in self._sensor_ports:
            port = self._sensor_ports[sensor_name]
            self._used_ports.discard(port)
            del self._sensor_ports[sensor_name]
    
    def get_sensor_port(self, sensor_name: str) -> Optional[int]:
        """Restituisce la porta assegnata a un sensore"""
        return self._sensor_ports.get(sensor_name)
    
    def validate_all_ports(self, sensors: dict[str, SensorBase]) -> dict[str, bool]:
        """
        Valida tutte le porte dei sensori WebSocket.
        
        Args:
            sensors: Dizionario di tutti i sensori
        
        Returns:
            Dizionario con nome sensore -> True se porta valida, False altrimenti
        """
        from app.protocols.websocket_protocol import WebSocketProtocol
        
        results = {}
        for name, sensor in sensors.items():
            # Verifica se il sensore usa un protocollo WebSocket
            if hasattr(sensor, 'protocol') and sensor.protocol:
                if isinstance(sensor.protocol, WebSocketProtocol):
                    port = sensor.protocol.port if hasattr(sensor.protocol, 'port') else sensor.port
                    if port is None:
                        results[name] = False
                    else:
                        results[name] = self.is_port_available(port)
                else:
                    results[name] = True  # Non è un protocollo websocket, skip
            else:
                results[name] = True  # Non ha protocollo, skip
        
        return results
    
    def get_used_ports(self) -> Set[int]:
        """Restituisce l'insieme delle porte in uso"""
        return self._used_ports.copy()
    
    def get_sensor_ports_mapping(self) -> dict[str, int]:
        """Restituisce la mappa nome sensore -> porta"""
        return self._sensor_ports.copy()

