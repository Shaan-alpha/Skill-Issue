from fastapi import FastAPI

from app.settings import VERSION

app = FastAPI(title="Skill Issue API", version=VERSION)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}
