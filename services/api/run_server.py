#!/usr/bin/env python3
import sys
import os
import threading
import time
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

print("Creating app...")
app = FastAPI(lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}

print("App created, running uvicorn...")
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)