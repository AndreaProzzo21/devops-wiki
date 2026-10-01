FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN adduser --disabled-password --gecos "" appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Solo ciò che serve a runtime (niente .env, .git, test, ecc.)
COPY app/ ./app/
COPY data/ ./data/
COPY static/ ./static/

# Validazione del dataset in fase di build: se un YAML è rotto
# (schema, id duplicati, related inesistenti) l'immagine non viene nemmeno creata
RUN python -c "from app.store import CommandStore; print(len(CommandStore().commands), 'comandi OK')"

# I file restano di root (sola lettura per appuser): nulla deve scrivere su disco
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8000/api/tools')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]