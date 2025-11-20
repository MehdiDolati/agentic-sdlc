import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from services.api.llm_selector import get_llm_for_project
from services.api.llm import get_llm_from_env

# Test with a sample project_id
print('Testing LLM selection...')
print(f'LLM_PROVIDER env: {os.getenv("LLM_PROVIDER", "(not set)")}')
print(f'SUPABASE_URL env: {os.getenv("SUPABASE_URL", "(not set)")}')
print(f'SUPABASE_ANON_KEY env: {"SET" if os.getenv("SUPABASE_ANON_KEY") else "(not set)"}')

llm_env = get_llm_from_env()
print(f'\nget_llm_from_env() returns: {type(llm_env).__name__ if llm_env else None}')

# Try with a test project_id
try:
    llm_project = get_llm_for_project('test-project-123', 'prd_generation')
    print(f'get_llm_for_project() returns: {type(llm_project).__name__ if llm_project else None}')
except Exception as e:
    print(f'get_llm_for_project() error: {e}')
