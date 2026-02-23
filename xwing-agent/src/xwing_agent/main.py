"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from xwing_agent.api.routes import router
from xwing_agent.config import get_settings
from xwing_agent.logging_config import get_logger, setup_logging

setup_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(f"Starting X-Wing Agent on {settings.api_host}:{settings.api_port}")
    yield
    logger.info("Shutting down X-Wing Agent")


app = FastAPI(
    title="X-Wing AI Agent",
    description="LLM-powered AI for X-Wing Miniatures Game",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "xwing_agent.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
    )
