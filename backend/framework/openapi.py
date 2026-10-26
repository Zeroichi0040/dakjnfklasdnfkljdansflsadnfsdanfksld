"""The API specification is generated from the live resource registry."""


def specification(resources):
    def response(description, schema=None):
        value = {"description": description}
        if schema:
            value["content"] = {"application/json": {"schema": schema}}
        return value

    def body(schema):
        return {"required": True, "content": {"application/json": {"schema": schema}}}

    csrf = {
        "name": "X-CSRFToken",
        "in": "header",
        "required": True,
        "schema": {"type": "string"},
        "description": "Fetch /api/v1/csrf with the same session cookie. Sign-in returns a new token.",
    }
    errors = {str(k): {"$ref": "#/components/responses/Error"} for k in (400, 401, 403, 404, 409, 415, 422, 429)}
    paths = {
        "/api/v1/csrf": {
            "get": {
                "security": [],
                "summary": "Get CSRF token",
                "responses": {
                    "200": response("Token", {"type": "object", "properties": {"csrf_token": {"type": "string"}}})
                },
            }
        },
        "/api/v1/auth/login": {
            "post": {
                "security": [],
                "summary": "Sign in",
                "parameters": [csrf],
                "requestBody": body(
                    {
                        "type": "object",
                        "required": ["email", "password"],
                        "properties": {
                            "email": {"type": "string", "format": "email"},
                            "password": {"type": "string", "maxLength": 128},
                        },
                    }
                ),
                "responses": {
                    "200": response(
                        "User and rotated CSRF token",
                        {
                            "type": "object",
                            "properties": {"user": {"type": "object"}, "csrf_token": {"type": "string"}},
                        },
                    ),
                    **errors,
                },
            }
        },
        "/api/v1/auth/logout": {
            "post": {
                "summary": "Sign out",
                "parameters": [csrf],
                "responses": {"204": response("Session cleared"), **errors},
            }
        },
        "/api/v1/me": {
            "get": {
                "summary": "Current account",
                "responses": {"200": response("Account", {"type": "object"}), **errors},
            }
        },
        "/api/v1/resources": {
            "get": {
                "summary": "Resources accessible to the current account",
                "responses": {"200": response("Resource catalog", {"type": "object"}), **errors},
            }
        },
        "/api/v1/files": {
            "get": {
                "summary": "List owned images",
                "responses": {"200": response("Paginated images", {"type": "object"}), **errors},
            },
            "post": {
                "summary": "Upload a verified private image",
                "parameters": [csrf],
                "requestBody": {
                    "required": True,
                    "content": {
                        "multipart/form-data": {
                            "schema": {
                                "type": "object",
                                "required": ["file"],
                                "properties": {"file": {"type": "string", "format": "binary"}},
                            }
                        }
                    },
                },
                "responses": {"201": response("Created image", {"type": "object"}), **errors},
            },
        },
        "/api/v1/files/{file_id}": {
            "delete": {
                "summary": "Delete an owned image",
                "parameters": [
                    csrf,
                    {"name": "file_id", "in": "path", "required": True, "schema": {"type": "string", "format": "uuid"}},
                ],
                "responses": {"204": response("Deleted"), **errors},
            }
        },
    }
    schemas = {}
    for resource in resources:
        properties, required = {}, []
        for field in resource.fields:
            kind = field.kind
            definition = {
                "type": "boolean" if kind == "boolean" else "integer" if kind == "integer" else "string",
                "description": field.help or field.label,
            }
            if kind in {"text", "textarea", "email", "url", "choice"}:
                definition["maxLength"] = field.max_length
            if kind == "date":
                definition["format"] = "date"
            if kind == "email":
                definition["format"] = "email"
            if kind == "url":
                definition["format"] = "uri"
            if kind == "decimal":
                definition["description"] += " (decimal string with at most 2 decimal places)"
            if kind == "choice":
                definition["enum"] = [x[0] for x in field.choices]
            if field.pattern:
                definition["pattern"] = field.pattern
            if not field.required and kind in {"date", "integer", "decimal"}:
                definition["type"] = [definition["type"], "null"]
            if field.required:
                required.append(field.name)
            properties[field.name] = definition
        version = {"type": "integer", "minimum": 1}
        schemas[resource.key + "Create"] = {
            "type": "object",
            "additionalProperties": False,
            "required": required,
            "properties": properties,
        }
        schemas[resource.key + "Update"] = {
            "type": "object",
            "additionalProperties": False,
            "required": ["version"],
            "properties": {**properties, "version": version},
        }
        record = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "properties": {
                        **properties,
                        "id": {"type": "integer"},
                        "version": version,
                        "created_at": {"type": "string", "format": "date-time"},
                        "updated_at": {"type": "string", "format": "date-time"},
                    },
                }
            },
        }
        base = "/api/v1/" + resource.key
        params = [
            {"name": "page", "in": "query", "schema": {"type": "integer", "minimum": 1, "default": 1}},
            {
                "name": "per_page",
                "in": "query",
                "schema": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
            },
            {"name": "q", "in": "query", "schema": {"type": "string", "maxLength": 120}},
            {"name": "sort", "in": "query", "schema": {"type": "string", "default": "-id"}},
        ]
        paths[base] = {
            "get": {
                "summary": "List " + resource.label,
                "description": "Authorization policy: " + resource.policy.name,
                "parameters": params,
                "responses": {
                    "200": response(
                        "Paginated records",
                        {
                            "type": "object",
                            "properties": {
                                "data": {"type": "array", "items": record["properties"]["data"]},
                                "pagination": {"type": "object"},
                            },
                        },
                    ),
                    **errors,
                },
            },
            "post": {
                "summary": "Create " + resource.singular,
                "parameters": [csrf],
                "requestBody": body({"$ref": "#/components/schemas/" + resource.key + "Create"}),
                "responses": {"201": response("Created record", record), **errors},
            },
        }
        paths[base + "/{record_id}"] = {
            "parameters": [
                {"name": "record_id", "in": "path", "required": True, "schema": {"type": "integer", "minimum": 1}}
            ],
            "get": {
                "summary": "Get " + resource.singular,
                "responses": {"200": response("Record and version ETag", record), **errors},
            },
            "patch": {
                "summary": "Update " + resource.singular,
                "parameters": [csrf],
                "requestBody": body({"$ref": "#/components/schemas/" + resource.key + "Update"}),
                "responses": {"200": response("Updated record", record), **errors},
            },
            "delete": {
                "summary": "Permanently delete " + resource.singular,
                "parameters": [csrf],
                "requestBody": body(
                    {
                        "type": "object",
                        "required": ["version"],
                        "additionalProperties": False,
                        "properties": {"version": version},
                    }
                ),
                "responses": {"204": response("Deleted"), **errors},
            },
        }
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Flask Fullstack Framework API",
            "version": "3.0.0",
            "description": "Generated from the configured resources. Same-origin session authentication and CSRF; no CORS wildcard.",
        },
        "servers": [{"url": "/"}],
        "security": [{"sessionCookie": []}],
        "paths": paths,
        "components": {
            "securitySchemes": {"sessionCookie": {"type": "apiKey", "in": "cookie", "name": "session"}},
            "schemas": schemas,
            "responses": {
                "Error": response(
                    "Request error",
                    {
                        "type": "object",
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "integer"},
                                    "message": {"type": "string"},
                                    "fields": {"type": "object"},
                                    "request_id": {"type": "string"},
                                },
                            }
                        },
                    },
                )
            },
        },
    }
