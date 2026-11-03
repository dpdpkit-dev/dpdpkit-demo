# One image for the whole demo site: the React and embed bundles are built in a Node stage, the site runs on Python.
# Trixie: its Python has the safe tar extraction scripts/fetch_admin_bundle.py uses.
FROM node:22-trixie-slim AS web
RUN apt-get update && apt-get install -y --no-install-recommends python-is-python3 ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY package.json package-lock.json vite.config.js admin-bundle.version ./
RUN npm ci
COPY frontend frontend
COPY scripts scripts
COPY app/static app/static
RUN npm run build

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN useradd --system --create-home demo
COPY app app
COPY --from=web /src/app/static/dist app/static/dist
USER demo
EXPOSE 8000
# Data is in memory, so DEMO_RESET_HOURS makes the process exit on a schedule and the restart policy reseeds it.
ENV DEMO_RESET_HOURS=24 DEMO_TRUST_PROXY=0
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import os, urllib.request as u; u.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/healthz', timeout=4)"
# Hosts such as Render set PORT.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
