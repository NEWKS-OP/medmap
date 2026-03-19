import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dependencies import close_db
from api.routers import (
    pipeline,
    upload,
    overview,
    agents,
    patients,
    alerts,
    quality,
    ask,
    corrections,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MEDMAP API starting up - v1.0.0")
    yield
    logger.info("MEDMAP API shutting down - closing connections")
    close_db()


app = FastAPI(
    title="MEDMAP API",
    version="1.0.1",
    description="Smart Health Data Mapping API — 27 endpoints for medical data pipeline, 9 routers",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline.router, prefix="/api/pipeline", tags=["pipeline"])
app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(overview.router, prefix="/api/overview", tags=["overview"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(quality.router, prefix="/api/quality", tags=["quality"])
app.include_router(ask.router, prefix="/api/ask", tags=["ask"])
app.include_router(corrections.router, prefix="/api/corrections", tags=["corrections"])


@app.get("/")
async def root():
    return {"name": "MEDMAP API", "version": "1.0.0", "status": "running", "endpoints": 27}


@app.get("/health")
async def health():
    try:
        from api.dependencies import get_db
        db = get_db()
        count = db.execute("SELECT COUNT(*) as cnt FROM tbCaseData").fetchone()["cnt"]
        return {"status": "ok", "db_connected": True, "cases_count": count, "api_version": "1.0.0"}
    except Exception as e:
        return {"status": "degraded", "db_connected": False, "error": str(e), "api_version": "1.0.0"}
