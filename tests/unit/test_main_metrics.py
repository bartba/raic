from prometheus_client import CollectorRegistry

from main import create_app


def test_create_app_configures_metrics_registry():
    registry = CollectorRegistry()

    app = create_app(metrics_registry=registry)

    assert app.state.metrics_registry is registry
    assert "request_count" in app.state.metrics
