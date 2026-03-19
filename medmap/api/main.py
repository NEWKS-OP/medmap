from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

app = FastAPI(title="MEDMAP API", version="1.0.0", description="Smart Health Data Mapping API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
    return {"name": "MEDMAP API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
