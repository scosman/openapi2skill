"""Tests for parser.py."""

import json
from pathlib import Path

from openapi2skill import parser


def test_parse_endpoints_basic() -> None:
    """Test basic endpoint extraction with all fields."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "description": "Returns all users",
                    "tags": ["Users"],
                    "responses": {"200": {"description": "Success"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)

    assert len(endpoints) == 1
    ep = endpoints[0]
    assert ep.path == "/users"
    assert ep.method == "GET"
    assert ep.summary == "List users"
    assert ep.description == "Returns all users"
    assert ep.tag == "Users"


def test_parse_endpoints_empty_paths() -> None:
    """Test that empty paths returns empty list."""
    spec = {"openapi": "3.0.0", "paths": {}}
    endpoints = parser.parse_endpoints(spec)
    assert endpoints == []


def test_parse_endpoints_missing_summary() -> None:
    """Test fallback to operationId when summary is missing."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "post": {
                    "operationId": "createUser",
                    "responses": {"201": {"description": "Created"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints[0].summary == "createUser"


def test_parse_endpoints_missing_summary_and_operation_id() -> None:
    """Test fallback to METHOD path when both summary and operationId are missing."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users/{id}": {
                "delete": {
                    "responses": {"204": {"description": "Deleted"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints[0].summary == "DELETE /users/{id}"


def test_parse_endpoints_no_tags() -> None:
    """Test that endpoints with no tags get 'Other' as tag."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/health": {
                "get": {
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints[0].tag == "Other"


def test_parse_endpoints_multiple_tags() -> None:
    """Test that only the first tag is used."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "tags": ["Users", "Admin", "Public"],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints[0].tag == "Users"


def test_parse_endpoints_multiple_methods() -> None:
    """Test that all HTTP methods are extracted."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {"summary": "List", "responses": {"200": {}}},
                "post": {"summary": "Create", "responses": {"201": {}}},
                "put": {"summary": "Update", "responses": {"200": {}}},
                "delete": {"summary": "Delete", "responses": {"204": {}}},
                "patch": {"summary": "Partial", "responses": {"200": {}}},
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    methods = {ep.method for ep in endpoints}
    assert methods == {"GET", "POST", "PUT", "DELETE", "PATCH"}


def test_extract_parameters_path_params() -> None:
    """Test extraction of path parameters."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users/{id}": {
                "get": {
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                            "description": "User ID",
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    params = endpoints[0].parameters

    assert len(params) == 1
    assert params[0].name == "id"
    assert params[0].location == "path"
    assert params[0].type == "integer"
    assert params[0].required is True
    assert params[0].description == "User ID"


def test_extract_parameters_query_params_with_default() -> None:
    """Test extraction of query parameters with default value."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "parameters": [
                        {
                            "name": "limit",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer", "default": 20},
                            "description": "Max results",
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    params = endpoints[0].parameters

    assert len(params) == 1
    assert params[0].name == "limit"
    assert params[0].location == "query"
    assert params[0].required is False
    assert params[0].default == "20"


def test_extract_parameters_merge_path_and_operation() -> None:
    """Test that path-level and operation-level params are merged."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users/{id}": {
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer"},
                    }
                ],
                "get": {
                    "parameters": [
                        {
                            "name": "fields",
                            "in": "query",
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
                "delete": {
                    "responses": {"204": {"description": "Deleted"}},
                },
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)

    # GET should have both path and query params
    get_ep = next(e for e in endpoints if e.method == "GET")
    assert len(get_ep.parameters) == 2
    param_names = {p.name for p in get_ep.parameters}
    assert "id" in param_names
    assert "fields" in param_names

    # DELETE should only have path param
    delete_ep = next(e for e in endpoints if e.method == "DELETE")
    assert len(delete_ep.parameters) == 1
    assert delete_ep.parameters[0].name == "id"


def test_extract_parameters_operation_overrides_path() -> None:
    """Test that operation params override path-level params with same name."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users/{id}": {
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                        "description": "Path-level",
                    }
                ],
                "get": {
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                            "description": "Operation-level",
                        }
                    ],
                    "responses": {"200": {"description": "OK"}},
                },
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    params = endpoints[0].parameters

    assert len(params) == 1
    assert params[0].type == "integer"
    assert params[0].description == "Operation-level"


def test_extract_request_body_simple() -> None:
    """Test extraction of simple request body."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {"type": "string"},
                                        "email": {"type": "string"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    rb = endpoints[0].request_body

    assert rb is not None
    assert rb.content_type == "application/json"
    assert len(rb.fields) == 2

    name_field = next(f for f in rb.fields if f.name == "name")
    assert name_field.type == "string"
    assert name_field.required is True


def test_extract_request_body_nested_object() -> None:
    """Test that nested objects are flattened with dot notation."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "address": {
                                            "type": "object",
                                            "properties": {
                                                "street": {"type": "string"},
                                                "city": {"type": "string"},
                                            },
                                        },
                                    },
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    rb = endpoints[0].request_body

    assert rb is not None
    field_names = {f.name for f in rb.fields}
    assert "name" in field_names
    assert "address.street" in field_names
    assert "address.city" in field_names


