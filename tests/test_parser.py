"""Tests for parser.py."""

import json
from pathlib import Path

from openapi2skill import parser
from openapi2skill.models import Field


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

    # Top-level array responses carry their type on `body_type` instead of
    # synthesizing a phantom `value` field. The old phantom-field behavior
    # made the generated doc claim the response was `{"value": [...]}` when
    # on the wire it was a bare array.
    assert responses[0].fields == []
    assert responses[0].body_type == "array of string"


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
    """Test anyOf schema handling with null variant."""
    schema = {
        "anyOf": [
            {"type": "string"},
            {"type": "null"},
        ]
    }

    fields = parser._schema_to_fields(schema)

    assert len(fields) == 1
    assert "one of: string or null" in fields[0].type
    assert fields[0].required is False


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


def test_extract_constraints_min_max_range() -> None:
    """Test min/max constraint uses compact range notation."""
    schema = {"type": "integer", "minimum": 0, "maximum": 100}
    constraints = parser._extract_constraints(schema)
    assert constraints == "0-100"


def test_extract_constraints_min_only() -> None:
    """Test minimum-only constraint."""
    schema = {"type": "integer", "minimum": 0}
    constraints = parser._extract_constraints(schema)
    assert constraints == ">=0"


def test_extract_constraints_max_only() -> None:
    """Test maximum-only constraint."""
    schema = {"type": "integer", "maximum": 100}
    constraints = parser._extract_constraints(schema)
    assert constraints == "<=100"


def test_extract_constraints_string_length_range() -> None:
    """Test string length constraint uses compact range notation."""
    schema = {"type": "string", "minLength": 1, "maxLength": 64}
    constraints = parser._extract_constraints(schema)
    assert constraints == "1-64 chars"


def test_extract_constraints_min_length_only() -> None:
    """Test minLength-only constraint."""
    schema = {"type": "string", "minLength": 1}
    constraints = parser._extract_constraints(schema)
    assert constraints == ">=1 chars"


def test_extract_constraints_max_length_only() -> None:
    """Test maxLength-only constraint."""
    schema = {"type": "string", "maxLength": 255}
    constraints = parser._extract_constraints(schema)
    assert constraints == "<=255 chars"


def test_extract_constraints_pattern() -> None:
    """Test pattern constraint uses backticks."""
    schema = {"type": "string", "pattern": "^[a-z]+$"}
    constraints = parser._extract_constraints(schema)
    assert constraints == "Pattern: `^[a-z]+$`"


def test_extract_constraints_multiple() -> None:
    """Test multiple constraints are combined."""
    schema = {
        "type": "string",
        "enum": ["admin", "user"],
        "minLength": 1,
    }
    constraints = parser._extract_constraints(schema)
    assert "One of: admin, user" in constraints
    assert ">=1 chars" in constraints


def test_extract_constraints_float_range() -> None:
    """Test float min/max uses compact range notation."""
    schema = {"type": "number", "minimum": 0.0, "maximum": 1.0}
    constraints = parser._extract_constraints(schema)
    assert constraints == "0.0-1.0"


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


def test_schema_collector_basic() -> None:
    """Test basic schema registration and retrieval."""
    collector = parser.SchemaCollector()

    fields = [
        Field(name="id", type="integer", required=True, description="", constraints="")
    ]
    name = collector.register("User", "A user", fields)

    assert name == "User"
    assert len(collector.schemas) == 1
    assert collector.schemas[0].name == "User"
    assert collector.schemas[0].description == "A user"


def test_schema_collector_dedup_identical() -> None:
    """Test that identical schemas return the same name."""
    collector = parser.SchemaCollector()

    fields1 = [
        Field(name="id", type="integer", required=True, description="", constraints="")
    ]
    fields2 = [
        Field(name="id", type="integer", required=True, description="", constraints="")
    ]

    name1 = collector.register("User", "A user", fields1)
    name2 = collector.register("User", "Another user", fields2)

    assert name1 == name2
    assert len(collector.schemas) == 1


