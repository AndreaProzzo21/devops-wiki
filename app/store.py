import re
import sqlite3
from pathlib import Path

import yaml
from pydantic import ValidationError
from rapidfuzz import fuzz, process

from .models import Command, CommandDetail, CommandPage, CommandSummary

# Cerca la cartella data/commands risalendo dalle directory o dalla root corrente
def _find_data_dir() -> Path:
    # Prova i percorsi comuni
    candidates = [
        Path(__file__).resolve().parent.parent / "data" / "commands",
        Path("data/commands"),
        Path("../data/commands")
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    return Path("data/commands") # Fallback di default

DATA_DIR = _find_data_dir()

# Pesi BM25 per colonna (stesso ordine della CREATE VIRTUAL TABLE)
COLUMNS = ["id", "name", "tool", "category", "keywords", "summary", "description", "flags", "examples"]
WEIGHTS = [0, 10.0, 3.0, 2.0, 8.0, 4.0, 1.0, 2.0, 2.0]


def _summary(c: Command) -> CommandSummary:
    return CommandSummary(id=c.id, tool=c.tool, category=c.category,
                          name=c.name, summary=c.summary, danger=c.danger)


class CommandStore:
    def __init__(self, data_dir: Path = DATA_DIR):
        self.commands: dict[str, Command] = {}
        self._load(data_dir)
        self._validate_relations()
        self._build_index()
        # ordine stabile per la navigazione: tool, poi nome (calcolato una sola volta)
        self._sorted = sorted(self.commands.values(), key=lambda c: (c.tool, c.name.lower()))

    # ---------- caricamento & validazione ----------
    def _load(self, data_dir: Path):
        errors = []
        for path in sorted(data_dir.glob("*.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
            for i, item in enumerate(raw):
                try:
                    cmd = Command(**item)
                except ValidationError as e:
                    errors.append(f"{path.name}[{i}]: {e}")
                    continue
                if cmd.id in self.commands:
                    errors.append(f"{path.name}: id duplicato '{cmd.id}'")
                self.commands[cmd.id] = cmd
        if errors:
            raise RuntimeError("Dataset non valido:\n" + "\n".join(errors))

    def _validate_relations(self):
        broken = [f"{c.id} -> {r}" for c in self.commands.values()
                  for r in c.related if r not in self.commands]
        if broken:
            raise RuntimeError("related inesistenti:\n" + "\n".join(broken))

    # ---------- indice FTS5 ----------
    def _build_index(self):
        self.db = sqlite3.connect(":memory:", check_same_thread=False)
        cols = ", ".join(COLUMNS)
        self.db.execute(
            f"CREATE VIRTUAL TABLE idx USING fts5({cols}, "
            "tokenize='unicode61 remove_diacritics 2')"
        )
        rows = []
        for c in self.commands.values():
            rows.append((
                c.id, c.name, c.tool, c.category, " ".join(c.keywords), c.summary,
                c.description,
                " ".join(f"{f.flag} {f.description}" for f in c.flags),
                " ".join(f"{e.cmd} {e.description}" for e in c.examples),
            ))
        self.db.executemany(f"INSERT INTO idx VALUES ({','.join('?' * len(COLUMNS))})", rows)
        self.db.commit()
        # vocabolario per la correzione dei refusi (nomi, tool, keyword)
        self._vocab = sorted({
            w for c in self.commands.values()
            for w in self._tokens(" ".join([c.name, c.tool, *c.keywords])) if len(w) > 2
        })

    # ---------- ricerca ----------
    @staticmethod
    def _tokens(q: str) -> list[str]:
        return re.findall(r"\w+", q.lower())

    def search(self, q: str, tool: str | None = None,
               category: str | None = None, limit: int = 20) -> list[CommandSummary]:
        tokens = self._tokens(q)
        if not tokens:
            return []
        # AND esatto -> AND/OR con refusi corretti -> OR sui termini originali
        ids = (self._fts(tokens, "AND", tool, category, limit)
               or self._fuzzy(tokens, tool, category, limit)
               or self._fts(tokens, "OR", tool, category, limit))
        return [_summary(self.commands[i]) for i in ids]

    def _fts(self, tokens, op, tool, category, limit) -> list[str]:
        match = f" {op} ".join(f'"{t}"*' for t in tokens)
        sql = f"SELECT id FROM idx WHERE idx MATCH ? "
        params: list = [match]
        if tool:
            sql += "AND tool = ? "; params.append(tool)
        if category:
            sql += "AND category = ? "; params.append(category)
        sql += f"ORDER BY bm25(idx, {', '.join(map(str, WEIGHTS))}) LIMIT ?"
        params.append(limit)
        return [r[0] for r in self.db.execute(sql, params)]

    def _fuzzy(self, tokens, tool, category, limit) -> list[str]:
        """Corregge ogni parola sul vocabolario (kubctl -> kubectl) e ripete la ricerca."""
        fixed = []
        for t in tokens:
            # parole corte o già prefisso valido (es. "kub", "up") restano invariate
            if len(t) < 4 or any(w.startswith(t) for w in self._vocab):
                fixed.append(t)
                continue
            hit = process.extractOne(t, self._vocab, scorer=fuzz.WRatio, score_cutoff=80)
            fixed.append(hit[0] if hit else t)
        if fixed == tokens:
            return []
        return self._fts(fixed, "AND", tool, category, limit) or \
               self._fts(fixed, "OR", tool, category, limit)

    # ---------- navigazione ----------
    def get(self, cmd_id: str) -> CommandDetail | None:
        c = self.commands.get(cmd_id)
        if not c:
            return None
        related = [self.commands[r] for r in c.related]
        if len(related) < 4:  # completa con comandi della stessa categoria
            extra = [x for x in self.commands.values()
                     if x.tool == c.tool and x.category == c.category
                     and x.id != c.id and x.id not in c.related]
            related += extra[: 4 - len(related)]
        return CommandDetail(**c.model_dump(), related_commands=[_summary(r) for r in related])

    def tools(self) -> list[dict]:
        out: dict[str, dict] = {}
        for c in self.commands.values():
            t = out.setdefault(c.tool, {"tool": c.tool, "count": 0, "categories": {}})
            t["count"] += 1
            t["categories"][c.category] = t["categories"].get(c.category, 0) + 1
        return sorted(out.values(), key=lambda t: t["tool"])

    def list(self, tool: str | None = None, category: str | None = None,
             page: int = 1, limit: int = 20) -> CommandPage:
        matched = [c for c in self._sorted
                   if (not tool or c.tool == tool) and (not category or c.category == category)]
        total = len(matched)
        pages = max(1, -(-total // limit))          # ceil
        page = min(max(page, 1), pages)             # clamp: mai una pagina fuori range
        start = (page - 1) * limit
        return CommandPage(items=[_summary(c) for c in matched[start:start + limit]],
                           total=total, page=page, pages=pages, limit=limit)