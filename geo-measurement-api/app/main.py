from fastapi import FastAPI

from app.config import settings
from app.database import Base, engine
from app.routers import files

Base.metadata.create_all(bind=engine)
settings.upload_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(files.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
