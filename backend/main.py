# backend/main.py
"""
ARGUS v2.2 - Provenance Graph Anomaly Detection System
Main FastAPI application with 6-layer detection pipeline
"""

import sys
import os
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


from backend.collectors.sysmon_collector import SysmonCollector

logger = setup_logger(__name__)

# ═══════════════════════════════════════════════════════════════
# LIFESPAN EVENTS
# ═══════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""

    # STARTUP
    try:
        logger.info("=" * 80)
        logger.info("🚀 ARGUS v2.2 Backend Initializing...")
        logger.info("=" * 80)

        # Initialize database (must happen before collectors that use SessionLocal)
        init_db()

        # ──────────────────────────────────────────────────────────
        # START Layer 2 Runtime Engine
        # ──────────────────────────────────────────────────────────
        app.state.layer2_engine = Layer2RuntimeEngine()
        app.state.layer2_engine.start()

        # ──────────────────────────────────────────────────────────
        # START Layer 1 Graph Ingestion
        # ──────────────────────────────────────────────────────────
        app.state.graph_worker = GraphIngestionWorker()
        app.state.graph_worker.start()


        # ──────────────────────────────────────────────────────────
        # Sysmon Collector
        # ──────────────────────────────────────────────────────────
        sm_enabled = os.getenv("ARGUS_SYSMON_ENABLED", "true").lower() == "true"
        app.state.sysmon = SysmonCollector(
            enabled=sm_enabled,
            poll_seconds=float(os.getenv("ARGUS_SYSMON_POLL_SEC", "1.0")),
            audit_enabled=os.getenv("ARGUS_AUDIT_ENABLED", "true").lower() == "true",
        )
        if sm_enabled:
            app.state.sysmon.start()
        else:
            logger.info("⏭️ SysmonCollector disabled by ARGUS_SYSMON_ENABLED=false")

        # ──────────────────────────────────────────────────────────
        # Layer 5: Learning Scheduler (weekly retraining)
        # ──────────────────────────────────────────────────────────
        try:
            from backend.layers.layer5_learning.scheduler import LearningScheduler
            LearningScheduler.init_scheduler()
        except Exception as sched_err:
            logger.warning(f"⚠️ Learning scheduler init failed (non-fatal): {sched_err}")

        logger.info("✅ Database initialized successfully")
        logger.info("✅ API running on 0.0.0.0:8000")
        logger.info("✅ Debug mode: True")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        sys.exit(1)

    yield

    # SHUTDOWN
    try:
        e = getattr(app.state, "layer2_engine", None)
        if e:
            e.stop()
    except Exception as ex:
        logger.error(f"❌ Failed to stop layer2 engine cleanly: {ex}")
    try:
        gw = getattr(app.state, "graph_worker", None)
        if gw:
            gw.stop()
    except Exception as ex:
        logger.error(f"❌ Failed to stop graph worker cleanly: {ex}")

    try:
        sm = getattr(app.state, "sysmon", None)
        if sm:
            sm.stop()
    except Exception as e:
        logger.error(f"❌ Failed to stop sysmon cleanly: {e}")

    logger.info("🛑 ARGUS Backend shutting down...")


# ═══════════════════════════════════════════════════════════════
# FASTAPI APP
# ═══════════════════════════════════════════════════════════════

app = FastAPI(
    title="ARGUS v2.2",
    description="Provenance Graph Anomaly Detection System",
    version="2.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ═══════════════════════════════════════════════════════════════
# CORS MIDDLEWARE
# ═══════════════════════════════════════════════════════════════

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════
# ROOT ENDPOINT
# ═══════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════
# INCLUDE ALL LAYER ROUTERS
# ═══════════════════════════════════════════════════════════════

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

# ═══════════════════════════════════════════════════════════════
# ERROR HANDLERS
# ═══════════════════════════════════════════════════════════════

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
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
    """Handle 500 errors"""
    logger.error(f"❌ Server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "detail": str(exc),
        },
    )

# ═══════════════════════════════════════════════════════════════
# STARTUP LOG (local dev convenience)
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Run from repository root so `backend` is importable. Prefer:
    #   python run_argus.py
    # or:
    #   uvicorn backend.main:app --host 127.0.0.1 --port 8000
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    import run_argus

    run_argus.main()