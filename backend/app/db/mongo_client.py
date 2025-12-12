from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
import os
from datetime import datetime
from app.models import SensorData, SensorConfig, SensorTemplate


class MongoClientWrapper:
    """Wrapper per la connessione MongoDB asincrona con Motor"""
    
    def __init__(self, connection_string: Optional[str] = None, db_name: str = "smart_home"):
        self.connection_string = connection_string or os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.db_name = db_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
    
    async def connect(self) -> None:
        """Connette al database MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.connection_string)
            self.db = self.client[self.db_name]
            # Test connessione
            await self.client.admin.command('ping')
            print(f"Connesso a MongoDB: {self.db_name}")
        except Exception as e:
            print(f"Errore connessione MongoDB: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Disconnette dal database"""
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
    
    async def save_sensor_data(self, sensor_data: SensorData) -> None:
        """Salva i dati di un sensore nel database"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_data
        document = {
            "sensor_name": sensor_data.sensor_name,
            "timestamp": sensor_data.timestamp,
            "data": sensor_data.data,
            "status": sensor_data.status,
            "error": sensor_data.error
        }
        await collection.insert_one(document)
    
    async def get_sensor_data(
        self,
        sensor_name: Optional[str] = None,
        limit: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> list:
        """Recupera i dati dei sensori dal database"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_data
        query = {}
        
        if sensor_name:
            query["sensor_name"] = sensor_name
        
        if start_date or end_date:
            query["timestamp"] = {}
            if start_date:
                query["timestamp"]["$gte"] = start_date
            if end_date:
                query["timestamp"]["$lte"] = end_date
        
        cursor = collection.find(query).sort("timestamp", -1).limit(limit)
        results = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])  # Converti ObjectId in stringa
            results.append(doc)
        
        return results
    
    async def get_latest_sensor_data(self, sensor_name: Optional[str] = None) -> Optional[dict]:
        """Recupera l'ultimo dato disponibile per un sensore"""
        data = await self.get_sensor_data(sensor_name=sensor_name, limit=1)
        return data[0] if data else None
    
    async def get_sensors_list(self) -> list[str]:
        """Recupera la lista di tutti i sensori che hanno inviato dati"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_data
        sensors = await collection.distinct("sensor_name")
        return sensors
    
    async def save_sensor_template(self, template: SensorTemplate) -> None:
        """Salva il template dei sensori nel database"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_template
        document = template.model_dump()
        # Usa upsert per aggiornare se esiste già
        await collection.replace_one(
            {"_id": "sensor_template"},
            {"_id": "sensor_template", **document},
            upsert=True
        )
    
    async def get_sensor_template(self) -> Optional[SensorTemplate]:
        """Recupera il template dei sensori dal database"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_template
        doc = await collection.find_one({"_id": "sensor_template"})
        if doc:
            doc.pop("_id", None)  # Rimuovi _id per la creazione del modello
            return SensorTemplate(**doc)
        return None
    
    async def save_sensor_config(self, sensor_config: SensorConfig) -> None:
        """Salva la configurazione di un sensore nel database"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_configs
        document = sensor_config.model_dump()
        # Usa il nome come _id per garantire unicità
        await collection.replace_one(
            {"name": sensor_config.name},
            document,
            upsert=True
        )
    
    async def get_sensor_config(self, name: str) -> Optional[SensorConfig]:
        """Recupera la configurazione di un sensore dal database"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_configs
        doc = await collection.find_one({"name": name})
        if doc:
            return SensorConfig(**doc)
        return None
    
    async def get_all_sensor_configs(self) -> List[SensorConfig]:
        """Recupera tutte le configurazioni dei sensori dal database"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_configs
        configs = []
        async for doc in collection.find({}):
            configs.append(SensorConfig(**doc))
        return configs
    
    async def delete_sensor_config(self, name: str) -> bool:
        """Elimina la configurazione di un sensore dal database"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_configs
        result = await collection.delete_one({"name": name})
        return result.deleted_count > 0
    
    async def update_sensor_config(self, name: str, updates: Dict[str, Any]) -> bool:
        """Aggiorna la configurazione di un sensore nel database"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_configs
        # Rimuovi None values
        updates = {k: v for k, v in updates.items() if v is not None}
        if not updates:
            return False
        
        result = await collection.update_one(
            {"name": name},
            {"$set": updates}
        )
        return result.modified_count > 0

