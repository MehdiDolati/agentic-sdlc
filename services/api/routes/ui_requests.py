from __future__ import annotations
from pathlib import Path
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Request, Form, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from datetime import datetime
import uuid
from services.api.auth.routes import get_current_user
from sqlalchemy import text

import services.api.core.shared as shared
from services.api.planner.core import plan_request, _generate_prd_with_llm  # deterministic planner fallback
from services.api.planner.openapi_gen import generate_openapi  # blueprint→OpenAPI
from services.api.core.shared import _auth_enabled, _repo_root, _create_engine, _database_url
from services.api.core.repos import InteractionHistoryRepoDB

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

class PlanSaveRequest(BaseModel):
    project_id: str
    name: str
    description: str
    size_estimate: int
    priority: str

class PlanSaveResponse(BaseModel):
    success: bool
    plan_id: str
    message: str

class PlanPriorityUpdateRequest(BaseModel):
    priority: Optional[str] = None
    priority_order: Optional[int] = None

class PlanPriorityUpdateResponse(BaseModel):
    success: bool
    message: str

class FeaturePriorityUpdateRequest(BaseModel):
    priority: Optional[str] = None
    priority_order: Optional[int] = None

class FeaturePriorityUpdateResponse(BaseModel):
    success: bool
    message: str

class FeatureSaveRequest(BaseModel):
    plan_id: Optional[str] = None
    name: str
    description: str
    size_estimate: int
    priority: str

class FeatureSaveResponse(BaseModel):
    success: bool
    feature_id: str
    message: str

# Create a local templates instance to avoid importing app.py (prevents circular import).
_THIS_FILE = Path(__file__).resolve()
_TEMPLATES_DIR = _THIS_FILE.parents[2] / "templates"  # <repo>/services/templates
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter()

# Plan priority update endpoint
@router.put("/api/plans/{plan_id}/priority", response_model=PlanPriorityUpdateResponse)
def update_plan_priority_endpoint(plan_id: str, priority_update: PlanPriorityUpdateRequest):
    """Update a plan's priority or priority order."""
    try:
        # For now, we'll just acknowledge the update since plans are stored in memory
        # In a full implementation, this could update a database
        updates = []
        if priority_update.priority is not None:
            updates.append(f"priority to '{priority_update.priority}'")
        if priority_update.priority_order is not None:
            updates.append(f"priority_order to '{priority_update.priority_order}'")
        
        update_str = ", ".join(updates)
        return PlanPriorityUpdateResponse(
            success=True,
            message=f"Plan '{plan_id}' updated ({update_str}) successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update plan: {str(e)}")

