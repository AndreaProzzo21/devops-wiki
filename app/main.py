import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from .models import CommandDetail, CommandPage, CommandSummary
from .store import CommandStore

store: CommandStore

# Global IP limit; search has a stricter ceiling (burst per second + minute).
# With multiple workers/replicas, in-memory counters are per-process: use Redis if global limits are needed.
BEHIND_CLOUDFLARE = os.getenv("BEHIND_CLOUDFLARE", "").lower() in {"1", "true", "yes"}


def client_ip(request: Request) -> str:
    """
    Extract the IP address used as the rate limit key.

    Behind Cloudflare Tunnel, the TCP peer is always cloudflared, so get_remote_address()
    would put ALL users in the same bucket. CF-Connecting-IP contains a single address
    (X-Forwarded-For appends: left values are chosen by the client). It should be considered
    reliable ONLY if the app is reachable EXCLUSIVELY via the tunnel (no published ports).
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


app = FastAPI(
    title="DevOps Command Wiki API",
    description="""
Centralized API for navigating, searching, and retrieving DevOps commands, deployment scripts, and infrastructure snippets.
Provides rate-limited search capabilities and paginated access to the command database.
    """,
    version="1.0.0",
    contact={
        "name": "DevOps Team"
    },
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limited(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        {"detail": "Too many requests. Please try again later."}, 
        status_code=429,
        headers={"Retry-After": "60"}
    )


@app.get(
    "/api/search", 
    response_model=list[CommandSummary],
    tags=["Search"],
    summary="Search for commands",
    description="Perform a rate-limited, full-text search across all commands. Results can be optionally filtered by tool and category."
)
@limiter.limit("10/second;120/minute")
def search(
    request: Request, 
    q: str = Query(..., min_length=1, description="The search query string. Matches against command name, summary, and description."), 
    tool: str | None = Query(None, description="Optional tool name to filter results (e.g., 'kubectl', 'docker')."),
    category: str | None = Query(None, description="Optional category name to filter results within a tool."), 
    limit: int = Query(20, ge=1, le=100, description="Maximum number of search results to return.")
):
    return store.search(q, tool, category, limit)


@app.get(
    "/api/commands", 
    response_model=CommandPage,
    tags=["Commands"],
    summary="List all commands",
    description="Retrieve a paginated list of all available commands. Can be filtered by specific tools or categories."
)
def list_commands(
    tool: str | None = Query(None, description="Filter the list by a specific tool."), 
    category: str | None = Query(None, description="Filter the list by a specific category."),
    page: int = Query(1, ge=1, description="The page number to retrieve for pagination."), 
    limit: int = Query(20, ge=1, le=100, description="Number of items to return per page.")
):
    return store.list(tool=tool, category=category, page=page, limit=limit)


@app.get(
    "/api/commands/{cmd_id}", 
    response_model=CommandDetail,
    tags=["Commands"],
    summary="Get command details",
    description="Retrieve the full details, flags, and examples of a specific command using its unique identifier.",
    responses={
        404: {"description": "Command not found"}
    }
)
def get_command(
    cmd_id: str = Path(..., description="The unique identifier of the command (e.g., 'kubectl-get-pods').")
):
    cmd = store.get(cmd_id)
    if not cmd:
        raise HTTPException(status_code=404, detail="Command not found")
    return cmd


@app.get(
    "/api/tools",
    tags=["Metadata"],
    summary="List available tools",
    description="Retrieve a complete list of all tools documented in the wiki, including their available categories and total command counts."
)
def tools():
    return store.tools()


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def serve_ui():
    """
    Serves the main Single Page Application UI.
    Hidden from the OpenAPI schema (include_in_schema=False) to keep the API documentation clean.
    """
    return FileResponse("static/index.html")