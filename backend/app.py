from fastapi import FastAPI
from pymongo import MongoClient
import os

app = FastAPI()

client = MongoClient(os.getenv("MONGODB_URL"))
db = client["mydb"]

@app.get("/")
def home():
    return {"message": "backend ok"}

@app.get("/users")
def users():
    return list(db.users.find({}, {"_id": 0}))
