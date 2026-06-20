# ADR-003 — Policy broker before storage

## Context
A memory system that stores whatever the model extracts will eventually persist secrets, sensitive
PII, or low-utility noise. Storage must be gated by an explicit, auditable policy decision
(invariant #5: policy-before-storage).

## Decision
Insert a **Policy Broker / Evaluator** between the Extractor and the Write Service. It is the single
choke point that decides one of:

```text
SAVE · PENDING_APPROVAL · BLOCK · DROP_LOW_UTILITY · UPDATE_EXISTING · MERGE_WITH_EXISTING
```

It runs, in order: secret/credential detection → PII/sensitivity classification → utility/dedup
checks → final scoring. Every decision emits an audit event with a human-readable reason.

## Alternatives considered
- **Filter inside the extractor** — couples extraction quality to safety; harder to test/audit in isolation.
- **Post-write moderation** — violates policy-before-storage; secrets briefly persist.
- **Pure LLM judge** — flexible but non-deterministic and unverifiable for hard rules like "block
  API keys". We use deterministic detectors for hard rules and reserve LLM scoring for nuance.

## Trade-offs
- Deterministic regex detectors can over/under-match; mitigated by defense in depth (regex +
  sensitivity classifier + approval queue) and the eval/adversarial suite.
- A single choke point is a potential bottleneck, but it is the property that makes safety provable.

## Consequences
- Implemented in `app/services/policy_broker.py` with detectors in `app/core/redaction.py`.
- Sensitive content with `require_approval_for_sensitive` becomes `pending` (not retrievable).
- Secret-like content is `BLOCK`ed and never written; only an audit record remains.

## Exit strategy
Promote rules into a versioned policy bundle (e.g., OPA/Rego or a rules table) so policies can change
without code deploys; keep the broker interface stable.
