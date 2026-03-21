"""Integration tests for the full pipeline."""

import json
from pathlib import Path

from openapi2skill.generator import (
    generate_reference_md,
    generate_skill_md,
    generate_tag_api_list_md,
)
from openapi2skill.parser import group_by_tag, parse_endpoints
from openapi2skill.resolver import resolve_refs
from openapi2skill.writer import assign_filenames, assign_tag_filenames, write_output


def test_full_pipeline_with_sample_spec(tmp_path: Path) -> None:
    """Test the full pipeline with the sample spec fixture."""
    # Load sample spec
    fixture_path = Path(__file__).parent / "fixtures" / "sample_spec.json"
    spec = json.loads(fixture_path.read_text())

    # Resolve refs
    spec = resolve_refs(spec)

    # Parse endpoints
    endpoints = parse_endpoints(spec)
    assert len(endpoints) == 3

    # Group by tag - now returns TagGroup objects
    tag_groups = group_by_tag(endpoints, spec)
    assert len(tag_groups) == 1
    assert tag_groups[0].name == "Users"

    # Assign endpoint filenames
    endpoint_filenames = assign_filenames(endpoints)
    assert len(endpoint_filenames) == 3

    # Assign tag filenames
    tag_filenames = assign_tag_filenames(tag_groups)
    assert len(tag_filenames) == 1

    # Generate SKILL.md - now tag index
    preamble = "# Test API"
    skill_md = generate_skill_md(preamble, tag_groups, tag_filenames)

    # Verify SKILL.md content - tag index, not endpoint tables
    assert "# Test API" in skill_md
    assert "## API Reference" in skill_md
    assert "### Users" in skill_md
    # Link to tag file
    assert "reference/users_api_list.md" in skill_md
    # No endpoint tables in SKILL.md
    assert "| Endpoint | Method |" not in skill_md

    # Generate per-tag API list files
    tag_api_lists = []
    for tag_group in tag_groups:
        filename = tag_filenames[tag_group.name]
        content = generate_tag_api_list_md(tag_group, endpoint_filenames)
        tag_api_lists.append((filename, content))

    # Verify tag API list content
    tag_list_content = tag_api_lists[0][1]
    assert "# Users API" in tag_list_content
    assert "/users" in tag_list_content
    assert "List all users" in tag_list_content
    assert "Create a user" in tag_list_content
    assert "Get user by ID" in tag_list_content

    # Generate reference files
    references = []
    for endpoint in endpoints:
        ep_key = f"{endpoint.method}_{endpoint.path}"
        filename = endpoint_filenames[ep_key]
        content = generate_reference_md(endpoint)
        references.append((filename, content))

    # Write output
    output_dir = str(tmp_path / "output")
    result_path = write_output(output_dir, skill_md, tag_api_lists, references)

    # Verify output structure
    result_path = Path(result_path)
    assert result_path.exists()
    assert (result_path / "SKILL.md").exists()
    assert (result_path / "reference").exists()

    # Verify reference files
    reference_dir = result_path / "reference"
    reference_files = list(reference_dir.glob("*.md"))
    # 3 endpoint refs + 1 tag list = 4 files
    assert len(reference_files) == 4

    # Verify file names
    ref_filenames = [f.name for f in reference_files]
    assert "get_users.md" in ref_filenames
    assert "post_users.md" in ref_filenames
    assert "get_users_id.md" in ref_filenames
    assert "users_api_list.md" in ref_filenames

    # Verify SKILL.md links to tag file
    skill_md_content = (result_path / "SKILL.md").read_text()
    assert "reference/users_api_list.md" in skill_md_content

    # Verify tag list file links to endpoint refs
    tag_list_file = reference_dir / "users_api_list.md"
    tag_list_content = tag_list_file.read_text()
    assert "reference/get_users.md" in tag_list_content
    assert "reference/post_users.md" in tag_list_content
    assert "reference/get_users_id.md" in tag_list_content

    # Verify reference file content
    get_users_content = (reference_dir / "get_users.md").read_text()
    assert "# List all users" in get_users_content
    assert "**GET /users**" in get_users_content
    assert "## Responses" in get_users_content

    post_users_content = (reference_dir / "post_users.md").read_text()
    assert "# Create a user" in post_users_content
    assert "**POST /users**" in post_users_content
    assert "## Request" in post_users_content
    assert "### Request Body" in post_users_content
    assert "name" in post_users_content
    assert "email" in post_users_content

    get_user_content = (reference_dir / "get_users_id.md").read_text()
    assert "# Get user by ID" in get_user_content
    assert "**GET /users/{id}**" in get_user_content
    assert "## Request" in get_user_content
    assert "### Path Parameters" in get_user_content
    assert "id" in get_user_content


