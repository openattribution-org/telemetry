# Contributing to the OpenAttribution Telemetry specification

## What belongs here

This repo contains the **specification** - the data model, event types, privacy levels, conformance levels, and transport guidance. It does not contain SDK or server code.

| File | Purpose |
|------|---------|
| [SPECIFICATION.md](./SPECIFICATION.md) | The normative specification |
| [telemetry-session.json](./telemetry-session.json) | JSON Schema for validation |
| [CONSIDERATIONS.md](./CONSIDERATIONS.md) | Deferred items under consideration for future versions |
| [tests/](./tests/) | Conformance test suite |
| [acp/](./acp/) | Agentic Commerce Protocol extension |
| [ucp/](./ucp/) | Universal Commerce Protocol extension |

For SDK contributions, see:
- Python: [openattribution-org/telemetry-py](https://github.com/openattribution-org/telemetry-py)
- TypeScript: [openattribution-org/telemetry-js](https://github.com/openattribution-org/telemetry-js)

## Proposing changes

Schema changes affect all implementations. Before submitting a PR:

1. Open an issue describing the change and its motivation
2. Reference the relevant section of SPECIFICATION.md
3. Consider backwards compatibility - can existing consumers ignore new fields?
4. Update both SPECIFICATION.md and telemetry-session.json
5. Update extension schemas in `acp/` or `ucp/` if applicable
6. Add or update test cases in `tests/` for any new fields or conformance rules
7. Run `python tests/validate.py` to verify all tests pass

## Conformance levels

The spec defines three conformance levels: **Retrieval**, **Grounding**, and **Attribution** (section 5.7). When proposing new required fields, specify which conformance level they apply to. New optional fields do not require a conformance level change.

## Future considerations

Items deferred from v0.1 are documented in [CONSIDERATIONS.md](./CONSIDERATIONS.md). If you want to champion one of these items for a future version, open an issue referencing the relevant section and describe the implementation experience or market conditions that justify inclusion.

## Conventions

- **British English** in documentation
- **Sentence case** for headings
- Schema fields use **snake_case**
- New optional fields are preferred over breaking changes
- RFC 2119 keywords (MUST, SHOULD, MAY) used per the Introduction

## Licence

By contributing, you agree that your contributions will be licensed under the Apache 2.0 licence.
