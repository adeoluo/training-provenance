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

## Non-goals
- Authentication, authorization, and transport security are delegated to the deployment
  environment (a reverse proxy or gateway), as described in the operations guide. Cryptographic
  signing of the ledger for non-repudiation is a possible extension, not a current goal.