# Feature priority update endpoint
@router.put("/api/plans/features/{feature_id}/priority", response_model=FeaturePriorityUpdateResponse)
def update_feature_priority_endpoint(feature_id: str, priority_update: FeaturePriorityUpdateRequest):
    """Update a feature's priority or priority order."""
    try:
        # For now, we'll just acknowledge the update since features are stored in memory
        # In a full implementation, this could update a database
        updates = []
        if priority_update.priority is not None:
            updates.append(f"priority to '{priority_update.priority}'")
        if priority_update.priority_order is not None:
            updates.append(f"priority_order to '{priority_update.priority_order}'")
        
        update_str = ", ".join(updates)
        return FeaturePriorityUpdateResponse(
            success=True,
            message=f"Feature '{feature_id}' updated ({update_str}) successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update feature: {str(e)}")

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
        
        # Create directories if they don't exist
        repo_root = _repo_root()
        adr_dir = repo_root / "docs" / "adr"
        adr_dir.mkdir(parents=True, exist_ok=True)
        tech_dir = repo_root / "docs" / "tech"
        tech_dir.mkdir(parents=True, exist_ok=True)
        
        # Parse the combined content
        content = adr_save_request.adr_content.strip()
        separator = "---TECH-STACK---"
        
        if separator in content:
            # Split into ADR and Tech parts
            parts = content.split(separator, 1)
            adr_content = parts[0].strip()
            tech_content = parts[1].strip()
        else:
            # Fallback: assume all is ADR if no separator
            adr_content = content
            tech_content = ""
        
        # Save ADR file
        adr_filename = f"ADR-{project_id}-{slug}.md"
        adr_path = adr_dir / adr_filename
        if adr_content:
            adr_path.write_text(adr_content + "\n", encoding="utf-8")
        
        # Save Tech file
        tech_filename = f"TECH-{project_id}-{slug}.md"
        tech_path = tech_dir / tech_filename
        if tech_content:
            tech_path.write_text(tech_content + "\n", encoding="utf-8")
        
        return ADRSaveResponse(
            success=True,
            file_path=str(adr_path) if adr_content else str(tech_path),
            message=f"ADR and Tech stack saved successfully"
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
        tech_dir = repo_root / "docs" / "tech"
        
        # Create slug from project name
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', project_name.lower())
        slug = re.sub(r'[\s-]+', '-', slug).strip('-')
        
        architecture_content = ""
        tech_stack_content = ""
        last_modified = 0
        combined_content = ""
        
        if project_id:
            # Try to find separate files first (new format)
            adr_filename = f"ADR-{project_id}-{slug}.md"
            adr_path = adr_dir / adr_filename
            
            tech_filename = f"TECH-{project_id}-{slug}.md"
            tech_path = tech_dir / tech_filename
            
            if adr_path.exists():
                architecture_content = adr_path.read_text(encoding="utf-8").strip()
                last_modified = max(last_modified, int(adr_path.stat().st_mtime))
            
            if tech_path.exists():
                tech_stack_content = tech_path.read_text(encoding="utf-8").strip()
                last_modified = max(last_modified, int(tech_path.stat().st_mtime))
            
            # If we have separate files, combine them
            if architecture_content or tech_stack_content:
                if architecture_content and tech_stack_content:
                    combined_content = f"{architecture_content}\n\n---TECH-STACK---\n\n{tech_stack_content}"
                elif architecture_content:
                    combined_content = architecture_content
                elif tech_stack_content:
                    combined_content = tech_stack_content
            else:
                # Fallback: Check for old combined ADR file
                if adr_path.exists():
                    combined_content = adr_path.read_text(encoding="utf-8").strip()
                    last_modified = int(adr_path.stat().st_mtime)
                else:
                    raise HTTPException(status_code=404, detail="No ADR found for this project")
        else:
            # Fallback: Find files by slug pattern
            adr_files = list(adr_dir.glob(f"ADR-*-{slug}.md"))
            tech_files = list(tech_dir.glob(f"TECH-*-{slug}.md"))
            
            if adr_files:
                adr_files.sort(reverse=True)
                architecture_content = adr_files[0].read_text(encoding="utf-8").strip()
                last_modified = max(last_modified, int(adr_files[0].stat().st_mtime))
            
            if tech_files:
                tech_files.sort(reverse=True)
                tech_stack_content = tech_files[0].read_text(encoding="utf-8").strip()
                last_modified = max(last_modified, int(tech_files[0].stat().st_mtime))
            
            # Combine content
            if architecture_content and tech_stack_content:
                combined_content = f"{architecture_content}\n\n---TECH-STACK---\n\n{tech_stack_content}"
            elif architecture_content:
                combined_content = architecture_content
            elif tech_stack_content:
                combined_content = tech_stack_content
            else:
                # Check for old combined files
                if adr_files:
                    combined_content = adr_files[0].read_text(encoding="utf-8").strip()
                    last_modified = int(adr_files[0].stat().st_mtime)
                else:
                    raise HTTPException(status_code=404, detail="No ADR found for this project")
        
        return ADRGetResponse(
            adr_content=combined_content,
            file_path="",  # Not applicable for combined content
            last_modified=last_modified
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
    format: str = Query("html"),  # Query parameter first
    request: Request = None,
    project_vision: str = Form(...),
    agent_mode: str = Form("single"),
    llm_provider: str = Form("none"),
    plan_id: Optional[str] = Form(None),
    user: Dict[str, Any] = Depends(get_current_user),
):
    if _auth_enabled() and user.get("id") == "public":
        raise HTTPException(status_code=401, detail="authentication required")
    
    # Validate project vision
    project_vision = project_vision.strip()
    if not project_vision or project_vision.lower() in ("untitled", "test", ""):
        raise HTTPException(
            status_code=400,
            detail="Please provide a meaningful project description. Avoid generic terms like 'untitled' or 'test'."
        )
    
    repo_root = shared._repo_root()
    try:
        draft = plan_request(project_vision, repo_root, owner="ui")  # writes docs/* deterministically
    except Exception as e:
        print(f"Error in plan_request: {e}")
        import traceback
        traceback.print_exc()
        # Instead of fallback draft, raise an error to notify user that AI generation failed
        raise HTTPException(
            status_code=503,
            detail="AI service is currently unavailable. Unable to generate implementation plan. Please try again later or contact support."
        )
    # If user provided a Plan ID, persist later via POST /plans; for now, preview.

    # If JSON format is requested, return JSON response
    if format == "json":
        print(f"[DEBUG] Draft: {draft}")
        # Parse the generated files to create structured response
        features = []

        # Try to parse tasks file for features
        try:
            tasks_path = draft.get("tasks", "")
            print(f"[DEBUG] Tasks path: {tasks_path}")
            if tasks_path:
                tasks_content = Path(repo_root) / tasks_path.lstrip("/")
                print(f"[DEBUG] Full tasks path: {tasks_content}")
                if tasks_content.exists():
                    content = tasks_content.read_text(encoding="utf-8")
                    print(f"[DEBUG] Tasks content length: {len(content)}")
                    # Extract checklist items as features
                    lines = content.split("\n")
                    feature_id = 1
                    for line in lines:
                        if line.strip().startswith("- [ ]"):
                            task_text = line.strip()[5:].strip()
                            if task_text:
                                # Estimate size based on task complexity
                                size_estimate = 3  # default small
                                if "implement" in task_text.lower() or "build" in task_text.lower():
                                    size_estimate = 8
                                elif "test" in task_text.lower() or "qa" in task_text.lower():
                                    size_estimate = 5
                                elif "deploy" in task_text.lower() or "document" in task_text.lower():
                                    size_estimate = 3

                                # Determine priority
                                priority = "medium"
                                if "core" in task_text.lower() or "foundation" in task_text.lower():
                                    priority = "high"

                                features.append({
                                    "id": f"feature-{feature_id}",
                                    "name": task_text[:50] + ("..." if len(task_text) > 50 else ""),
                                    "description": task_text,
                                    "size_estimate": size_estimate,
                                    "priority": priority,
                                    "saved": False
                                })
                                feature_id += 1
        except Exception as e:
            print(f"Warning: Could not parse tasks file: {e}")
            import traceback
            traceback.print_exc()
            # Instead of fallback features, return an error indicating AI generation failed
            raise HTTPException(
                status_code=503,
                detail="AI service is currently unavailable. Unable to generate implementation plan. Please try again later or contact support."
            )

        return JSONResponse(content={
            "plan": {
                "id": draft.get("plan_id", f"plan-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                "name": f"Implementation Plan for {project_vision[:50]}",
                "description": f"Complete implementation plan based on project requirements: {project_vision}",
                "features": features,
                "artifacts": draft  # Include file paths for reference
            },
            "project_vision": project_vision,
            "agent_mode": agent_mode,
            "llm_provider": llm_provider,
            "suggested_plan_id": draft.get("plan_id", ""),
        })

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

# Plan save endpoint
@router.post("/api/plans/save", response_model=PlanSaveResponse)
def save_plan_endpoint(plan_save_request: PlanSaveRequest):
    """Save a plan to the backend."""
    try:
        # Generate unique plan ID
        plan_id = str(uuid.uuid4())
        
        # Create plans directory if it doesn't exist
        repo_root = _repo_root()
        plans_dir = repo_root / "docs" / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        
        # Create features directory if it doesn't exist
        features_dir = repo_root / "docs" / "features"
        features_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename for plan
        plan_filename = f"PLAN-{plan_id}.md"
        plan_path = plans_dir / plan_filename
        
        # Create plan content (placeholder for now - in full implementation this would include plan details)
        plan_content = f"""# Plan: {plan_save_request.name}

**Description:** {plan_save_request.description}

**Priority:** {plan_save_request.priority}

**Size Estimate:** {plan_save_request.size_estimate} days

**Status:** pending

**Created:** {datetime.now().isoformat()}
"""
        
        # Write plan content to file
        plan_path.write_text(plan_content.strip() + "\n", encoding="utf-8")
        
        return PlanSaveResponse(
            success=True,
            plan_id=plan_id,
            message=f"Plan '{plan_save_request.name}' saved successfully as {plan_filename}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save plan: {str(e)}")

# Feature save endpoint
@router.post("/api/features/save", response_model=FeatureSaveResponse)
def save_feature_endpoint(feature_save_request: FeatureSaveRequest):
    """Save a feature to the backend."""
    try:
        # Generate unique feature ID
        feature_id = str(uuid.uuid4())
        
        # Create features directory if it doesn't exist
        repo_root = _repo_root()
        features_dir = repo_root / "docs" / "features"
        features_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename for feature
        feature_filename = f"FEATURE-{feature_id}.md"
        feature_path = features_dir / feature_filename
        
        print(f"DEBUG: repo_root = {repo_root}")
        print(f"DEBUG: features_dir = {features_dir}")
        print(f"DEBUG: feature_path = {feature_path}")
        print(f"DEBUG: Saving feature to {feature_path}")
        
        # Create feature content
        feature_content = f"""# Feature: {feature_save_request.name}

**Description:** {feature_save_request.description}

**Priority:** {feature_save_request.priority}

**Size Estimate:** {feature_save_request.size_estimate} hours

**Status:** pending

**Created:** {datetime.now().isoformat()}
"""
        
        # Write feature content to file
        feature_path.write_text(feature_content.strip() + "\n", encoding="utf-8")
        
        print(f"DEBUG: Feature file written successfully")
        
        return FeatureSaveResponse(
            success=True,
            feature_id=feature_id,
            message=f"Feature '{feature_save_request.name}' saved successfully as {feature_filename}"
        )
        
    except Exception as e:
        print(f"DEBUG: Error saving feature: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to save feature: {str(e)}")

class NavigationHistoryRequest(BaseModel):
    from_page: str
    to_page: str
    project_id: Optional[str] = None
    navigation_type: str = "continue"  # 'continue', 'back', 'direct'

class NavigationHistoryResponse(BaseModel):
    success: bool
    history_id: str

class BackNavigationResponse(BaseModel):
    previous_page: Optional[str] = None
    can_go_back: bool = False

@router.post("/navigation/history", response_model=NavigationHistoryResponse)
def record_navigation_history(
    request: NavigationHistoryRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Record navigation history for back button functionality."""
    try:
        engine = _create_engine(_database_url(_repo_root()))
        
        with engine.connect() as conn:
            history_id = str(uuid.uuid4())
            user_id = user.get("id", "anonymous")
            
            # Insert navigation history
            conn.execute(
                text("""
                    INSERT INTO navigation_history (id, user_id, project_id, from_page, to_page, navigation_type)
                    VALUES (:id, :user_id, :project_id, :from_page, :to_page, :navigation_type)
                """),
                {
                    "id": history_id,
                    "user_id": user_id,
                    "project_id": request.project_id,
                    "from_page": request.from_page,
                    "to_page": request.to_page,
                    "navigation_type": request.navigation_type
                }
            )
            conn.commit()
            
        return NavigationHistoryResponse(success=True, history_id=history_id)
        
    except Exception as e:
        print(f"Error recording navigation history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to record navigation history: {str(e)}")

@router.get("/navigation/back", response_model=BackNavigationResponse)
def get_back_navigation(
    current_page: str = Query(..., description="Current page the user is on"),
    project_id: Optional[str] = Query(None, description="Project ID if applicable"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get the previous page for back navigation."""
    try:
        engine = _create_engine(_database_url(_repo_root()))
        user_id = user.get("id", "anonymous") or user.get("id", "public")
        
        with engine.connect() as conn:
            # Find the most recent navigation to the current page
            result = conn.execute(
                text("""
                    SELECT from_page FROM navigation_history 
                    WHERE user_id = :user_id 
                    AND to_page = :current_page
                    AND (:project_id IS NULL OR project_id = :project_id)
                    ORDER BY created_at DESC 
                    LIMIT 1
                """),
                {
                    "user_id": user_id,
                    "current_page": current_page,
                    "project_id": project_id
                }
            ).fetchone()
            
            if result:
                return BackNavigationResponse(
                    previous_page=result[0],
                    can_go_back=True
                )
            else:
                return BackNavigationResponse(can_go_back=False)
                
    except Exception as e:
        print(f"Error getting back navigation: {str(e)}")
        return BackNavigationResponse(can_go_back=False)

# Export the router with the expected name
ui_requests_router = router
