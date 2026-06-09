from fastapi import FastAPI

from config import Settings
from middleware.auth_mw import configure_auth
from middleware.logging_mw import configure_logging
from middleware.metrics_mw import configure_metrics
from routers.classify import router as classify_router
from routers.health import router as health_router
from services.bootstrap import build_runtime_components


def create_app(
    settings=None,
    schema_manager=None,
    vector_store=None,
    embedder_client=None,
    llm_client=None,
    pipeline=None,
    api_auth_token=None,
    logger=None,
    metrics_registry=None,
    bootstrap_runtime: bool = False,
    fail_fast: bool = False,
) -> FastAPI:
    app = FastAPI(title="RAIC Command Interpreter")
    bootstrap_error = None

    if bootstrap_runtime and settings is None:
        try:
            settings = Settings()
        except Exception as error:
            bootstrap_error = error

    configure_metrics(app, registry=metrics_registry)
    configure_logging(app, logger=logger)
    if settings is not None and api_auth_token is None:
        api_auth_token = getattr(settings, "api_auth_token", None)
    configure_auth(app, token=api_auth_token)

    app.include_router(health_router)
    app.include_router(classify_router)

    if bootstrap_runtime and bootstrap_error is None:
        try:
            runtime = build_runtime_components(
                settings=settings,
                schema_manager=schema_manager,
                vector_store=vector_store,
                embedder_client=embedder_client,
                llm_client=llm_client,
            )
            settings = runtime.settings
            schema_manager = runtime.schema_manager
            vector_store = runtime.vector_store
            embedder_client = runtime.embedder_client
            llm_client = runtime.llm_client
            pipeline = runtime.pipeline
        except Exception as error:
            bootstrap_error = error

    if settings is not None:
        app.state.settings = settings
    if schema_manager is not None:
        app.state.schema_manager = schema_manager
    if vector_store is not None:
        app.state.vector_store = vector_store
    if embedder_client is not None:
        app.state.embedder_client = embedder_client
    if llm_client is not None:
        app.state.llm_client = llm_client
    if pipeline is not None:
        app.state.pipeline = pipeline
    if bootstrap_error is not None:
        app.state.bootstrap_error = str(bootstrap_error)
        if fail_fast:
            raise RuntimeError("application bootstrap failed") from bootstrap_error

    return app


app = create_app(bootstrap_runtime=True)
