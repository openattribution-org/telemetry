# Governance

## Status

The OpenAttribution Telemetry specification is an open standard stewarded by OpenAttribution. It is in preview (v0.x); see [SPECIFICATION.md](./SPECIFICATION.md) section 12 for the versioning policy.

## Stewardship

OpenAttribution maintains this specification as a neutral, multi-stakeholder standard. The wire format is meant to be implementable by anyone and to belong to the ecosystem rather than to any single operator or coalition.

This repository is structured to keep the standard neutral and portable:

- **The repository contains only the wire format.** Community- and operator-specific requirements - accreditation tiers, conformance marks, privacy floors, commercial terms - live in separate profiles maintained by the bodies that define them, and carry no normative weight here. The standard carries no operator-specific normative content.
- **Apache 2.0 throughout.** Contributions are accepted under the same licence (see [CONTRIBUTING.md](./CONTRIBUTING.md)). No contributor-side terms restrict redistribution or re-hosting.
- **No dependency on any single operator's infrastructure.** The specification can be implemented without access to any OpenAttribution-operated system. The deployment patterns in SPECIFICATION.md section 7.3 name a public aggregation point as one option, not a required intermediary. A competing operator can implement this standard and reach parity by consuming the same wire format.

## Profiles

A profile selects from this standard and adds requirements for a particular community: a required conformance level, delivery guarantees, privacy floors, accreditation, a conformance mark. Profiles reference this specification by version.

The dependency runs one way. A profile references the standard; the standard does not reference any profile. A new profile needs no change to the standard, and a profile's requirements never become normative here. This lets communities set their own rules on top of one shared wire format without fragmenting it.

The [SPUR Telemetry Profile](https://github.com/SPUR-Coalition/telemetry-profile) is one such profile, defining publisher-facing accreditation and a conformance mark held by the SPUR Coalition. Other communities may define their own.

## Changes to the specification

Specification changes follow the process in [CONTRIBUTING.md](./CONTRIBUTING.md). Required-field and conformance-level changes are breaking and follow the versioning policy in SPECIFICATION.md section 12.

## Licensing

Apache License 2.0. See [LICENSE](./LICENSE).
