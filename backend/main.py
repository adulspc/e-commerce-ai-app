from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.exception_handlers import register_exception_handlers
from backend.routers import analysis, clustering, dataset, sessions

app = FastAPI(
    title="E-Commerce Product Clustering System",
    version="0.9.0",
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(dataset.router)
app.include_router(clustering.router)
app.include_router(analysis.router)
app.include_router(sessions.router)
