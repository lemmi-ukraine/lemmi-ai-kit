# Coding Patterns Reference — Python Backend

Detailed implementation patterns for error handling, HTTP clients, dependency injection,
authentication, and feature decorators. Read this file when implementing services that
involve cross-feature communication, external API calls, or route boilerplate reduction.

## Error Handling Architecture

The application uses **centralized error handling** via `UnifiedMiddleware`.

**Shared exceptions** (from `app.services.utils.errors`):
- `BadRequestError` (400), `UnauthorizedError` (401), `NotFoundError` (404),
  `ConflictError` (409), plus any project-specific shared exceptions
  (e.g. a 412 precondition error)

**Feature-specific exceptions** live in `features/{feature}/exceptions/` with a base class
and one exception per file. They are converted to shared exceptions at the API route boundary.

**Route exception conversion pattern:**
```python
try:
    return await service.get_resource(resource_id)
except ResourceNotFoundError as e:
    raise NotFoundError(str(e)) from e
except AccessDeniedError as e:
    raise UnauthorizedError(str(e)) from e
except YourFeatureServiceError as e:
    logger.error(f"Feature error: {str(e)}", exc_info=True)
    raise HTTPException(status_code=500, detail=str(e)) from e
```

**HTTPException is only acceptable** for non-standard status codes: 422, 410, 429, 500.

## Feature Route Decorators

Each feature should have a decorator in `api/decorators.py` that eliminates boilerplate:
- Exception mapping (feature → shared exceptions)
- Logging context initialization
- User ID extraction from `current_user`
- JWT token extraction (optional)

**Usage (after):**
```python
@router.get("/resources/{resource_id}")
@handle_your_feature_request(requires_auth_token=True, log_context_keys=['resource_id'])
async def get_resource(
    resource_id: UUID,
    current_user: dict = Depends(get_current_user_flexible),
    service: ResourceService = Depends(get_resource_service),
    auth_token: str = None,  # Injected by decorator
):
    return await service.get_resource(resource_id, current_user['id'], auth_token)
```

**Reference implementation:** `backend/app/features/<feature>/api/decorators.py` in any
feature that has adopted the pattern.

## HTTP Client Architecture

**Internal clients** (`BaseInternalClient`): Cross-feature communication with JWT auth.
**External clients** (`BaseExternalClient`): Third-party APIs with API key auth.
Both live in `backend/app/core/http/`.

```python
class BillingDataModifier(BaseInternalClient):
    def __init__(self, auth_token: str, logger: logging.Logger,
                 base_url: str | None = None, timeout: float = 10.0):
        super().__init__(base_url=base_url, auth_token=auth_token,
                         logger=logger, timeout=timeout)
```

**Key rules:**
- Auth token is REQUIRED (no `| None = None`)
- Logger is injected for testability
- Use enums, not magic strings
- Return Pydantic models, not raw dicts
- Use `_make_request()` and `_handle_response_status()` from base class

## Data Modifier Pattern

Data Modifiers are HTTP clients for cross-feature data updates:
- Live in the consuming feature's `services/` directory
- Non-blocking: failures should not prevent the primary operation
- Always wrap in try/except and log errors

```python
try:
    await self.billing_data_modifier.update_invoice_status(...)
except Exception as e:
    self.logger.error(f"Status update failed: {str(e)}", exc_info=True)
```

## Service Dependency Injection

Services receive dependencies through constructor injection:
- Repositories, HTTP clients, loggers, other services
- Factory functions in `features/{feature}/dependencies.py` resolve via FastAPI Depends
- Required dependencies have no default; optional use `| None = None`
- Tests mock at the DI boundary using protocol overrides

```python
async def get_order_task_service(
    request: Request,
    task_repo: OrderTaskRepository = Depends(get_order_task_repository),
) -> OrderTaskService:
    auth_token = extract_token_from_request(request)
    modifier = BillingDataModifier(auth_token=auth_token, logger=logger)
    return OrderTaskService(task_repo=task_repo, billing_data_modifier=modifier, logger=logger)
```

## Auth Token Flow

1. Extract token in route (via decorator or manual `extract_token_from_request()`)
2. Pass token to client constructor
3. Base client adds token to request headers
4. Internal endpoint validates JWT and user ownership

**Rules:** Never optional, fail fast, no token storage, secure logging (`[REDACTED]`).
