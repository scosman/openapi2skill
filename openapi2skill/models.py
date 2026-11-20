"""Data models for the OpenAPI skill generator."""

from dataclasses import dataclass


@dataclass
class TagGroup:
    """Represents a group of endpoints under a tag."""

    name: str
    description: str  # empty string if not present in spec
    endpoints: list["Endpoint"]


@dataclass
class Schema:
    """Represents a named object schema for the Schemas section."""

    name: str
    description: str
    fields: list["Field"]


@dataclass
class Endpoint:
    """Represents a single API endpoint."""

    path: str
    method: str
    summary: str
    description: str
    tag: str
    tags: list[str]
    parameters: list["Parameter"]
    request_body: "RequestBody | None"
    responses: list["Response"]
    schemas: list["Schema"]


@dataclass
class Parameter:
    """Represents a path, query, or header parameter."""

    name: str
    location: str  # "path", "query", "header"
    type: str
    required: bool
    description: str
    default: str | None
    constraints: str


@dataclass
class RequestBody:
    """Represents a request body schema."""

    content_type: str
    fields: list["Field"]
    example: dict | None
    # Set when the body is a top-level non-object (e.g., a Pydantic RootModel
    # list wrapper that serializes as a bare array on the wire). When set,
    # `fields` is empty and the generator renders the type inline instead of
    # a field table — the old behavior synthesized a phantom `value` field,
    # which made consumers write `.value[]` filters that don't exist.
    body_type: str | None = None


@dataclass
class Field:
    """Represents a field in a request body or response."""

    name: str
    type: str
    required: bool
    description: str
    constraints: str


@dataclass
class Response:
    """Represents an API response."""

    status_code: str
    description: str
    fields: list["Field"]
    example: dict | None
    # See RequestBody.body_type — same semantics for responses.
    body_type: str | None = None
