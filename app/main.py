from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db.mongo import close_client, ensure_help_indexes
from app.routers.chat import router as chat_router
from app.routers.help import router as help_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create the help indexes on startup, release the Mongo client on shutdown.

    A database that is unreachable at startup is logged rather than fatal — the
    API still serves `/api/health`, which reports the failure.
    """
    try:
        await ensure_help_indexes()
        app.state.database_ready = True
        app.state.database_error = ""
    except Exception as exc:  # startup must not hard-fail on Mongo
        app.state.database_ready = False
        app.state.database_error = f"{type(exc).__name__}: {exc}"
        print(f"WARNING: MongoDB unavailable at startup — {app.state.database_error}")
    try:
        yield
    finally:
        await close_client()


app = FastAPI(
    title="Claude Support SAP AI",
    description="AI-powered SAP support assistant powered by Claude",
    version="0.2.0",
    lifespan=lifespan,
)

app.include_router(chat_router)
app.include_router(help_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
