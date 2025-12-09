from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
import re
from pydantic import BaseModel

from services.api.core.shared import _repo_root
from services.api.auth.routes import get_current_user

router = APIRouter(prefix="/api/documents", tags=["documents"])

class DocumentStatus(BaseModel):
    """Document status for a project."""
    prd: bool = False
    architecture: bool = False
    userStories: bool = False
    apis: bool = False
    plans: bool = False
    adr: bool = False

def parse_tech_document(content: str) -> Dict[str, Any]:
    """Parse technology stack document and extract structured data."""
    tech_stack = {
        "frontend": [],
        "backend": [],
        "database": [],
        "infrastructure": []
    }
    
    try:
        # Extract Backend section
        backend_match = re.search(r'#### 2\.1\. Backend(.*?)(?=####|$)', content, re.DOTALL)
        if backend_match:
            backend_section = backend_match.group(1)
            # Extract technologies mentioned with bold markers
            languages = re.findall(r'\*\*([^*]+?)\*\*', backend_section)
            tech_stack["backend"] = [lang for lang in languages if lang and not lang.startswith('Rationale')][:5]
        
        # Extract Frontend section
        frontend_match = re.search(r'#### 2\.2\. Frontend(.*?)(?=####|$)', content, re.DOTALL)
        if frontend_match:
            frontend_section = frontend_match.group(1)
            languages = re.findall(r'\*\*([^*]+?)\*\*', frontend_section)
            tech_stack["frontend"] = [lang for lang in languages if lang and not lang.startswith('Rationale')][:5]
        
        # Extract Database section
        database_match = re.search(r'#### 2\.3\. Database(.*?)(?=####|$)', content, re.DOTALL)
        if database_match:
            database_section = database_match.group(1)
            databases = re.findall(r'\*\*([^*]+?)\*\*', database_section)
            tech_stack["database"] = [db for db in databases if db and not db.startswith('Rationale')][:5]
        
        # Extract Infrastructure section
        infra_match = re.search(r'#### 2\.[4-9]\. (?:Infrastructure|Deployment|DevOps)(.*?)(?=####|$)', content, re.DOTALL)
        if infra_match:
            infra_section = infra_match.group(1)
            infra_items = re.findall(r'\*\*([^*]+?)\*\*', infra_section)
            tech_stack["infrastructure"] = [item for item in infra_items if item and not item.startswith('Rationale')][:5]
    
    except Exception as e:
        print(f"Error parsing tech document: {e}")
    
    return tech_stack

@router.get("/{project_id}/tech")
def get_tech_document(
    project_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get parsed technology stack from project's tech document."""
    try:
        repo_root = _repo_root()
        tech_dir = repo_root / "docs" / "tech"
        
        if not tech_dir.exists():
            raise HTTPException(status_code=404, detail="Tech documents directory not found")
        
        # Look for tech document for this project
        tech_files = list(tech_dir.glob(f"*{project_id}*.md"))
        
        if not tech_files:
            raise HTTPException(status_code=404, detail="Tech document not found for this project")
        
        # Use the first matching file
        tech_file = tech_files[0]
        
        with open(tech_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the document
        tech_stack = parse_tech_document(content)

        # Return both the parsed structure and the raw content so frontends
        # can display the raw doc when the parser couldn't extract structured items.
        return {"parsed": tech_stack, "raw": content}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read tech document: {str(e)}")

def _check_plan_exists(project_id: str) -> bool:
    """Check if a plan exists for the project in the database."""
    try:
        from services.api.core.shared import _create_engine, _database_url, _repo_root
        from sqlalchemy import text
        
        engine = _create_engine(_database_url(_repo_root()))
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT COUNT(*) FROM plans WHERE project_id = :project_id"),
                {"project_id": project_id}
            )
            count = result.scalar()
            print(f"[_check_plan_exists] Found {count} plans for project {project_id}")
            return count > 0
    except Exception as e:
        print(f"[_check_plan_exists] Error checking plans for project {project_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

@router.get("/{project_id}/status", response_model=DocumentStatus)
def get_document_status(
    project_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get document status for a project - which documents exist."""
    try:
        repo_root = _repo_root()
        
        # Main document directories to check
        docs_dirs = [
            repo_root / "docs",
            repo_root / "data" / "docs"
        ]
        
        # Document type mappings to directory/file patterns
        doc_patterns = {
            "prd": ["prd"],
            "architecture": ["tech", "architecture"], 
            "userStories": ["stories", "features"],
            "apis": ["api", "openapi"],
            "plans": ["plans"],
            "adr": ["adr"]
        }
        
        status = DocumentStatus()
        
        # Check each document type
        for doc_type, patterns in doc_patterns.items():
            found = False
            
            # Special handling for plans - check database first
            if doc_type == "plans":
                found = _check_plan_exists(project_id)
            
            # If not found, check filesystem
            if not found:
                for docs_dir in docs_dirs:
                    if found:
                        break
                    
                    if not docs_dir.exists():
                        continue
                        
                    # Check each pattern directory
                    for pattern in patterns:
                        try:
                            pattern_dir = docs_dir / pattern
                            if pattern_dir.exists() and pattern_dir.is_dir():
                                # Look for project-specific files
                                files = list(pattern_dir.glob("*"))
                                for file_path in files:
                                    if file_path.is_file() and file_path.suffix in ['.md', '.txt', '.json', '.yaml', '.yml']:
                                        file_name_lower = file_path.name.lower()
                                        
                                        # Check if file contains project ID
                                        if project_id.lower() in file_name_lower:
                                            found = True
                                            break
                                
                                if found:
                                    break
                        except Exception as e:
                            continue
                    
                    if found:
                        break
            
            # Set the status for this document type
            setattr(status, doc_type, found)
        
        return status
        
    except Exception as e:
        print(f"Error checking document status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check document status: {str(e)}")
