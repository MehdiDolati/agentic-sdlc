# Interaction History Enhancement: Agent and Step Tracking

## Overview
This document describes the enhancement to the interaction history system that tracks which agent and SDLC step each conversation happened in.

## Problem Statement
Previously, the `interaction_history` table only tracked:
- What was asked (prompt)
- What was answered (response)
- Which project it belonged to

**Missing information:**
- Which agent (tool/AI model) was used for the conversation?
- At which SDLC step did this conversation occur?

## Solution: Unified Agent Model

### 1. New `agents` Table

```sql
CREATE TABLE agents (
    id SERIAL PRIMARY KEY,
    agent_type TEXT NOT NULL UNIQUE,      -- 'supabase', 'architect', 'qa', 'dev', etc.
    agent_name TEXT NOT NULL,              -- Human-readable name
    description TEXT,                      -- What this agent does
    is_builtin BOOLEAN DEFAULT false,      -- true for built-in (Supabase), false for project-specific
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

**Key insight:** Supabase AI is now treated as a built-in agent, eliminating the need to distinguish between "Supabase chat" and "custom agents" in the UI layer.

**Built-in agents:**
- `supabase` - Supabase AI (always available)

**Project-specific agents:**
These are linked to `project_agents` table and represent custom agents per project:
- `architect` - Architecture discussion agent
- `qa` - QA planning agent
- `dev` - Development agent
- etc.

### 2. Enhanced `interaction_history` Table

**New columns:**

```python
agent_id: Optional[int]           # FK to agents.id
step: Optional[str]               # SDLC phase: 'requirements', 'architecture', 'planning', 'development', 'testing'
agent_type: Optional[str]         # Denormalized for quick access without joining
```

**Example records:**

```
project_id: 'proj-123'
agent_id: 1                       # Supabase agent
agent_type: 'supabase'
step: 'requirements'
prompt: "What are the main features?"
response: "Based on the project..."
---
project_id: 'proj-123'
agent_id: 2                       # Project-specific architect agent
agent_type: 'architect'
step: 'architecture'
prompt: "How should we structure the database?"
response: "I recommend..."
```

## Usage in Code

### Recording Chat History

```python
from services.api.models import InteractionHistoryCreate

# When saving interaction from Supabase AI
interaction = InteractionHistoryCreate(
    project_id=project_id,
    agent_id=1,  # Supabase agent ID
    agent_type='supabase',
    step='requirements',
    prompt=user_message,
    response=ai_response,
    role='assistant'
)

# When saving interaction from project-specific agent
interaction = InteractionHistoryCreate(
    project_id=project_id,
    agent_id=agent_db.id,  # ID from agents or project_agents table
    agent_type='architect',
    step='architecture',
    prompt=user_message,
    response=ai_response,
    role='assistant'
)
```

### Querying Chat History

```python
# Get all conversations for a project at a specific SDLC step
query = select(_HISTORY_TABLE).where(
    and_(
        _HISTORY_TABLE.c.project_id == project_id,
        _HISTORY_TABLE.c.step == 'architecture'
    )
)

# Get all conversations with a specific agent
query = select(_HISTORY_TABLE).where(
    and_(
        _HISTORY_TABLE.c.project_id == project_id,
        _HISTORY_TABLE.c.agent_type == 'supabase'
    )
)

# Get conversation timeline (all interactions in order)
query = select(_HISTORY_TABLE).where(
    _HISTORY_TABLE.c.project_id == project_id
).order_by(_HISTORY_TABLE.c.created_at)
```

## Benefits

1. **Unified tracking:** No special handling needed for Supabase vs custom agents
2. **Clear audit trail:** Know exactly which agent and step each conversation belongs to
3. **Better analytics:** Can track which agents/steps are most used
4. **Future-proof:** Easy to add new agent types or SDLC phases
5. **Denormalization:** `agent_type` column allows quick filtering without joins
6. **Backwards compatible:** Both columns are nullable for existing data

## SDLC Steps Reference

Standard SDLC steps that can be tracked:
- `requirements` - Gathering and defining requirements
- `architecture` - System design and architecture discussions
- `planning` - Project planning and breakdown
- `development` - Development phase conversations
- `testing` - Testing and QA discussions
- `deployment` - Deployment planning
- `maintenance` - Post-launch maintenance

## Migration Path

1. Migration `013_add_interaction_tracking.sql` creates:
   - `agents` table
   - Inserts built-in Supabase agent
   - Adds columns to `interaction_history`

2. Update routes and services to include `agent_id` and `step` when recording interactions

3. Existing `interaction_history` records will have `NULL` values for new columns (graceful degradation)

## Indexes for Performance

Created indexes on:
- `agents.agent_type` - For quick agent lookups
- `interaction_history.agent_id` - For filtering by agent
- `interaction_history.step` - For filtering by SDLC phase
- `interaction_history.project_id, step` - For per-project per-step queries
- `interaction_history.project_id, agent_id` - For per-project per-agent queries
