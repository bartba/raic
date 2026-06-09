from main import create_app


def test_create_app_registers_expected_routes():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/health" in paths
    assert "/ready" in paths
    assert "/metrics" in paths
    assert "/v1/classify" in paths


def test_create_app_accepts_optional_runtime_state():
    settings = object()
    schema_manager = object()
    vector_store = object()
    embedder_client = object()
    llm_client = object()
    pipeline = object()

    app = create_app(
        settings=settings,
        schema_manager=schema_manager,
        vector_store=vector_store,
        embedder_client=embedder_client,
        llm_client=llm_client,
        pipeline=pipeline,
    )

    assert app.state.settings is settings
    assert app.state.schema_manager is schema_manager
    assert app.state.vector_store is vector_store
    assert app.state.embedder_client is embedder_client
    assert app.state.llm_client is llm_client
    assert app.state.pipeline is pipeline


def test_create_app_records_bootstrap_error_without_fail_fast():
    app = create_app(settings=object(), bootstrap_runtime=True)

    assert hasattr(app.state, "bootstrap_error")
    assert not hasattr(app.state, "pipeline")
