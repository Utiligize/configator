# Architecture Decision Records

## Table of Contents

- [Table of Contents](#table-of-contents)
- [ADR-001: Use Structlog for logging](#adr-001-use-structlog-for-logging)
- [ADR-002: Cache resolved secrets](#adr-002-cache-resolved-secrets)
- [ADR-003: Validate Pydantic models after loading](#adr-003-validate-pydantic-models-after-loading)

## ADR-001: Use Structlog for logging

**Date:** 2025-11-12

**Context:**

We want the module to output structured logs.

**Decision:**

Use [structlog](https://www.structlog.org/) for log messages.

**Consequences:**

- Benefits
  - Emits structured, machine-readable logs (JSON, key/value) that are easy to index and query in log stores (ELK, Loki, Datadog).
  - Encourages consistent log schema and contextual logging (event-wise context, bound processors).
  - Easier to attach contextual data (request id, user id) without string formatting.
  - Simpler testing and assertions against emitted events.
  - Flexible output pipelines — processors can format, filter, redact, or enrich events centrally.

- Costs / Trade-offs
  - Adds a runtime dependency (structlog) and requires team familiarity with its API and concepts (processors, bind, event_dict).
  - Slight configuration complexity to wire structlog with Python's stdlib logging and third‑party libraries.
  - Possible performance overhead if many expensive processors are used; careful processor design is required.

- Operational considerations
  - Decide a canonical output format (JSON for ingestion systems or human console format for local dev).
  - Standardize event and field names to avoid fragmentation across services.
  - Implement redaction/PII handling as processors.
  - Ensure log rotation/retention and existing monitoring tooling accept the chosen format.

- Developer impact
  - Improves debuggability and observability long term.
  - Requires documentation and examples for developers to adopt consistent usage.
  - Tests should assert on structured events instead of formatted strings.

## ADR-002: Cache resolved secrets

**Date:** 2025-11-12

**Context:**

Secret references (`op://...`) may be used multiple times or reference each other recursively. Each resolution requires an API call to 1Password, which adds latency and API usage.

**Decision:**

Implement an in-memory cache for resolved secrets within a Config instance to avoid redundant API calls.

**Consequences:**

- Benefits
  - Reduces API calls to 1Password
  - Improves performance for repeated access
  - Prevents unnecessary network overhead for recursive references
  - Reduces load on 1Password infrastructure

- Costs / Trade-offs
  - Secrets cached in memory for the lifetime of the Config object
  - Stale data if secrets change during Config lifetime
  - Increased memory usage proportional to number of secrets
  - Cache is not shared across Config instances

- Operational considerations
  - Cache is instance-scoped, not global
  - No TTL or invalidation mechanism (recreate Config for fresh data)
  - Memory contains sensitive data until garbage collection

- Developer impact
  - Transparent to users (implementation detail)
  - Config instances should be short-lived in sensitive contexts
  - No API changes required

## ADR-003: Validate Pydantic models after loading

**Date:** 2025-11-12

**Context:**

When Pydantic BaseModel templates are provided, we need to ensure loaded config data conforms to the expected schema and types.

**Decision:**

Use Pydantic's validation to parse and validate loaded config data against provided BaseModel schemas.

**Consequences:**

- Benefits
  - Type safety for loaded configuration
  - Clear error messages for schema mismatches
  - Automatic type coercion where appropriate
  - Runtime validation of configuration structure
  - Leverages Pydantic's robust validation features

- Costs / Trade-offs
  - Validation overhead at load time
  - Requires all config schemas to be defined as Pydantic models
  - Validation errors may occur at runtime rather than deploy time

- Developer impact
  - Define config schemas as Pydantic BaseModel classes
  - Clear validation errors when config doesn't match schema
  - Type hints provide IDE support and documentation
