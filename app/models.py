from typing import Literal
from pydantic import BaseModel, Field


class Flag(BaseModel):
    flag: str
    description: str


class Example(BaseModel):
    cmd: str
    description: str


class Command(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")  # es. kubectl-get-pods
    tool: str                      # kubectl, helm, terraform...
    category: str                  # workloads, networking, state...
    name: str                      # "kubectl get pods"
    syntax: str                    # "kubectl get pods [-n NS] [-o wide]"
    summary: str                   # una riga
    description: str = ""
    flags: list[Flag] = []
    examples: list[Example] = []
    keywords: list[str] = []       # sinonimi IT/EN: "elenca pod", "list pods"
    related: list[str] = []        # id di altri comandi
    danger: Literal["none", "caution", "destructive"] = "none"


class CommandSummary(BaseModel):
    id: str
    tool: str
    category: str
    name: str
    summary: str
    danger: str


class CommandDetail(Command):
    related_commands: list[CommandSummary] = []


class CommandPage(BaseModel):
    items: list[CommandSummary]
    total: int
    page: int
    pages: int
    limit: int