from typing import Dict

from fastapi import APIRouter, Request, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest

router = APIRouter()


@router.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(request: Request, response: Response) -> Dict[str, object]:
    checks = {
        "schema": hasattr(request.app.state, "schema_manager"),
        "index": hasattr(request.app.state, "vector_store"),
        "settings": hasattr(request.app.state, "settings"),
        "pipeline": hasattr(request.app.state, "pipeline"),
    }
    bootstrap_error = getattr(request.app.state, "bootstrap_error", None)
    is_ready = all(checks.values()) and bootstrap_error is None
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    body = {
        "status": "ok" if is_ready else "not_ready",
        "checks": checks,
    }
    if bootstrap_error is not None:
        body["bootstrap_error"] = bootstrap_error

    return body


@router.get("/metrics")
def metrics(request: Request) -> Response:
    registry = getattr(request.app.state, "metrics_registry", REGISTRY)
    return Response(
        content=generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )
