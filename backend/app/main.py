from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api import auth
from backend.app.api.recovery import router as recovery_router
from backend.app.api.recovery_actions import (
    router as recovery_actions_router,
)


app = FastAPI(
    title="RazorRecover AI",
    description="AI-powered revenue recovery platform",
    version="0.1.0",
)


# ------------------------------------------------------------------
# CORS
# ------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
# ------------------------------------------------------------------
# API ROUTERS
# ------------------------------------------------------------------

app.include_router(
    recovery_router,
)

app.include_router(
    recovery_actions_router,
)


# ------------------------------------------------------------------
# HEALTH CHECK
# ------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "razorrecover-ai",
        "version": "0.1.0",
    }