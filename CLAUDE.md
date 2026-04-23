# CLAUDE.md

This is the **OpenAttribution Telemetry Specification** repo - not a code library. It defines the wire format, schemas, conformance levels, and extension points for OA telemetry.

## Repo structure

```
SPECIFICATION.md          Main spec document
telemetry-session.json    JSON Schema for session documents (draft 2020-12)
telemetry-event.json      JSON Schema for standalone event envelopes
acp/                      Agent Content Protocol extension (content attribution RFC)
ucp/                      Unified Content Protocol extension
tests/                    Conformance test suite
  valid/                  Fixtures that must pass schema validation
  invalid/                Fixtures that must fail (schema or application-layer rules)
  validate.py             Test runner
CONSIDERATIONS.md         Design rationale and open questions
CONTRIBUTING.md           Contribution guidelines
```

## Running conformance tests

```sh
pip install jsonschema
python tests/validate.py
```

Exit code 0 means all tests pass. The runner checks both JSON Schema validity and application-layer conformance rules (privacy level field gating) that the schema alone cannot express.

## Conventions

- British English throughout spec and guides.
- JSON Schema draft 2020-12.
- No marketing language - describe mechanisms, not aspirations.
- Test fixtures include a `_test_description` field explaining what each fixture validates.
- Extension schemas live in their own directories (`acp/`, `ucp/`) with their own READMEs.
