from fastapi import FastAPI

from backend.app.api.recovery import router as recovery_router
from backend.app.api.recovery_actions import (
    router as recovery_actions_router,
)


app = FastAPI(
    title="RazorRecover AI",
    description="AI-powered revenue recovery platform",
    version="0.1.0",
)


app.include_router(
    recovery_router,
)

app.include_router(
    recovery_actions_router,
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "razorrecover-ai",
        "version": "0.1.0",
    }
