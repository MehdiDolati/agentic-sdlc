from services.api.planner.openapi_gen import generate_openapi


def test_generate_minimal_openapi_happy_path():
    blueprint = {
        "info": {
            "title": "Planner API",
            "version": "0.1.0",
            "description": "Generated from PRD",
        },
        "schemas": {
            "Plan": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                },
                "required": ["id", "title"],
                "additionalProperties": False,
            }
        },
        "security_schemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        },
        "default_security": ["bearerAuth"],
        "paths": [
            {
                "path": "/plans",
                "method": "get",
                "summary": "List plans",
                "tags": ["plans"],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Plan"},
                                }
                            }
                        },
                    }
                },
            },
            {
                "path": "/plans",
                "method": "post",
                "summary": "Create plan",
                "request": {
                    "contentType": "application/json",
                    "schema": {"$ref": "#/components/schemas/Plan"},
                },
                "responses": {
                    "201": {"description": "Created"}
                },
                "security": ["bearerAuth"],
            },
        ],
        "servers": [{"url": "https://api.example.com"}],
    }

    spec = generate_openapi(blueprint)

    assert spec["openapi"].startswith("3.1")
    assert spec["info"]["title"] == "Planner API"
    assert "description" in spec["info"]

    # Schemas
    assert "Plan" in spec["components"]["schemas"]

    # Security
    assert "bearerAuth" in spec["components"]["securitySchemes"]
    assert {"bearerAuth": []} in spec.get("security", [])

    # Paths & operations
    assert "/plans" in spec["paths"]
    get_op = spec["paths"]["/plans"]["get"]
    post_op = spec["paths"]["/plans"]["post"]

    assert get_op["responses"]["200"]["content"]["application/json"]["schema"]["items"]["$ref"] == "#/components/schemas/Plan"
    assert "requestBody" in post_op
    assert post_op["responses"]["201"]["description"] == "Created"
    assert {"bearerAuth": []} in post_op["security"]


def test_generate_openapi_validation_errors():
    # missing info.version
    bad = {
        "info": {"title": "X"},
        "paths": [{"path": "/x", "method": "get", "responses": {"200": {"description": "ok"}}}],
    }
    import pytest
    with pytest.raises(ValueError):
        generate_openapi(bad)

    # empty paths
    bad2 = {
        "info": {"title": "X", "version": "1"},
        "paths": [],
    }
    with pytest.raises(ValueError):
        generate_openapi(bad2)

    # invalid method
    bad3 = {
        "info": {"title": "X", "version": "1"},
        "paths": [{"path": "/x", "method": "FOO", "responses": {"200": {"description": "ok"}}}],
    }
    with pytest.raises(ValueError):
        generate_openapi(bad3)