def test_schema_collector_conflict_different() -> None:
    """Test that different schemas with same name get V2 suffix."""
    collector = parser.SchemaCollector()

    fields1 = [
        Field(name="id", type="integer", required=True, description="", constraints="")
    ]
    fields2 = [
        Field(name="id", type="string", required=True, description="", constraints="")
    ]

    name1 = collector.register("User", "User v1", fields1)
    name2 = collector.register("User", "User v2", fields2)

    assert name1 == "User"
    assert name2 == "UserV2"
    assert len(collector.schemas) == 2


def test_schema_collector_fingerprint_order_independent() -> None:
    """Test that same fields in different order produce same fingerprint."""
    collector = parser.SchemaCollector()

    fields1 = [
        Field(name="a", type="integer", required=True, description="", constraints=""),
        Field(name="b", type="string", required=False, description="", constraints=""),
    ]
    fields2 = [
        Field(name="b", type="string", required=False, description="", constraints=""),
        Field(name="a", type="integer", required=True, description="", constraints=""),
    ]

    name1 = collector.register("Schema1", "", fields1)
    name2 = collector.register("Schema2", "", fields2)

    assert name1 == name2


def test_derive_schema_name_from_ref() -> None:
    """Test that x-schema-name is preferred."""
    schema = {"x-schema-name": "TaskMetadata", "type": "object"}
    name = parser._derive_schema_name(schema, "some_field")
    assert name == "TaskMetadata"


def test_derive_schema_name_from_field() -> None:
    """Test snake_case to PascalCase conversion."""
    assert (
        parser._derive_schema_name({}, "questions_and_answers") == "QuestionsAndAnswers"
    )
    assert parser._derive_schema_name({}, "task_metadata") == "TaskMetadata"
    assert parser._derive_schema_name({}, "data_by_topic") == "DataByTopic"


def test_endpoint_has_schemas_field() -> None:
    """Test that Endpoint has schemas field initialized to empty list."""
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
    assert hasattr(endpoints[0], "schemas")
    assert endpoints[0].schemas == []


def test_should_create_schema_with_properties() -> None:
    """Test _should_create_schema returns True for schema with properties."""
    schema = {"type": "object", "properties": {"id": {"type": "integer"}}}
    assert parser._should_create_schema(schema) is True


def test_should_create_schema_with_x_schema_name() -> None:
    """Test _should_create_schema returns True for schema with x-schema-name."""
    schema = {"x-schema-name": "User", "type": "object"}
    assert parser._should_create_schema(schema) is True


def test_should_create_schema_array_with_object_items() -> None:
    """Test _should_create_schema returns True for array with object items."""
    schema = {
        "type": "array",
        "items": {"type": "object", "properties": {"id": {"type": "integer"}}},
    }
    assert parser._should_create_schema(schema) is True


def test_should_create_schema_bare_object() -> None:
    """Test _should_create_schema returns False for bare object without properties."""
    schema = {"type": "object"}
    assert parser._should_create_schema(schema) is False


def test_should_create_schema_empty_properties() -> None:
    """Test _should_create_schema returns False for object with empty properties."""
    schema = {"type": "object", "properties": {}}
    assert parser._should_create_schema(schema) is False


def test_should_create_schema_null_type() -> None:
    """Test _should_create_schema returns False for null type."""
    schema = {"type": "null"}
    assert parser._should_create_schema(schema) is False


def test_render_type_with_schema_object() -> None:
    """Test _render_type_with_schema for object type."""
    schema = {"type": "object"}
    assert parser._render_type_with_schema(schema, "User") == "User"


def test_render_type_with_schema_array() -> None:
    """Test _render_type_with_schema for array type."""
    schema = {"type": "array", "items": {"type": "object"}}
    assert parser._render_type_with_schema(schema, "User") == "array of User"


