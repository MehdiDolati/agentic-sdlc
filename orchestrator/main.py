import yaml, json
from pathlib import Path
def load_yaml(p):
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
def main():
    root = Path(__file__).resolve().parents[1]
    stack = load_yaml(root / "configs" / "STACK_CONFIG.yaml")
    team = load_yaml(root / "configs" / "TEAM_PROFILE.yaml")
    runtime = load_yaml(root / "configs" / "runtime-config.yaml")
    summary = {
        "stack_languages": stack.get("languages"),
        "profile": team.get("name"),
        "runtime_stack": runtime.get("stack"),
    }
    print(json.dumps(summary, indent=2))
if __name__ == "__main__":
    main()
