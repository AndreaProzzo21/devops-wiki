from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .models import CommandDetail, CommandSummary
from .store import CommandStore

store: CommandStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store
    store = CommandStore()  # fallisce subito se il dataset è invalido
    yield


app = FastAPI(title="DevOps Command Wiki", lifespan=lifespan)


@app.get("/api/search", response_model=list[CommandSummary])
def search(q: str = Query(..., min_length=1), tool: str | None = None,
           category: str | None = None, limit: int = Query(20, le=100)):
    return store.search(q, tool, category, limit)


@app.get("/api/commands", response_model=list[CommandSummary])
def list_commands(tool: str | None = None, category: str | None = None):
    return store.list(tool, category)


@app.get("/api/commands/{cmd_id}", response_model=CommandDetail)
def get_command(cmd_id: str):
    cmd = store.get(cmd_id)
    if not cmd:
        raise HTTPException(404, "Comando non trovato")
    return cmd


@app.get("/api/tools")
def tools():
    return store.tools()


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")