def test_extract_request_body_with_enum() -> None:
    """Test that enum values are captured in constraints."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "role": {
                                            "type": "string",
                                            "enum": ["admin", "user", "guest"],
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    rb = endpoints[0].request_body
    assert rb is not None

    role_field = rb.fields[0]
    assert "One of: admin, user, guest" in role_field.constraints


def test_extract_request_body_with_example() -> None:
    """Test that examples are extracted from request body."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"},
                                "example": {
                                    "name": "Alice",
                                    "email": "alice@example.com",
                                },
                            }
                        }
                    },
                    "responses": {"201": {"description": "Created"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    rb = endpoints[0].request_body
    assert rb is not None

    assert rb.example == {"name": "Alice", "email": "alice@example.com"}


def test_extract_request_body_none_when_missing() -> None:
    """Test that request body is None when not present."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints[0].request_body is None


def test_extract_responses_simple() -> None:
    """Test extraction of simple response."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                        },
                                    }
                                }
                            },
                        }
                    }
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    responses = endpoints[0].responses

    assert len(responses) == 1
    assert responses[0].status_code == "200"
    assert responses[0].description == "Success"
    assert len(responses[0].fields) == 2


def test_extract_responses_array_type() -> None:
    """Test that array types are rendered correctly."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    }
                                }
                            },
                        }
                    }
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    responses = endpoints[0].responses

    # Array schema produces a single field describing the array
    assert len(responses[0].fields) == 1
    assert responses[0].fields[0].type == "array of string"


def test_extract_responses_multiple_status_codes() -> None:
    """Test extraction of multiple response codes."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "post": {
                    "responses": {
                        "201": {"description": "Created"},
                        "400": {"description": "Bad Request"},
                        "422": {"description": "Validation Error"},
                    }
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    responses = endpoints[0].responses

    assert len(responses) == 3
    status_codes = {r.status_code for r in responses}
    assert status_codes == {"201", "400", "422"}


