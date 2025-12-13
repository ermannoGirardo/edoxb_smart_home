from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SensorType(str, Enum):
    """Tipi di sensori supportati"""
    HTTP = "http"
    WEBSOCKET = "websocket"


class SensorConfig(BaseModel):
    """Configurazione di un sensore dal file YAML"""
    name: str = Field(..., description="Nome univoco del sensore")
    type: Optional[SensorType] = Field(None, description="Tipo di sensore (deprecato, usare protocol). Se protocol è specificato, type è opzionale")
    ip: Optional[str] = Field(None, description="Indirizzo IP del sensore (obbligatorio per HTTP/WebSocket, opzionale per MQTT)")
    port: Optional[int] = Field(None, description="Porta del sensore")
    protocol: Optional[str] = Field(None, description="Protocollo di comunicazione (http, websocket, ecc.). Se non specificato, viene dedotto da 'type'")
    endpoint: Optional[str] = Field(None, description="Percorso URL per sensori HTTP (es: /api/temperature)")
    http_protocol: Optional[str] = Field("http", description="Protocollo HTTP (http o https) - solo per protocollo HTTP")
    path: Optional[str] = Field(None, description="Path WebSocket")
    actions: Optional[Dict[str, str]] = Field(default_factory=dict, description="Azioni disponibili per il sensore (es: {'accendi': '/color/0?turn=on'})")
    enabled: bool = Field(True, description="Se il sensore è abilitato")
    poll_interval: Optional[int] = Field(5, description="Intervallo di polling in secondi. Se None o 0, il polling è disabilitato (utile per pulsanti)")
    timeout: Optional[int] = Field(10, description="Timeout in secondi per le richieste HTTP/WebSocket", gt=0)
    template_id: Optional[str] = Field(None, description="ID del template usato per creare il sensore (es: 'shelly_rgbw2', 'custom')")
    # Campi MQTT (opzionali, definiti dal plugin del sensore)
    device_id: Optional[str] = Field(None, description="ID del dispositivo (es: per Shelly H&T: 'ABC123'). Usato per sostituire {device_id} nei topic MQTT")
    mqtt_topic_status: Optional[str] = Field(None, description="Topic MQTT per ricevere aggiornamenti di stato (es: 'shellies/shellyht-{device_id}/sensor/#'). Se non specificato, usa 'sensors/{name}/status'")
    mqtt_topic_command: Optional[str] = Field(None, description="Topic MQTT per inviare comandi (es: 'shellies/shellyht-{device_id}/command'). Se non specificato, usa 'sensors/{name}/command'")
    
    @model_validator(mode='after')
    def validate_protocol_fields(self):
        """Valida che i campi richiesti siano presenti in base al protocollo"""
        protocol = self.get_communication_protocol()
        
        # Per protocolli HTTP/WebSocket, ip è obbligatorio
        if protocol in ['http', 'websocket']:
            if not self.ip:
                raise ValueError(f"Campo 'ip' obbligatorio per protocollo {protocol}")
        
        # Per protocollo MQTT, device_id è obbligatorio
        if protocol == 'mqtt':
            if not self.device_id:
                raise ValueError("Campo 'device_id' obbligatorio per protocollo MQTT")
        
        return self
    
    def get_communication_protocol(self) -> str:
        """Restituisce il protocollo di comunicazione, deducendolo da 'type' se necessario"""
        if self.protocol:
            return self.protocol.lower()
        # Retrocompatibilità: deduci da type
        if self.type:
            if self.type == SensorType.HTTP:
                return "http"
            elif self.type == SensorType.WEBSOCKET:
                return "websocket"
        return "http"  # default


class SensorData(BaseModel):
    """Dati ricevuti da un sensore"""
    sensor_name: str = Field(..., description="Nome del sensore")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp della lettura")
    data: Dict[str, Any] = Field(..., description="Dati del sensore")
    status: str = Field("ok", description="Stato della lettura")
    error: Optional[str] = Field(None, description="Eventuale errore")


class SensorStatus(BaseModel):
    """Stato di un sensore"""
    name: str
    type: str
    ip: Optional[str] = Field(None, description="Indirizzo IP del sensore (opzionale per sensori MQTT)")
    port: Optional[int]
    connected: bool
    last_update: Optional[datetime]
    enabled: bool
    actions: Optional[Dict[str, str]] = Field(default_factory=dict, description="Azioni disponibili per il sensore")
    protocol: Optional[str] = Field(None, description="Protocollo di comunicazione utilizzato")
    template_id: Optional[str] = Field(None, description="ID del template usato per creare il sensore")


class SensorListResponse(BaseModel):
    """Risposta con lista sensori"""
    sensors: List[SensorStatus]


class SensorDataResponse(BaseModel):
    """Risposta con dati di un sensore"""
    sensor_name: str
    data: Dict[str, Any]
    timestamp: datetime
    status: str


class FrontendDataRequest(BaseModel):
    """Richiesta dati per frontend"""
    sensor_names: Optional[List[str]] = Field(None, description="Lista nomi sensori, None per tutti")
    limit: Optional[int] = Field(100, description="Numero massimo di record")


class FrontendDataResponse(BaseModel):
    """Risposta dati per frontend"""
    sensors: Dict[str, List[Dict[str, Any]]]
    timestamp: datetime = Field(default_factory=datetime.now)


class SensorFieldTemplate(BaseModel):
    """Template di un campo per la configurazione di un sensore"""
    name: str = Field(..., description="Nome del campo")
    type: str = Field(..., description="Tipo del campo (string, integer, boolean, enum, object)")
    required: bool = Field(..., description="Se il campo è obbligatorio")
    description: str = Field(..., description="Descrizione del campo")
    default: Optional[Any] = Field(None, description="Valore di default")
    example: Optional[Any] = Field(None, description="Esempio di valore")
    values: Optional[List[str]] = Field(None, description="Valori possibili per campi enum")


