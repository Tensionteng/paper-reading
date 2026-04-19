import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import engine, Base
from app.routers import papers
from app.config import settings

# Create data directories
os.makedirs(settings.papers_dir, exist_ok=True)
os.makedirs(settings.images_dir, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown


app = FastAPI(
    title=settings.app_name,
    description="ArXiv paper structured reading report generator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Laboratory internal use
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(papers.router, prefix="/api/papers", tags=["papers"])

# Serve uploaded images
app.mount("/images", StaticFiles(directory=settings.images_dir), name="images")

# In production, frontend static files are served from dist folder
frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend/dist")
if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        from fastapi.responses import FileResponse
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Frontend not built"}