def test_extract_responses_with_example() -> None:
    """Test that response examples are extracted."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users/{id}": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {"type": "object"},
                                    "example": {"id": 1, "name": "Alice"},
                                }
                            },
                        }
                    }
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    responses = endpoints[0].responses

    assert responses[0].example == {"id": 1, "name": "Alice"}


def test_schema_to_fields_simple_object() -> None:
    """Test schema_to_fields with simple object."""
    schema = {
        "type": "object",
        "required": ["id"],
        "properties": {
            "id": {"type": "integer", "description": "User ID"},
            "name": {"type": "string"},
        },
    }

    fields = parser._schema_to_fields(schema)

    assert len(fields) == 2
    id_field = next(f for f in fields if f.name == "id")
    assert id_field.required is True
    assert id_field.description == "User ID"

    name_field = next(f for f in fields if f.name == "name")
    assert name_field.required is False


def test_schema_to_fields_nested_flattening() -> None:
    """Test that nested objects are flattened with dot notation."""
    schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                        },
                    },
                },
            }
        },
    }

    fields = parser._schema_to_fields(schema)
    field_names = {f.name for f in fields}

    assert "user.name" in field_names
    assert "user.address.city" in field_names


def test_schema_to_fields_depth_limit() -> None:
    """Test that nesting is limited to 3 levels."""
    schema = {
        "type": "object",
        "properties": {
            "level1": {
                "type": "object",
                "properties": {
                    "level2": {
                        "type": "object",
                        "properties": {
                            "level3": {
                                "type": "object",
                                "properties": {
                                    "level4": {"type": "string"},
                                },
                            },
                        },
                    }
                },
            }
        },
    }

    fields = parser._schema_to_fields(schema)
    field_names = {f.name for f in fields}

    # At depth 3, level4 should not be flattened further - level3 becomes "object"
    assert "level1.level2.level3" in field_names
    # level4 should not appear as a separate field
    assert "level1.level2.level3.level4" not in field_names


def test_schema_to_fields_allOf() -> None:
    """Test allOf schema merging."""
    schema = {
        "allOf": [
            {
                "type": "object",
                "required": ["id"],
                "properties": {"id": {"type": "integer"}},
            },
            {
                "type": "object",
                "required": ["name"],
                "properties": {"name": {"type": "string"}},
            },
        ]
    }

    fields = parser._schema_to_fields(schema)

    assert len(fields) == 2
    field_names = {f.name for f in fields}
    assert "id" in field_names
    assert "name" in field_names

    # Check required is merged
    id_field = next(f for f in fields if f.name == "id")
    name_field = next(f for f in fields if f.name == "name")
    assert id_field.required is True
    assert name_field.required is True


def test_schema_to_fields_oneOf() -> None:
    """Test oneOf schema handling."""
    schema = {
        "oneOf": [
            {"type": "string"},
            {"type": "integer"},
        ]
    }

    fields = parser._schema_to_fields(schema)

    assert len(fields) == 1
    assert "one of: string, integer" in fields[0].type


def test_schema_to_fields_anyOf() -> None:
    """Test anyOf schema handling."""
    schema = {
        "anyOf": [
            {"type": "string"},
            {"type": "null"},
        ]
    }

    fields = parser._schema_to_fields(schema)

    assert len(fields) == 1
    assert "one of: string, null" in fields[0].type


def test_schema_to_fields_enum() -> None:
    """Test enum constraint extraction."""
    schema = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["active", "inactive", "pending"],
            }
        },
    }

    fields = parser._schema_to_fields(schema)
    status_field = fields[0]

    assert "One of: active, inactive, pending" in status_field.constraints


def test_render_type_simple() -> None:
    """Test rendering of simple types."""
    assert parser._render_type({"type": "string"}) == "string"
    assert parser._render_type({"type": "integer"}) == "integer"
    assert parser._render_type({"type": "number"}) == "number"
    assert parser._render_type({"type": "boolean"}) == "boolean"


def test_render_type_array() -> None:
    """Test rendering of array types."""
    schema = {"type": "array", "items": {"type": "string"}}
    assert parser._render_type(schema) == "array of string"

    schema = {"type": "array", "items": {"type": "integer"}}
    assert parser._render_type(schema) == "array of integer"


def test_render_type_array_of_objects() -> None:
    """Test rendering of array of objects."""
    schema = {
        "type": "array",
        "items": {"type": "object", "properties": {"id": {"type": "integer"}}},
    }
    assert parser._render_type(schema) == "array of object"


def test_render_type_oneOf() -> None:
    """Test rendering of oneOf types."""
    schema = {
        "oneOf": [
            {"type": "string"},
            {"type": "integer"},
        ]
    }
    assert parser._render_type(schema) == "one of: string, integer"


def test_render_type_allOf() -> None:
    """Test rendering of allOf types."""
    schema = {
        "allOf": [
            {"type": "object", "properties": {"id": {"type": "integer"}}},
            {"type": "object", "properties": {"name": {"type": "string"}}},
        ]
    }
    assert parser._render_type(schema) == "object"


def test_group_by_tag_basic() -> None:
    """Test basic tag grouping returns TagGroup objects."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {"tags": ["Users"], "responses": {"200": {}}},
                "post": {"tags": ["Users"], "responses": {"201": {}}},
            },
            "/products": {
                "get": {"tags": ["Products"], "responses": {"200": {}}},
            },
        },
    }

    endpoints = parser.parse_endpoints(spec)
    grouped = parser.group_by_tag(endpoints, spec)

    assert len(grouped) == 2
    tags = [g.name for g in grouped]
    assert "Users" in tags
    assert "Products" in tags
    # Check that TagGroup objects have correct attributes
    assert all(hasattr(g, "name") for g in grouped)
    assert all(hasattr(g, "description") for g in grouped)
    assert all(hasattr(g, "endpoints") for g in grouped)


