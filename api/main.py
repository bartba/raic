from fastapi import FastAPI

from routers.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="RAIC Command Interpreter")
    app.include_router(health_router)
    return app


app = create_app()