class SensorTemplate(BaseModel):
    """Template completo per la configurazione di un sensore"""
    common_fields: List[SensorFieldTemplate] = Field(..., description="Campi comuni a tutti i tipi")
    http_fields: List[SensorFieldTemplate] = Field(default_factory=list, description="Campi specifici per HTTP")
    websocket_fields: List[SensorFieldTemplate] = Field(default_factory=list, description="Campi specifici per WebSocket")


class SensorCreateRequest(BaseModel):
    """Richiesta per creare un nuovo sensore"""
    name: str = Field(..., description="Nome univoco del sensore")
    type: Optional[SensorType] = Field(None, description="Tipo di sensore (deprecato, usare protocol). Se protocol è specificato, type è opzionale")
    ip: Optional[str] = Field(None, description="Indirizzo IP del sensore (obbligatorio per HTTP/WebSocket, opzionale per MQTT)")
    port: Optional[int] = Field(None, description="Porta del sensore")
    protocol: Optional[str] = Field(None, description="Protocollo di comunicazione (http, websocket, mqtt, ecc.)")
    endpoint: Optional[str] = Field(None, description="Percorso URL per sensori HTTP")
    http_protocol: Optional[str] = Field("http", description="Protocollo HTTP (http o https) - solo per protocollo HTTP")
    path: Optional[str] = Field(None, description="Path WebSocket")
    actions: Optional[Dict[str, str]] = Field(default_factory=dict, description="Azioni disponibili per il sensore (es: {'accendi': '/color/0?turn=on'})")
    enabled: bool = Field(True, description="Se il sensore è abilitato")
    poll_interval: Optional[int] = Field(5, description="Intervallo di polling in secondi")
    timeout: Optional[int] = Field(10, description="Timeout in secondi", gt=0)
    template_id: Optional[str] = Field(None, description="ID del template usato per creare il sensore (es: 'shelly_rgbw2', 'custom')")
    # Campi MQTT (opzionali, definiti dal plugin del sensore)
    device_id: Optional[str] = Field(None, description="ID del dispositivo (es: per Shelly H&T: 'ABC123'). Usato per sostituire {device_id} nei topic MQTT")
    mqtt_topic_status: Optional[str] = Field(None, description="Topic MQTT per ricevere aggiornamenti di stato (es: 'shellies/shellyht-{device_id}/sensor/#'). Se non specificato, usa 'sensors/{name}/status'")
    mqtt_topic_command: Optional[str] = Field(None, description="Topic MQTT per inviare comandi (es: 'shellies/shellyht-{device_id}/command'). Se non specificato, usa 'sensors/{name}/command'")
    
    @model_validator(mode='after')
    def validate_protocol_fields(self):
        """Valida che i campi richiesti siano presenti in base al protocollo"""
        protocol = self.protocol or (self.type.value if self.type else "http")
        protocol = protocol.lower()
        
        # Per protocolli HTTP/WebSocket, ip è obbligatorio
        if protocol in ['http', 'websocket']:
            if not self.ip:
                raise ValueError(f"Campo 'ip' obbligatorio per protocollo {protocol}")
        
        # Per protocollo MQTT, device_id è obbligatorio
        if protocol == 'mqtt':
            if not self.device_id:
                raise ValueError("Campo 'device_id' obbligatorio per protocollo MQTT")
        
        return self


class SensorUpdateRequest(BaseModel):
    """Richiesta per aggiornare un sensore esistente"""
    ip: Optional[str] = Field(None, description="Indirizzo IP del sensore")
    port: Optional[int] = Field(None, description="Porta del sensore")
    protocol: Optional[str] = Field(None, description="Protocollo di comunicazione (http, websocket, mqtt, ecc.)")
    endpoint: Optional[str] = Field(None, description="Percorso URL per sensori HTTP")
    http_protocol: Optional[str] = Field(None, description="Protocollo HTTP (http o https) - solo per protocollo HTTP")
    path: Optional[str] = Field(None, description="Path WebSocket")
    actions: Optional[Dict[str, str]] = Field(None, description="Azioni disponibili per il sensore (es: {'accendi': '/color/0?turn=on'})")
    enabled: Optional[bool] = Field(None, description="Se il sensore è abilitato")
    poll_interval: Optional[int] = Field(None, description="Intervallo di polling in secondi")
    timeout: Optional[int] = Field(None, description="Timeout in secondi", gt=0)
    # Campi MQTT (opzionali, definiti dal plugin del sensore)
    mqtt_topic_status: Optional[str] = Field(None, description="Topic MQTT per ricevere aggiornamenti di stato (es: 'shellies/shelly_rgbw2_XXXXXX/status'). Se non specificato, usa 'sensors/{name}/status'")
    mqtt_topic_command: Optional[str] = Field(None, description="Topic MQTT per inviare comandi (es: 'shellies/shelly_rgbw2_XXXXXX/command'). Se non specificato, usa 'sensors/{name}/command'")


class SensorActionResponse(BaseModel):
    """Risposta all'esecuzione di un'azione su un sensore"""
    sensor_name: str = Field(..., description="Nome del sensore")
    action_name: str = Field(..., description="Nome dell'azione eseguita")
    success: bool = Field(..., description="Se l'azione è stata eseguita con successo")
    status_code: Optional[int] = Field(None, description="Codice di stato HTTP della risposta")
    data: Optional[Dict[str, Any]] = Field(None, description="Dati della risposta")
    error: Optional[str] = Field(None, description="Eventuale errore")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp dell'esecuzione")
