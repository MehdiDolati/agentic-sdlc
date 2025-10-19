from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Create database engine and session
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost/agentic")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Import the full implementations from repos.py
import importlib.util
import sys
import os

# Load the repos.py module directly
repos_path = os.path.join(os.path.dirname(__file__), '..', 'repos.py')
spec = importlib.util.spec_from_file_location("repos", repos_path)
repos_module = importlib.util.module_from_spec(spec)
sys.modules["services.api.core.repos_module"] = repos_module
spec.loader.exec_module(repos_module)

# Re-export the classes and functions
PlansRepoDB = repos_module.PlansRepoDB
NotesRepoDB = repos_module.NotesRepoDB
RunsRepoDB = repos_module.RunsRepoDB
ProjectsRepoDB = repos_module.ProjectsRepoDB
InteractionHistoryRepoDB = repos_module.InteractionHistoryRepoDB
ensure_plans_schema = repos_module.ensure_plans_schema
ensure_runs_schema = repos_module.ensure_runs_schema
ensure_notes_schema = repos_module.ensure_notes_schema
ensure_projects_schema = repos_module.ensure_projects_schema

from .agent_template import AgentTemplateRepository
from .repository import RepositoryRepository as RepositoriesRepoDB
from .agents import AgentsRepoDB, AgentRunsRepoDB

__all__ = [
    'AgentTemplateRepository',
    'PlansRepoDB',
    'NotesRepoDB',
    'RunsRepoDB',
    'ProjectsRepoDB',
    'InteractionHistoryRepoDB',
    'ensure_plans_schema',
    'ensure_runs_schema',
    'ensure_notes_schema',
    'ensure_projects_schema',
    'RepositoriesRepoDB',
    'AgentsRepoDB',
    'AgentRunsRepoDB'
]