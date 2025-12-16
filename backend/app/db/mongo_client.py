from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, Dict, Any
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from app.models import SensorData, SensorConfig, SensorTemplate


class MongoClientWrapper:
    """Wrapper per la connessione MongoDB asincrona con Motor"""
    
    def __init__(self, connection_string: Optional[str] = None, db_name: str = "smart_home", backup_dir: str = "/app/backup"):
        self.connection_string = connection_string or os.getenv("MONGODB_URL", "mongodb://localhost:27017")
        self.db_name = db_name
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None
        # Configura directory backup (può essere sovrascritta da variabile d'ambiente)
        backup_path = os.getenv("BACKUP_DIR", backup_dir)
        self.backup_dir = Path(backup_path)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    async def export_data_to_file(self, start_date: datetime, end_date: datetime, sensor_name: Optional[str] = None) -> str:
        """Esporta i dati in un file JSON per il backup giornaliero"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        collection = self.db.sensor_data
        query = {
            "timestamp": {"$gte": start_date, "$lt": end_date}
        }
        
        if sensor_name:
            query["sensor_name"] = sensor_name
        
        # Recupera tutti i documenti nel range
        cursor = collection.find(query).sort("timestamp", 1)
        documents = []
        async for doc in cursor:
            # Converti ObjectId in stringa
            doc["_id"] = str(doc["_id"])
            # Converti datetime in ISO string
            if isinstance(doc.get("timestamp"), datetime):
                doc["timestamp"] = doc["timestamp"].isoformat()
            documents.append(doc)
        
        # Crea directory per la data (YYYY-MM-DD)
        date_str = start_date.strftime("%Y-%m-%d")
        backup_path = self.backup_dir / date_str
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Nome file
        if sensor_name:
            filename = f"{sensor_name}_{date_str}.json"
        else:
            filename = f"sensor_data_{date_str}.json"
        
        file_path = backup_path / filename
        
        # Salva in JSON
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({
                "export_date": datetime.now().isoformat(),
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "sensor_name": sensor_name,
                "total_records": len(documents),
                "data": documents
            }, f, indent=2, ensure_ascii=False)
        
        return str(file_path)
    
    async def save_sensor_data(self, sensor_data: SensorData) -> None:
        """Salva i dati di un sensore nel database, esporta e mantiene solo gli ultimi 24 ore"""
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
        
        # Inserisci il nuovo documento
        await collection.insert_one(document)
        
        # Controlla se ci sono dati da esportare (più vecchi di 24 ore)
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        # Recupera i dati vecchi PRIMA di eliminarli
        old_data_cursor = collection.find({
            "sensor_name": sensor_data.sensor_name,
            "timestamp": {"$lt": cutoff_time}
        })
        old_data = await old_data_cursor.to_list(length=None)
        
        if old_data:
            # Raggruppa per data (giorno)
            data_by_date = defaultdict(list)
            
            for doc in old_data:
                doc_timestamp = doc["timestamp"]
                if isinstance(doc_timestamp, datetime):
                    doc_date = doc_timestamp.date()
                    data_by_date[doc_date].append(doc)
            
            # Esporta per ogni giorno
            for date, docs in data_by_date.items():
                start_of_day = datetime.combine(date, datetime.min.time())
                end_of_day = datetime.combine(date, datetime.max.time())
                
                try:
                    # Esporta solo i dati di questo sensore per questo giorno
                    file_path = await self.export_data_to_file(
                        start_of_day,
                        end_of_day,
                        sensor_name=sensor_data.sensor_name
                    )
                    print(f"Esportati {len(docs)} documenti per {sensor_data.sensor_name} del {date} -> {file_path}")
                except Exception as e:
                    print(f"Errore esportazione backup per {sensor_data.sensor_name} del {date}: {e}")
            
            # Dopo l'esportazione, elimina i dati vecchi
            result = await collection.delete_many({
                "sensor_name": sensor_data.sensor_name,
                "timestamp": {"$lt": cutoff_time}
            })
            
            if result.deleted_count > 0:
                print(f"Eliminati {result.deleted_count} documenti vecchi per {sensor_data.sensor_name} (dopo backup)")
    
    async def cleanup_old_data(self, hours: int = 24, minutes: Optional[int] = None) -> int:
        """Pulisce i dati più vecchi di N ore (o N minuti se specificato) per tutti i sensori, esportandoli prima"""
        if self.db is None:
            raise RuntimeError("Database non connesso")
        
        # Per test: usa minuti invece di ore
        if minutes is not None:
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
        else:
            cutoff_time = datetime.now() - timedelta(hours=hours)
        
        collection = self.db.sensor_data
        
        # Recupera i dati vecchi PRIMA di eliminarli
        old_data_cursor = collection.find({
            "timestamp": {"$lt": cutoff_time}
        })
        old_data = await old_data_cursor.to_list(length=None)
        
        if old_data:
            # Raggruppa per data e sensore
            data_by_date_sensor = defaultdict(lambda: defaultdict(list))
            
            for doc in old_data:
                doc_timestamp = doc["timestamp"]
                if isinstance(doc_timestamp, datetime):
                    doc_date = doc_timestamp.date()
                    sensor = doc.get("sensor_name", "unknown")
                    data_by_date_sensor[doc_date][sensor].append(doc)
            
            # Esporta per ogni giorno e sensore
            for date, sensors_data in data_by_date_sensor.items():
                start_of_day = datetime.combine(date, datetime.min.time())
                end_of_day = datetime.combine(date, datetime.max.time())
                
                for sensor_name, docs in sensors_data.items():
                    try:
                        file_path = await self.export_data_to_file(
                            start_of_day,
                            end_of_day,
                            sensor_name=sensor_name
                        )
                        print(f"Esportati {len(docs)} documenti per {sensor_name} del {date} -> {file_path}")
                    except Exception as e:
                        print(f"Errore esportazione backup per {sensor_name} del {date}: {e}")
        
        # Dopo l'esportazione, elimina i dati vecchi
        result = await collection.delete_many({
            "timestamp": {"$lt": cutoff_time}
        })
        
        return result.deleted_count
    
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

