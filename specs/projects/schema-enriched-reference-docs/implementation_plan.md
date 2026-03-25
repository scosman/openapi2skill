---
status: complete
---

# Implementation Plan: Schema-Enriched Reference Docs

## Phases

- [x] Phase 1: Resolver + Models + SchemaCollector — Annotate `$ref` resolutions with `x-schema-name` in `resolver.py`, add `Schema` dataclass and `schemas` field on `Endpoint` in `models.py`, implement `SchemaCollector` class and name-derivation helpers in `parser.py`. Tests for resolver annotation and collector logic (dedup, conflicts, fingerprinting).
- [x] Phase 2: Parser integration — Modify `_schema_to_fields`, `_extract_request_body`, `_extract_responses`, and `_extract_endpoint` to thread the collector, register schemas, and produce named type references. Tests for all schema-collection scenarios (named refs, inline objects, arrays, transitive, oneOf variants, no-properties fallback, backward compat with collector=None).
- [ ] Phase 3: Generator + integration — Add `_generate_schemas_section` to `generator.py`, call it from `generate_reference_md`. Update integration test. Run against a real API spec and verify output for the problem endpoints from the project overview.
