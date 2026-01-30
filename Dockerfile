FROM python:3.12-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    libgraphite2-3 libharfbuzz0b \
  && rm -rf /var/lib/apt/lists/*

# Install tectonic (LaTeX engine)
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh \
 && mv tectonic /usr/local/bin/tectonic

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

# IMPORTANT: your FastAPI app lives in api.py (module "api") and is named "app"
CMD ["bash", "-lc", "uvicorn api:app --host 0.0.0.0 --port ${PORT}"]
