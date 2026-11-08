# Threat Model - Training Provenance

## Assets
- The integrity of tracked artifacts and runs, the trustworthiness of provenance claims, and
  service availability.

## Trust boundaries
- The HTTP service accepts untrusted JSON from clients. The tracked pipeline is built in-process
  from trusted code; there is no external data ingestion at request time.

## Threats and mitigations
- **Artifact tampering.** Replacing a stored artifact's bytes is detected by the integrity check,
  which recomputes each artifact's hash and compares it to its identifier. Whole-lineage
  verification reports the specific run whose outputs no longer match.
- **Provenance forgery.** Because run identity is the hash of the operation, inputs, parameters,
  and code version, a run cannot be silently altered without changing its identifier, and its
  outputs cannot be changed without failing verification.
- **Malformed requests.** The `/lineage` endpoint requires a non-empty string artifact identifier
  and returns 404 for unknown artifacts; invalid JSON bodies return a 400.
- **Resource exhaustion.** Queries operate over the fixed, small in-memory graph, so there is no
  input-controlled amplification; a real deployment bounds artifact sizes at ingestion.

## Standards mapping

The threats are mapped to the OWASP Top 10 for LLM Applications 2026 and MITRE ATLAS v2026.10
(IDs and names checked against `ATLAS.yaml` from the
[v2026.10 release of mitre-atlas/atlas-data](https://github.com/mitre-atlas/atlas-data/releases)).
The OWASP Top 10 for Agentic Applications 2026 is not mapped because no agent is involved.

| Threat | OWASP LLM 2026 | MITRE ATLAS v2026.10 | Role of this project |
|---|---|---|---|
| Tampered dataset artifact | LLM04:2026 Supply Chain; LLM05:2026 Data and Model Poisoning | AML.T0010.002 Supply Chain Compromise: Data Repository; AML.T0059 Erode Dataset Integrity; AML.T0020 Training Data Poisoning | Detects: the integrity check rehashes every artifact |
| Tampered model or output artifact | LLM04:2026 Supply Chain; LLM05:2026 Data and Model Poisoning | AML.T0010.003 Supply Chain Compromise: Model Repository; AML.T0018 Manipulate AI Model | Detects: lineage verification names the run whose outputs no longer match |
| Provenance forgery | LLM04:2026 Supply Chain | AML.T0138 Indicator Removal | Detects altered runs through content-addressed run identity; records are not signed |
| Resource exhaustion through the service | LLM06:2026 Unbounded Consumption | AML.T0029 Denial of AI Service | Bounded by the small in-memory graph |

The project implements AML.M0025 Maintain AI Dataset Provenance and AML.M0014 Verify AI
Artifacts, and its lineage graph records the inputs that AML.M0023 Maintain an AI Bill of
Materials asks for (datasets, configuration and code version). AML.M0013 Code Signing is not
implemented (see Non-goals). In NIST AI 600-1 (Generative AI Profile) terms it addresses the
Information Integrity and Value Chain and Component Integration risks.

## Non-goals
- Authentication, authorization, and transport security are delegated to the deployment
  environment (a reverse proxy or gateway), as described in the operations guide. Cryptographic
  signing of the ledger for non-repudiation is a possible extension, not a current goal.
