
# DevOps Command Wiki

**A practical command reference for DevOps and infrastructure operations.**

DevOps Command Wiki is a lightweight, searchable knowledge base designed to make everyday infrastructure tasks and troubleshooting easier.

**[Live API](https://api.flowingbot.com) · [Docs](https://andreaprozzo21.github.io/devops-wiki/) · [GitHub Repository](https://github.com/AndreaProzzo21/devops-wiki)**

## Features

- **Smart Search** — Quickly find commands and useful examples.
- **Command Reference** — Explore descriptions, flags, and practical usage.
- **DevOps Toolkit** — Commands for Linux, Docker, Kubernetes, and more.
- **REST API** — Access the command database programmatically.
- **Self-hosted** — Run your own instance with Docker.

## Tech Stack

- Python & FastAPI
- HTML, CSS & JavaScript
- YAML
- Docker
- OpenAPI

## Quick Start

```bash
git clone https://github.com/AndreaProzzo21/devops-wiki.git
cd devops-wiki
docker compose up -d --build
```

Then open `http://localhost:8000` in your browser.

## API

The project provides a REST API to search and retrieve commands.

| Endpoint | Description |
|---|---|
| `GET /api/search` | Search commands |
| `GET /api/commands` | Browse available commands |
| `GET /api/commands/{cmd_id}` | Get command details |
| `GET /api/tools` | List supported tools |

- **Live API:** [api.flowingbot.com](https://api.flowingbot.com)
- **OpenAPI Specification:** [openapi.json](https://andreaprozzo21.github.io/devops-wiki/openapi.json)

## Contributing

Want to improve the wiki or expand its command database?

Contributions are welcome! You can suggest improvements, add new commands, or introduce entirely new tools.

Check out CONTRIBUTING.md for contribution guidelines and feel free to open a Pull Request.
