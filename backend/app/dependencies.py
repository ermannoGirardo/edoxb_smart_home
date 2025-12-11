from typing import Optional
from app.services.business_logic import BusinessLogic
from app.db.mongo_client import MongoClientWrapper

# Variabili globali per i servizi (saranno inizializzate in main.py)
business_logic: Optional[BusinessLogic] = None
mongo_client: Optional[MongoClientWrapper] = None


def get_business_logic() -> BusinessLogic:
    """Dependency per ottenere l'istanza di BusinessLogic"""
    if business_logic is None:
        raise RuntimeError("BusinessLogic non inizializzato")
    return business_logic


def get_mongo_client() -> MongoClientWrapper:
    """Dependency per ottenere l'istanza di MongoClientWrapper"""
    if mongo_client is None:
        raise RuntimeError("MongoClient non inizializzato")
    return mongo_client

