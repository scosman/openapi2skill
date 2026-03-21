"""Parser for extracting structured endpoint data from OpenAPI specs."""

from openapi2skill.models import (
    Endpoint,
    Field,
    Parameter,
    RequestBody,
    Response,
    TagGroup,
)

HTTP_METHODS = {"get", "post", "put", "delete", "patch"}


def parse_endpoints(spec: dict) -> list[Endpoint]:
    """Extract all endpoints from a resolved OpenAPI spec.

    Args:
        spec: A resolved OpenAPI spec dict (all $refs should be pre-resolved)

    Returns:
        List of Endpoint objects
    """
    endpoints = []
    paths = spec.get("paths", {})

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        for method in HTTP_METHODS:
            if method not in path_item:
                continue

            operation = path_item[method]
            if not isinstance(operation, dict):
                continue

            endpoint = _extract_endpoint(path, method, path_item, operation)
            endpoints.append(endpoint)

    return endpoints


def group_by_tag(endpoints: list[Endpoint], spec: dict) -> list[TagGroup]:
    """Group endpoints by tag, ordered by the spec's top-level tags array.

    Args:
        endpoints: List of Endpoint objects
        spec: The OpenAPI spec dict

    Returns:
        List of TagGroup objects in display order
    """
    # Build lookup dict from spec's top-level tags array: {tag_name: description}
    tag_descriptions: dict[str, str] = {}
    for tag in spec.get("tags", []):
        if "name" in tag:
            tag_descriptions[tag["name"]] = tag.get("description", "")

    # Get ordered tag names from spec's top-level tags array
    spec_tags = list(tag_descriptions.keys())

    # Group endpoints by their tag
    tag_groups: dict[str, list[Endpoint]] = {}
    for endpoint in endpoints:
        tag = endpoint.tag
        if tag not in tag_groups:
            tag_groups[tag] = []
        tag_groups[tag].append(endpoint)

    # Build ordered result
    result: list[TagGroup] = []
    seen_tags: set[str] = set()

    # First: tags from spec's top-level tags array (in order)
    for tag in spec_tags:
        if tag in tag_groups:
            description = tag_descriptions.get(tag, "")
            result.append(
                TagGroup(name=tag, description=description, endpoints=tag_groups[tag])
            )
            seen_tags.add(tag)

    # Then: remaining tags in order of first encounter
    for endpoint in endpoints:
        tag = endpoint.tag
        if tag not in seen_tags:
            description = tag_descriptions.get(tag, "")
            result.append(
                TagGroup(name=tag, description=description, endpoints=tag_groups[tag])
            )
            seen_tags.add(tag)

    return result


def _extract_endpoint(
    path: str, method: str, path_item: dict, operation: dict
) -> Endpoint:
    """Extract a single Endpoint from an OpenAPI operation."""
    summary = _extract_summary(operation, method, path)
    description = operation.get("description", "")
    tag = _extract_tag(operation)
    parameters = _extract_parameters(path_item, operation)
    request_body = _extract_request_body(operation.get("requestBody"))
    responses = _extract_responses(operation.get("responses", {}))

    return Endpoint(
        path=path,
        method=method.upper(),
        summary=summary,
        description=description,
        tag=tag,
        parameters=parameters,
        request_body=request_body,
        responses=responses,
    )


def _extract_summary(operation: dict, method: str, path: str) -> str:
    """Extract summary with fallback chain: summary -> operationId -> METHOD path."""
    if "summary" in operation and operation["summary"]:
        return operation["summary"]
    if "operationId" in operation and operation["operationId"]:
        return operation["operationId"]
    return f"{method.upper()} {path}"


def _extract_tag(operation: dict) -> str:
    """Extract the first tag, or 'Other' if none."""
    tags = operation.get("tags", [])
    if tags and isinstance(tags, list) and len(tags) > 0:
        return tags[0]
    return "Other"


