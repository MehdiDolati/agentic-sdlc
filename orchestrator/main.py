import yaml, json, sys
from pathlib import Path

def load_yaml(p):
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def main():
    root = Path(__file__).resolve().parents[1]
    stack = load_yaml(root / "configs" / "STACK_CONFIG.yaml")
    team = load_yaml(root / "configs" / "TEAM_PROFILE.yaml")
    runtime = load_yaml(root / "configs" / "runtime-config.yaml")
    registry = load_yaml(root / "orchestrator" / "registry.yaml")
    capabilities = load_yaml(root / "orchestrator" / "capability_graph.yaml")

    summary = {
        "stack_languages": stack.get("languages"),
        "profile": team.get("name"),
        "runtime_stack": runtime.get("stack"),
        "agents_configured": list(registry.get("agents", {}).keys()),
        "tasks_supported": list(capabilities.get("tasks", {}).keys())
    }
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
