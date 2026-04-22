"""Tests for generator.py."""

from openapi2skill import generator
from openapi2skill.models import (
    Endpoint,
    Field,
    Parameter,
    RequestBody,
    Response,
    Schema,
    TagGroup,
)


def test_escape_table_cell_pipe() -> None:
    """Test that pipe characters are escaped."""
    result = generator.escape_table_cell("hello | world")
    assert result == "hello \\| world"


def test_escape_table_cell_newlines() -> None:
    """Test that newlines are replaced with space."""
    result = generator.escape_table_cell("hello\nworld")
    assert result == "hello world"


def test_escape_table_cell_carriage_return() -> None:
    """Test that carriage returns are replaced with space."""
    result = generator.escape_table_cell("hello\r\nworld")
    assert result == "hello  world"


def test_escape_table_cell_multiple_pipes() -> None:
    """Test escaping multiple pipes."""
    result = generator.escape_table_cell("a | b | c")
    assert result == "a \\| b \\| c"


def test_truncate_description_no_change() -> None:
    """Test that short text is unchanged."""
    result = generator.truncate_description("short text")
    assert result == "short text"


def test_truncate_description_exact_length() -> None:
    """Test that text at exactly max length is unchanged."""
    text = "x" * 100
    result = generator.truncate_description(text)
    assert result == text
    assert len(result) == 100


def test_truncate_description_with_ellipsis() -> None:
    """Test that long text is truncated with ellipsis."""
    text = "x" * 150
    result = generator.truncate_description(text)
    assert result == "x" * 100 + "..."
    assert len(result) == 103


def test_truncate_description_custom_length() -> None:
    """Test custom max length."""
    text = "hello world"
    result = generator.truncate_description(text, max_length=5)
    assert result == "hello..."


def test_generate_skill_md_basic() -> None:
    """Test basic SKILL.md generation with tag index."""
    endpoints = [
        Endpoint(
            path="/users",
            method="GET",
            summary="List users",
            description="Returns all users",
            tag="Users",
            tags=["Users"],
            parameters=[],
            request_body=None,
            responses=[
                Response(status_code="200", description="OK", fields=[], example=None)
            ],
            schemas=[],
        )
    ]
    tag_groups = [
        TagGroup(name="Users", description="Manage users", endpoints=endpoints)
    ]
    tag_filenames = {"Users": "users_api_list.md"}

    result = generator.generate_skill_md("Test preamble", tag_groups, tag_filenames)

    assert "Test preamble" in result
    assert "## API Reference" in result
    assert "### Users" in result
    assert "Manage users" in result
    assert "**Endpoints:** reference/users_api_list.md" in result
    # No endpoint tables in SKILL.md anymore - check for table header and endpoint paths
    assert "| Endpoint | Method |" not in result
    assert "`/users`" not in result  # Endpoint paths are not in SKILL.md


def test_generate_skill_md_with_preamble() -> None:
    """Test that preamble is included verbatim."""
    preamble = "# Custom API\n\nThis is a custom preamble."
    endpoints = [
        Endpoint(
            path="/test",
            method="GET",
            summary="Test",
            description="",
            tag="Test",
            tags=["Test"],
            parameters=[],
            request_body=None,
            responses=[],
            schemas=[],
        )
    ]
    tag_groups = [TagGroup(name="Test", description="", endpoints=endpoints)]
    tag_filenames = {"Test": "test_api_list.md"}

    result = generator.generate_skill_md(preamble, tag_groups, tag_filenames)

    assert "# Custom API" in result
    assert "This is a custom preamble." in result

    assert "### Test" in result


def test_generate_skill_md_empty_endpoints() -> None:
    """Test that empty tag groups produces empty API Reference."""
    result = generator.generate_skill_md("Preamble", [], {})

    assert "Preamble" in result
    assert "## API Reference" in result


