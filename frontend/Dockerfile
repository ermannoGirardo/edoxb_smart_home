# Stage 1: Build dell'applicazione React
FROM node:20-alpine AS builder

WORKDIR /app

# Copia i file di configurazione delle dipendenze
COPY package*.json ./

# Installa le dipendenze
RUN npm ci

# Copia il resto dei file del progetto
COPY . .

# Build dell'applicazione React
RUN npm run build

# Stage 2: Server Nginx per servire l'app buildata
FROM nginx:alpine

# Installa netcat per wait-for-backend.sh
RUN apk add --no-cache netcat-openbsd

# Copia la configurazione Nginx personalizzata
COPY nginx.conf /etc/nginx/nginx.conf

# Copia lo script di attesa
COPY wait-for-backend.sh /wait-for-backend.sh
RUN chmod +x /wait-for-backend.sh

# Copia i file buildati dallo stage builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copia configurazione sensori dalla cartella public
# Il file viene copiato da scripts/prepare-frontend-build.js prima del build
COPY --from=builder /app/public/sensors.config.json /usr/share/nginx/html/sensors.config.json

# Espone la porta 80
EXPOSE 80

# Avvia Nginx dopo aver aspettato il backend
CMD ["sh", "-c", "/wait-for-backend.sh backend 8000 nginx -g 'daemon off;'"]

