from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any
from pathlib import Path
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
                data = await mongo_client.get_sensor_data(
                    sensor_name=sensor_name,
                    limit=request.limit or 100
                )
                sensors_data[sensor_name] = data
        else:
            # Dati per tutti i sensori
            all_sensors = await mongo_client.get_sensors_list()
            for sensor_name in all_sensors:
                data = await mongo_client.get_sensor_data(
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
        sensors = await mongo_client.get_sensors_list()
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
        data = await mongo_client.get_latest_sensor_data(sensor_name=sensor_name)
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
        template = await mongo_client.get_sensor_template()
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


def _get_sketches_dir() -> Path:
    """Restituisce il percorso della directory sketches"""
    backend_root = Path(__file__).parent.parent.parent.parent
    return backend_root / "app" / "sketches"


def _list_sketches_for_protocol(protocol: str) -> List[Dict[str, Any]]:
    """Lista tutti gli sketch disponibili per un protocollo (include sottocartelle)"""
    sketches_dir = _get_sketches_dir() / protocol
    sketches = []
    
    if not sketches_dir.exists():
        return sketches
    
    # Mappa nomi file a descrizioni
    descriptions = {
        "temperature_sensor.py": {
            "name": "Temperatura/Umidità",
            "description": "Sketch per sensore temperatura/umidità (DHT22/DHT11)"
        },
        "motion_sensor.py": {
            "name": "Movimento/PIR",
            "description": "Sketch per sensore movimento/PIR"
        },
        "basic_sensor.py": {
            "name": "Base/Generico",
            "description": "Sketch base template per sensore generico"
        },
    }
    
    # Cerca file .py direttamente nella cartella del protocollo
    for sketch_file in sketches_dir.glob("*.py"):
        if sketch_file.name == "__init__.py":
            continue
        
        sketch_id = sketch_file.stem  # Nome senza estensione
        file_path = sketch_file.relative_to(sketches_dir)
        desc = descriptions.get(str(file_path), {
            "name": sketch_id.replace("_", " ").title(),
            "description": f"Sketch per {sketch_id}"
        })
        
        sketches.append({
            "id": sketch_id,
            "name": desc["name"],
            "description": desc["description"],
            "filename": sketch_file.name,
            "protocol": protocol
        })
    
    # Cerca anche nelle sottocartelle
    for subdir in sketches_dir.iterdir():
        if subdir.is_dir() and not subdir.name.startswith('__'):
            for sketch_file in subdir.glob("*.py"):
                if sketch_file.name == "__init__.py":
                    continue
                
                sketch_id = f"{subdir.name}/{sketch_file.stem}"  # es: shelly_rgbw2/shelly_rgbw2
                file_path = sketch_file.relative_to(sketches_dir)
                desc = descriptions.get(str(file_path), {
                    "name": f"{subdir.name.replace('_', ' ').title()} - {sketch_file.stem.replace('_', ' ').title()}",
                    "description": f"Sketch per {subdir.name.replace('_', ' ')}"
                })
                
                sketches.append({
                    "id": sketch_id,
                    "name": desc["name"],
                    "description": desc["description"],
                    "filename": str(file_path),
            "protocol": protocol
        })
    
    return sketches


@router.get("/sketches")
async def get_all_sketches():
    """Restituisce la lista di tutti gli sketch disponibili per tutti i protocolli"""
    all_sketches = {}
    
    # Lista protocolli supportati
    protocols = ["http", "websocket"]
    
    for protocol in protocols:
        sketches = _list_sketches_for_protocol(protocol)
        if sketches:
            all_sketches[protocol] = sketches
    
    return {"sketches": all_sketches}


@router.get("/sketches/{protocol}")
async def get_sketches_for_protocol(protocol: str):
    """Restituisce la lista degli sketch disponibili per un protocollo specifico"""
    if protocol not in ["http", "websocket"]:
        raise HTTPException(
            status_code=400,
            detail=f"Protocollo '{protocol}' non supportato. Protocolli disponibili: http, websocket"
        )
    
    sketches = _list_sketches_for_protocol(protocol)
    return {"protocol": protocol, "sketches": sketches}


@router.get("/sketches/{protocol}/{sketch_id}")
async def get_sketch(protocol: str, sketch_id: str):
    """Restituisce il contenuto di uno sketch specifico"""
    if protocol not in ["http", "websocket"]:
        raise HTTPException(
            status_code=400,
            detail=f"Protocollo '{protocol}' non supportato"
        )
    
    sketches_dir = _get_sketches_dir() / protocol
    
    # Supporta sia file diretti che file in sottocartelle (es: shelly_rgbw2/shelly_rgbw2)
    if "/" in sketch_id:
        # È in una sottocartella
        sketch_file = sketches_dir / f"{sketch_id}.py"
    else:
        # È nella cartella principale
    sketch_file = sketches_dir / f"{sketch_id}.py"
    
    if not sketch_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Sketch '{sketch_id}' non trovato per protocollo '{protocol}'. "
                   f"File cercato: {sketch_file}"
        )
    
    try:
        with open(sketch_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "protocol": protocol,
            "sketch_id": sketch_id,
            "filename": sketch_file.name,
            "content": content
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore nella lettura dello sketch: {str(e)}"
        )


