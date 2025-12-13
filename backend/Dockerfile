FROM python:3.11-slim

WORKDIR /app

# Installa dipendenze (aiohttp già presente per HTTP, serve anche per download plugin)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia solo il core (senza sensori specifici)
COPY app/ app/

# Rimuovi route sensori specifici (verranno scaricate come plugin)
RUN rm -f app/api/routes/shelly_*.py || true

# Crea directory per i plugin (vuota all'inizio)
RUN mkdir -p /app/plugins

# Variabili d'ambiente per configurazione plugin
ENV SENSOR_REGISTRY_URL=https://raw.githubusercontent.com/edoxb/smart-home-sensors/main
ENV ENABLED_SENSORS=""

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
