from types import SimpleNamespace

from fastapi import Response

from routers.health import health, metrics, ready


def make_request_state(**state):
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(**state)))


def test_health_returns_ok():
    assert health() == {"status": "ok"}


def test_ready_returns_not_ready_without_required_state():
    response = Response()

    body = ready(make_request_state(), response)

    assert response.status_code == 503
    assert body == {
        "status": "not_ready",
        "checks": {
            "schema": False,
            "index": False,
            "settings": False,
            "pipeline": False,
        },
    }


def test_ready_returns_ok_with_required_state():
    response = Response()

    body = ready(
        make_request_state(
            schema_manager=object(),
            vector_store=object(),
            settings=object(),
            pipeline=object(),
        ),
        response,
    )

    assert response.status_code == 200
    assert body == {
        "status": "ok",
        "checks": {
            "schema": True,
            "index": True,
            "settings": True,
            "pipeline": True,
        },
    }


def test_ready_returns_bootstrap_error_when_present():
    response = Response()

    body = ready(
        make_request_state(
            schema_manager=object(),
            vector_store=object(),
            settings=object(),
            pipeline=object(),
            bootstrap_error="cannot load vector store",
        ),
        response,
    )

    assert response.status_code == 503
    assert body["status"] == "not_ready"
    assert body["bootstrap_error"] == "cannot load vector store"


def test_metrics_returns_prometheus_payload():
    response = metrics(make_request_state())

    assert response.status_code == 200
    assert "text/plain" in response.media_type
    assert b"python_info" in response.body
