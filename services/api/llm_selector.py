"""
Helper functions for LLM client selection based on project settings.
"""
from typing import Optional
import os
from services.api.llm import get_llm_from_env, SupabaseLLM, LLMClient
from fastapi import HTTPException


def get_llm_for_project(project_id: str, step_name: str = "story_generation") -> LLMClient:
    """
    Get the appropriate LLM client based on project settings.
    
    Args:
        project_id: The project ID
        step_name: The SDLC step name (e.g., "story_generation", "prd_generation", "architecture")
    
    Returns:
        LLMClient instance configured for the project
        
    Raises:
        HTTPException: If no LLM is configured
    """
    from services.api.core.repos.project import ProjectRepository
    from services.api.core.repos.project_agent import ProjectAgentRepository
    from services.api.core.shared import _create_engine, _database_url, _repo_root
    
    # Get project settings
    engine = _create_engine(_database_url(_repo_root()))
    project_repo = ProjectRepository(engine)
    
    try:
        # Try to get project by ID (could be int or string UUID)
        try:
            # First try as int
            proj_id = int(project_id)
            project = project_repo.get(proj_id)
        except ValueError:
            # If not an int, try as string (UUID)
            project = project_repo.get_by_id_or_name(project_id)
        
        if not project:
            raise ValueError(f"Project {project_id} not found")
    except Exception as e:
        # Project not found or error, fall back to env-based LLM
        print(f"[LLM] Error getting project {project_id}: {e}, falling back to env-based LLM")
        return _get_env_llm_or_raise()
    
    # Check if project wants to use Supabase LLM
    use_supabase = getattr(project, 'use_supabase_llm', True)
    
    if use_supabase:
        # Use Supabase LLM from backend
        supabase_url = os.getenv("SUPABASE_URL", "").strip()
        supabase_key = os.getenv("SUPABASE_ANON_KEY", "").strip()
        
        if supabase_url and supabase_key:
            print(f"[LLM] Using Supabase LLM for project {project_id}")
            return SupabaseLLM(supabase_url, supabase_key)
        else:
            # Supabase not configured, fall back to env-based
            print(f"[LLM] Supabase not configured, falling back to env-based LLM")
            return _get_env_llm_or_raise()
    else:
        # Use custom agents from project_agents table
        agent_repo = ProjectAgentRepository(engine)
        
        try:
            agents = agent_repo.list_by_project(project_id, step_key=step_name)
            
            if agents:
                # Found project-specific agent for this step
                agent = agents[0]  # Use first matching agent
                print(f"[LLM] Using project agent: {agent.name} for step {step_name}")
                
                # Get agent configuration and create appropriate LLM client
                config = getattr(agent, 'config', {})
                provider = config.get('provider', '').lower()
                
                if provider == 'openai':
                    from services.api.llm import OpenAIChatLLM
                    return OpenAIChatLLM(
                        api_key=config.get('api_key') or os.getenv("OPENAI_API_KEY", ""),
                        model=config.get('model', 'gpt-4o-mini')
                    )
                elif provider == 'anthropic':
                    from services.api.llm import AnthropicMessagesLLM
                    return AnthropicMessagesLLM(
                        api_key=config.get('api_key') or os.getenv("ANTHROPIC_API_KEY", ""),
                        model=config.get('model', 'claude-3-5-sonnet-latest')
                    )
                elif provider == 'supabase':
                    supabase_url = config.get('supabase_url') or os.getenv("SUPABASE_URL", "")
                    supabase_key = config.get('supabase_key') or os.getenv("SUPABASE_ANON_KEY", "")
                    return SupabaseLLM(supabase_url, supabase_key)
                else:
                    # Unknown provider, fall back to env
                    print(f"[LLM] Unknown provider {provider}, falling back to env-based LLM")
                    return _get_env_llm_or_raise()
            else:
                # No agent assigned for this step, fall back to env-based LLM
                print(f"[LLM] No agent assigned for step {step_name}, falling back to env-based LLM")
                return _get_env_llm_or_raise()
                
        except Exception as e:
            print(f"[LLM] Error getting project agents: {e}, falling back to env-based LLM")
            return _get_env_llm_or_raise()


def _get_env_llm_or_raise() -> LLMClient:
    """Get LLM from environment or raise HTTPException."""
    llm_client = get_llm_from_env()
    
    if not llm_client:
        raise HTTPException(
            status_code=503,
            detail="LLM service is not configured. Please set LLM_PROVIDER environment variable (openai, anthropic, supabase, or ollama) and the corresponding API key, or configure project-specific agents."
        )
    
    return llm_client
