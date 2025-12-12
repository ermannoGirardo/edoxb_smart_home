from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum


class SensorType(str, Enum):
    """Tipi di sensori supportati"""
    HTTP = "http"
    WEBSOCKET = "websocket"
    CUSTOM = "custom"


class SensorConfig(BaseModel):
    """Configurazione di un sensore dal file YAML"""
    name: str = Field(..., description="Nome univoco del sensore")
    type: SensorType = Field(..., description="Tipo di sensore")
    ip: str = Field(..., description="Indirizzo IP del sensore")
    port: Optional[int] = Field(None, description="Porta del sensore")
    endpoint: Optional[str] = Field(None, description="Percorso URL per sensori HTTP (es: /api/temperature)")
    protocol: Optional[str] = Field("http", description="Protocollo per sensori HTTP (http o https)")
    path: Optional[str] = Field(None, description="Path WebSocket")
    custom_class: Optional[str] = Field(None, description="Classe personalizzata per sensori custom")
    custom_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parametri personalizzati")
    actions: Optional[Dict[str, str]] = Field(default_factory=dict, description="Azioni disponibili per il sensore (es: {'accendi': '/color/0?turn=on'})")
    enabled: bool = Field(True, description="Se il sensore è abilitato")
    poll_interval: Optional[int] = Field(5, description="Intervallo di polling in secondi")
    timeout: Optional[int] = Field(10, description="Timeout in secondi per le richieste HTTP/WebSocket", gt=0)


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
    ip: str
    port: Optional[int]
    connected: bool
    last_update: Optional[datetime]
    enabled: bool
    actions: Optional[Dict[str, str]] = Field(default_factory=dict, description="Azioni disponibili per il sensore")


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
    custom_fields: List[SensorFieldTemplate] = Field(default_factory=list, description="Campi specifici per custom")


class SensorCreateRequest(BaseModel):
    """Richiesta per creare un nuovo sensore"""
    name: str = Field(..., description="Nome univoco del sensore")
    type: SensorType = Field(..., description="Tipo di sensore")
    ip: str = Field(..., description="Indirizzo IP del sensore")
    port: Optional[int] = Field(None, description="Porta del sensore")
    endpoint: Optional[str] = Field(None, description="Percorso URL per sensori HTTP")
    protocol: Optional[str] = Field("http", description="Protocollo per sensori HTTP")
    path: Optional[str] = Field(None, description="Path WebSocket")
    custom_class: Optional[str] = Field(None, description="Classe personalizzata per sensori custom")
    custom_params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parametri personalizzati")
    actions: Optional[Dict[str, str]] = Field(default_factory=dict, description="Azioni disponibili per il sensore (es: {'accendi': '/color/0?turn=on'})")
    enabled: bool = Field(True, description="Se il sensore è abilitato")
    poll_interval: Optional[int] = Field(5, description="Intervallo di polling in secondi")
    timeout: Optional[int] = Field(10, description="Timeout in secondi", gt=0)


class SensorUpdateRequest(BaseModel):
    """Richiesta per aggiornare un sensore esistente"""
    ip: Optional[str] = Field(None, description="Indirizzo IP del sensore")
    port: Optional[int] = Field(None, description="Porta del sensore")
    endpoint: Optional[str] = Field(None, description="Percorso URL per sensori HTTP")
    protocol: Optional[str] = Field(None, description="Protocollo per sensori HTTP")
    path: Optional[str] = Field(None, description="Path WebSocket")
    custom_class: Optional[str] = Field(None, description="Classe personalizzata per sensori custom")
    custom_params: Optional[Dict[str, Any]] = Field(None, description="Parametri personalizzati")
    actions: Optional[Dict[str, str]] = Field(None, description="Azioni disponibili per il sensore (es: {'accendi': '/color/0?turn=on'})")
    enabled: Optional[bool] = Field(None, description="Se il sensore è abilitato")
    poll_interval: Optional[int] = Field(None, description="Intervallo di polling in secondi")
    timeout: Optional[int] = Field(None, description="Timeout in secondi", gt=0)


class SensorActionResponse(BaseModel):
    """Risposta all'esecuzione di un'azione su un sensore"""
    sensor_name: str = Field(..., description="Nome del sensore")
    action_name: str = Field(..., description="Nome dell'azione eseguita")
    success: bool = Field(..., description="Se l'azione è stata eseguita con successo")
    status_code: Optional[int] = Field(None, description="Codice di stato HTTP della risposta")
    data: Optional[Dict[str, Any]] = Field(None, description="Dati della risposta")
    error: Optional[str] = Field(None, description="Eventuale errore")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp dell'esecuzione")
