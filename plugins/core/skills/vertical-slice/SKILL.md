---
name: vertical-slice
user-invocable: false
metadata:
  type: reference
description: |
  Enforce vertical slice architecture for Python backend features in this project.
  Covers feature directory scaffolding, layer separation (API/Service/Storage),
  one-class-per-file convention, prompt-as-view pattern, enum placement, import rules,
  and anti-patterns. Use when: creating new backend features, adding files to existing
  features, reviewing feature structure, or troubleshooting circular imports between features.
---

# Vertical Slice Architecture - Python Backend

## When This Skill Activates

- Creating a new backend feature from scratch
- Adding files (routes, services, models, entities) to an existing feature
- Reviewing or refactoring feature structure
- Resolving import errors between features

## Core Rules

1. **Feature-centric**: Code lives in `backend/app/features/{feature_name}/`, not by technical layer.
2. **One class per file**: File named in `snake_case` matching the class. Rare exceptions only.
3. **Layer flow**: `API -> Service -> Storage`. Never reverse.
4. **No cross-feature imports**: Features talk through internal APIs or shared `core` modules.
5. **Absolute imports only**: `from app.features.{feature}.services import {Feature}Service`. No relative imports.
6. **Import from package `__init__.py`**: Not from deep file paths.

## Feature Directory Template

```
backend/app/features/{feature_name}/
├── __init__.py
├── README.md                          # Feature docs (keep in sync with onboarding)
├── dependencies.py                    # FastAPI DI overrides
├── constants.py                       # Feature constants
├── prompts/                           # Prompt templates (if LLMs used)
│   └── {template_name}/
│       ├── system.txt                 # System instructions
│       └── user.txt                   # User data template with placeholders
├── config/
│   ├── __init__.py                    # Re-export public config API
│   ├── {feature}_settings.py          # Pydantic settings (one class)
│   ├── domain_tables.py               # Mapping/weights (optional)
│   └── business_rules.py              # Rule thresholds (optional)
├── exceptions/
│   ├── __init__.py
│   └── {exception_name}.py            # One exception class per file
├── api/
│   ├── __init__.py
│   ├── routes.py                      # Public FastAPI endpoints
│   ├── internal_routes.py             # JWT-authenticated internal endpoints
│   ├── decorators.py                  # Feature-specific auth/logging/error mapping
│   ├── converters.py                  # API model <-> service model conversion
│   ├── enums.py                       # API-layer enums (OpenAPI)
│   └── models/
│       ├── __init__.py
│       ├── {response_name}.py         # One response class per file
│       └── internal/
│           ├── __init__.py
│           └── {model_name}.py        # Internal API models
├── services/
│   ├── __init__.py
│   ├── {feature}_service.py           # Main service
│   ├── prompt_loader.py               # Prompt template loader (if LLMs)
│   ├── prompt_builder.py              # Prompt builder (if LLMs)
│   ├── enums/
│   │   ├── __init__.py
│   │   └── {enum_name}.py             # Business-only enums (one per file)
│   └── models/
│       ├── __init__.py
│       ├── ai_requests/               # DTOs for prompt building
│       │   └── {request_name}.py
│       ├── ai_responses/              # AI provider response contracts
│       │   └── {response_name}.py
│       └── internal/                  # Shared service-layer DTOs
│           └── {model_name}.py
├── storage/
│   ├── __init__.py
│   ├── enums/                         # Persisted enums (used in ORM columns)
│   │   ├── __init__.py
│   │   └── {enum_name}.py
│   ├── entities/                      # SQLAlchemy models
│   │   ├── __init__.py
│   │   └── {entity_name}.py
│   └── repositories/                  # DB access encapsulation
│       ├── __init__.py
│       └── {repository_name}.py
├── utils/
│   ├── __init__.py
│   └── {utility_name}.py
└── tests/
    ├── __init__.py
    ├── test_api.py
    ├── test_services.py
    └── test_storage.py
```

## Scaffolding a New Feature

```bash
FEATURE=my_feature
mkdir -p backend/app/features/${FEATURE}/{api/models/internal,services/models/{ai_requests,ai_responses,internal},services/enums,storage/{entities,enums,repositories},config,exceptions,utils,tests}
find backend/app/features/${FEATURE} -type d -exec touch {}/__init__.py \;
```

