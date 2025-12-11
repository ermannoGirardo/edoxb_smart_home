# edoxb_smart_home

Sistema smart home con frontend React, backend FastAPI e database MongoDB.

## Architettura

Il progetto utilizza Docker Compose per orchestrare tre container interconnessi tramite una rete Docker personalizzata.

### Container e Porte

#### Frontend (React + Nginx)
- **Porta esposta**: `3000` → `80` (interno)
- **Servizio**: Applicazione React buildata e servita tramite Nginx
- **Accesso**: http://localhost:3000
- **Build**: Multi-stage Docker build (Node.js per build, Nginx per servire)
- **Configurazione**: Usa `frontend/nginx.conf` per il reverse proxy e supporto SPA

#### Backend (FastAPI)
- **Porta esposta**: `8000` → `8000` (interno)
- **Servizio**: API REST FastAPI con Uvicorn
- **Accesso**: http://localhost:8000
- **Endpoint API**: http://localhost:8000/docs (Swagger UI)
- **Database**: Si connette a MongoDB tramite la rete interna

#### MongoDB
- **Porta esposta**: `27017` → `27017` (interno)
- **Servizio**: Database NoSQL MongoDB versione 6
- **Accesso diretto**: mongodb://localhost:27017
- **Volume persistente**: `mongo_data` per la persistenza dei dati
- **Restart**: Sempre (restart: always)

### Rete Docker

Tutti i container sono connessi alla rete personalizzata `smart_home_network`:

- **Tipo**: Bridge network
- **Nome**: `smart_home_network`
- **Container connessi**:
  - `frontend`
  - `backend`
  - `mongo`

La rete permette ai container di comunicare tra loro usando i nomi dei servizi come hostname:
- Il backend può raggiungere MongoDB con: `mongodb://mongo:27017/mydb`
- Il frontend può fare richieste al backend tramite il reverse proxy configurato in nginx

### Sottoreti

La rete `smart_home_network` crea una sottorete isolata dove:
- I container possono comunicare tra loro senza esporre porte all'esterno
- Solo le porte specificate nella sezione `ports` sono accessibili dall'host
- La comunicazione interna avviene tramite i nomi dei servizi (DNS interno di Docker)

## Avvio

```bash
docker-compose up --build
```

Per eseguire in background:
```bash
docker-compose up -d --build
```

## Stop

```bash
docker-compose down
```

Per rimuovere anche i volumi:
```bash
docker-compose down -v
```