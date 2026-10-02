import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from .models import CommandDetail, CommandPage, CommandSummary
from .store import CommandStore

store: CommandStore

# Limite globale per IP; la ricerca ha un tetto più stretto (burst al secondo + minuto).
# Con più worker/repliche i contatori in memoria sono per-processo: usa Redis (storage_uri) se servono limiti globali.
BEHIND_CLOUDFLARE = os.getenv("BEHIND_CLOUDFLARE", "").lower() in {"1", "true", "yes"}


def client_ip(request: Request) -> str:
    """IP usato come chiave del rate limit.

    Dietro Cloudflare Tunnel il peer TCP è sempre cloudflared, quindi get_remote_address()
    metterebbe TUTTI gli utenti nello stesso bucket. CF-Connecting-IP contiene un solo indirizzo
    (X-Forwarded-For invece accoda: i valori a sinistra li sceglie il client). Va considerato
    affidabile solo se l'app è raggiungibile ESCLUSIVAMENTE tramite il tunnel (nessuna porta pubblicata).
    """
    if BEHIND_CLOUDFLARE:
        ip = request.headers.get("cf-connecting-ip")
        if ip:
            return ip
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip, default_limits=["240/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store
    store = CommandStore()  # fails fast if the dataset is invalid
    yield


app = FastAPI(title="DevOps Command Wiki", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limited(request: Request, exc: RateLimitExceeded):
    return JSONResponse({"detail": "Too many requests"}, status_code=429,
                        headers={"Retry-After": "60"})


@app.get("/api/search", response_model=list[CommandSummary])
@limiter.limit("10/second;120/minute")
def search(request: Request, q: str = Query(..., min_length=1), tool: str | None = None,
           category: str | None = None, limit: int = Query(20, ge=1, le=100)):
    return store.search(q, tool, category, limit)


@app.get("/api/commands", response_model=CommandPage)
def list_commands(tool: str | None = None, category: str | None = None,
                  page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    return store.list(tool=tool, category=category, page=page, limit=limit)


@app.get("/api/commands/{cmd_id}", response_model=CommandDetail)
def get_command(cmd_id: str):
    cmd = store.get(cmd_id)
    if not cmd:
        raise HTTPException(404, "Command not found")
    return cmd


@app.get("/api/tools")
def tools():
    return store.tools()


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")