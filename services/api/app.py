from fastapi import FastAPI
from pydantic import BaseModel
from pathlib import Path
try:
    from .planner import plan_request
except ImportError:
    from planner import plan_request


try:
    from .routes.notes import router as notes_router
except ImportError:
    from routes.notes import router as notes_router
app = FastAPI(title="Agentic SDLC API", version="0.4.0")

class RequestIn(BaseModel):
    text: str

app.include_router(notes_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/requests")
def create_request(req: RequestIn):
    repo_root = Path(__file__).resolve().parents[2]
    artifacts = plan_request(req.text, repo_root)
    return {"message": "Planned and generated artifacts", "artifacts": artifacts, "request": req.text}
