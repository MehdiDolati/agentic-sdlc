from __future__ import annotations

from typing import Any, Mapping, MutableMapping, Dict, List
from pathlib import Path


ALLOWED_METHODS = {"get", "put", "post", "delete", "patch", "options", "head"}


def _slugify_operation_id(method: str, path: str) -> str:
    # e.g. GET /plans/{id}  -> get_plans_id
    core = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    return f"{method.lower()}_{core or 'root'}"


def _ensure_dict(d: Any, name: str) -> Dict[str, Any]:
    if not isinstance(d, dict):
        raise ValueError(f"{name} must be an object")
    return d


def _ensure_list(v: Any, name: str) -> List[Any]:
    if not isinstance(v, list):
        raise ValueError(f"{name} must be a list")
    return v


def generate_openapi(blueprint: Mapping[str, Any]) -> Dict[str, Any]:
    """
    Build a minimal OpenAPI 3.1 document from a simple PRD/blueprint dict.

    Expected blueprint shape (loose, validated as used):

    {
      "info": {"title": "...", "version": "1.0.0", "description": "..."},
      "schemas": { "Plan": { ... JSON Schema ... }, ... },
      "security_schemes": { "bearerAuth": {"type":"http","scheme":"bearer","bearerFormat":"JWT"}, ... },
      "default_security": ["bearerAuth"],    # optional – list of scheme names
      "paths": [
        {
          "path": "/plans",
          "method": "get",
          "summary": "List plans",
          "tags": ["plans"],
          "operationId": "listPlans",        # optional, auto-slugged if omitted
          "request": {                       # optional; turned into requestBody
            "contentType": "application/json",
            "schema": { "type":"object", ... }
          },
          "requestBody": {...},              # alternatively pass OpenAPI requestBody as-is
          "responses": {                     # OpenAPI-style responses object
            "200": {
              "description": "OK",
              "content": {
                "application/json": {
                  "schema": {"type":"array","items":{"$ref":"#/components/schemas/Plan"}}
                }
              }
            }
          },
          "security": ["bearerAuth"]        # optional per-op security override
        },
        ...
      ],
      "servers": [{"url": "https://api.example.com"}]  # optional
    }
    """
    bp = _ensure_dict(blueprint, "blueprint")

    info = _ensure_dict(bp.get("info", {}), "info")
    title = info.get("title")
    version = info.get("version")
    if not title or not version:
        raise ValueError("info.title and info.version are required")

    spec: Dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": title,
            "version": version,
        },
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {},
        },
    }

    if "description" in info and info["description"]:
        spec["info"]["description"] = info["description"]

    # Servers (optional)
    servers = bp.get("servers")
    if servers:
        _ensure_list(servers, "servers")
        spec["servers"] = servers

    # Schemas -> components.schemas (pass-through JSON Schema)
    for name, schema in _ensure_dict(bp.get("schemas", {}), "schemas").items():
        spec["components"]["schemas"][name] = schema

    # Security schemes
    security_schemes = _ensure_dict(bp.get("security_schemes", {}), "security_schemes")
    if security_schemes:
        spec["components"]["securitySchemes"] = security_schemes

    default_security = bp.get("default_security") or []
    if default_security:
        _ensure_list(default_security, "default_security")
        # Convert list of scheme names -> list of requirement objects
        spec["security"] = [{name: []} for name in default_security]

    # Paths
    paths_def = _ensure_list(bp.get("paths", []), "paths")
    if not paths_def:
        raise ValueError("paths must contain at least one route")

    for route in paths_def:
        route = _ensure_dict(route, "paths[*]")
        path = route.get("path")
        method = (route.get("method") or "").lower()
        if not path or method not in ALLOWED_METHODS:
            raise ValueError(f"Invalid route: path='{path}' method='{method}'")

        op: Dict[str, Any] = {
            "responses": _ensure_dict(route.get("responses", {}), "responses"),
        }
        if not op["responses"]:
            raise ValueError(f"Route {method.upper()} {path} must define responses")

        if "summary" in route:
            op["summary"] = route["summary"]
        if "tags" in route:
            op["tags"] = _ensure_list(route["tags"], "tags")
        op["operationId"] = route.get("operationId") or _slugify_operation_id(method, path)

        # Request (either simplified "request" or full "requestBody")
        if "requestBody" in route and route["requestBody"]:
            op["requestBody"] = _ensure_dict(route["requestBody"], "requestBody")
        elif "request" in route and route["request"]:
            req = _ensure_dict(route["request"], "request")
            ct = req.get("contentType") or "application/json"
            schema_obj = _ensure_dict(req.get("schema", {}), "request.schema")
            op["requestBody"] = {
                "required": True,
                "content": {
                    ct: {"schema": schema_obj}
                }
            }

        # Per-operation security (optional)
        if "security" in route and route["security"] is not None:
            names = _ensure_list(route["security"], "security")
            op["security"] = [{n: []} for n in names]

        # Install into paths
        if path not in spec["paths"]:
            spec["paths"][path] = {}
        spec["paths"][path][method] = op

    return spec