def test_generate_skill_md_multiple_tags() -> None:
    """Test multiple tag groups."""
    endpoints1 = [
        Endpoint(
            path="/users",
            method="GET",
            summary="List users",
            description="",
            tag="Users",
            tags=["Users"],
            parameters=[],
            request_body=None,
            responses=[],
            schemas=[],
        )
    ]
    endpoints2 = [
        Endpoint(
            path="/products",
            method="GET",
            summary="List products",
            description="",
            tag="Products",
            tags=["Products"],
            parameters=[],
            request_body=None,
            responses=[],
            schemas=[],
        )
    ]
    tag_groups = [
        TagGroup(name="Users", description="User management", endpoints=endpoints1),
        TagGroup(name="Products", description="Product catalog", endpoints=endpoints2),
    ]
    tag_filenames = {"Users": "users_api_list.md", "Products": "products_api_list.md"}

    result = generator.generate_skill_md("Test", tag_groups, tag_filenames)

    assert "### Users" in result
    assert "### Products" in result
    assert "User management" in result
    assert "Product catalog" in result
    # Should have links to tag files, not endpoint tables
    assert "reference/users_api_list.md" in result
    assert "reference/products_api_list.md" in result

    # No endpoint tables in SKILL.md - check for table header and endpoint paths
    assert "| Endpoint | Method |" not in result
    assert "`/users`" not in result
    assert "`/products`" not in result


def test_generate_skill_md_tag_without_description() -> None:
    """Test tag without description shows only link."""
    endpoints = [
        Endpoint(
            path="/test",
            method="GET",
            summary="Test",
            description="",
            tag="Test",
            tags=["Test"],
            parameters=[],
            request_body=None,
            responses=[],
            schemas=[],
        )
    ]
    tag_groups = [TagGroup(name="Test", description="", endpoints=endpoints)]
    tag_filenames = {"Test": "test_api_list.md"}

    result = generator.generate_skill_md("Test", tag_groups, tag_filenames)

    assert "### Test" in result
    assert "**Endpoints:** reference/test_api_list.md" in result


