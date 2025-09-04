#!/usr/bin/env bash
set -euo pipefail
echo "Bootstrapping local dev..."
python3 -m venv .venv && source .venv/bin/activate
pip install -r orchestrator/requirements.txt
pip install -r services/api/requirements.txt
echo "Done. Try: uvicorn services.api.app:app --reload"