def _extract_parameters(path_item: dict, operation: dict) -> list[Parameter]:
    """Extract and merge path-level and operation-level parameters."""
    # Start with path-level parameters
    path_params = path_item.get("parameters", [])
    op_params = operation.get("parameters", [])

    # Build lookup for operation params (name+in -> param)
    op_lookup = {
        (p.get("name"), p.get("in")): p for p in op_params if isinstance(p, dict)
    }

    # Start with path params that aren't overridden
    merged = []
    seen_keys: set[tuple[str, str]] = set()

    for param in path_params:
        if not isinstance(param, dict):
            continue
        name = param.get("name", "")
        location = param.get("in", "")
        key = (name, location)

        if key in op_lookup:
            # Operation param overrides path param
            merged.append(_param_to_parameter(op_lookup[key]))
            seen_keys.add(key)
        else:
            merged.append(_param_to_parameter(param))
            seen_keys.add(key)

    # Add operation params that weren't overrides
    for param in op_params:
        if not isinstance(param, dict):
            continue
        name = param.get("name", "")
        location = param.get("in", "")
        key = (name, location)

        if key not in seen_keys:
            merged.append(_param_to_parameter(param))

    return merged


def _param_to_parameter(param: dict) -> Parameter:
    """Convert an OpenAPI parameter dict to a Parameter object."""
    name = param.get("name", "")
    location = param.get("in", "")
    required = param.get("required", False)
    description = param.get("description", "")

    schema = param.get("schema", {})
    param_type = _render_type(schema)

    default_val = schema.get("default")
    default = str(default_val) if default_val is not None else None

    return Parameter(
        name=name,
        location=location,
        type=param_type,
        required=required,
        description=description,
        default=default,
    )


def _extract_request_body(request_body: dict | None) -> RequestBody | None:
    """Extract RequestBody from OpenAPI requestBody spec."""
    if not request_body or not isinstance(request_body, dict):
        return None

    content = request_body.get("content", {})
    if not content:
        return None

    # Prefer application/json
    json_content = content.get("application/json", {})
    if not json_content:
        # Fall back to first available content type
        for content_type, ct_data in content.items():
            json_content = ct_data
            break

    schema = json_content.get("schema", {})
    if not schema:
        return None

    fields = _schema_to_fields(schema)
    example = json_content.get("example") or schema.get("example")

    return RequestBody(
        content_type="application/json",
        fields=fields,
        example=example,
    )


def _extract_responses(responses: dict) -> list[Response]:
    """Extract Response objects from OpenAPI responses spec."""
    result = []

    for status_code, response_spec in responses.items():
        if not isinstance(response_spec, dict):
            continue

        description = response_spec.get("description", "")
        fields = []
        example = None

        content = response_spec.get("content", {})
        json_content = content.get("application/json", {})

        if json_content:
            schema = json_content.get("schema", {})
            if schema:
                fields = _schema_to_fields(schema)
                example = json_content.get("example") or schema.get("example")

        result.append(
            Response(
                status_code=str(status_code),
                description=description,
                fields=fields,
                example=example,
            )
        )

    return result


