from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.services.business_logic import BusinessLogic
from app.models import SensorStatus, SensorDataResponse, SensorCreateRequest, SensorUpdateRequest, SensorActionResponse
from app.dependencies import get_business_logic


router = APIRouter(prefix="/sensors", tags=["sensors"])


@router.get("/", response_model=List[SensorStatus])
async def list_sensors(
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Restituisce la lista di tutti i sensori con il loro stato"""
    return await business_logic.get_sensor_status()


@router.get("/{sensor_name}", response_model=SensorStatus)
async def get_sensor_status(
    sensor_name: str,
    business_logic: BusinessLogic = Depends(get_business_logic)
):
    """Restituisce lo stato di un sensore specifico"""
    status_list = await business_logic.get_sensor_status(sensor_name)
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
        raise HTTPException(
            status_code=404,
            detail=f"Sensore '{sensor_name}' non trovato o disabilitato"
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
    
    # Verifica se il sensore esiste già
    if request.name in business_logic.sensors:
        raise HTTPException(
            status_code=400,
            detail=f"Sensore '{request.name}' già esistente"
        )
    
    # Crea la configurazione
    sensor_config = SensorConfig(**request.model_dump())
    
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
    if sensor_name not in business_logic.sensors:
        raise HTTPException(status_code=404, detail=f"Sensore '{sensor_name}' non trovato")
    
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

