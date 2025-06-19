# ADR-0003 – Monorepo Migration & Refactor

**Status**: Draft  
**Created**: {{DATE}}  
**Author**: PrivateGPT Engineering

---

## 1. Context

The codebase currently mixes micro-service logic, shared helpers and utility
scripts in a flat directory tree.  Duplicate code, large files (>400 LOC) and
a lack of strong module boundaries make maintenance hard and exceed LLM context
windows when auto-generating code or analysing issues.

To address this we are migrating to a mono-repo layout rooted under
`src/privategpt/` with Clean Architecture layering:

1. **core** – pure domain + CQRS
2. **infra** – adapters to external tech (Weaviate, Ollama, SQL, Redis)
3. **services** – FastAPI/Streamlit entrypoints (edge layer)
4. **shared** – cross-cutting helpers (config, security, logging, clients)

## 2. Goals

* Single import-able package (`privategpt`) installable via
  `pip install -e .`
* No duplicate code across services.
* Every file ≤ 300 LOC where feasible; routers ≤ 200 LOC.
* ≥ 70 % unit-test coverage (core + shared) and ≥ 90 % typed with `mypy
  --strict`.
* Zero downtime migration for production containers.

## 3. Out-of-Scope

* Re-writing business logic (functionality parity expected).
* Moving away from FastAPI (kept).
* Database schema changes (minimal metadata differences may occur but no
  destructive ALTERs).

## 4. Target Directory Tree (excerpt)

```text
src/privategpt/
  core/                 # domain + CQRS
  infra/
    weaviate/
    ollama/
    database/
    redis/
  shared/
  services/
    auth/
    knowledge/
    ui/
```
See ADR-0002 for full tree.

### 4.1 Full File Structure Example

```text
src/privategpt/
  core/
    domain/
      entities/
        document.py
        user.py
      ports/
        document_repository.py
        user_repository.py
      commands/
        add_document.py
        delete_document.py
      queries/
        get_document.py
        search_documents.py
    application/
      command_handlers/
        add_document_handler.py
        delete_document_handler.py
      query_handlers/
        get_document_handler.py
        search_documents_handler.py
  infra/
    weaviate/
      repository.py
    ollama/
      embedding_provider.py
    database/
      session.py
      repositories/
        document_repository.py
        user_repository.py
    redis/
      client.py
  shared/
    config.py
    security.py
    logging.py
    auth_client.py
  services/
    auth/
      main.py
      routers/
        auth_router.py
      schemas/
        user.py
    knowledge/
      main.py
      routers/
        document_router.py
        search_router.py
        chat_router.py
      schemas/
        document.py
        search.py
        chat.py
    ui/
      main.py
      pages/
        auth_page.py
        knowledge_page.py
        chat_page.py
```

## 5. Migration Phases

| Phase | Deliverable | Key Tasks |
|-------|-------------|-----------|
| 0 | Branch + skeleton | Create `src/` pkg, add `pyproject.toml`, pre-commit config |
| 1 | Shared layer | Move `config_loader`, logging, security, duplicated clients |
| 2 | Core layer   | Implement domain entities + ports + CQRS commands |
| 3 | Infra layer  | Adapt Weaviate, Ollama, Redis, SQLAlchemy session |
| 4 | Auth service | Rewrite using new layers (**done**) |
| 5 | Knowledge svc | a) Move Pydantic schemas<br>b) Refactor routers to use core commands<br>c) Replace Celery tasks with command calls |
| 6 | UI (Streamlit) | Update imports, replace old `auth_client` |
| 7 | Testing | Add unit + contract + e2e tests; configure GitHub Actions |
| 8 | Cleanup | Delete legacy folders, update docker-compose, tag release |

### 5.1 Phase 5 Detailed Steps

1. `schemas.py` → `services/knowledge/schemas/` split into
   `document.py`, `search.py`, `chat.py`.
2. Introduce `services/knowledge/service.py` that wires:
   * `WeaviateDocumentRepository`
   * `DefaultTextSplitter`
   * `OllamaEmbeddingProvider`
   * Core command handlers (`AddDocumentHandler`, etc.)
3. Break `routers/documents.py` into sub-routers:
   * `upload_router.py`
   * `admin_router.py`
4. Delete legacy directory `docker/knowledge-service/app` once parity tests
   pass.

## 6. File/Module Mapping

| Old Path | New Path | Notes |
|----------|----------|-------|
| `docker/auth-service/security.py` | `shared/security.py` | Slimmed, stateless |
| `docker/knowledge-service/app/services/auth_client.py` | `shared/auth_client.py` | Single source |
| `docker/knowledge-service/app/services/weaviate_client.py` | `infra/weaviate/repository.py` | Adapter implements `DocumentRepository` |
| `docker/knowledge-service/app/services/chunking.py` | `infra/text_splitter.py` | Wrapper for `split_text_into_chunks` |

Full mapping maintained in `docs/mapping.csv` (to be generated).

## 7. Database & Data

Auth service now defaults to SQLite for local dev; production continues to use
PostgreSQL via `DATABASE_URL`. Alembic migrations will be generated after the
initial port. No data loss expected.

Knowledge service uses Weaviate; schema initialisation stays in infra adapter.

## 8. Configuration & Secrets

* `.env` moves to `/env/` folder with one file per service (auth.env,
  knowledge.env).
* `shared.settings` wraps `pydantic.BaseSettings` (future ticket) with Redis
  overrides.

## 9. CI/CD Plan

1. Pre-commit: black, ruff, mypy, markdown-lint.  
2. GitHub Actions matrix (py3.9-3.12) runs:
   * `pip install -e .[dev]`
   * `pytest -q`
   * `mypy src/privategpt`