Then register the router in `backend/app/api/api.py`:
```python
from app.features.{feature}.api.routes import router as {feature}_router
api_router.include_router({feature}_router, prefix="", tags=["{Feature}"])
```

## Layer Responsibilities

### API Layer
- Thin route handlers: validate input, call service, return response.
- Use feature `decorators.py` for auth token extraction, logging context, exception-to-HTTP mapping.
- Set logging context once at API entry; services log directly.
- Models optimized for HTTP: request schemas, response schemas, error responses.

### Service Layer
- All business logic and domain rules.
- Async I/O for all network/DB operations.
- Inject storage via protocols; keep testable.
- Split long workflows into helpers.

### Storage Layer
- SQLAlchemy entities, repositories, Alembic migrations.
- Repositories encapsulate all DB access; services never write raw SQL.
- Enums in `storage/enums/` are persisted and used in ORM columns.

## Enum Placement

| Enum Type | Location | Example |
|-----------|----------|---------|
| Persisted (DB columns) | `storage/enums/` | e.g., `ItemCategory`, `RecordStatus` |
| Business-only | `services/enums/` | e.g., `ScoreDelta`, `WeightLevel` |
| OpenAPI contract | `api/enums.py` or `api/models/` | Response status enums |
| WebSocket events | `core/websocket/models/` | `RealtimeOutboundEvent`, `RealtimeInboundEvent` |

Import via package: `from app.features.{feature}.storage.enums import ItemCategory`

WebSocket event enums are **never** feature-specific — import from `app.core.websocket.models`.

## Core AI Provider Abstractions

AI provider implementations (protocols, client wrappers, provider-specific configs) live in
`core/ai/{capability}/`, **not** inside feature slices:

```
core/ai/
├── chat/          # ChatProtocol + OpenAIChatClient
├── realtime/      # RealtimeProtocol + OpenAIRealtimeClient
└── {capability}/  # New capabilities follow the same pattern
```

Each capability follows the pattern: `Protocol` + `Factory` + provider implementations.
Features consume these via DI; the business logic stays in the feature slice.

## External Client Layering

When an external API has more than one calling pattern, OR non-trivial policy (fail-open vs
fail-closed per error class, fire-and-forget consume, accept-both-during-a-status-migration), do NOT
let callers use the raw HTTP client — each caller will reinvent the policy and they drift. Layer it:

- `_xxx_client.py` — **private** HTTP transport (leading underscore), raises typed exceptions, returns typed models.
- `xxx_service.py` — **public** behavioral wrapper that owns the policy; the only thing routes/decorators call.
- `__init__.py` re-exports the service, its protocol, exceptions, and enums — but **not** the client.

Tests construct the service with `MagicMock(spec=Protocol)`; never patch the client. When a new system
replaces an old one, place new code under the **new** module's namespace immediately (readers grep by
domain name, not the historical path) — even if the old module is still importable.

## Prompt-as-View Pattern (LLM Features)

- **Prompts are views**: `.txt` templates format data for AI.
- **Models are DTOs**: Pydantic models structure data for prompt building and response parsing.
- Request models go in `services/models/ai_requests/`.
- Response models go in `services/models/ai_responses/`.
- Use `PromptTemplate` enum for type-safe template names.
- Use prompt loader with validation + caching.
- Centralize generation params in settings; no hardcoded temps/tokens.

### Prompt Storage

- **Local**: `prompts/{feature}/` at repo root (Docker-mounted to `/app/prompts/{feature}/`).
- **Cloud**: Same path structure in object storage (e.g., a GCS bucket).
- Config: `prompts_dir = "{feature}"` in feature settings.

## Anti-Patterns (Feature-Specific)

For the full convention rules and "Do not" list, see AGENTS.md.
For import and code style examples, see the installed language-conventions skill.

These are vertical-slice-specific anti-patterns:

- Circular feature dependencies (features talk through internal APIs, not direct imports)
- God services (too many responsibilities — split into focused services)
- Magic strings in AI responses (use typed response models in `ai_responses/`)
- Raw dicts for prompt building (use request models in `ai_requests/`)
- Mixing AI response models with internal utility models

