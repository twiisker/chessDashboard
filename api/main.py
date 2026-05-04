from fastapi import FastAPI

from api.route_analyze import router as analyze_router
from api.route_deep_dive import router as deep_dive_router
from api.route_repertoire import router as repertoire_router
from api.route_peer_report import router as peer_report_router
from api.route_style import router as style_router

app = FastAPI(
    title="Chess Analytics API",
    description="Backend API serving validated chess metrics.",
    version="1.0.0",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(analyze_router)
app.include_router(deep_dive_router)
app.include_router(repertoire_router)
app.include_router(peer_report_router)
app.include_router(style_router)