def test_group_by_tag_spec_tag_order() -> None:
    """Test that spec-defined tags come first in order."""
    spec = {
        "openapi": "3.0.0",
        "tags": [
            {"name": "Admin"},
            {"name": "Users"},
        ],
        "paths": {
            "/users": {
                "get": {"tags": ["Users"], "responses": {"200": {}}},
            },
            "/admin": {
                "get": {"tags": ["Admin"], "responses": {"200": {}}},
            },
        },
    }

    endpoints = parser.parse_endpoints(spec)
    grouped = parser.group_by_tag(endpoints, spec)

    # Admin should come first per spec tag order
    assert grouped[0].name == "Admin"
    assert grouped[1].name == "Users"


def test_group_by_tag_other_last() -> None:
    """Test that 'Other' group comes last."""
    spec = {
        "openapi": "3.0.0",
        "tags": [{"name": "Users"}],
        "paths": {
            "/users": {
                "get": {"tags": ["Users"], "responses": {"200": {}}},
            },
            "/health": {
                "get": {"responses": {"200": {}}},  # No tags
            },
        },
    }

    endpoints = parser.parse_endpoints(spec)
    grouped = parser.group_by_tag(endpoints, spec)

    assert grouped[-1].name == "Other"


def test_group_by_tag_adhoc_tags_after_spec_tags() -> None:
    """Test that ad-hoc tags appear after spec-defined tags."""
    spec = {
        "openapi": "3.0.0",
        "tags": [{"name": "Users"}],
        "paths": {
            "/users": {
                "get": {"tags": ["Users"], "responses": {"200": {}}},
            },
            "/products": {
                "get": {"tags": ["Products"], "responses": {"200": {}}},
            },
        },
    }

    endpoints = parser.parse_endpoints(spec)
    grouped = parser.group_by_tag(endpoints, spec)

    # Users (spec-defined) comes first, Products (ad-hoc) comes second
    assert grouped[0].name == "Users"
    assert grouped[1].name == "Products"


def test_group_by_tag_endpoints_per_group() -> None:
    """Test that correct endpoints are in each group."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {"tags": ["Users"], "responses": {"200": {}}},
                "post": {"tags": ["Users"], "responses": {"201": {}}},
            },
            "/products": {
                "get": {"tags": ["Products"], "responses": {"200": {}}},
            },
        },
    }

    endpoints = parser.parse_endpoints(spec)
    grouped = parser.group_by_tag(endpoints, spec)

    users_group = next(g for g in grouped if g.name == "Users")
    products_group = next(g for g in grouped if g.name == "Products")

    assert len(users_group.endpoints) == 2
    assert len(products_group.endpoints) == 1


def test_group_by_tag_with_description() -> None:
    """Test that tag descriptions are extracted from spec."""
    spec = {
        "openapi": "3.0.0",
        "tags": [
            {"name": "Users", "description": "User management operations"},
            {"name": "Products", "description": "Product catalog"},
        ],
        "paths": {
            "/users": {
                "get": {"tags": ["Users"], "responses": {"200": {}}},
            },
            "/products": {
                "get": {"tags": ["Products"], "responses": {"200": {}}},
            },
        },
    }

    endpoints = parser.parse_endpoints(spec)
    grouped = parser.group_by_tag(endpoints, spec)

    users_group = next(g for g in grouped if g.name == "Users")
    products_group = next(g for g in grouped if g.name == "Products")

    assert users_group.description == "User management operations"
    assert products_group.description == "Product catalog"


def test_group_by_tag_without_description() -> None:
    """Test that tags without descriptions have empty string."""
    spec = {
        "openapi": "3.0.0",
        "tags": [{"name": "Users"}],  # No description
        "paths": {
            "/users": {
                "get": {"tags": ["Users"], "responses": {"200": {}}},
            },
        },
    }

    endpoints = parser.parse_endpoints(spec)
    grouped = parser.group_by_tag(endpoints, spec)

    assert grouped[0].description == ""


def test_group_by_tag_adhoc_without_description() -> None:
    """Test that ad-hoc tags (not in spec tags array) have empty description."""
    spec = {
        "openapi": "3.0.0",
        "tags": [{"name": "Users", "description": "User ops"}],
        "paths": {
            "/users": {
                "get": {"tags": ["Users"], "responses": {"200": {}}},
            },
            "/products": {
                "get": {"tags": ["Products"], "responses": {"200": {}}},  # Ad-hoc tag
            },
        },
    }

    endpoints = parser.parse_endpoints(spec)
    grouped = parser.group_by_tag(endpoints, spec)

    products_group = next(g for g in grouped if g.name == "Products")
    assert products_group.description == ""


def test_parse_sample_spec() -> None:
    """Test parsing the sample spec fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_spec.json"
    spec = json.loads(fixture_path.read_text())

    endpoints = parser.parse_endpoints(spec)

    assert len(endpoints) == 3

    # Check GET /users
    get_users = next(e for e in endpoints if e.path == "/users" and e.method == "GET")
    assert get_users.summary == "List all users"
    assert get_users.tag == "Users"
    assert len(get_users.responses) == 1
    assert get_users.responses[0].status_code == "200"

    # Check POST /users
    post_users = next(e for e in endpoints if e.path == "/users" and e.method == "POST")
    assert post_users.summary == "Create a user"
    assert post_users.request_body is not None

    # Check GET /users/{id}
    get_user_by_id = next(
        e for e in endpoints if e.path == "/users/{id}" and e.method == "GET"
    )
    assert get_user_by_id.summary == "Get user by ID"
    assert len(get_user_by_id.parameters) == 1
    assert get_user_by_id.parameters[0].name == "id"


