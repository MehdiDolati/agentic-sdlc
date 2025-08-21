from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Agentic SDLC API", version="0.1.0")

class RequestIn(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/requests")
def create_request(req: RequestIn):
    # In a real system, this would create a workspace, parse req, and enqueue a plan.
    return {"message": "Request received", "text": req.text}
