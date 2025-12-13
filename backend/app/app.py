from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import os

app = FastAPI()

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient(os.getenv("MONGODB_URL"))
db = client["mydb"]

# Router API con prefisso /api
api_router = APIRouter(prefix="/api")

@api_router.get("/")
def home():
    return {"message": "backend ok"}


@api_router.get("/users")
def users():
    return list(db.users.find({}, {"_id": 0}))

# Includi il router API nell'app
app.include_router(api_router)