## Refactoring a Slice — Moves & Deletes

- **Moving an entity** into/out of a feature: update `app/storage/models/__init__.py` to re-import it
  from the new path, or Alembic autogenerate silently skips the table.
- **Before MOVING a file into a feature**, grep every consumer across `backend` AND `tests`. If any
  consumer is in `core/` or another feature, it must stay shared (`app/services/`) — moving it inverts
  the import direction. (Run plan-critic to catch these.)
- **Before DELETING "dormant/unused" infra**, grep `backend` + `tests` for the symbol — a spec's
  "this is unused" is frequently one call site stale (a guarded no-op consumer). The grep, not the
  design doc, is the source of truth.
- **Removing a system that consumed a JWT claim / request attribute**: audit the whole life cycle —
  writer → parser → storage → *readers*. If nothing reads it to make a decision anymore, delete the
  parse/propagate path in the same PR. A static grep finds the writers and echo-back layer and hides
  that the consumer is gone; grep `\.get("claim")`, `payload["claim"]`, and typed-container accesses.

## Config Pattern

```python
# config/__init__.py re-exports:
from app.features.{feature}.config import {Feature}Settings, DomainTables, BusinessRules

# Usage:
settings = {Feature}Settings()
```

## Registry/Pipeline Extension Points (conflict-free decomposition)

When decomposing an if/elif churn axis (event dispatch, action dispatch, ordered phases) into
registries/pipelines, drive them from **append-only ordered registration modules** (one list-literal
per axis, e.g. `event_behavior_registrations.py`) — adding a feature = new file + one list append;
no existing handler/router is touched, so merge conflicts vanish by construction. Two contracts make
it work:

- **Composition-root chicken-and-egg**: steps/behaviors need the session reference, but the session
  needs them wired. Build the session first, wire the registry/pipeline against it via a composition
  helper, AND have the facade self-wire defaults from the SAME registration tables when not injected
  (so direct-construction tests still get a working session).
- **Per-handler isolation drops client-error contracts**: a router that logs-and-continues per
  handler swallows the client-facing ERROR a decorator used to emit. Wrap each handler in an
  error-shaping adapter at the composition root (log + send client ERROR + swallow→continue).
- Sibling features converge by MIRRORING the structure, never cross-importing — if both need it,
  the abstraction belongs in `core/`.

## Before Adding a Channel, Inventory What the Consumer Already Receives

When a component lacks a discriminator, the reflex is a new channel — a protocol method, a session
hook, a no-op for the sibling strategy, plus wiring. Inventory the fields on the objects it is
**already handed** first. The stereo assembler could not distinguish "a pause inside one spoken
turn" from "two distinct turns", and the discriminator was already in its own input:
`StereoBatcher` records a `TurnBoundary` at every `response.created` and `_create_batch` attaches
them to `TranscriptionBatch.turn_boundaries` — a field the stereo assembler received on every batch
and never read (only the mono assembler consumed it). Reading it made the fix one file with no
plumbing.

The cheaper design was also the **more correct** one, which is the usual shape: an existing field
is already in the producer's native units. The boundary is a buffer-length watermark — the same
coordinate frame as utterance times — so it needs no wall clock and no provider event-ordering
assumption, whereas the `current_position_seconds()` stamp it replaced would have reintroduced
clock skew. Watch especially for **two-implementation seams**, where one strategy routinely
populates a shared model field the other ignores: grep the shared dataclass's fields against each
consumer. At the time of the fix `batch.turn_boundaries` was read only by the MONO assembler —
that asymmetry was the whole finding. It now has readers in both (`stereo_transcript_assembly.py`
and `transcript_assembly.py`), so grepping it today shows a healthy seam; the lesson is the
diagnostic, not the current count.

## Composition-Root Facades Are Exempt from Line-Count NFRs

A session facade is a composition root: its residual is constructor wiring + the multi-Protocol
contract surface + design-mandated inline hot paths + thin delegators — not further decomposable
without churning every construction site for a metric. Set line-count NFRs on behaviors/handlers/
steps, NOT on composition-root facades; extract every genuinely separable concern, then document
the residual as a composition-root deviation (same reasoning as the dependency-count exemption).