def test_group_sample_spec() -> None:
    """Test grouping the sample spec fixture."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_spec.json"
    spec = json.loads(fixture_path.read_text())

    endpoints = parser.parse_endpoints(spec)
    grouped = parser.group_by_tag(endpoints, spec)

    assert len(grouped) == 1
    assert grouped[0].name == "Users"
    assert len(grouped[0].endpoints) == 3


def test_extract_constraints_enum() -> None:
    """Test enum constraint extraction."""
    schema = {"type": "string", "enum": ["a", "b", "c"]}
    constraints = parser._extract_constraints(schema)
    assert "One of: a, b, c" in constraints


def test_extract_constraints_format() -> None:
    """Test format constraint extraction."""
    schema = {"type": "string", "format": "email"}
    constraints = parser._extract_constraints(schema)
    assert "Format: email" in constraints


def test_extract_constraints_min_max() -> None:
    """Test min/max constraint extraction."""
    schema = {"type": "integer", "minimum": 0, "maximum": 100}
    constraints = parser._extract_constraints(schema)
    assert "Min: 0" in constraints
    assert "Max: 100" in constraints


def test_extract_constraints_string_length() -> None:
    """Test string length constraint extraction."""
    schema = {"type": "string", "minLength": 1, "maxLength": 100}
    constraints = parser._extract_constraints(schema)
    assert "Min length: 1" in constraints
    assert "Max length: 100" in constraints


def test_extract_constraints_pattern() -> None:
    """Test pattern constraint extraction."""
    schema = {"type": "string", "pattern": "^[a-z]+$"}
    constraints = parser._extract_constraints(schema)
    assert "Pattern: ^[a-z]+$" in constraints


def test_extract_constraints_multiple() -> None:
    """Test multiple constraints are combined."""
    schema = {
        "type": "string",
        "enum": ["admin", "user"],
        "minLength": 1,
    }
    constraints = parser._extract_constraints(schema)
    assert "One of: admin, user" in constraints
    assert "Min length: 1" in constraints


def test_empty_summary_uses_operation_id() -> None:
    """Test that empty summary falls back to operationId."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "summary": "",  # Empty string
                    "operationId": "listUsers",
                    "responses": {"200": {}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints[0].summary == "listUsers"


def test_empty_description_is_empty_string() -> None:
    """Test that missing description is empty string."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": {
                    "summary": "List users",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints[0].description == ""


def test_path_item_not_dict_is_skipped() -> None:
    """Test that non-dict path items are skipped."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": "not a dict",
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints == []


def test_operation_not_dict_is_skipped() -> None:
    """Test that non-dict operations are skipped."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "get": "not a dict",
            },
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints == []


def test_response_without_content() -> None:
    """Test response without content has no fields."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/users": {
                "delete": {
                    "responses": {
                        "204": {"description": "No content"},
                    }
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)
    assert endpoints[0].responses[0].fields == []
