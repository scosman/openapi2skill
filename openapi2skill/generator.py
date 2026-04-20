"""Markdown generators for SKILL.md and reference files."""

import json

from openapi2skill.models import Endpoint, Schema, TagGroup

DEFAULT_PREAMBLE = """---
name: api-definition
description: Description of this API and when to use this skill.
---

This skill describes the endpoints and functionality of an API. Use the tag list
below to find the relevant API area, then read the linked file for a list of
endpoints. Each endpoint links to a detailed reference file with full
request/response details. You can call these APIs using curl or any HTTP client."""


def escape_table_cell(text: str) -> str:
    """Escape text for safe inclusion in a markdown table cell.

    Args:
        text: The text to escape

    Returns:
        Escaped text safe for markdown tables
    """
    # Replace pipe characters with escaped version
    text = text.replace("|", "\\|")
    # Replace newlines with space
    text = text.replace("\n", " ").replace("\r", " ")
    return text


def truncate_description(text: str, max_length: int = 100) -> str:
    """Truncate text to max_length, adding '...' if truncated.

    Args:
        text: The text to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated text with '...' if it was shortened
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def _append_constraints(description: str, constraints: str) -> str:
    """Append constraints to description, joining with '. ' if both present."""
    if constraints:
        if description:
            sep = " " if description.endswith(".") else ". "
            return f"{description}{sep}{constraints}"
        return constraints
    return description


def generate_skill_md(
    preamble: str,
    tag_groups: list[TagGroup],
    tag_filenames: dict[str, str],
) -> str:
    """Generate the SKILL.md content with tag index.

    Args:
        preamble: Markdown to include verbatim at the top
        tag_groups: List of TagGroup objects
        tag_filenames: Dict mapping tag name to per-tag filename

    Returns:
        Complete SKILL.md content
    """
    lines: list[str] = []

    # Add preamble
    lines.append(preamble)
    lines.append("")

    # Add API Reference section
    lines.append("## API Reference")
    lines.append("")

    for tag_group in tag_groups:
        lines.append(f"### {tag_group.name}")
        lines.append("")
        if tag_group.description:
            lines.append(tag_group.description)
            lines.append("")
        filename = tag_filenames.get(
            tag_group.name, f"{tag_group.name.lower()}_api_list.md"
        )
        lines.append(f"**Endpoints:** reference/{filename}")
        lines.append("")

    return "\n".join(lines)


def generate_tag_api_list_md(
    tag_group: TagGroup,
    endpoint_filenames: dict[str, str],
) -> str:
    """Generate a per-tag API list file.

    Args:
        tag_group: TagGroup object with endpoints
        endpoint_filenames: Dict mapping "{method}_{path}" to reference filenames

    Returns:
        Complete per-tag API list content
    """
    lines: list[str] = []

    # Heading
    lines.append(f"# {tag_group.name} API")
    lines.append("")

    # Tag description if present
    if tag_group.description:
        lines.append(tag_group.description)
        lines.append("")

    # Endpoint table
    lines.append("|Endpoint|Method|Name|Description|API Details URL|")
    lines.append("|-|-|-|-|-|")

    for endpoint in tag_group.endpoints:
        ep_key = f"{endpoint.method}_{endpoint.path}"
        filename = endpoint_filenames.get(ep_key, f"{ep_key}.md")

        # Escape and truncate values for table
        name = escape_table_cell(endpoint.summary)
        description = truncate_description(escape_table_cell(endpoint.description))

        lines.append(
            f"|`{endpoint.path}`|{endpoint.method}|{name}|{description}|reference/{filename}|"
        )

    lines.append("")

    return "\n".join(lines)


def generate_reference_md(endpoint: Endpoint) -> str:
    """Generate a reference markdown file for one endpoint.

    Args:
        endpoint: The endpoint to generate documentation for

    Returns:
        Complete reference file content
    """
    lines: list[str] = []

    # Title and method/path
    lines.append(f"# {endpoint.summary}")
    lines.append("")
    lines.append(f"**{endpoint.method} {endpoint.path}**")
    lines.append("")

    # Tags
    if endpoint.tags:
        lines.append(f"**Tags:** {', '.join(endpoint.tags)}")
        lines.append("")

    # Full description
    if endpoint.description:
        lines.append(endpoint.description)
        lines.append("")

    # Request section
    has_request_content = endpoint.parameters or endpoint.request_body is not None

    if has_request_content:
        lines.append("## Request")
        lines.append("")

        # Path parameters
        path_params = [p for p in endpoint.parameters if p.location == "path"]
        if path_params:
            lines.append("### Path Parameters")
            lines.append("")
            lines.append("|Name|Type|Required|Description|")
            lines.append("|-|-|-|-|")
            for param in path_params:
                desc = _append_constraints(param.description, param.constraints)
                lines.append(
                    f"|{param.name}|{param.type}|{'Yes' if param.required else 'No'}|{desc}|"
                )
            lines.append("")

        # Query parameters
        query_params = [p for p in endpoint.parameters if p.location == "query"]
        if query_params:
            lines.append("### Query Parameters")
            lines.append("")
            lines.append("|Name|Type|Required|Default|Description|")
            lines.append("|-|-|-|-|-|")
            for param in query_params:
                default = param.default if param.default else ""
                desc = _append_constraints(param.description, param.constraints)
                lines.append(
                    f"|{param.name}|{param.type}|{'Yes' if param.required else 'No'}|{default}|{desc}|"
                )
            lines.append("")

        # Request body
        if endpoint.request_body:
            lines.append("### Request Body")
            lines.append("")
            lines.append(f"**Content Type:** `{endpoint.request_body.content_type}`")
            lines.append("")

            if endpoint.request_body.body_type and not endpoint.request_body.fields:
                lines.append(f"**Body:** {endpoint.request_body.body_type}")
                lines.append("")
            elif endpoint.request_body.fields:
                lines.append("|Field|Type|Required|Description|")
                lines.append("|-|-|-|-|")
                for field in endpoint.request_body.fields:
                    desc = _append_constraints(field.description, field.constraints)
                    lines.append(
                        f"|{field.name}|{field.type}|{'Yes' if field.required else 'No'}|{desc}|"
                    )
                lines.append("")

            # Example
            if endpoint.request_body.example:
                lines.append("#### Example")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(endpoint.request_body.example, indent=2))
                lines.append("```")
                lines.append("")

    # Responses section
    if endpoint.responses:
        lines.append("## Responses")
        lines.append("")

        for response in endpoint.responses:
            # Get status code description
            status_desc = _get_status_description(response.status_code)
            header = f"### {response.status_code} {status_desc}"
            lines.append(header)
            lines.append("")

            if response.description:
                lines.append(response.description)
                lines.append("")

            if response.body_type and not response.fields:
                lines.append(f"**Body:** {response.body_type}")
                lines.append("")
            elif response.fields:
                lines.append("|Field|Type|Description|")
                lines.append("|-|-|-|")
                for field in response.fields:
                    desc = _append_constraints(field.description, field.constraints)
                    lines.append(f"|{field.name}|{field.type}|{desc}|")
                lines.append("")

            if response.example:
                lines.append("#### Example")
                lines.append("")
                lines.append("```json")
                lines.append(json.dumps(response.example, indent=2))
                lines.append("```")
                lines.append("")

    if endpoint.schemas:
        lines.extend(_generate_schemas_section(endpoint.schemas))

    return "\n".join(lines)


def _get_status_description(status_code: str) -> str:
    """Get a human-readable description for an HTTP status code.

    Args:
        status_code: The HTTP status code as a string

    Returns:
        Human-readable status description
    """
    descriptions = {
        "200": "OK",
        "201": "Created",
        "202": "Accepted",
        "204": "No Content",
        "400": "Bad Request",
        "401": "Unauthorized",
        "403": "Forbidden",
        "404": "Not Found",
        "405": "Method Not Allowed",
        "409": "Conflict",
        "422": "Validation Error",
        "429": "Too Many Requests",
        "500": "Internal Server Error",
        "502": "Bad Gateway",
        "503": "Service Unavailable",
    }
    return descriptions.get(status_code, "")


def _generate_schemas_section(schemas: list[Schema]) -> list[str]:
    """Generate markdown lines for the Schemas section.

    Args:
        schemas: List of Schema objects to render

    Returns:
        List of markdown lines for the Schemas section
    """
    if not schemas:
        return []

    lines: list[str] = []

    lines.append("## Schemas")
    lines.append("")

    for schema in schemas:
        lines.append(f"### {schema.name}")
        lines.append("")

        if schema.description:
            lines.append(schema.description)
            lines.append("")

        lines.append("|Field|Type|Required|Description|")
        lines.append("|-|-|-|-|")

        for field in schema.fields:
            desc = _append_constraints(field.description, field.constraints)
            lines.append(
                f"|{field.name}|{field.type}|{'Yes' if field.required else 'No'}|{desc}|"
            )

        lines.append("")

    return lines
