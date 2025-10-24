from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
from services.api.auth.routes import get_current_user
from services.api.core.shared import _auth_enabled, _create_engine, _database_url, _repo_root
from services.api.core.repos import InteractionHistoryRepoDB

import services.api.core.shared as shared
from services.api.planner.core import plan_request, _generate_prd_with_llm, _get_chat_history_context  # deterministic planner fallback
from services.api.planner.openapi_gen import generate_openapi  # blueprint→OpenAPI

# Create a local templates instance to avoid importing app.py (prevents circular import).
_THIS_FILE = Path(__file__).resolve()
_TEMPLATES_DIR = _THIS_FILE.parents[2] / "templates"  # <repo>/services/templates
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

class PRDRequest(BaseModel):
    project_name: str
    project_description: Optional[str] = None
    include_chat_history: bool = True

class PRDResponse(BaseModel):
    prd_content: str
    plan_id: Optional[str] = None

class ChatRequest(BaseModel):
    project_id: str
    project_name: str
    message: str

class ChatResponse(BaseModel):
    content: str
    timestamp: str

class PRDSaveRequest(BaseModel):
    project_name: str
    prd_content: str
    project_id: str

class PRDSaveResponse(BaseModel):
    success: bool
    file_path: str
    message: str

class PRDGetResponse(BaseModel):
    prd_content: str
    file_path: str
    last_modified: int

class ADRRequest(BaseModel):
    project_name: str
    project_description: Optional[str] = None
    prd_content: Optional[str] = None
    include_chat_history: bool = True

class ADRResponse(BaseModel):
    adr_content: str
    plan_id: Optional[str] = None

class ADRSaveRequest(BaseModel):
    project_name: str
    adr_content: str
    project_id: str

class ADRSaveResponse(BaseModel):
    success: bool
    file_path: str
    message: str

class ADRGetResponse(BaseModel):
    adr_content: str
    file_path: str
    last_modified: int

# Create a local templates instance to avoid importing app.py (prevents circular import).
_THIS_FILE = Path(__file__).resolve()
_TEMPLATES_DIR = _THIS_FILE.parents[2] / "templates"  # <repo>/services/templates
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()

