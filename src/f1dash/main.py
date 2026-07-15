from fastapi import FastAPI

from f1dash.api.routes import router as api_router
from f1dash.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="FastF1-powered API for a pit wall multi-view dashboard.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.app_env}


app.include_router(api_router)
