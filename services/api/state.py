from typing import Dict, Any
import sys

# One in-memory store per resource name
DBS: Dict[str, Dict[str, Any]] = {}

# Ensure both names resolve to the same module object
_self = sys.modules[__name__]
sys.modules.setdefault("state", _self)
sys.modules.setdefault("services.api.state", _self)
