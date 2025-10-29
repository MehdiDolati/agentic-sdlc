# Database Schema: Interaction History Enhancement

## Entity Relationship Diagram

```
┌─────────────────────┐         ┌──────────────────┐
│    interaction_     │         │   agents         │
│     history         │◄────────│  (new table)     │
├─────────────────────┤         ├──────────────────┤
│ id (PK)             │         │ id (PK)          │
│ project_id (FK)     │────────►│ agent_type       │
│ agent_id (FK) ◄─────┼─────────┤ agent_name       │
│ step                │         │ description      │
│ agent_type          │         │ is_builtin       │
│ prompt              │         │ created_at       │
│ response            │         │ updated_at       │
│ role                │         └──────────────────┘
│ metadata            │
│ created_at          │
└─────────────────────┘
         ▲
         │ (project_id FK)
         │
    ┌────┴─────────────┐
    │   projects       │
    ├──────────────────┤
    │ id (PK)          │
    │ name             │
    │ description      │
    │ ...              │
    └──────────────────┘
```

## Table Definitions

### agents (NEW)

```
Column              Type        Constraints
─────────────────────────────────────────────
id                  SERIAL      PRIMARY KEY
agent_type          TEXT        NOT NULL, UNIQUE
agent_name          TEXT        NOT NULL
description         TEXT        
is_builtin          BOOLEAN     DEFAULT false
created_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
updated_at          TIMESTAMP   DEFAULT CURRENT_TIMESTAMP
```

**Purpose:** Central registry of all agents in the system (built-in and project-specific).

**Built-in agents:**
| agent_type | agent_name   | is_builtin |
|------------|-------------|-----------|
| supabase   | Supabase AI | true      |

### interaction_history (MODIFIED)

**Original columns:**
```
id          STRING      PRIMARY KEY
project_id  STRING      (FK to projects)
prompt      STRING      NOT NULL
response    STRING      NOT NULL
role        STRING      (user, assistant)
metadata    JSON
created_at  TIMESTAMP
```

**New columns added:**
```
agent_id    INTEGER     (FK to agents.id) NULLABLE
step        STRING      (requirements, architecture, planning, etc.) NULLABLE
agent_type  STRING      (denormalized from agents.agent_type) NULLABLE
```

## Data Flow Examples

### Recording a Supabase AI Conversation

```
1. User asks question in Requirements phase
2. System calls Supabase AI API
3. Store in interaction_history with:
   - agent_id: 1 (Supabase agent)
   - agent_type: 'supabase'
   - step: 'requirements'
   - prompt: user's question
   - response: Supabase AI response
```

### Recording a Project-Specific Agent Conversation

```
1. Project has custom "architect" agent
2. User asks architecture question
3. System identifies agent from project context
4. Store in interaction_history with:
   - agent_id: 2 (custom architect agent)
   - agent_type: 'architect'
   - step: 'architecture'
   - prompt: user's question
   - response: agent's response
```

## Query Patterns

### Find all Supabase conversations in a project

```sql
SELECT * FROM interaction_history
WHERE project_id = 'proj-123'
  AND agent_type = 'supabase'
ORDER BY created_at DESC;
```

### Find all conversations in architecture phase

```sql
SELECT * FROM interaction_history
WHERE project_id = 'proj-123'
  AND step = 'architecture'
ORDER BY created_at DESC;
```

### Find which agent handled planning phase

```sql
SELECT DISTINCT agent_type, COUNT(*) as conversation_count
FROM interaction_history
WHERE project_id = 'proj-123'
  AND step = 'planning'
GROUP BY agent_type;
```

### Get timeline of all project conversations

```sql
SELECT 
    created_at,
    agent_type,
    step,
    prompt,
    response
FROM interaction_history
WHERE project_id = 'proj-123'
ORDER BY created_at;
```

## Indexes

Created for performance optimization:

```sql
CREATE INDEX idx_agents_type 
    ON agents(agent_type);

CREATE INDEX idx_interaction_history_agent_id 
    ON interaction_history(agent_id);

CREATE INDEX idx_interaction_history_step 
    ON interaction_history(step);

CREATE INDEX idx_interaction_history_project_step 
    ON interaction_history(project_id, step);

CREATE INDEX idx_interaction_history_project_agent 
    ON interaction_history(project_id, agent_id);
```

## Backwards Compatibility

- New columns in `interaction_history` are **NULLABLE**
- Existing records automatically have `NULL` values for `agent_id`, `step`, `agent_type`
- No data loss during migration
- UI can gracefully handle missing agent information
- Queries can filter by `agent_id IS NOT NULL` to exclude legacy data if needed