def _schema_to_fields(schema: dict, prefix: str = "", depth: int = 0) -> list[Field]:
    """Convert an OpenAPI schema to a list of Field objects.

    Args:
        schema: OpenAPI schema dict
        prefix: Prefix for nested field names (dot notation)
        depth: Current nesting depth (limit of 3)

    Returns:
        List of Field objects
    """
    if not schema or not isinstance(schema, dict):
        return []

    # Handle allOf by merging all sub-schemas
    if "allOf" in schema:
        merged = _merge_all_of(schema["allOf"])
        return _schema_to_fields(merged, prefix, depth)

    # Handle oneOf/anyOf - return a single field describing the union
    if "oneOf" in schema or "anyOf" in schema:
        variants = schema.get("oneOf") or schema.get("anyOf", [])
        type_names = []
        for v in variants:
            if isinstance(v, dict):
                type_names.append(_render_type(v))
        union_type = f"one of: {', '.join(type_names)}" if type_names else "any"
        return [
            Field(
                name=prefix.rstrip(".") if prefix else "value",
                type=union_type,
                required=True,
                description=schema.get("description", ""),
                constraints=_extract_constraints(schema),
            )
        ]

    # For non-object schemas, return a single field describing the type
    schema_type = schema.get("type", "object")
    if schema_type != "object":
        return [
            Field(
                name=prefix.rstrip(".") if prefix else "value",
                type=_render_type(schema),
                required=True,
                description=schema.get("description", ""),
                constraints=_extract_constraints(schema),
            )
        ]

    properties = schema.get("properties", {})
    if not properties:
        return []

    required_fields = set(schema.get("required", []))
    fields = []

    for prop_name, prop_schema in properties.items():
        if not isinstance(prop_schema, dict):
            continue

        field_name = f"{prefix}{prop_name}" if prefix else prop_name
        prop_type = prop_schema.get("type", "object")
        is_required = prop_name in required_fields
        description = prop_schema.get("description", "")
        constraints = _extract_constraints(prop_schema)

        # Handle nested objects - flatten with dot notation up to depth limit of 3
        # depth=0 is root level, depth=1 is first nesting, etc.
        # Stop flattening when depth >= 2 to limit to 3 levels total
        if prop_type == "object" and "properties" in prop_schema and depth < 2:
            nested_fields = _schema_to_fields(prop_schema, f"{field_name}.", depth + 1)
            fields.extend(nested_fields)
        else:
            fields.append(
                Field(
                    name=field_name,
                    type=_render_type(prop_schema),
                    required=is_required,
                    description=description,
                    constraints=constraints,
                )
            )

    return fields


def _merge_all_of(all_of: list) -> dict:
    """Merge allOf sub-schemas into a single schema."""
    merged: dict = {"type": "object", "properties": {}, "required": []}

    for sub_schema in all_of:
        if not isinstance(sub_schema, dict):
            continue

        # Merge properties
        if "properties" in sub_schema:
            merged["properties"].update(sub_schema["properties"])

        # Merge required
        if "required" in sub_schema:
            merged["required"].extend(sub_schema["required"])

        # Merge description (prefer first non-empty)
        if "description" in sub_schema and "description" not in merged:
            merged["description"] = sub_schema["description"]

    # Deduplicate required
    merged["required"] = list(set(merged["required"]))

    return merged


def _render_type(schema: dict) -> str:
    """Render a schema's type as a human-readable string."""
    if not schema or not isinstance(schema, dict):
        return "any"

    # Handle oneOf/anyOf
    if "oneOf" in schema or "anyOf" in schema:
        variants = schema.get("oneOf") or schema.get("anyOf", [])
        type_names = [_render_type(v) for v in variants if isinstance(v, dict)]
        return f"one of: {', '.join(type_names)}" if type_names else "any"

    # Handle allOf
    if "allOf" in schema:
        merged = _merge_all_of(schema["allOf"])
        return _render_type(merged)

    schema_type = schema.get("type", "any")

    if schema_type == "array":
        items = schema.get("items", {})
        item_type = _render_type(items) if isinstance(items, dict) else "any"
        return f"array of {item_type}"

    if schema_type == "object" and "properties" not in schema:
        return "object"

    return schema_type


def _extract_constraints(schema: dict) -> str:
    """Extract constraint string from schema (enums, format, etc.)."""
    constraints = []

    if "enum" in schema:
        enum_values = ", ".join(str(v) for v in schema["enum"])
        constraints.append(f"One of: {enum_values}")

    if "format" in schema:
        constraints.append(f"Format: {schema['format']}")

    if "minimum" in schema:
        constraints.append(f"Min: {schema['minimum']}")

    if "maximum" in schema:
        constraints.append(f"Max: {schema['maximum']}")

    if "minLength" in schema:
        constraints.append(f"Min length: {schema['minLength']}")

    if "maxLength" in schema:
        constraints.append(f"Max length: {schema['maxLength']}")

    if "pattern" in schema:
        constraints.append(f"Pattern: {schema['pattern']}")

    return ". ".join(constraints)
