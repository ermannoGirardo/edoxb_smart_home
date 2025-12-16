from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from app.services.business_logic import BusinessLogic
from app.models import SensorStatus, SensorDataResponse, SensorCreateRequest, SensorUpdateRequest, SensorActionResponse
from app.dependencies import get_business_logic


router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.get("/", response_model=List[SensorStatus])
async def list_sensors(
    check_connection: bool = Query(False, description="Se True, verifica le connessioni dei sensori"),
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """
    Restituisce la lista di tutti i sensori con il loro stato.
    
    - check_connection=False (default): Restituisce subito lo stato cached (veloce, non bloccante)
    - check_connection=True: Verifica la connessione di tutti i sensori (più lento ma aggiornato)
    """
    print(f"GET /sensors/ - check_connection={check_connection}")
    return await business_logic.get_sensor_status(check_connection=check_connection)


@router.get("/{sensor_name}", response_model=SensorStatus)
async def get_sensor_status(
    sensor_name: str,
    check_connection: bool = Query(False, description="Se True, verifica la connessione del sensore"),
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """
    Restituisce lo stato di un sensore specifico.
    
    - check_connection=False (default): Restituisce subito lo stato cached (veloce)
    - check_connection=True: Verifica la connessione (più lento ma aggiornato)
    """
    print(f"GET /sensors/{sensor_name} - check_connection={check_connection}")
    status_list = await business_logic.get_sensor_status(sensor_name, check_connection=check_connection)
    if not status_list:
        raise HTTPException(status_code=404, detail=f"Sensore '{sensor_name}' non trovato")
    return status_list[0]


@router.get("/{sensor_name}/data", response_model=SensorDataResponse)
async def read_sensor_data(
    sensor_name: str,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Legge i dati da un sensore specifico"""
    sensor_data = await business_logic.read_sensor_data(sensor_name)
    
    if sensor_data is None:
        # Verifica se il sensore esiste almeno (anche se disabilitato o senza dati)
        status_list = await business_logic.get_sensor_status(sensor_name, check_connection=False)
        
        # Se il sensore non è in memoria, prova a caricarlo dal database
        if not status_list:
            # Prova a caricare il sensore dal database se esiste
            try:
                from app.models import SensorConfig
                # Accedi a mongo_client tramite business_logic
                if hasattr(business_logic, '_management_service') and hasattr(business_logic._management_service, 'mongo_client'):
                    mongo_client = business_logic._management_service.mongo_client
                    if mongo_client is not None and mongo_client.db is not None:
                        # Prova a caricare la configurazione dal database
                        config_dict = await mongo_client.db.sensor_configs.find_one({"name": sensor_name})
                        if config_dict:
                            # Rimuovi _id per creare SensorConfig
                            config_dict.pop("_id", None)
                            sensor_config = SensorConfig(**config_dict)
                            
                            # Aggiungi il sensore alla business logic
                            success = await business_logic.add_sensor(sensor_config)
                            if success:
                                # Riprova a leggere i dati
                                sensor_data = await business_logic.read_sensor_data(sensor_name)
                                if sensor_data is not None:
                                    return SensorDataResponse(
                                        sensor_name=sensor_data.sensor_name,
                                        data=sensor_data.data,
                                        timestamp=sensor_data.timestamp,
                                        status=sensor_data.status
                                    )
                                # Se il sensore è stato caricato ma non ha dati, aggiorna status_list
                                status_list = await business_logic.get_sensor_status(sensor_name, check_connection=False)
            except Exception as e:
                print(f"Errore caricamento sensore {sensor_name} dal database: {e}")
        
        # Se ancora non esiste, restituisci 404
        if not status_list:
            raise HTTPException(
                status_code=404,
                detail=f"Sensore '{sensor_name}' non trovato"
            )
        
        # Se il sensore esiste ma non ha dati (es. MQTT senza messaggi ancora),
        # restituisci una risposta vuota invece di 404
        from app.models import SensorData
        from datetime import datetime
        sensor_data = SensorData(
            sensor_name=sensor_name,
            timestamp=datetime.now(),
            data={},
            status="ok",
            error="Nessun dato disponibile ancora"
        )
    
    return SensorDataResponse(
        sensor_name=sensor_data.sensor_name,
        data=sensor_data.data,
        timestamp=sensor_data.timestamp,
        status=sensor_data.status
    )


@router.post("/{sensor_name}/enable")
async def enable_sensor(
    sensor_name: str,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Abilita un sensore"""
    success = business_logic.enable_sensor(sensor_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Sensore '{sensor_name}' non trovato")
    return {"message": f"Sensore '{sensor_name}' abilitato", "sensor_name": sensor_name}


@router.post("/{sensor_name}/disable")
async def disable_sensor(
    sensor_name: str,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Disabilita un sensore"""
    success = business_logic.disable_sensor(sensor_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Sensore '{sensor_name}' non trovato")
    return {"message": f"Sensore '{sensor_name}' disabilitato", "sensor_name": sensor_name}


@router.post("/{sensor_name}/connect")
async def connect_sensor(
    sensor_name: str,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Connette manualmente un sensore"""
    if sensor_name not in business_logic.sensors:
        raise HTTPException(status_code=404, detail=f"Sensore '{sensor_name}' non trovato")
    
    sensor = business_logic.sensors[sensor_name]
    connected = await sensor.connect()
    
    if connected:
        return {"message": f"Sensore '{sensor_name}' connesso", "connected": True}
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Impossibile connettere il sensore '{sensor_name}'"
        )


@router.post("/{sensor_name}/disconnect")
async def disconnect_sensor(
    sensor_name: str,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Disconnette manualmente un sensore"""
    if sensor_name not in business_logic.sensors:
        raise HTTPException(status_code=404, detail=f"Sensore '{sensor_name}' non trovato")
    
    sensor = business_logic.sensors[sensor_name]
    await sensor.disconnect()
    
    return {"message": f"Sensore '{sensor_name}' disconnesso", "connected": False}


@router.post("/", status_code=201)
async def create_sensor(
    request: SensorCreateRequest,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Crea un nuovo sensore"""
    from app.models import SensorConfig
    from app.api.routes.frontend import _get_sensor_templates
    import os
    
    # Verifica se il sensore esiste già
    if request.name in business_logic.sensors:
        raise HTTPException(
            status_code=400,
            detail=f"Sensore '{request.name}' già esistente"
        )
    
    # Prepara i dati della richiesta
    request_data = request.model_dump()
    
    # Se è specificato un template_id, applica i default_config dal template
    if request.template_id and request.template_id != "custom":
        try:
            templates = _get_sensor_templates()
            template = next((t for t in templates if t["id"] == request.template_id), None)
            
            if template and "default_config" in template:
                default_config = template["default_config"].copy()
                print(f"Applicazione default_config dal template {request.template_id}: {default_config}")
                
                # Rimuovi 'type' se il protocollo è MQTT (type enum non supporta MQTT, si usa solo protocol)
                if default_config.get("protocol") == "mqtt" and "type" in default_config:
                    default_config.pop("type")
                    print(f"  - Rimosso 'type' per protocollo MQTT (usare solo 'protocol')")
                
                # Applica i valori di default solo se non sono già specificati nella richiesta
                for key, value in default_config.items():
                    if key not in request_data or request_data[key] is None:
                        request_data[key] = value
                        print(f"  - Applicato {key} = {value}")
        except Exception as e:
            print(f"⚠ Errore nell'applicazione default_config dal template: {e}")
    
    # Crea la configurazione
    sensor_config = SensorConfig(**request_data)
    
    # Aggiungi il sensore
    success = await business_logic.add_sensor(sensor_config)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nella creazione del sensore '{request.name}'"
        )
    
    return {
        "message": f"Sensore '{request.name}' creato con successo",
        "sensor_name": request.name
    }


@router.put("/{sensor_name}")
async def update_sensor(
    sensor_name: str,
    request: SensorUpdateRequest,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Aggiorna un sensore esistente"""
    if sensor_name not in business_logic.sensors:
        raise HTTPException(status_code=404, detail=f"Sensore '{sensor_name}' non trovato")
    
    # Prepara gli aggiornamenti (rimuovi None)
    updates = request.model_dump(exclude_unset=True, exclude_none=True)
    
    if not updates:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")
    
    # Aggiorna il sensore
    success = await business_logic.update_sensor(sensor_name, updates)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nell'aggiornamento del sensore '{sensor_name}'"
        )
    
    return {
        "message": f"Sensore '{sensor_name}' aggiornato con successo",
        "sensor_name": sensor_name
    }


@router.delete("/{sensor_name}")
async def delete_sensor(
    sensor_name: str,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Elimina un sensore"""
    # FastAPI decodifica automaticamente l'URL, ma verifichiamo comunque
    # Il nome potrebbe avere spazi o caratteri speciali
    print(f"Tentativo eliminazione sensore: '{sensor_name}'")
    print(f"Sensori disponibili: {list(business_logic.sensors.keys())}")
    
    if sensor_name not in business_logic.sensors:
        # Prova a cercare case-insensitive o con spazi normalizzati
        sensor_name_lower = sensor_name.lower().strip()
        matching_sensor = None
        for key in business_logic.sensors.keys():
            if key.lower().strip() == sensor_name_lower:
                matching_sensor = key
                break
        
        if matching_sensor:
            sensor_name = matching_sensor
            print(f"Trovato sensore con nome normalizzato: '{sensor_name}'")
        else:
            raise HTTPException(status_code=404, detail=f"Sensore '{sensor_name}' non trovato. Sensori disponibili: {list(business_logic.sensors.keys())}")
    
    success = await business_logic.remove_sensor(sensor_name)
    if not success:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nell'eliminazione del sensore '{sensor_name}'"
        )
    
    return {
        "message": f"Sensore '{sensor_name}' eliminato con successo",
        "sensor_name": sensor_name
    }


@router.post("/{sensor_name}/actions/{action_name}", response_model=SensorActionResponse)
async def execute_sensor_action(
    sensor_name: str,
    action_name: str,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Esegue un'azione su un sensore"""
    try:
        result = await business_logic.execute_sensor_action(sensor_name, action_name)
        if not result.success:
            # Se l'azione non è riuscita, restituisci comunque la risposta ma con status code appropriato
            if result.error and "non trovata" in result.error.lower():
                raise HTTPException(status_code=404, detail=result.error)
            else:
                raise HTTPException(status_code=500, detail=result.error or "Errore nell'esecuzione dell'azione")
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nell'esecuzione dell'azione: {str(e)}")

