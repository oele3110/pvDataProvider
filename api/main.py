import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import auth, routes_history, routes_live, routes_status
from collector.collector_service import CollectorService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    collector = CollectorService()
    app.state.collector = collector
    await collector.start()
    logger.info("CollectorService started")
    yield
    await collector.stop()
    logger.info("CollectorService stopped")


def create_app() -> FastAPI:
    app = FastAPI(title="PV Monitor API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # tighten for production if needed
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router, prefix="/api")
    app.include_router(routes_status.router, prefix="/api")
    app.include_router(routes_history.router, prefix="/api")
    app.include_router(routes_live.router)  # WebSocket at /ws (no /api prefix)

    return app


app = create_app()
