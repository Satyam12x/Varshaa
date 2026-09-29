# VARSHA API for Render: Express/TypeScript server + the Python engine that runs the daily cycle.
FROM node:22-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive PIP_NO_CACHE_DIR=1 PYTHON=/opt/venv/bin/python PYTHONUNBUFFERED=1
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv libeccodes0 curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Same library versions the models were trained with (pickled scikit-learn models need a matching version).
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install numpy==2.2.6 pandas==2.3.3 scipy==1.15.3 scikit-learn==1.7.2 eccodes

WORKDIR /app
COPY backend/package.json backend/package-lock.json backend/
RUN npm ci --prefix backend
COPY backend backend
COPY engine engine

# Runtime data snapshot (models, districts, normals, current products) from the deploy-data branch.
# Bump DATA_REV to force a fresh download after re-running tools/deploy/publish_data.py.
ARG DATA_URL=https://github.com/Satyam12x/Varshaa/archive/refs/heads/deploy-data.tar.gz
ARG DATA_REV=1
RUN mkdir -p data && curl -fsSL "$DATA_URL?rev=$DATA_REV" | tar -xz --strip-components=1 -C data \
 && /opt/venv/bin/python -c "import eccodes, sklearn; print('eccodes', eccodes.__version__, 'sklearn', sklearn.__version__)"

ENV PORT=10000
EXPOSE 10000
CMD ["npm", "--prefix", "backend", "start"]
