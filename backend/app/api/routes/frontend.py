from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any
from app.db.mongo_client import MongoClientWrapper
from app.models import FrontendDataRequest, FrontendDataResponse, SensorTemplate
from app.dependencies import get_mongo_client


router = APIRouter(prefix="/frontend", tags=["frontend"])


@router.post("/data", response_model=FrontendDataResponse)
async def get_frontend_data(
    request: FrontendDataRequest,
    mongo_client: MongoClientWrapper = Depends(get_mongo_client)
):
    """Restituisce i dati dei sensori per il frontend"""
    try:
        sensors_data: Dict[str, List[Dict[str, Any]]] = {}
        
        if request.sensor_names:
            # Dati per sensori specifici
            for sensor_name in request.sensor_names:
                data = mongo_client.get_sensor_data(
                    sensor_name=sensor_name,
                    limit=request.limit or 100
                )
                sensors_data[sensor_name] = data
        else:
            # Dati per tutti i sensori
            all_sensors = mongo_client.get_sensors_list()
            for sensor_name in all_sensors:
                data = mongo_client.get_sensor_data(
                    sensor_name=sensor_name,
                    limit=request.limit or 100
                )
                sensors_data[sensor_name] = data
        
        return FrontendDataResponse(sensors=sensors_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero dati: {str(e)}")


@router.get("/sensors")
async def get_available_sensors(
    mongo_client: MongoClientWrapper = Depends(get_mongo_client)
):
    """Restituisce la lista di tutti i sensori che hanno inviato dati"""
    try:
        sensors = mongo_client.get_sensors_list()
        return {"sensors": sensors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero lista sensori: {str(e)}")


@router.get("/sensors/{sensor_name}/latest")
async def get_latest_sensor_data(
    sensor_name: str,
    mongo_client: MongoClientWrapper = Depends(get_mongo_client)
):
    """Restituisce l'ultimo dato disponibile per un sensore"""
    try:
        data = mongo_client.get_latest_sensor_data(sensor_name=sensor_name)
        if data is None:
            raise HTTPException(
                status_code=404,
                detail=f"Nessun dato disponibile per il sensore '{sensor_name}'"
            )
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero dati: {str(e)}"
        )


@router.get("/sensor-template", response_model=SensorTemplate)
async def get_sensor_template(
    mongo_client: MongoClientWrapper = Depends(get_mongo_client)
):
    """Restituisce il template dei campi disponibili per configurare un sensore"""
    try:
        template = mongo_client.get_sensor_template()
        if template is None:
            raise HTTPException(
                status_code=404,
                detail="Template sensori non trovato nel database"
            )
        return template
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nel recupero template: {str(e)}"
        )

