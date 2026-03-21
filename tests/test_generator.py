"""Tests for generator.py."""

from openapi2skill import generator
from openapi2skill.models import (
    Endpoint,
    Field,
    Parameter,
    RequestBody,
    Response,
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
            parameters=[],
            request_body=None,
            responses=[
                Response(status_code="200", description="OK", fields=[], example=None)
            ],
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
            parameters=[],
            request_body=None,
            responses=[],
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
            parameters=[],
            request_body=None,
            responses=[],
        )
    ]
    endpoints2 = [
        Endpoint(
            path="/products",
            method="GET",
            summary="List products",
            description="",
            tag="Products",
            parameters=[],
            request_body=None,
            responses=[],
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
            parameters=[],
            request_body=None,
            responses=[],
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
        parameters=[],
        request_body=None,
        responses=[
            Response(status_code="200", description="Success", fields=[], example=None)
        ],
    )

    result = generator.generate_reference_md(endpoint)

    assert "# List users" in result
    assert "**GET /users**" in result
    assert "Returns all users in the system" in result
    assert "## Responses" in result
    assert "### 200 OK" in result


def test_generate_reference_md_with_path_params() -> None:
    """Test path parameters section."""
    endpoint = Endpoint(
        path="/users/{id}",
        method="GET",
        summary="Get user",
        description="",
        tag="Users",
        parameters=[
            Parameter(
                name="id",
                location="path",
                type="integer",
                required=True,
                description="User ID",
                default=None,
            )
        ],
        request_body=None,
        responses=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "## Request" in result
    assert "### Path Parameters" in result
    assert "| id | integer | Yes | User ID |" in result


def test_generate_reference_md_with_query_params() -> None:
    """Test query parameters section with defaults."""
    endpoint = Endpoint(
        path="/users",
        method="GET",
        summary="List users",
        description="",
        tag="Users",
        parameters=[
            Parameter(
                name="limit",
                location="query",
                type="integer",
                required=False,
                description="Max results",
                default="20",
            )
        ],
        request_body=None,
        responses=[],
    )

    result = generator.generate_reference_md(endpoint)

    assert "### Query Parameters" in result
    assert "| limit | integer | No | 20 | Max results |" in result


def test_generate_reference_md_with_request_body() -> None:
    """Test request body section."""
    endpoint = Endpoint(
        path="/users",
        method="POST",
        summary="Create user",
        description="",
        tag="Users",
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
    )

    result = generator.generate_reference_md(endpoint)

    assert "### Request Body" in result
    assert "**Content Type:** `application/json`" in result
    assert "| name | string | Yes | User name |" in result
    assert "| role | string | No | User role. One of: admin, user |" in result


def test_generate_reference_md_with_request_body_example() -> None:
    """Test request body example is included."""
    endpoint = Endpoint(
        path="/users",
        method="POST",
        summary="Create user",
        description="",
        tag="Users",
        parameters=[],
        request_body=RequestBody(
            content_type="application/json",
            fields=[],
            example={"name": "Alice", "email": "alice@example.com"},
        ),
        responses=[],
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
    )

    result = generator.generate_reference_md(endpoint)

    assert "| id | integer | User ID |" in result
    assert "| name | string | User name |" in result


def test_generate_reference_md_with_response_example() -> None:
    """Test response example is included."""
    endpoint = Endpoint(
        path="/users/{id}",
        method="GET",
        summary="Get user",
        description="",
        tag="Users",
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
        parameters=[],
        request_body=None,
        responses=[
            Response(status_code="200", description="OK", fields=[], example=None)
        ],
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
        parameters=[],
        request_body=None,
        responses=[
            Response(
                status_code="418", description="I'm a teapot", fields=[], example=None
            ),
        ],
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
            parameters=[],
            request_body=None,
            responses=[
                Response(status_code="200", description="OK", fields=[], example=None)
            ],
        )
    ]
    tag_group = TagGroup(
        name="Users", description="User management", endpoints=endpoints
    )
    endpoint_filenames = {"GET_/users": "get_users.md"}

    result = generator.generate_tag_api_list_md(tag_group, endpoint_filenames)

    assert "# Users API" in result
    assert "User management" in result
    assert "| Endpoint | Method | Name | Description | API Details URL |" in result
    assert "`/users`" in result
    assert "GET" in result
    assert "List users" in result
    assert "reference/get_users.md" in result


def test_generate_tag_api_list_md_without_description() -> None:
    """Test per-tag file without description."""
    endpoints = [
        Endpoint(
            path="/test",
            method="GET",
            summary="Test",
            description="",
            tag="Test",
            parameters=[],
            request_body=None,
            responses=[],
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
            parameters=[],
            request_body=None,
            responses=[],
        ),
        Endpoint(
            path="/users",
            method="POST",
            summary="Create user",
            description="",
            tag="Users",
            parameters=[],
            request_body=None,
            responses=[],
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
            parameters=[],
            request_body=None,
            responses=[],
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
            parameters=[],
            request_body=None,
            responses=[],
        )
    ]
    tag_group = TagGroup(name="Test", description="", endpoints=endpoints)
    endpoint_filenames = {"GET_/test": "get_test.md"}

    result = generator.generate_tag_api_list_md(tag_group, endpoint_filenames)

    assert "xxx..." in result
    assert long_desc not in result