def test_pipeline_with_empty_spec(tmp_path: Path) -> None:
    """Test pipeline with an empty spec (no paths)."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Empty API", "version": "1.0.0"},
        "paths": {},
    }

    endpoints = parse_endpoints(spec)
    assert len(endpoints) == 0

    tag_groups = group_by_tag(endpoints, spec)
    assert len(tag_groups) == 0

    endpoint_filenames = assign_filenames(endpoints)
    assert len(endpoint_filenames) == 0

    tag_filenames = assign_tag_filenames(tag_groups)
    assert len(tag_filenames) == 0

    skill_md = generate_skill_md("Empty API", tag_groups, tag_filenames)
    assert "Empty API" in skill_md
    assert "## API Reference" in skill_md

    output_dir = str(tmp_path / "output")
    result_path = write_output(output_dir, skill_md, [], [])

    result_path = Path(result_path)
    assert (result_path / "SKILL.md").exists()
    assert (result_path / "reference").exists()
    assert len(list((result_path / "reference").glob("*.md"))) == 0


def test_pipeline_preserves_spec_unchanged(tmp_path: Path) -> None:
    """Test that the pipeline does not modify the original spec."""
    fixture_path = Path(__file__).parent / "fixtures" / "sample_spec.json"
    original_spec = json.loads(fixture_path.read_text())

    # Make a copy for comparison
    import copy

    spec_copy = copy.deepcopy(original_spec)

    # Run through pipeline
    spec = json.loads(fixture_path.read_text())
    spec = resolve_refs(spec)
    parse_endpoints(spec)

    # Original spec should be unchanged
    assert original_spec == spec_copy


def test_pipeline_with_custom_preamble(tmp_path: Path) -> None:
    """Test that custom preamble is included correctly."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/test": {
                "get": {
                    "summary": "Test endpoint",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    endpoints = parse_endpoints(spec)
    tag_groups = group_by_tag(endpoints, spec)
    _ = assign_filenames(endpoints)
    tag_filenames = assign_tag_filenames(tag_groups)

    custom_preamble = """# My Custom API

## Authentication

This API uses Bearer tokens.

## Rate Limits

- 100 requests per minute
"""

    skill_md = generate_skill_md(custom_preamble, tag_groups, tag_filenames)

    assert "# My Custom API" in skill_md
    assert "## Authentication" in skill_md
    assert "Bearer tokens" in skill_md
    assert "## Rate Limits" in skill_md
    assert "100 requests per minute" in skill_md
    assert "## API Reference" in skill_md


def test_reference_file_with_full_endpoint_details(tmp_path: Path) -> None:
    """Test that reference files contain all endpoint details."""
    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {
            "/users/{id}": {
                "put": {
                    "summary": "Update user",
                    "description": "Updates an existing user with the provided data.",
                    "tags": ["Users"],
                    "parameters": [
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                            "description": "User ID",
                        },
                        {
                            "name": "notify",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "boolean", "default": True},
                            "description": "Send notification",
                        },
                    ],
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["name"],
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "User name",
                                        },
                                        "email": {
                                            "type": "string",
                                            "description": "Email address",
                                        },
                                        "role": {
                                            "type": "string",
                                            "enum": ["admin", "user"],
                                            "description": "User role",
                                        },
                                    },
                                },
                                "example": {
                                    "name": "Alice",
                                    "email": "alice@example.com",
                                },
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "User updated",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "id": {"type": "integer"},
                                            "name": {"type": "string"},
                                        },
                                    },
                                    "example": {"id": 1, "name": "Alice"},
                                }
                            },
                        },
                        "404": {"description": "User not found"},
                    },
                }
            }
        },
    }

    endpoints = parse_endpoints(spec)
    assert len(endpoints) == 1

    reference_md = generate_reference_md(endpoints[0])

    # Check title and method
    assert "# Update user" in reference_md
    assert "**PUT /users/{id}**" in reference_md

    # Check full description
    assert "Updates an existing user with the provided data." in reference_md

    # Check path parameters
    assert "### Path Parameters" in reference_md
    assert "| id | integer | Yes | User ID |" in reference_md

    # Check query parameters with default
    assert "### Query Parameters" in reference_md
    assert "| notify | boolean | No | True | Send notification |" in reference_md

    # Check request body
    assert "### Request Body" in reference_md
    assert "**Content Type:** `application/json`" in reference_md
    assert "| name | string | Yes | User name |" in reference_md
    assert "| email | string | No | Email address |" in reference_md
    assert "| role | string | No | User role. One of: admin, user |" in reference_md

    # Check request body example
    assert "#### Example" in reference_md
    assert '"name": "Alice"' in reference_md

    # Check responses
    assert "### 200 OK" in reference_md
    assert "User updated" in reference_md
    assert "### 404 Not Found" in reference_md
    assert "User not found" in reference_md

    # Check response example
    assert '"id": 1' in reference_md