# ========== ROUTE DI RETROCOMPATIBILITÀ (deprecate) ==========
@router.get("/websocket-logics")
async def get_websocket_logics():
    """DEPRECATO: Usa /sketches/websocket invece"""
    sketches = _list_sketches_for_protocol("websocket")
    return {"logics": sketches, "deprecated": True, "use": "/sketches/websocket"}


@router.get("/websocket-logics/{logic_id}/sketch")
async def get_websocket_sketch(logic_id: str):
    """DEPRECATO: Usa /sketches/websocket/{logic_id} invece"""
    return await get_sketch("websocket", logic_id)


# ========== SENSOR TEMPLATES ==========

def _get_sensor_templates() -> List[Dict[str, Any]]:
    """Lista tutti i template di sensori disponibili (solo quelli abilitati)"""
    import os
    from pathlib import Path
    
    # Leggi sensori abilitati da variabile d'ambiente
    enabled_sensors_str = os.getenv("ENABLED_SENSORS", "")
    enabled_sensors = [s.strip() for s in enabled_sensors_str.split(",") if s.strip()]
    
    # Template base disponibili
    all_templates = {
        "shelly_rgbw2": {
            "id": "shelly_rgbw2",
            "name": "Shelly RGBW2",
            "description": "Controller LED RGBW con controllo colore e luminosità",
            "protocol": "http",
            "required_fields": ["name", "ip"],
            "optional_fields": [],
            "default_config": {
                "protocol": "http",
                "enabled": True,
                "type": "http"
            },
            "control_interface": "shelly_rgbw2"
        },
        "shelly_dimmer2": {
            "id": "shelly_dimmer2",
            "name": "Shelly Dimmer 2",
            "description": "Dimmer per controllo luminosità luce dimmerabile",
            "protocol": "http",
            "required_fields": ["name", "ip"],
            "optional_fields": [],
            "default_config": {
                "protocol": "http",
                "enabled": True,
                "type": "http"
            },
            "control_interface": "shelly_dimmer2"
        }
    }
    
    # Carica metadata dai plugin scaricati (se disponibili)
    plugins_dir = Path("/app/plugins")
    for sensor_id in enabled_sensors:
        if sensor_id not in all_templates:
            # Prova a caricare metadata dal plugin
            metadata_path = plugins_dir / sensor_id / "metadata.json"
            if metadata_path.exists():
                try:
                    import json
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                        all_templates[sensor_id] = {
                            "id": metadata.get("id", sensor_id),
                            "name": metadata.get("name", sensor_id.replace("_", " ").title()),
                            "description": metadata.get("description", ""),
                            "protocol": metadata.get("protocol", "http"),
                            "required_fields": metadata.get("required_fields", ["name", "ip"]),
                            "optional_fields": metadata.get("optional_fields", []),
                            "default_config": {
                                "protocol": metadata.get("protocol", "http"),
                                "enabled": True,
                                "type": metadata.get("protocol", "http")
                            },
                            "control_interface": metadata.get("template_id", sensor_id)
                        }
                except:
                    pass
    
    # Restituisce solo i template dei sensori abilitati
    templates = []
    for sensor_id in enabled_sensors:
        if sensor_id in all_templates:
            templates.append(all_templates[sensor_id])
    
    return templates


@router.get("/sensor-templates")
async def get_sensor_templates():
    """Restituisce la lista di tutti i template di sensori disponibili"""
    return {"templates": _get_sensor_templates()}


@router.get("/sensor-templates/{template_id}/config")
async def get_template_config(template_id: str):
    """Restituisce la configurazione di un template specifico"""
    templates = _get_sensor_templates()
    template = next((t for t in templates if t["id"] == template_id), None)
    
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_id}' non trovato")
    
    return template

