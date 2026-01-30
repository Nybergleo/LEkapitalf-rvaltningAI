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

CMD ["bash", "-lc", "uvicorn app:app --host 0.0.0.0 --port ${PORT}"]