def test_schema_to_fields_with_collector_named_ref() -> None:
    """Test schema with x-schema-name registers schema and uses name in type."""
    collector = parser.SchemaCollector()
    schema = {
        "type": "object",
        "x-schema-name": "TaskMetadata",
        "description": "Task metadata",
        "properties": {"id": {"type": "integer"}},
    }

    fields = parser._schema_to_fields(schema, "", 0, collector)

    assert len(fields) == 1
    assert fields[0].name == "id"
    assert len(collector.schemas) == 0  # Root schema is not registered, only nested


def test_schema_to_fields_with_collector_inline_object() -> None:
    """Test inline object at depth limit gets PascalCase name from field name."""
    collector = parser.SchemaCollector()
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
                                "description": "Deep nested object",
                                "properties": {"value": {"type": "string"}},
                            }
                        },
                    }
                },
            }
        },
    }

    _ = parser._schema_to_fields(schema, "", 0, collector)

    assert len(collector.schemas) == 1
    assert collector.schemas[0].name == "Level3"


def test_schema_to_fields_array_of_objects() -> None:
    """Test array of objects produces 'array of SchemaName' type."""
    collector = parser.SchemaCollector()
    schema = {
        "type": "array",
        "description": "List of Q&A items",
        "items": {
            "type": "object",
            "properties": {
                "question": {"type": "string"},
                "answer": {"type": "string"},
            },
        },
    }

    fields = parser._schema_to_fields(schema, "questions_and_answers", 0, collector)

    assert len(collector.schemas) == 1
    assert collector.schemas[0].name == "QuestionsAndAnswers"
    assert fields[0].type == "array of QuestionsAndAnswers"


def test_schema_to_fields_transitive() -> None:
    """Test schema A referencing schema B includes both in collector."""
    collector = parser.SchemaCollector()
    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "x-schema-name": "User",
            "properties": {
                "name": {"type": "string"},
                "addresses": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "x-schema-name": "Address",
                        "properties": {
                            "city": {"type": "string"},
                            "zip": {"type": "string"},
                        },
                    },
                },
            },
        },
    }

    parser._schema_to_fields(schema, "", 0, collector)

    schema_names = {s.name for s in collector.schemas}
    assert "User" in schema_names
    assert "Address" in schema_names


def test_schema_to_fields_no_properties_object() -> None:
    """Test bare object without properties stays as 'object', no schema created."""
    collector = parser.SchemaCollector()
    schema = {
        "type": "object",
        "properties": {
            "metadata": {"type": "object", "description": "Free-form metadata"}
        },
    }

    fields = parser._schema_to_fields(schema, "", 0, collector)

    assert len(collector.schemas) == 0
    metadata_field = next(f for f in fields if f.name == "metadata")
    assert metadata_field.type == "object"


def test_schema_to_fields_oneof_with_object_variants() -> None:
    """Test oneOf with object variants registers each variant schema."""
    collector = parser.SchemaCollector()
    schema = {
        "oneOf": [
            {
                "x-schema-name": "SuccessResult",
                "type": "object",
                "properties": {"data": {"type": "string"}},
            },
            {
                "x-schema-name": "ErrorResult",
                "type": "object",
                "properties": {"error": {"type": "string"}},
            },
            {"type": "null"},
        ]
    }

    fields = parser._schema_to_fields(schema, "", 0, collector)

    schema_names = {s.name for s in collector.schemas}
    assert "SuccessResult" in schema_names
    assert "ErrorResult" in schema_names
    assert "SuccessResult" in fields[0].type
    assert "ErrorResult" in fields[0].type


def test_schema_to_fields_without_collector() -> None:
    """Test passing collector=None produces existing behavior."""
    schema = {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {"type": "object", "properties": {"id": {"type": "integer"}}},
            }
        },
    }

    fields = parser._schema_to_fields(schema, "", 0, None)

    assert len(fields) == 1
    assert fields[0].type == "array of object"


