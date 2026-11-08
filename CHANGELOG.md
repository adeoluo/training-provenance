# Changelog

All notable changes to this project are documented here. The file is generated
from Conventional Commits by [git-cliff](https://git-cliff.org) when a release is cut
with `make cut-release`.

## [0.1.1] 2026-11-08

### Documentation

- Standard README structure and language framing (#11)
- Horizontal layered architecture diagram
- Compact horizontal architecture diagram
- Remove authorship statements from docs and scripts
- Recorded demos of more commands, with their vhs tapes (#1)
- Recorded demos of the HTTP service and more commands (#2)
- Complete citation metadata and bump it on release (#4)
- Map the threat model to OWASP LLM 2026 and MITRE ATLAS v2026.10 (#6)
- Add standards keywords to the citation metadata (#7)

### Build and CI

- Run CodeQL on main and on a weekly schedule only

### Maintenance

- Add release automation, AGENTS.md, llms.txt and contributor docs
- Classify squash merges in the changelog by the commits they contain
- Latest toolchain and CI versions (#3)
- Release script keeps hard-coded version strings in step (#5)

## [0.1.0] 2026-11-01

### Features

- Content-addressed provenance with a lineage DAG and reproducibility verification
- End-to-end reproduction, crash recovery, and an exhaustive tamper matrix (#10)

### Bug fixes

- Reject ambiguous inputs so content hashing stays injective (#8)

### Documentation

- Use plain, factual wording (#7)

### Maintenance

- Initialize repository
- Bump GitHub Actions to current major versions
- Remove Dependabot configuration
