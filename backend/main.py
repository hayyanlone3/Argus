# backend/main.py
import sys
import os

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.shared.logger import setup_logger
from backend.database.connection import init_db

# Import all layer routers
from backend.layers.layer0_bouncer.routes import router as layer0_router
from backend.layers.layer1_graph_engine.routes import router as layer1_router
from backend.layers.layer2_scoring.routes import router as layer2_router
from backend.layers.layer3_correlator.routes import router as layer3_router
from backend.layers.layer4_response.routes import router as layer4_router
from backend.layers.layer4_response.policy_routes import router as policy_router
from backend.layers.layer5_learning.routes import router as layer5_router

# Layer 2 Engine
from backend.layers.layer2_scoring.runtime_engine import Layer2RuntimeEngine
# Layer 1 Ingestion
from backend.layers.layer1_graph_engine.ingestion import GraphIngestionWorker

# ML Models
from backend.ml.inference.model_loader import get_ml_loader

from backend.collectors.sysmon_collector import SysmonCollector

logger = setup_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.layers.layer2_scoring.event_stream import SCORING_QUEUE, GRAPH_QUEUE, EVENT_QUEUE
    from queue import Empty

    for q in [SCORING_QUEUE, GRAPH_QUEUE, EVENT_QUEUE]:
        while not q.empty():
            try:
                q.get_nowait()
            except Empty:
                break

    # STARTUP
    try:
        logger.info("=" * 80)
        logger.info("ARGUS Backend Initializing...")
        logger.info("=" * 80)

        init_db()

        # ML models - DISABLED for faster startup
        # Auto-scoring doesn't need ML models
        logger.info("ML models: Disabled (using rule-based auto-scoring for speed)")
        app.state.ml_loader = None

        # Layer 2 Runtime Engine - ENABLED for UI display
        # This populates the live event stream for Layer 2 dashboard
        app.state.layer2_engine = Layer2RuntimeEngine()
        app.state.layer2_engine.start()
        logger.info("Layer 2: Runtime engine enabled for UI event stream")

        app.state.graph_worker = GraphIngestionWorker()
        app.state.graph_worker.start()

        sm_enabled = os.getenv("ARGUS_SYSMON_ENABLED", "true").lower() == "true"
        poll_sec = float(os.getenv("ARGUS_SYSMON_POLL_SEC", "0.1"))  # Default to 0.1s for real-time
        app.state.sysmon = SysmonCollector(
            enabled=sm_enabled,
            poll_seconds=poll_sec,
            audit_enabled=os.getenv("ARGUS_AUDIT_ENABLED", "true").lower() == "true",
        )
        if sm_enabled:
            logger.info(f"Starting Sysmon collector (poll={poll_sec}s)")
            app.state.sysmon.start()
        else:
            logger.info("SysmonCollector disabled by ARGUS_SYSMON_ENABLED=false")

        # Learning scheduler - DISABLED for faster startup
        # Not needed for real-time detection
        logger.info("Learning scheduler: Disabled (not needed for real-time detection)")

        logger.info("=" * 80)
        logger.info("✅ ARGUS READY FOR REAL-TIME DETECTION")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        sys.exit(1)

    yield

    # SHUTDOWN
    # Stop Layer 2 engine
    try:
        e = getattr(app.state, "layer2_engine", None)
        if e:
            e.stop()
    except Exception as ex:
        logger.error(f"Failed to stop layer2 engine cleanly: {ex}")
    
    try:
        gw = getattr(app.state, "graph_worker", None)
        if gw:
            gw.stop()
    except Exception as ex:
        logger.error(f"Failed to stop graph worker cleanly: {ex}")

    try:
        sm = getattr(app.state, "sysmon", None)
        if sm:
            sm.stop()
    except Exception as e:
        logger.error(f"Failed to stop sysmon cleanly: {e}")

    logger.info("ARGUS Backend shutting down...")

app = FastAPI(
    title="ARGUS",
    description="Provenance Graph Anomaly Detection System",
    version="2.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.2.0",
        "environment": "development",
        "database": "connected",
        "api_url": "http://0.0.0.0:8000",
    }

# Layer 0: Bouncer
app.include_router(layer0_router, prefix="/api/layer0", tags=["Layer 0: Bouncer"])

# Layer 1: Graph Engine
app.include_router(layer1_router, prefix="/api/layer1", tags=["Layer 1: Graph Engine"])

# Layer 2: Scoring
app.include_router(layer2_router, prefix="/api/layer2", tags=["Layer 2: Scoring"])

# Layer 3: Correlator
app.include_router(layer3_router, prefix="/api/layer3", tags=["Layer 3: Correlator"])

# Layer 4: Response
app.include_router(layer4_router, prefix="/api/layer4", tags=["Layer 4: Response"])

# Layer 5: Learning
app.include_router(layer5_router, prefix="/api/layer5", tags=["Layer 5: Learning"])

# Policy Configuration
app.include_router(policy_router)

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "path": str(request.url),
            "message": f"Endpoint {request.url.path} not found",
        },
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    logger.error(f"Server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "detail": str(exc),
        },
    )

if __name__ == "__main__":
    import pathlib
    import uvicorn

    root = pathlib.Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=int(os.getenv("ARGUS_PORT", "8000")),
        log_level="error",
        access_log=False,
        reload=False,
    )