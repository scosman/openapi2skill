# openapi2skill

Generate agent skills from OpenAPI specs. Creates [agentskills.io](https://agentskills.io) format documentation so AI agents can discover and call your API.

## Why Skills and not MCP?

OpenAPI specs can have thousands of endpoints so MCP wrappers immediately flood your context with many tools. With an Agent Skill we can have progressive disclosure:

 - Describe the API's purpose and tags in the main SKILL.md
 - List available APIs for each tag in `references/TAG_api_list.md`
 - Give detailed API spec for each API in `references/get_user.md` (see [example](#example-api-definition) below)

Your agent can call these APIs using any tool you like, often just `curl`.

## Installation

```bash
git clone git@github.com:scosman/openapi2spec.git
cd openapi2spec
uv sync
```

## Usage

```bash
uv run openapi2skill --spec <url-or-file> [--preamble <file>] [--output <dir>]
```

### Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--spec` | Yes | - | URL or file path to the OpenAPI JSON spec |
| `--preamble` | No | Built-in default | Path to a markdown file prepended to SKILL.md |
| `--output` | No | `./output` | Directory where skill files are written |

### Examples

From a URL:
```bash
uv run openapi2skill --spec https://api.example.com/openapi.json
```

From a local file:
```bash
uv run openapi2skill --spec ./openapi.json --output ./docs
```

With a custom preamble:
```bash
uv run openapi2skill --spec ./openapi.json --preamble ./preamble.md
```

## Output Structure

Each run creates a timestamped subdirectory:

```
output/
  2026-03-19_143052/
    SKILL.md
    reference/
      get_users.md
      post_users.md
      get_users_id.md
      ...
```

### SKILL.md

Contains a summary table of all endpoints grouped by tag, with links to detailed reference files.

### Reference Files

Each endpoint gets a detailed markdown file with:
- Path and query parameters
- Request body schema with field types and constraints
- Response schemas for each status code
- Examples (when available in the spec)

#### Example API Definition `references/get_user.md`

```md
# Get User

**GET /api/users/{user_id}**

Retrieve a user's profile by their ID.

## Path Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| user_id | string | Yes | The user's ID (e.g. `usr_4kQx9mP2`) |

## Responses

### 200 OK

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique user ID (e.g. `usr_4kQx9mP2`) |
| email | string | User's email address (e.g. `jane@example.com`) |
| name | string | Full display name (e.g. `Jane Smith`) |
| created_at | string | ISO 8601 signup timestamp (e.g. `2024-01-08T09:15:00Z`) |
| role | string | One of: `admin`, `member`, `viewer` |
| active | boolean | `false` if the account has been deactivated |

### 404 Not Found

| Field | Type | Description |
|-------|------|-------------|
| error | string | Human-readable message (e.g. `User not found`) |
```


## Requirements

- Python 3.13+
- OpenAPI 3.x JSON spec (YAML not supported)

## Development

Run tests:
```bash
uv run pytest
```

Lint and format:
```bash
uv run ruff check .
uv run ruff format .
```
