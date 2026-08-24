from fastapi import FastAPI

app = FastAPI(
    title="RazorRecover AI",
    description="AI-powered revenue recovery platform",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "razorrecover-ai",
        "version": "0.1.0",
    }