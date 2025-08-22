from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
# services/api/app.py
try:
    # when imported as a package: services.api.app
    from .planner import plan_request
except ImportError:
    # when run from inside services/api (tests, local runs)
    from planner import plan_request


app = FastAPI(title="Agentic SDLC API", version="0.3.0")

class RequestIn(BaseModel):
    text: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/requests")
def create_request(req: RequestIn):
    repo_root = Path(__file__).resolve().parents[2]
    artifacts = plan_request(req.text, repo_root)
    return {"message": "Planned and generated artifacts", "artifacts": artifacts, "request": req.text}