def test_generate_reference_md_basic() -> None:
    """Test basic reference file generation."""
    endpoint = Endpoint(
        path="/users",
        method="GET",
        summary="List users",
        description="Returns all users in the system",
        tag="Users",
        tags=["Users"],
        parameters=[],
        request_body=None,
        responses=[
            Response(status_code="200", description="Success", fields=[], example=None)
        ],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "# List users" in result
    assert "**GET /users**" in result
    assert "**Tags:** Users" in result
    assert "Returns all users in the system" in result
    assert "## Responses" in result
    assert "### 200 OK" in result


def test_generate_reference_md_multiple_tags() -> None:
    """Test that multiple tags are displayed."""
    endpoint = Endpoint(
        path="/users",
        method="GET",
        summary="List users",
        description="",
        tag="Users",
        tags=["Users", "Admin"],
        parameters=[],
        request_body=None,
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "**Tags:** Users, Admin" in result


def test_generate_reference_md_no_tags() -> None:
    """Test that tags line is omitted when no tags."""
    endpoint = Endpoint(
        path="/users",
        method="GET",
        summary="List users",
        description="",
        tag="Other",
        tags=[],
        parameters=[],
        request_body=None,
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "**Tags:**" not in result


def test_generate_reference_md_with_path_params() -> None:
    """Test path parameters section."""
    endpoint = Endpoint(
        path="/users/{id}",
        method="GET",
        summary="Get user",
        description="",
        tag="Users",
        tags=["Users"],
        parameters=[
            Parameter(
                name="id",
                location="path",
                type="integer",
                required=True,
                description="User ID",
                default=None,
                constraints="",
            )
        ],
        request_body=None,
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "## Request" in result
    assert "### Path Parameters" in result
    assert "|id|integer|Yes|User ID|" in result


def test_generate_reference_md_with_query_params() -> None:
    """Test query parameters section with defaults."""
    endpoint = Endpoint(
        path="/users",
        method="GET",
        summary="List users",
        description="",
        tag="Users",
        tags=["Users"],
        parameters=[
            Parameter(
                name="limit",
                location="query",
                type="integer",
                required=False,
                description="Max results",
                default="20",
                constraints="",
            )
        ],
        request_body=None,
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "### Query Parameters" in result
    assert "|limit|integer|No|20|Max results|" in result


def test_generate_reference_md_with_request_body() -> None:
    """Test request body section."""
    endpoint = Endpoint(
        path="/users",
        method="POST",
        summary="Create user",
        description="",
        tag="Users",
        tags=["Users"],
        parameters=[],
        request_body=RequestBody(
            content_type="application/json",
            fields=[
                Field(
                    name="name",
                    type="string",
                    required=True,
                    description="User name",
                    constraints="",
                ),
                Field(
                    name="role",
                    type="string",
                    required=False,
                    description="User role",
                    constraints="One of: admin, user",
                ),
            ],
            example=None,
        ),
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "### Request Body" in result
    assert "**Content Type:** `application/json`" in result
    assert "|name|string|Yes|User name|" in result
    assert "|role|string|No|User role. One of: admin, user|" in result


def test_generate_reference_md_with_request_body_example() -> None:
    """Test request body example is included."""
    endpoint = Endpoint(
        path="/users",
        method="POST",
        summary="Create user",
        description="",
        tag="Users",
        tags=["Users"],
        parameters=[],
        request_body=RequestBody(
            content_type="application/json",
            fields=[],
            example={"name": "Alice", "email": "alice@example.com"},
        ),
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "#### Example" in result
    assert '"name": "Alice"' in result
    assert '"email": "alice@example.com"' in result
    assert "```json" in result


def test_generate_reference_md_without_request_body_example() -> None:
    """Test no example section when request body has no example."""
    endpoint = Endpoint(
        path="/users",
        method="POST",
        summary="Create user",
        description="",
        tag="Users",
        tags=["Users"],
        parameters=[],
        request_body=RequestBody(
            content_type="application/json",
            fields=[
                Field(
                    name="name",
                    type="string",
                    required=True,
                    description="",
                    constraints="",
                )
            ],
            example=None,
        ),
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "#### Example" not in result


def test_generate_reference_md_with_response_fields() -> None:
    """Test response fields are included."""
    endpoint = Endpoint(
        path="/users/{id}",
        method="GET",
        summary="Get user",
        description="",
        tag="Users",
        tags=["Users"],
        parameters=[],
        request_body=None,
        responses=[
            Response(
                status_code="200",
                description="Success",
                fields=[
                    Field(
                        name="id",
                        type="integer",
                        required=True,
                        description="User ID",
                        constraints="",
                    ),
                    Field(
                        name="name",
                        type="string",
                        required=True,
                        description="User name",
                        constraints="",
                    ),
                ],
                example=None,
            )
        ],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "|id|integer|User ID|" in result
    assert "|name|string|User name|" in result


def test_generate_reference_md_with_response_example() -> None:
    """Test response example is included."""
    endpoint = Endpoint(
        path="/users/{id}",
        method="GET",
        summary="Get user",
        description="",
        tag="Users",
        tags=["Users"],
        parameters=[],
        request_body=None,
        responses=[
            Response(
                status_code="200",
                description="Success",
                fields=[],
                example={"id": 1, "name": "Alice"},
            )
        ],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "#### Example" in result
    assert '"id": 1' in result
    assert "```json" in result


def test_generate_reference_md_multiple_responses() -> None:
    """Test multiple response codes."""
    endpoint = Endpoint(
        path="/users",
        method="POST",
        summary="Create user",
        description="",
        tag="Users",
        tags=["Users"],
        parameters=[],
        request_body=None,
        responses=[
            Response(status_code="201", description="Created", fields=[], example=None),
            Response(
                status_code="400", description="Bad Request", fields=[], example=None
            ),
            Response(
                status_code="422",
                description="Validation Error",
                fields=[],
                example=None,
            ),
        ],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "### 201 Created" in result
    assert "### 400 Bad Request" in result
    assert "### 422 Validation Error" in result


def test_generate_reference_md_no_request_section_when_empty() -> None:
    """Test no Request section when no params or body."""
    endpoint = Endpoint(
        path="/health",
        method="GET",
        summary="Health check",
        description="",
        tag="System",
        tags=["System"],
        parameters=[],
        request_body=None,
        responses=[
            Response(status_code="200", description="OK", fields=[], example=None)
        ],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "## Request" not in result


def test_generate_reference_md_status_descriptions() -> None:
    """Test common status code descriptions."""
    endpoint = Endpoint(
        path="/test",
        method="GET",
        summary="Test",
        description="",
        tag="Test",
        tags=["Test"],
        parameters=[],
        request_body=None,
        responses=[
            Response(status_code="200", description="", fields=[], example=None),
            Response(status_code="201", description="", fields=[], example=None),
            Response(status_code="204", description="", fields=[], example=None),
            Response(status_code="400", description="", fields=[], example=None),
            Response(status_code="401", description="", fields=[], example=None),
            Response(status_code="404", description="", fields=[], example=None),
            Response(status_code="422", description="", fields=[], example=None),
            Response(status_code="500", description="", fields=[], example=None),
        ],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "200 OK" in result
    assert "201 Created" in result
    assert "204 No Content" in result
    assert "400 Bad Request" in result
    assert "401 Unauthorized" in result
    assert "404 Not Found" in result
    assert "422 Validation Error" in result
    assert "500 Internal Server Error" in result


def test_generate_reference_md_unknown_status_code() -> None:
    """Test unknown status codes have no description."""
    endpoint = Endpoint(
        path="/test",
        method="GET",
        summary="Test",
        description="",
        tag="Test",
        tags=["Test"],
        parameters=[],
        request_body=None,
        responses=[
            Response(
                status_code="418", description="I'm a teapot", fields=[], example=None
            ),
        ],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "### 418 " in result  # Just status code, no known description


def test_default_preamble_exists() -> None:
    """Test that DEFAULT_PREAMBLE is defined."""
    assert generator.DEFAULT_PREAMBLE
    assert "API" in generator.DEFAULT_PREAMBLE
    assert "curl" in generator.DEFAULT_PREAMBLE
    # New preamble mentions 2-level navigation
    assert "tag list" in generator.DEFAULT_PREAMBLE.lower()


# Tests for generate_tag_api_list_md


def test_generate_tag_api_list_md_basic() -> None:
    """Test basic per-tag API list generation."""
    endpoints = [
        Endpoint(
            path="/users",
            method="GET",
            summary="List users",
            description="Returns all users",
            tag="Users",
            tags=["Users"],
            parameters=[],
            request_body=None,
            responses=[
                Response(status_code="200", description="OK", fields=[], example=None)
            ],
            schemas=[],
        )
    ]
    tag_group = TagGroup(
        name="Users", description="User management", endpoints=endpoints
    )
    endpoint_filenames = {"GET_/users": "get_users.md"}

    result = generator.generate_tag_api_list_md(tag_group, endpoint_filenames)

    assert "# Users API" in result
    assert "User management" in result
    assert "|Endpoint|Method|Name|Description|Details File|" in result
    assert "`/users`" in result
    assert "GET" in result
    assert "List users" in result
    # Detail files are siblings of the tag list file, so the cell must be a
    # bare filename with no "reference/" prefix.
    assert "|get_users.md|" in result
    assert "reference/get_users.md" not in result


def test_generate_tag_api_list_md_without_description() -> None:
    """Test per-tag file without description."""
    endpoints = [
        Endpoint(
            path="/test",
            method="GET",
            summary="Test",
            description="",
            tag="Test",
            tags=["Test"],
            parameters=[],
            request_body=None,
            responses=[],
            schemas=[],
        )
    ]
    tag_group = TagGroup(name="Test", description="", endpoints=endpoints)
    endpoint_filenames = {"GET_/test": "get_test.md"}

    result = generator.generate_tag_api_list_md(tag_group, endpoint_filenames)

    assert "# Test API" in result
    # No description line
    assert result.count("\n\n") <= 2  # Heading, table header, no description paragraph


def test_generate_tag_api_list_md_multiple_endpoints() -> None:
    """Test per-tag file with multiple endpoints."""
    endpoints = [
        Endpoint(
            path="/users",
            method="GET",
            summary="List users",
            description="",
            tag="Users",
            tags=["Users"],
            parameters=[],
            request_body=None,
            responses=[],
            schemas=[],
        ),
        Endpoint(
            path="/users",
            method="POST",
            summary="Create user",
            description="",
            tag="Users",
            tags=["Users"],
            parameters=[],
            request_body=None,
            responses=[],
            schemas=[],
        ),
    ]
    tag_group = TagGroup(name="Users", description="", endpoints=endpoints)
    endpoint_filenames = {"GET_/users": "get_users.md", "POST_/users": "post_users.md"}

    result = generator.generate_tag_api_list_md(tag_group, endpoint_filenames)

    assert "`/users`" in result
    assert "GET" in result
    assert "POST" in result
    assert "List users" in result
    assert "Create user" in result


def test_generate_tag_api_list_md_escapes_special_chars() -> None:
    """Test that special characters in summary/description are escaped."""
    endpoints = [
        Endpoint(
            path="/test",
            method="GET",
            summary="Test | pipe",
            description="Line1\nLine2",
            tag="Test",
            tags=["Test"],
            parameters=[],
            request_body=None,
            responses=[],
            schemas=[],
        )
    ]
    tag_group = TagGroup(name="Test", description="", endpoints=endpoints)
    endpoint_filenames = {"GET_/test": "get_test.md"}

    result = generator.generate_tag_api_list_md(tag_group, endpoint_filenames)

    assert "\\|" in result
    assert "Line1 Line2" in result


def test_generate_tag_api_list_md_truncates_description() -> None:
    """Test that long descriptions are truncated."""
    long_desc = "x" * 150
    endpoints = [
        Endpoint(
            path="/test",
            method="GET",
            summary="Test",
            description=long_desc,
            tag="Test",
            tags=["Test"],
            parameters=[],
            request_body=None,
            responses=[],
            schemas=[],
        )
    ]
    tag_group = TagGroup(name="Test", description="", endpoints=endpoints)
    endpoint_filenames = {"GET_/test": "get_test.md"}

    result = generator.generate_tag_api_list_md(tag_group, endpoint_filenames)

    assert "xxx..." in result
    assert long_desc not in result


def test_generate_schemas_section_empty() -> None:
    """Test empty schemas list produces no output."""
    result = generator._generate_schemas_section([])
    assert result == []


def test_generate_schemas_section_single() -> None:
    """Test single schema renders correctly."""
    schemas = [
        Schema(
            name="Address",
            description="A postal address",
            fields=[
                Field(
                    name="street",
                    type="string",
                    required=True,
                    description="Street name",
                    constraints="",
                ),
                Field(
                    name="city",
                    type="string",
                    required=True,
                    description="City name",
                    constraints="",
                ),
            ],
        )
    ]

    result = generator._generate_schemas_section(schemas)

    assert "## Schemas" in result
    assert "### Address" in result
    assert "A postal address" in result
    assert "|Field|Type|Required|Description|" in result
    assert "|street|string|Yes|Street name|" in result
    assert "|city|string|Yes|City name|" in result


def test_generate_schemas_section_multiple() -> None:
    """Test multiple schemas all rendered."""
    schemas = [
        Schema(
            name="User",
            description="",
            fields=[
                Field(
                    name="id",
                    type="integer",
                    required=True,
                    description="",
                    constraints="",
                )
            ],
        ),
        Schema(
            name="Address",
            description="",
            fields=[
                Field(
                    name="city",
                    type="string",
                    required=True,
                    description="",
                    constraints="",
                )
            ],
        ),
    ]

    result = generator._generate_schemas_section(schemas)
    result_text = "\n".join(result)

    assert "### User" in result_text
    assert "### Address" in result_text
    assert "|id|integer|Yes||" in result_text
    assert "|city|string|Yes||" in result_text


def test_generate_schemas_section_with_description() -> None:
    """Test schema description is included."""
    schemas = [
        Schema(
            name="TaskMetadata",
            description="Metadata about the model used for a task",
            fields=[],
        )
    ]

    result = generator._generate_schemas_section(schemas)
    result_text = "\n".join(result)

    assert "Metadata about the model used for a task" in result_text


def test_generate_schemas_section_with_constraints() -> None:
    """Test field constraints are included in description."""
    schemas = [
        Schema(
            name="Item",
            description="",
            fields=[
                Field(
                    name="status",
                    type="string",
                    required=False,
                    description="Item status",
                    constraints="One of: active, inactive",
                ),
            ],
        )
    ]

    result = generator._generate_schemas_section(schemas)
    result_text = "\n".join(result)

    assert "Item status. One of: active, inactive" in result_text


def test_reference_md_with_schemas() -> None:
    """Test endpoint with schemas includes Schemas section."""
    endpoint = Endpoint(
        path="/users",
        method="POST",
        summary="Create user",
        description="",
        tag="Users",
        tags=["Users"],
        parameters=[],
        request_body=None,
        responses=[
            Response(
                status_code="200",
                description="Success",
                fields=[
                    Field(
                        name="user",
                        type="User",
                        required=True,
                        description="The created user",
                        constraints="",
                    )
                ],
                example=None,
            )
        ],
        schemas=[
            Schema(
                name="User",
                description="A user object",
                fields=[
                    Field(
                        name="id",
                        type="integer",
                        required=True,
                        description="User ID",
                        constraints="",
                    ),
                    Field(
                        name="name",
                        type="string",
                        required=True,
                        description="User name",
                        constraints="",
                    ),
                ],
            )
        ],
    )

    result = generator.generate_reference_md(endpoint)

    assert "## Schemas" in result
    assert "### User" in result
    assert "A user object" in result
    assert "|id|integer|Yes|User ID|" in result


def test_reference_md_no_schemas() -> None:
    """Test endpoint without schemas has no Schemas section."""
    endpoint = Endpoint(
        path="/health",
        method="GET",
        summary="Health check",
        description="",
        tag="System",
        tags=["System"],
        parameters=[],
        request_body=None,
        responses=[
            Response(status_code="200", description="OK", fields=[], example=None)
        ],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "## Schemas" not in result


def test_reference_md_schemas_after_responses() -> None:
    """Test Schemas section appears after Responses section."""
    endpoint = Endpoint(
        path="/test",
        method="GET",
        summary="Test",
        description="",
        tag="Test",
        tags=["Test"],
        parameters=[],
        request_body=None,
        responses=[
            Response(status_code="200", description="OK", fields=[], example=None)
        ],
        schemas=[Schema(name="TestSchema", description="", fields=[])],
    )

    result = generator.generate_reference_md(endpoint)

    responses_pos = result.find("## Responses")
    schemas_pos = result.find("## Schemas")
    assert responses_pos > 0
    assert schemas_pos > responses_pos


# Tests for compact constraint format in description


def test_request_body_string_length_constraints() -> None:
    """Test string length constraints use compact range in description."""
    endpoint = Endpoint(
        path="/tools",
        method="POST",
        summary="Create tool",
        description="",
        tag="Tools",
        tags=["Tools"],
        parameters=[],
        request_body=RequestBody(
            content_type="application/json",
            fields=[
                Field(
                    name="name",
                    type="string",
                    required=True,
                    description="Tool name",
                    constraints="1-64 chars",
                ),
            ],
            example=None,
        ),
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "|name|string|Yes|Tool name. 1-64 chars|" in result


def test_request_body_int_range_constraints() -> None:
    """Test integer range constraints use compact range in description."""
    endpoint = Endpoint(
        path="/items",
        method="POST",
        summary="Create item",
        description="",
        tag="Items",
        tags=["Items"],
        parameters=[],
        request_body=RequestBody(
            content_type="application/json",
            fields=[
                Field(
                    name="priority",
                    type="integer",
                    required=False,
                    description="Item priority",
                    constraints="0-100",
                ),
            ],
            example=None,
        ),
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "|priority|integer|No|Item priority. 0-100|" in result


def test_response_field_float_range_constraints() -> None:
    """Test float range constraints in response fields."""
    endpoint = Endpoint(
        path="/items/{id}",
        method="GET",
        summary="Get item",
        description="",
        tag="Items",
        tags=["Items"],
        parameters=[],
        request_body=None,
        responses=[
            Response(
                status_code="200",
                description="Success",
                fields=[
                    Field(
                        name="score",
                        type="number",
                        required=True,
                        description="Item score",
                        constraints="0.0-1.0",
                    ),
                ],
                example=None,
            )
        ],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "|score|number|Item score. 0.0-1.0|" in result


def test_constraints_only_no_description() -> None:
    """Test field with constraints but no description shows just constraints."""
    endpoint = Endpoint(
        path="/tools",
        method="POST",
        summary="Create tool",
        description="",
        tag="Tools",
        tags=["Tools"],
        parameters=[],
        request_body=RequestBody(
            content_type="application/json",
            fields=[
                Field(
                    name="name",
                    type="string",
                    required=True,
                    description="",
                    constraints="1-64 chars",
                ),
            ],
            example=None,
        ),
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "|name|string|Yes|1-64 chars|" in result


def test_path_param_with_constraints() -> None:
    """Test path parameter constraints appear in description."""
    endpoint = Endpoint(
        path="/items/{id}",
        method="GET",
        summary="Get item",
        description="",
        tag="Items",
        tags=["Items"],
        parameters=[
            Parameter(
                name="id",
                location="path",
                type="integer",
                required=True,
                description="Item ID",
                default=None,
                constraints=">=1",
            )
        ],
        request_body=None,
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "|id|integer|Yes|Item ID. >=1|" in result


def test_query_param_with_constraints() -> None:
    """Test query parameter constraints appear in description."""
    endpoint = Endpoint(
        path="/items",
        method="GET",
        summary="List items",
        description="",
        tag="Items",
        tags=["Items"],
        parameters=[
            Parameter(
                name="limit",
                location="query",
                type="integer",
                required=False,
                description="Max results",
                default="20",
                constraints="1-100",
            ),
        ],
        request_body=None,
        responses=[],
        schemas=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "|limit|integer|No|20|Max results. 1-100|" in result
