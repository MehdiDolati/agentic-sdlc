-- Backfill step_key for existing project_agents based on their description
-- The description follows the pattern "Agent assigned to {step_name} step"

UPDATE project_agents 
SET step_key = 'requirement_gathering'
WHERE step_key IS NULL 
  AND (description LIKE '%requirement_gathering%' OR type = 'requirements');

UPDATE project_agents 
SET step_key = 'architecture_design'
WHERE step_key IS NULL 
  AND (description LIKE '%architecture_design%' OR type = 'architect');

UPDATE project_agents 
SET step_key = 'planner'
WHERE step_key IS NULL 
  AND (description LIKE '%planner%' OR type = 'planner');

UPDATE project_agents 
SET step_key = 'dev_coder'
WHERE step_key IS NULL 
  AND (description LIKE '%dev_coder%' OR type = 'developer' OR type = 'dev');

UPDATE project_agents 
SET step_key = 'reviewer'
WHERE step_key IS NULL 
  AND (description LIKE '%reviewer%' OR type = 'qa' OR type = 'reviewer');

UPDATE project_agents 
SET step_key = 'tester'
WHERE step_key IS NULL 
  AND (description LIKE '%tester%' OR type = 'tester' OR type = 'qa');

-- For any remaining NULL step_keys, try to extract from description
-- This handles the pattern "Agent assigned to {step_name} step"
UPDATE project_agents
SET step_key = CASE
    WHEN description LIKE '%requirement_gathering step%' THEN 'requirement_gathering'
    WHEN description LIKE '%architecture_design step%' THEN 'architecture_design'
    WHEN description LIKE '%planner step%' THEN 'planner'
    WHEN description LIKE '%dev_coder step%' THEN 'dev_coder'
    WHEN description LIKE '%reviewer step%' THEN 'reviewer'
    WHEN description LIKE '%tester step%' THEN 'tester'
    ELSE 'general'
END
WHERE step_key IS NULL;
