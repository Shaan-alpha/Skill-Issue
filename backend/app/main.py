from fastapi import FastAPI

from app.settings import settings

app = FastAPI(title="Skill Issue API", version=settings.version)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": settings.version}
