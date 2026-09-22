"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jobflow.api.routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="JobFlow",
        description="Reliable Concurrent Background Job Processing Platform",
        version="0.1.0",
    )
    
    # Add CORS middleware for frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Register routes
    app.include_router(router)
    
    return app


# For uvicorn command-line usage: uvicorn jobflow.app:app --reload
app = create_app()