# PRD generation endpoint
@router.post("/api/prd/generate", response_model=PRDResponse)
def generate_prd_endpoint(
    prd_request: PRDRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate PRD using chat history and LLM."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    # Get chat history if requested
    chat_context = ""
    if prd_request.include_chat_history:
        from services.api.planner.core import _get_chat_history_context
        chat_context = _get_chat_history_context(prd_request.project_name)

    # Combine project info with chat context
    full_request = f"{prd_request.project_name}"
    if prd_request.project_description:
        full_request += f"\n{prd_request.project_description}"

    if chat_context:
        full_request += f"\n\n{chat_context}"

    # Get stack info (simplified for now)
    stack = {"language": "python", "framework": "fastapi", "database": "sqlite"}
    gates = {"coverage_gate": 0.8, "risk_threshold": "medium", "approvals": {}}

    # Generate PRD using our LLM function
    prd_content = _generate_prd_with_llm(
        full_request,
        user.get("id", "public"),
        stack,
        gates
    )

    if not prd_content:
        # Fallback to basic template
        prd_content = f"""# Product Requirements Document — {prd_request.project_name}

## Problem Statement
{full_request}

## Goals & Non-Goals
- **Goals**: Deliver the requested functionality
- **Non-Goals**: Out of scope features

## Requirements
- Core functionality as discussed in chat
"""

    return PRDResponse(
        prd_content=prd_content,
        plan_id=None  # Could generate a plan ID here if needed
    )

# PRD save endpoint
@router.post("/api/prd/save", response_model=PRDSaveResponse)
def save_prd_endpoint(prd_save_request: PRDSaveRequest):
    """Save PRD to backend file system for use in SDLC workflows."""
    # Skip authentication for PRD saves to enable SDLC workflows
    try:
        import re
        
        # Create slug from project name
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', prd_save_request.project_name.lower())
        slug = re.sub(r'[\s-]+', '-', slug).strip('-')
        
        # Use project_id from request (now required)
        project_id = prd_save_request.project_id
        
        # Create PRD directory if it doesn't exist
        repo_root = _repo_root()
        prd_dir = repo_root / "docs" / "prd"
        prd_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with new format: PRD-{project_id}-{slug}
        prd_filename = f"PRD-{project_id}-{slug}.md"
        prd_path = prd_dir / prd_filename
        
        # Write PRD content to file
        prd_path.write_text(prd_save_request.prd_content.strip() + "\n", encoding="utf-8")
        
        return PRDSaveResponse(
            success=True,
            file_path=str(prd_path),
            message=f"PRD saved successfully as {prd_filename}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save PRD: {str(e)}")

# PRD get endpoint
@router.get("/api/prd/{project_name}")
def get_prd_endpoint(
    project_name: str,
    project_id: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the PRD for a project."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    try:
        import re
        from services.api.core.shared import _repo_root
        
        repo_root = _repo_root()
        prd_dir = repo_root / "docs" / "prd"
        
        if project_id:
            # If project_id is provided, find the specific PRD file
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', project_name.lower())
            slug = re.sub(r'[\s-]+', '-', slug).strip('-')
            prd_filename = f"PRD-{project_id}-{slug}.md"
            prd_path = prd_dir / prd_filename
            
            if not prd_path.exists():
                raise HTTPException(status_code=404, detail="No PRD found for this project")
        else:
            # Fallback: Create slug from project name and find matching files
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', project_name.lower())
            slug = re.sub(r'[\s-]+', '-', slug).strip('-')
            
            # Find PRD files matching the slug pattern
            prd_files = list(prd_dir.glob(f"PRD-*-{slug}.md"))
            
            if not prd_files:
                raise HTTPException(status_code=404, detail="No PRD found for this project")
            
            # Sort by filename and get the most recent
            prd_files.sort(reverse=True)
            prd_path = prd_files[0]
        
        # Read and return PRD content
        prd_content = prd_path.read_text(encoding="utf-8")
        
        return PRDGetResponse(
            prd_content=prd_content,
            file_path=str(prd_path),
            last_modified=int(prd_path.stat().st_mtime)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get PRD: {str(e)}")

# ADR generation endpoint
@router.post("/api/adr/generate", response_model=ADRResponse)
def generate_adr_endpoint(
    adr_request: ADRRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Generate ADR using PRD content and chat history."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    # Get LLM client
    from services.api.llm import get_llm_from_env
    llm_client = get_llm_from_env()
    
    if not llm_client:
        # Fallback ADR content
        adr_content = f"""# Architecture Design Records (ADR)
## {adr_request.project_name}

## ADR 001: Technology Stack Selection

### Context
{adr_request.project_description or "Project requires technology stack selection for optimal architecture."}

### Decision
We will use a modern web stack with React frontend and FastAPI backend.

### Consequences
- **Positive**: Fast development, good ecosystem support
- **Negative**: Learning curve for new technologies
- **Risks**: Technology changes, maintenance overhead

### Status
Accepted
"""
    else:
        # Generate ADR using LLM
        system_prompt = """You are an expert software architect. Generate comprehensive Architecture Design Records (ADR) and Technology Stack Specification based on the provided PRD and project information. Follow ADR best practices with clear context, decisions, and consequences."""
        
        user_prompt = f"""Generate Architecture Design Records and Technology Stack Specification for this project:

Project: {adr_request.project_name}
Description: {adr_request.project_description or 'No description provided'}

PRD Content:
{adr_request.prd_content or 'No PRD content available'}

Please create TWO separate documents:

1. ARCHITECTURE DESIGN RECORDS (ADR) - covering system design decisions
2. TECHNOLOGY STACK SPECIFICATION - detailed technology choices and implementation guidelines

SEPARATE the two documents with this exact keyword: ---TECH-STACK---

Format the ADR section as proper ADR documents with Context, Decision, Consequences, and Status sections.
Format the Tech Stack section as detailed implementation specifications.

Example structure:
# Architecture Design Records (ADR)
## [Project Name]

[ADR content here]

---TECH-STACK---

# Technology Stack Specification
## [Project Name]

[Tech stack content here]"""

        try:
            adr_content = llm_client.generate_plan(user_prompt, system_prompt=system_prompt)
        except Exception as e:
            print(f"LLM ADR generation failed: {e}")
            # Fallback content
            adr_content = f"""# Architecture Design Records (ADR)
## {adr_request.project_name}

## ADR 001: Technology Stack Selection

### Context
{adr_request.project_description or "Project requires technology stack selection."}

### Decision
Selected technology stack based on project requirements.

### Status
Draft - Requires refinement with LLM
"""

    return ADRResponse(
        adr_content=adr_content,
        plan_id=None
    )

# ADR save endpoint
@router.post("/api/adr/save", response_model=ADRSaveResponse)
def save_adr_endpoint(adr_save_request: ADRSaveRequest):
    """Save ADR to backend file system."""
    try:
        import re
        
        # Create slug from project name
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', adr_save_request.project_name.lower())
        slug = re.sub(r'[\s-]+', '-', slug).strip('-')
        
        # Use project_id from request
        project_id = adr_save_request.project_id
        
        # Create ADR directory if it doesn't exist
        repo_root = _repo_root()
        adr_dir = repo_root / "docs" / "adr"
        adr_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with format: ADR-{project_id}-{slug}
        adr_filename = f"ADR-{project_id}-{slug}.md"
        adr_path = adr_dir / adr_filename
        
        # Write ADR content to file
        adr_path.write_text(adr_save_request.adr_content.strip() + "\n", encoding="utf-8")
        
        return ADRSaveResponse(
            success=True,
            file_path=str(adr_path),
            message=f"ADR saved successfully as {adr_filename}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save ADR: {str(e)}")

# ADR get endpoint
@router.get("/api/adr/{project_name}")
def get_adr_endpoint(
    project_name: str,
    project_id: Optional[str] = Query(None),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Get the ADR for a project."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    try:
        import re
        from services.api.core.shared import _repo_root
        
        repo_root = _repo_root()
        adr_dir = repo_root / "docs" / "adr"
        
        if project_id:
            # If project_id is provided, find the specific ADR file
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', project_name.lower())
            slug = re.sub(r'[\s-]+', '-', slug).strip('-')
            adr_filename = f"ADR-{project_id}-{slug}.md"
            adr_path = adr_dir / adr_filename
            
            if not adr_path.exists():
                raise HTTPException(status_code=404, detail="No ADR found for this project")
        else:
            # Fallback: Create slug from project name and find matching files
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', project_name.lower())
            slug = re.sub(r'[\s-]+', '-', slug).strip('-')
            
            # Find ADR files matching the slug pattern
            adr_files = list(adr_dir.glob(f"ADR-*-{slug}.md"))
            
            if not adr_files:
                raise HTTPException(status_code=404, detail="No ADR found for this project")
            
            # Sort by filename and get the most recent
            adr_files.sort(reverse=True)
            adr_path = adr_files[0]
        
        # Read and return ADR content
        adr_content = adr_path.read_text(encoding="utf-8")
        
        return ADRGetResponse(
            adr_content=adr_content,
            file_path=str(adr_path),
            last_modified=int(adr_path.stat().st_mtime)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get ADR: {str(e)}")

# Chat endpoint
@router.post("/api/chat/message", response_model=ChatResponse)
def chat_message_endpoint(
    chat_request: ChatRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Send a chat message and get AI response."""
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")

    # Get LLM client
    from services.api.llm import get_llm_from_env
    llm_client = get_llm_from_env()
    
    if not llm_client:
        # Fallback response if no LLM configured
        response_content = f"I understand you're working on '{chat_request.project_name}'. This is a fallback response because no LLM provider is configured. Please set LLM_PROVIDER environment variable."
    else:
        # Use LLM to generate a helpful response for requirements gathering
        system_prompt = f"""You are an AI assistant helping to gather requirements for a software project called "{chat_request.project_name}". 
        Be helpful, ask clarifying questions, and help the user define clear, actionable requirements.
        Keep responses conversational but focused on requirements gathering."""
        
        # For now, we'll use a simple approach - in a real implementation, you'd use the LLM's chat completion
        # Since the current LLM interface only has generate_plan, we'll create a simple response
        response_content = f"Thanks for your message: '{chat_request.message}'. I'm here to help gather requirements for {chat_request.project_name}. What specific features or functionality are you looking to implement?"

    # Save the conversation to history
    try:
        engine = _create_engine(_database_url(_repo_root()))
        repo = InteractionHistoryRepoDB(engine)
        
        # Save user message
        repo.add({
            "project_id": chat_request.project_id,
            "role": "user", 
            "prompt": chat_request.message,
            "response": "",
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
        
        # Save AI response
        repo.add({
            "project_id": chat_request.project_id,
            "role": "assistant",
            "prompt": "",
            "response": response_content,
            "metadata": {"timestamp": datetime.now().isoformat()}
        })
    except Exception as e:
        print(f"Warning: Could not save chat history: {e}")

    return ChatResponse(
        content=response_content,
        timestamp=datetime.now().isoformat()
    )

# Render the form
@router.get("/ui/requests/new", response_class=HTMLResponse)
def new_request_form(request: Request):
    return templates.TemplateResponse(
    request,
    "requests_new.html",
    {
        "providers": ["none", "openai", "anthropic", "azure", "local"],
        "modes": ["single", "multi"],
        "default_provider": "none",
        "default_mode": "single",
    },
)
ui_requests_router = APIRouter()

# Handle submission: build a draft plan + artifacts for review
@router.post("/ui/requests", response_class=HTMLResponse)
def submit_request(
    request: Request,
    project_vision: str = Form(...),
    agent_mode: str = Form("single"),
    llm_provider: str = Form("none"),
    plan_id: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(get_current_user),
):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    repo_root = shared._repo_root()
    draft = plan_request(project_vision, repo_root, owner="ui")  # writes docs/* deterministically
    # If user provided a Plan ID, persist later via POST /plans; for now, preview.

    # Ensure we have an OpenAPI draft in memory even if generator module not present
    try:
        blueprint = {
            "info": {"title": "Agentic Feature API", "version": "0.1.0",
                     "description": project_vision[:400]},
            "paths": [
                {"path": "/plans", "method": "get", "summary": "List Plans",
                 "responses": {"200": {"description": "OK"}}},
            ],
            "security_schemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
            "default_security": ["bearerAuth"],
        }
        openapi = generate_openapi(blueprint)  # raises if invalid
    except Exception:
        # Conservative fallback: show the skeleton used in planner.core
        openapi = {"openapi": "3.1.0", "info": {"title": "Agentic Feature API", "version": "0.1.0"}, "paths": {}}

    return templates.TemplateResponse(
        request,
        "requests_review.html",
        {
            "plan": draft,
            "openapi_json": openapi,
            "project_vision": project_vision,
            "agent_mode": agent_mode,
            "llm_provider": llm_provider,
            "suggested_plan_id": plan_id or draft.get("id") or "",
        },
    )