def test_extract_endpoint_with_schemas() -> None:
    """Test full endpoint extraction produces schemas."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/tasks": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "task_metadata": {
                                            "type": "object",
                                            "properties": {
                                                "priority": {"type": "integer"}
                                            },
                                        }
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)

    assert len(endpoints[0].schemas) >= 1
    schema_names = {s.name for s in endpoints[0].schemas}
    assert "TaskMetadata" in schema_names or "Item" in schema_names


def test_extract_request_body_uses_collector() -> None:
    """Test request body schemas are collected."""
    collector = parser.SchemaCollector()
    request_body = {
        "content": {
            "application/json": {
                "schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    },
                }
            }
        }
    }

    parser._extract_request_body(request_body, collector)

    assert len(collector.schemas) == 1
    assert collector.schemas[0].name == "Item"


def test_extract_responses_uses_collector() -> None:
    """Test response schemas are collected."""
    collector = parser.SchemaCollector()
    responses = {
        "200": {
            "description": "Success",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"id": {"type": "integer"}},
                        },
                    }
                }
            },
        }
    }

    parser._extract_responses(responses, collector)

    assert len(collector.schemas) == 1
    assert collector.schemas[0].name == "Item"


def test_schema_dedup_across_request_and_response() -> None:
    """Test identical schemas in request and response are deduplicated."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/items": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                        },
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Success",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "name": {"type": "string"},
                                            },
                                        },
                                    }
                                }
                            },
                        }
                    },
                }
            }
        },
    }

    endpoints = parser.parse_endpoints(spec)

    assert len(endpoints[0].schemas) == 1
    assert endpoints[0].schemas[0].name == "Item"


def test_oneof_with_null_variant_nullable() -> None:
    """Test oneOf with null variant marks field as nullable (not required)."""
    schema = {
        "oneOf": [
            {"type": "string"},
            {"type": "null"},
        ]
    }

    fields = parser._schema_to_fields(schema)

    assert len(fields) == 1
    assert "one of: string or null" in fields[0].type
    assert fields[0].required is False


def test_oneof_with_object_and_null_variants() -> None:
    """Test oneOf with object variant and null creates schema and marks nullable."""
    collector = parser.SchemaCollector()
    schema = {
        "oneOf": [
            {
                "type": "object",
                "x-schema-name": "Source",
                "properties": {"url": {"type": "string"}},
            },
            {"type": "null"},
        ]
    }

    fields = parser._schema_to_fields(schema, "source", 0, collector)

    assert len(collector.schemas) == 1
    assert collector.schemas[0].name == "Source"
    assert "Source" in fields[0].type
    assert "or null" in fields[0].type
    assert fields[0].required is False


def test_oneof_multiple_object_variants_registers_schemas() -> None:
    """Test oneOf with multiple object variants registers each as a schema."""
    collector = parser.SchemaCollector()
    schema = {
        "oneOf": [
            {
                "type": "object",
                "x-schema-name": "TextContent",
                "properties": {"text": {"type": "string"}},
            },
            {
                "type": "object",
                "x-schema-name": "ImageContent",
                "properties": {"url": {"type": "string"}},
            },
            {
                "type": "object",
                "x-schema-name": "VideoContent",
                "properties": {"video_url": {"type": "string"}},
            },
        ]
    }

    fields = parser._schema_to_fields(schema, "content", 0, collector)

    schema_names = {s.name for s in collector.schemas}
    assert "TextContent" in schema_names
    assert "ImageContent" in schema_names
    assert "VideoContent" in schema_names
    assert "TextContent" in fields[0].type
    assert "ImageContent" in fields[0].type
    assert "VideoContent" in fields[0].type


def test_oneof_inline_object_variants_derives_names() -> None:
    """Test oneOf with inline object variants derives names from field prefix."""
    collector = parser.SchemaCollector()
    schema = {
        "oneOf": [
            {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "const": "success"},
                    "data": {"type": "string"},
                },
            },
            {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "const": "error"},
                    "message": {"type": "string"},
                },
            },
        ]
    }

    fields = parser._schema_to_fields(schema, "result.", 0, collector)

    assert len(collector.schemas) == 2
    schema_names = {s.name for s in collector.schemas}
    assert "Result" in schema_names
    assert fields[0].required is True


