from fastapi import FastAPI

from app.config import settings
from app.routers.chat import router as chat_router

app = FastAPI(
    title="Claude Support SAP AI",
    description="AI-powered SAP support assistant powered by Claude",
    version="0.1.0",
)

app.include_router(chat_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
