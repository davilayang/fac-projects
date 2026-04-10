import logging

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from arxiv_rag.api.middleware import AuthMiddleware, TraceIdMiddleware
from arxiv_rag.api.routes import auth as auth_routes
from arxiv_rag.api.routes import generate, retrieve
from arxiv_rag.config import get_settings
from arxiv_rag.log import configure_logging

_STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.db_url, level=logging.getLevelName(settings.log_level))
    yield


app = FastAPI(title="arXiv RAG", version="0.1.0", lifespan=lifespan)

# Middleware runs in LIFO order — TraceId added last = outermost (runs first).
app.add_middleware(AuthMiddleware)
app.add_middleware(TraceIdMiddleware)

app.include_router(auth_routes.router)
app.include_router(retrieve.router, prefix="/apis")
app.include_router(generate.router, prefix="/apis")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui():
    return HTMLResponse(content=(_STATIC_DIR / "index.html").read_text())


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


def serve() -> None:
    import uvicorn

    uvicorn.run("arxiv_rag.api.server:app", host="0.0.0.0", port=8000, reload=True)
