import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import os

from app.config_loader import ConfigLoader
from app.sensors.factory import SensorFactory
from app.db.mongo_client import MongoClientWrapper
from app.services.mqtt_client import MQTTClient
from app.services.business_logic import BusinessLogic
from app.api.routes import sensors, frontend
# I router dei sensori vengono caricati dinamicamente dal plugin loader
from app import dependencies
from app.protocols.protocol_registry import ProtocolRegistry
from app.protocols.http_protocol import HTTPProtocol
from app.protocols.websocket_protocol import WebSocketProtocol


# Variabili globali per i servizi
business_logic: BusinessLogic = None
mongo_client: MongoClientWrapper = None
mqtt_client: Optional[MQTTClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestisce il ciclo di vita dell'applicazione"""
    global business_logic, mongo_client, mqtt_client
    
    # Aggiorna le variabili globali in dependencies
    dependencies.business_logic = None
    dependencies.mongo_client = None
    
    # Startup
    print("Avvio applicazione...")
    
    # Connessione MongoDB
    mongo_client = MongoClientWrapper()
    try:
        await mongo_client.connect()
    except Exception as e:
        print(f"Avviso: Impossibile connettersi a MongoDB: {e}")
        print("L'applicazione continuerà senza MongoDB")
        mongo_client = None
    
    # Carica template e salvalo nel DB se MongoDB è disponibile
    if mongo_client is not None:
        try:
            from pathlib import Path
            config_path = Path(__file__).parent / "sensors_config.yaml"
            config_loader = ConfigLoader(str(config_path))
            template = config_loader.load_template()
            
            # Salva il template nel DB (sovrascrive se esiste già)
            await mongo_client.save_sensor_template(template)
            print("Template sensori caricato e salvato nel database")
        except Exception as e:
            print(f"Avviso: Errore nel caricamento del template: {e}")
            # Prova a caricare il template dal DB se esiste
            template = await mongo_client.get_sensor_template()
            if template is not None:
                print("Template caricato dal database")
            else:
                print("Nessun template disponibile")
    
    # Connessione MQTT (implementazione da completare in seguito)
    # Per ora MQTT è disabilitato - la classe MQTTClient è uno stub vuoto
    mqtt_client = None
    
    # Registra i protocolli disponibili
    ProtocolRegistry.register_protocol("http", HTTPProtocol)
    ProtocolRegistry.register_protocol("websocket", WebSocketProtocol)
    print(f"Protocolli registrati: {ProtocolRegistry.list_protocols()}")
    
    # Carica configurazioni sensori dal database
    sensor_configs = []
    if mongo_client is not None:
        try:
            sensor_configs = await mongo_client.get_all_sensor_configs()
            print(f"Caricate {len(sensor_configs)} configurazioni sensori dal database")
        except Exception as e:
            print(f"Avviso: Errore nel caricamento dei sensori dal database: {e}")
    
    # Crea sensori
    sensors = SensorFactory.create_sensors_from_configs(sensor_configs)
    print(f"Creati {len(sensors)} sensori")
    
    # Crea business logic
    business_logic = BusinessLogic(
        sensors=sensors,
        mongo_client=mongo_client,
        mqtt_client=mqtt_client
    )
    
    # Aggiorna le variabili globali in dependencies
    dependencies.business_logic = business_logic
    dependencies.mongo_client = mongo_client
    
    # Valida e connetti tutti i sensori
    # La validazione delle porte viene fatta automaticamente in connect_all_sensors
    connection_results = await business_logic.connect_all_sensors()
    connected_count = sum(1 for v in connection_results.values() if v)
    print(f"Connessi {connected_count}/{len(connection_results)} sensori")
    
    # Mostra informazioni sulle porte assegnate ai sensori WebSocket
    from app.sensors.generic_sensor import GenericSensor
    websocket_sensors = {name: sensor for name, sensor in sensors.items() 
                        if isinstance(sensor, GenericSensor) and 
                        sensor.protocol and 
                        sensor.protocol.get_protocol_name() == "WebSocketProtocol"}
    if websocket_sensors:
        print("\nPorte WebSocket assegnate:")
        for name, sensor in websocket_sensors.items():
            if sensor.port:
                print(f"  - {name}: porta {sensor.port}")
            else:
                print(f"  - {name}: porta non assegnata")
    
    # Carica plugin sensori (solo all'avvio, zero overhead a runtime)
    enabled_sensors_str = os.getenv("ENABLED_SENSORS", "")
    enabled_sensors = [s.strip() for s in enabled_sensors_str.split(",") if s.strip()]
    
    if enabled_sensors:
        from app.plugins.plugin_loader import PluginLoader
        plugin_loader = PluginLoader()
        
        print(f"\nCaricamento plugin sensori ({len(enabled_sensors)} sensori)...")
        routers = await plugin_loader.load_enabled_sensors(enabled_sensors)
        
        # Registra i router (una volta, poi in memoria - zero overhead runtime)
        for sensor_id, router in routers:
            app.include_router(router)
            print(f"✓ Router {sensor_id} registrato nell'app")
    else:
        print("Nessun sensore abilitato (ENABLED_SENSORS non impostato)")
    
    # Avvia polling
    await business_logic.start_polling()
    
    print("Applicazione avviata con successo!")
    
    yield
    
    # Shutdown
    print("Arresto applicazione...")
    
    # Ferma polling
    if business_logic is not None:
        await business_logic.stop_polling()
        await business_logic.disconnect_all_sensors()
    
    # Disconnette MQTT
    if mqtt_client is not None:
        await mqtt_client.disconnect()
    
    # Disconnette MongoDB
    if mongo_client is not None:
        await mongo_client.disconnect()
    
    print("Applicazione arrestata")


# Crea app FastAPI
app = FastAPI(
    title="Smart Home Backend",
    description="Backend modulare per gestione sensori smart home",
    version="1.0.0",
    lifespan=lifespan
)

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Le dipendenze sono ora in app.dependencies per evitare importazioni circolari


# Include routers base (sempre presenti)
app.include_router(sensors.router)
app.include_router(frontend.router)

# I router dei sensori vengono caricati dinamicamente nel lifespan
# (vedi codice sopra nel lifespan)


@app.get("/")
async def root():
    """Endpoint root"""
    return {
        "message": "Smart Home Backend API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    mongo_connected = False
    if dependencies.mongo_client is not None:
        mongo_connected = dependencies.mongo_client.db is not None
    
    mqtt_connected = False
    if mqtt_client is not None:
        mqtt_connected = mqtt_client.connected
    
    sensors_count = 0
    if dependencies.business_logic is not None:
        sensors_count = len(dependencies.business_logic.sensors)
    
    return {
        "status": "healthy",
        "mongo_connected": mongo_connected,
        "mqtt_connected": mqtt_connected,
        "sensors_count": sensors_count
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

