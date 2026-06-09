from fastapi import APIRouter, HTTPException, Request, status

from middleware.metrics_mw import record_classify_decision, record_external_timeout
from models.request import ClassifyRequest
from models.response import ClassifyResponse

router = APIRouter(prefix="/v1")


@router.post("/classify", response_model=ClassifyResponse)
def classify(request: Request, payload: ClassifyRequest) -> ClassifyResponse:
    pipeline = getattr(request.app.state, "pipeline", None)
    if pipeline is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="classification pipeline is not ready",
        )

    response = pipeline.classify(payload)
    record_classify_decision(request, response.decision, response.intent)
    _record_timeout_metrics(request, response)
    return response


def _record_timeout_metrics(request: Request, response: ClassifyResponse) -> None:
    reason_text = " ".join(response.policy_reasons).lower()
    if "embedder" in reason_text and "timed out" in reason_text:
        record_external_timeout(request, "embedder")
    if "llm" in reason_text and "timed out" in reason_text:
        record_external_timeout(request, "llm")