def test_oneof_null_only_returns_any() -> None:
    """Test oneOf with only null variant returns 'any or null'."""
    schema = {
        "oneOf": [
            {"type": "null"},
        ]
    }

    fields = parser._schema_to_fields(schema)

    assert len(fields) == 1
    assert fields[0].type == "any or null"
    assert fields[0].required is False


def test_render_type_oneof_with_null() -> None:
    """Test _render_type handles null in oneOf correctly."""
    schema = {
        "oneOf": [
            {"type": "string"},
            {"type": "null"},
        ]
    }
    assert parser._render_type(schema) == "one of: string or null"


def test_nested_oneof_in_object_property() -> None:
    """Test oneOf nested inside object property expands object variant."""
    collector = parser.SchemaCollector()
    schema = {
        "type": "object",
        "properties": {
            "output": {
                "oneOf": [
                    {
                        "type": "object",
                        "x-schema-name": "Source",
                        "properties": {"url": {"type": "string"}},
                    },
                    {"type": "null"},
                ]
            }
        },
    }

    fields = parser._schema_to_fields(schema, "", 0, collector)

    assert len(collector.schemas) == 1
    assert collector.schemas[0].name == "Source"
    output_field = next(f for f in fields if f.name == "output")
    assert "Source" in output_field.type
    assert "or null" in output_field.type


def test_oneof_with_resolved_refs_registers_named_schemas():
    """Test that resolved $ref variants in oneOf get proper schema names."""
    from openapi2skill.resolver import resolve_refs
    from openapi2skill.parser import _schema_to_fields, SchemaCollector

    spec = {
        "components": {
            "schemas": {
                "KilnAgentRunConfigProperties": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "temperature": {"type": "number"},
                    },
                },
                "McpRunConfigProperties": {
                    "type": "object",
                    "properties": {
                        "server_url": {"type": "string"},
                        "timeout": {"type": "integer"},
                    },
                },
            }
        },
        "paths": {
            "/test": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "oneOf": [
                                        {
                                            "$ref": "#/components/schemas/KilnAgentRunConfigProperties"
                                        },
                                        {
                                            "$ref": "#/components/schemas/McpRunConfigProperties"
                                        },
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        },
    }

    resolved = resolve_refs(spec)

    schema = resolved["paths"]["/test"]["post"]["requestBody"]["content"][
        "application/json"
    ]["schema"]

    collector = SchemaCollector()
    fields = _schema_to_fields(schema, "", 0, collector)

    assert len(fields) == 1
    field_type = fields[0].type
    assert "object, object" not in field_type, f"Got: {field_type}"
    assert "KilnAgentRunConfigProperties" in field_type, f"Got: {field_type}"
    assert "McpRunConfigProperties" in field_type, f"Got: {field_type}"
    assert len(collector.schemas) == 2


def test_nested_oneof_field_in_object_registers_schemas():
    """Test that oneOf field inside an object registers variant schemas."""
    from openapi2skill.resolver import resolve_refs
    from openapi2skill.parser import _schema_to_fields, SchemaCollector

    spec = {
        "components": {
            "schemas": {
                "TaskRunConfig": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "run_config_properties": {
                            "oneOf": [
                                {
                                    "$ref": "#/components/schemas/KilnAgentRunConfigProperties"
                                },
                                {"$ref": "#/components/schemas/McpRunConfigProperties"},
                            ]
                        },
                    },
                },
                "KilnAgentRunConfigProperties": {
                    "type": "object",
                    "properties": {"model": {"type": "string"}},
                },
                "McpRunConfigProperties": {
                    "type": "object",
                    "properties": {"server_url": {"type": "string"}},
                },
            }
        }
    }

    resolved = resolve_refs(spec)
    schema = resolved["components"]["schemas"]["TaskRunConfig"]

    collector = SchemaCollector()
    fields = _schema_to_fields(schema, "", 0, collector)

    prop_field = next((f for f in fields if f.name == "run_config_properties"), None)
    assert prop_field is not None

    assert "object, object" not in prop_field.type, f"Got: {prop_field.type}"
    assert "KilnAgentRunConfigProperties" in prop_field.type, f"Got: {prop_field.type}"
    assert "McpRunConfigProperties" in prop_field.type, f"Got: {prop_field.type}"

    schema_names = [s.name for s in collector.schemas]
    assert "KilnAgentRunConfigProperties" in schema_names
    assert "McpRunConfigProperties" in schema_names


# ---------------------------------------------------------------------------
# Regression tests for the "named non-object schema wrapper" bug.
#
# Pydantic `RootModel` list wrappers and `Enum` classes arrive in the OpenAPI
# spec as named schemas (via `x-schema-name`) on non-object types (array,
# string, integer). The old renderer synthesized a phantom `{value: ...}`
# schema around them, so the generated doc claimed e.g. `GET /specs` returned
# `{"value": [...]}` and `ModelProviderName` was `{"value": string}` — when on
# the wire both serialize transparently (bare array / bare string). Consumers
# (human or LLM) then wrote jq filters like `.value[]` and `.priority.value`
# that fail at runtime.
# ---------------------------------------------------------------------------


def test_top_level_array_response_uses_body_type_not_phantom_value_field() -> None:
    """`list[Spec]` response should say `array of Spec`, not `{value: array of Spec}`."""
    spec = {
        "openapi": "3.0.0",
        "paths": {
            "/specs": {
                "get": {
                    "responses": {
                        "200": {
                            "description": "OK",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "x-schema-name": "Specs",
                                        "items": {
                                            "type": "object",
                                            "x-schema-name": "Spec",
                                            "properties": {
                                                "id": {"type": "string"},
                                                "name": {"type": "string"},
                                            },
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
    response = endpoints[0].responses[0]

    assert response.fields == []
    assert response.body_type == "array of Spec"

    # Inner Spec schema still registered for the ## Schemas section; the outer
    # `Specs` wrapper MUST NOT be registered (would recreate the bug).
    schema_names = [s.name for s in endpoints[0].schemas]
    assert "Spec" in schema_names
    assert "Specs" not in schema_names
    # And the inner Spec schema renders as its real object fields, not as a
    # synthesized `{value: ...}` wrapper.
    spec_schema = next(s for s in endpoints[0].schemas if s.name == "Spec")
    assert [f.name for f in spec_schema.fields] == ["id", "name"]


def test_named_array_property_inlines_does_not_synthesize_wrapper() -> None:
    """Named array property (`Generators`) renders as `array of PromptGenerator`.

    The Pydantic wrapper type does not get its own `### Generators` schema
    section — the inner item type does. Old behavior emitted both, with the
    outer wrapper containing a phantom `value` field.
    """
    collector = parser.SchemaCollector()
    schema = {
        "type": "object",
        "properties": {
            "generators": {
                "type": "array",
                "x-schema-name": "Generators",
                "description": "Available prompt generators.",
                "items": {
                    "type": "object",
                    "x-schema-name": "PromptGenerator",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                    },
                },
            },
        },
    }

    fields = parser._schema_to_fields(schema, "", 0, collector)

    gen_field = next(f for f in fields if f.name == "generators")
    assert gen_field.type == "array of PromptGenerator"

    schema_names = [s.name for s in collector.schemas]
    assert "PromptGenerator" in schema_names
    assert "Generators" not in schema_names


def test_named_enum_property_inlines_with_constraint() -> None:
    """Named enum property (`ModelProviderName`) renders inline as `string`.

    The enum arrives as `x-schema-name` on a string type. It must NOT
    register a `### ModelProviderName` schema (which would contain a phantom
    `{value: string}` field). The `One of: ...` constraint is preserved on
    the referencing property.
    """
    collector = parser.SchemaCollector()
    schema = {
        "type": "object",
        "properties": {
            "model_provider_name": {
                "type": "string",
                "x-schema-name": "ModelProviderName",
                "description": "Enumeration of supported providers.",
                "enum": ["openai", "anthropic", "openrouter"],
            },
        },
    }

    fields = parser._schema_to_fields(schema, "", 0, collector)

    prop = fields[0]
    assert prop.name == "model_provider_name"
    assert prop.type == "string"
    assert "One of: openai, anthropic, openrouter" in prop.constraints

    assert collector.schemas == []


def test_named_integer_enum_property_inlines_with_constraint() -> None:
    """Named int-enum (`Priority`) renders inline as `integer` with `One of: ...`."""
    collector = parser.SchemaCollector()
    schema = {
        "type": "object",
        "properties": {
            "priority": {
                "type": "integer",
                "x-schema-name": "Priority",
                "description": "P0 is highest.",
                "enum": [0, 1, 2, 3],
            },
        },
    }

    fields = parser._schema_to_fields(schema, "", 0, collector)

    prop = fields[0]
    assert prop.type == "integer"
    assert "One of: 0, 1, 2, 3" in prop.constraints
    assert collector.schemas == []


def test_should_create_schema_named_array_returns_false() -> None:
    """x-schema-name on an array must NOT opt into wrapper registration."""
    schema = {
        "type": "array",
        "x-schema-name": "Generators",
        "items": {"type": "string"},
    }
    assert parser._should_create_schema(schema) is False


def test_should_create_schema_named_string_enum_returns_false() -> None:
    """x-schema-name on a string enum must NOT opt into wrapper registration."""
    schema = {
        "type": "string",
        "x-schema-name": "ModelProviderName",
        "enum": ["openai", "anthropic"],
    }
    assert parser._should_create_schema(schema) is False


def test_should_create_schema_object_with_x_schema_name_still_true() -> None:
    """Object types with x-schema-name remain registerable (unchanged behavior)."""
    schema = {"type": "object", "x-schema-name": "User"}
    assert parser._should_create_schema(schema) is True


def test_anonymous_array_variant_in_one_of_inlines_not_wraps() -> None:
    """`trace: list[TraceMessage] | None` must render as `array of TraceMessage`.

    Before: the array variant had no x-schema-name, so the old code synthesized
    an auto-named ``Variant`` / ``VariantV2`` schema with a single phantom
    ``value: array of TraceMessage`` field (see chat_sessions doc before fix).
    After: no wrapper schema; items registered; union inlines the array type.
    """
    collector = parser.SchemaCollector()
    schema = {
        "type": "object",
        "properties": {
            "trace": {
                "anyOf": [
                    {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "x-schema-name": "TraceMessage",
                            "properties": {
                                "role": {"type": "string"},
                                "content": {"type": "string"},
                            },
                        },
                    },
                    {"type": "null"},
                ],
            },
        },
    }

    fields = parser._schema_to_fields(schema, "", 0, collector)

    assert fields[0].name == "trace"
    assert fields[0].type == "one of: array of TraceMessage or null"

    schema_names = [s.name for s in collector.schemas]
    assert "TraceMessage" in schema_names
    assert "Variant" not in schema_names
    assert "VariantV2" not in schema_names


def test_named_enum_in_one_of_does_not_register_wrapper() -> None:
    """`template: EvalTemplateId | null` union: no `{value: string}` wrapper registered.

    The old behavior registered `EvalTemplateId` as a schema with a single
    phantom `value: string` field. Like the property-level and body-level
    paths, union variants that are named primitives/enums must inline their
    wire type (`string`) instead.
    """
    collector = parser.SchemaCollector()
    schema = {
        "type": "object",
        "properties": {
            "template": {
                "description": "The template selected when creating this eval.",
                "anyOf": [
                    {
                        "type": "string",
                        "x-schema-name": "EvalTemplateId",
                        "enum": ["kiln_requirements", "tool_call", "jailbreak"],
                    },
                    {"type": "null"},
                ],
            },
        },
    }

    fields = parser._schema_to_fields(schema, "", 0, collector)

    assert fields[0].name == "template"
    assert fields[0].type == "one of: string or null"
    assert collector.schemas == []