3. Docker images rebuilt via Buildx and pushed with semantic-release tags.

## 10. Testing Strategy

* **Unit tests** – core & shared, pure functions (fast).
* **Contract tests** – infra adapters with Weaviate/Ollama testcontainers.
* **Integration tests** – service endpoints using `httpx.AsyncClient` &
  in-memory SQLite.
* **E2E** – Docker-compose up, run happy path scenario (upload, search, chat).

Coverage gate ≥ 70 % lines, `--cov=src/privategpt`.

## 11. Roll-back

Because services are containerised we can roll back by re-deploying the `v1`
Docker tags if migration fails. Data migrations are additive.

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Hidden coupling to legacy paths | Runtime errors | CI static import scan |
| Larger image size due to duplicate dependencies | Build fails | Consolidate `pyproject.toml` extras |
| Test coverage drop during port | Bugs leak | Coverage gate in CI |

## 13. Open Questions

1. Should we keep Celery or switch to RQ / background tasks?  
2. Do we spin off `privategpt-ui` as separate repo in future?

---

### Decision

Approved by lead engineer on {{DATE}}. Proceed with phased migration. 


privategpt/
├── 📄 README.md
├── 📄 docker-compose.yml            # Orchestration (Traefik, ELK, services)
├── 📁 docker/                       # Lightweight container build context
│   ├── 🐳 auth/                     # → builds src/privategpt/services/auth
│   │   └── 📄 Dockerfile
│   ├── 🐳 knowledge/
│   │   └── 📄 Dockerfile
│   ├── 🐳 ui/
│   │   └── 📄 Dockerfile
│   └── (other infra images…) 
├── 📁 env/                          # Never committed secrets
│   └── 📄 .env.example
├── 📁 scripts/                      # One-off ops utilities
│   ├── init-ollama.sh
│   ├── setup-dashboard.sh
│   └── …
├── 📁 docs/                         # Human + AI documentation
│   ├── adr/                         # Architecture Decision Records
│   │   └── 0001-initial-structure.md
│   ├── api/                         # Rendered FastAPI / OpenAPI specs
│   ├── ai/                          # LLM-friendly JSON service manifests
│   │   ├── knowledge-service.json
│   │   └── auth-service.json
│   ├── diagrams/                    # Auto-generated mermaid graphs
│   └── index_ai.yml                 # TOC for programmatic retrieval
├── 📁 tests/                        # Top-level for e2e (pytest –k "e2e")
│   ├── e2e/
│   │   └── test_full_flow.py
│   └── data/                        # fixtures, golden outputs
└── 📁 src/                          # Editable install: `pip install -e .`
    └── privategpt/
        ├── __init__.py
        ├── shared/                  # Cross-cutting helpers
        │   ├── __init__.py
        │   ├── settings.py          # Pydantic Settings, Redis overrides
        │   ├── logging.py           # JSON/structured logs
        │   ├── security.py          # JWT & password utils
        │   ├── auth_client.py       # Reusable client for Auth service
        │   ├── exceptions.py
        │   └── types.py             # Common pydantic models
        ├── core/                    # Pure business/domain logic
        │   ├── __init__.py
        │   ├── domain/              # Entities & value objects
        │   │   ├── __init__.py
        │   │   ├── document.py
        │   │   └── user.py
        │   ├── commands/            # Mutations (CQRS)
        │   │   ├── __init__.py
        │   │   ├── add_document.py
        │   │   └── delete_document.py
        │   └── queries/             # Reads (CQRS)
        │       ├── __init__.py
        │       ├── search_documents.py
        │       └── list_documents.py
        ├── infra/                   # Adapters to external tech
        │   ├── __init__.py
        │   ├── weaviate/
        │   │   ├── __init__.py
        │   │   ├── client.py
        │   │   └── repository.py
        │   ├── ollama/
        │   │   ├── __init__.py
        │   │   └── llm_client.py
        │   ├── redis/
        │   │   ├── __init__.py
        │   │   └── cache.py
        │   └── database/
        │       ├── __init__.py
        │       ├── models.py        # SQLAlchemy / Tortoise
        │       └── session.py
        ├── services/                # Edge/boundary layers
        │   ├── auth/
        │   │   ├── __init__.py
        │   │   ├── router.py        # FastAPI router
        │   │   ├── schemas.py       # Pydantic DTOs
        │   │   ├── service.py       # Orchestration logic
        │   │   └── main.py          # FastAPI entrypoint (asgi)
        │   ├── knowledge/
        │   │   ├── __init__.py
        │   │   ├── routers/
        │   │   │   ├── __init__.py
        │   │   │   ├── documents.py
        │   │   │   ├── search.py
        │   │   │   └── admin.py
        │   │   ├── schemas/
        │   │   │   ├── __init__.py
        │   │   │   ├── document.py
        │   │   │   └── search.py
        │   │   ├── service.py       # Application layer (uses core + infra)
        │   │   ├── tasks.py         # Celery / RQ tasks
        │   │   └── main.py
        │   └── ui/                  # Streamlit app (thin)
        │       ├── __init__.py
        │       ├── app.py
        │       └── pages/
        │           ├── dashboard.py
        │           ├── document_management.py
        │           ├── rag_chat.py
        │           └── …
        └── tests/                   # Unit + contract tests, mirrors packages
            ├── unit/
            │   ├── core/
            │   │   └── test_add_document.py
            │   ├── shared/
            │   │   └── test_settings.py
            │   └── …
            ├── contracts/
            │   ├── infra/
            │   │   └── test_weaviate_client.py
            │   └── …
            └── conftest.py          # Pytest fixtures