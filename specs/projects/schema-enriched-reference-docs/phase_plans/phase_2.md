---
status: complete
---

# Phase 2: Parser Integration

## Overview

Modify the parser functions to thread the `SchemaCollector` through the parsing process, registering schemas when complex objects are encountered and producing named type references instead of bare "object" or "array of object".

## Steps

### 1. Add `_should_create_schema` helper

**File:** `openapi2skill/parser.py`

**Add after `_derive_schema_name`:**

```python
def _should_create_schema(schema: dict) -> bool:
    """Return True if schema has enough structure to warrant a schema definition."""
    if not schema or not isinstance(schema, dict):
        return False
    if "properties" in schema and schema["properties"]:
        return True
    if "x-schema-name" in schema:
        return True
    if schema.get("type") == "array":
        items = schema.get("items", {})
        if isinstance(items, dict):
            if items.get("type") == "object" and items.get("properties"):
                return True
            if "x-schema-name" in items:
                return True
    return False
```

### 2. Add `_render_type_with_schema` helper

**File:** `openapi2skill/parser.py`

**Add after `_should_create_schema`:**

```python
def _render_type_with_schema(schema: dict, schema_name: str) -> str:
    """Render type string using the schema name."""
    if schema.get("type") == "array":
        return f"array of {schema_name}"
    return schema_name
```

### 3. Modify `_schema_to_fields` to accept collector parameter

**File:** `openapi2skill/parser.py`

**Change signature:**

```python
def _schema_to_fields(
    schema: dict, prefix: str = "", depth: int = 0, collector: SchemaCollector | None = None
) -> list[Field]:
```

**Key logic changes:**

1. Pass `collector` through recursive calls
2. At the point where nested objects at depth limit or without properties are rendered, register schemas instead of using opaque "object"
3. Handle arrays of objects similarly

**Modified logic for object handling (around lines 378-393):**

```python
# Inside the properties loop, when prop_type is object:
if prop_type == "object" and "properties" in prop_schema and depth < 2:
    # Existing: flatten with dot notation
    nested_fields = _schema_to_fields(prop_schema, f"{field_name}.", depth + 1, collector)
    fields.extend(nested_fields)
elif collector is not None and _should_create_schema(prop_schema):
    # NEW: register as named schema instead of opaque "object"
    schema_name = _derive_schema_name(prop_schema, prop_name)
    schema_fields = _schema_to_fields(prop_schema, "", 0, collector)
    final_name = collector.register(schema_name, prop_schema.get("description", ""), schema_fields)
    rendered_type = _render_type_with_schema(prop_schema, final_name)
    fields.append(Field(name=field_name, type=rendered_type, required=is_required,
                        description=description, constraints=constraints))
else:
    # Fallback: existing behavior
    fields.append(Field(name=field_name, type=_render_type(prop_schema), required=is_required,
                        description=description, constraints=constraints))
```

### 4. Handle oneOf/anyOf with object variants

**File:** `openapi2skill/parser.py`

**Modify the oneOf/anyOf handling block (around lines 331-346):**

When a variant is an object that should create a schema, register it and use the schema name in the type string.

### 5. Modify `_extract_request_body` to accept collector

**File:** `openapi2skill/parser.py`

**Change signature:**

```python
def _extract_request_body(request_body: dict | None, collector: SchemaCollector | None = None) -> RequestBody | None:
```

**Pass collector to `_schema_to_fields`:**

```python
fields = _schema_to_fields(schema, "", 0, collector)
```

### 6. Modify `_extract_responses` to accept collector

**File:** `openapi2skill/parser.py`

**Change signature:**

```python
def _extract_responses(responses: dict, collector: SchemaCollector | None = None) -> list[Response]:
```

**Pass collector to `_schema_to_fields`:**

```python
fields = _schema_to_fields(schema, "", 0, collector)
```

### 7. Modify `_extract_endpoint` to create collector and pass schemas

**File:** `openapi2skill/parser.py`

**Modify function body:**

```python
def _extract_endpoint(
    path: str, method: str, path_item: dict, operation: dict
) -> Endpoint:
    """Extract a single Endpoint from an OpenAPI operation."""
    summary = _extract_summary(operation, method, path)
    description = operation.get("description", "")
    tag = _extract_tag(operation)
    parameters = _extract_parameters(path_item, operation)
    
    collector = SchemaCollector()
    request_body = _extract_request_body(operation.get("requestBody"), collector)
    responses = _extract_responses(operation.get("responses", {}), collector)

    return Endpoint(
        path=path,
        method=method.upper(),
        summary=summary,
        description=description,
        tag=tag,
        parameters=parameters,
        request_body=request_body,
        responses=responses,
        schemas=collector.schemas,
    )
```

### 8. Handle arrays at the schema root level

**File:** `openapi2skill/parser.py`

**Modify the non-object schema handling (around lines 348-359):**

When the root schema is an array with object items, register the items schema and use the named reference.

## Tests

### test_parser.py — New tests

1. `test_schema_to_fields_with_collector_named_ref`: Schema with `x-schema-name` -> schema registered, field type uses name
2. `test_schema_to_fields_with_collector_inline`: Inline object at depth limit -> PascalCase name derived from field name
3. `test_schema_to_fields_array_of_objects`: Array of objects -> `array of SchemaName` type
4. `test_schema_to_fields_transitive`: Schema A references Schema B -> both in collector
5. `test_schema_to_fields_no_properties_object`: Bare object without properties -> stays "object", no schema created
6. `test_schema_to_fields_oneof_with_object_variants`: `oneOf` containing objects -> variant schemas registered
7. `test_schema_to_fields_without_collector`: Passing `collector=None` -> existing behavior unchanged
8. `test_extract_endpoint_with_schemas`: Full endpoint extraction produces schemas
9. `test_extract_request_body_uses_collector`: Request body schemas are collected
10. `test_extract_responses_uses_collector`: Response schemas are collected

## Verification

- Run `uv run ruff check .` — lint clean
- Run `uv run ruff format .` — format clean
- Run `uv run pytest` — all tests pass
